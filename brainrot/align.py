import os
# torch and ctranslate2 both bundle their own OpenMP runtime. KMP_DUPLICATE_LIB_OK alone only
# suppresses the abort - the two thread pools still deadlock under real contention (seen hanging
# forever in __kmp_suspend_64 on a real CLI run). Forcing single-threaded OMP avoids the pool
# entirely rather than trying to make two runtimes share one.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
# model is already cached locally - skip the network round-trip to check for updates,
# which was observed hanging (blocked in select_poll_poll) on this network.
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import re
import difflib
from dataclasses import dataclass
from typing import List

from faster_whisper import WhisperModel

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"\S+")
_NORM_RE = re.compile(r"[^\w']")


@dataclass
class WordTiming:
    word: str
    start: float
    end: float


def _normalize(word: str) -> str:
    return _NORM_RE.sub("", word).lower()


def _split_sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def _split_words(text: str) -> List[str]:
    return _WORD_RE.findall(text)


class WordAligner:
    def __init__(self, model_size: str = "small.en"):
        self.model = WhisperModel(model_size, device="cpu", compute_type="int8", cpu_threads=1, num_workers=1)

    def transcribe_words(self, wav_path: str) -> List[WordTiming]:
        segments, _ = self.model.transcribe(wav_path, word_timestamps=True, beam_size=1)
        words = []
        for seg in segments:
            for w in seg.words:
                words.append(WordTiming(w.word.strip(), w.start, w.end))
        return words

    def align_spoken_tokens(self, whisper_words: List[WordTiming], spoken_tokens: List[str]) -> List[WordTiming]:
        """Assign a timestamp to every spoken_script token, using whisper's timing as ground
        truth but our own known spoken text (whisper's transcript may mis-hear individual words)."""
        whisper_norm = [_normalize(w.word) for w in whisper_words]
        spoken_norm = [_normalize(t) for t in spoken_tokens]

        matcher = difflib.SequenceMatcher(a=whisper_norm, b=spoken_norm, autojunk=False)
        out: List[WordTiming] = [None] * len(spoken_tokens)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for k in range(i2 - i1):
                    w = whisper_words[i1 + k]
                    out[j1 + k] = WordTiming(spoken_tokens[j1 + k], w.start, w.end)
            elif tag == "replace":
                # same count -> pair up directly; different count -> spread across the whisper time span
                span_start = whisper_words[i1].start if i1 < len(whisper_words) else _prev_end(out, j1)
                span_end = whisper_words[i2 - 1].end if i2 > i1 else span_start
                self._fill_span(out, spoken_tokens, j1, j2, span_start, span_end)
            elif tag == "insert":
                # spoken has tokens whisper never heard (rare) - interpolate inside neighboring span
                span_start = whisper_words[i1].start if i1 < len(whisper_words) else _prev_end(out, j1)
                span_end = whisper_words[i1].start if i1 < len(whisper_words) else span_start
                self._fill_span(out, spoken_tokens, j1, j2, span_start, span_end)
            # tag == "delete": whisper heard extra words not in spoken_script - drop them, no output slots to fill

        # any unfilled gaps (shouldn't normally happen): interpolate from neighbors
        self._patch_gaps(out, spoken_tokens)
        return out

    @staticmethod
    def _fill_span(out: List, tokens: List[str], j1: int, j2: int, span_start: float, span_end: float):
        n = j2 - j1
        if n <= 0:
            return
        if span_end <= span_start:
            span_end = span_start + 0.05 * n
        lengths = [max(len(tokens[j]), 1) for j in range(j1, j2)]
        total = sum(lengths)
        cursor = span_start
        for idx, j in enumerate(range(j1, j2)):
            dur = (lengths[idx] / total) * (span_end - span_start)
            out[j] = WordTiming(tokens[j], cursor, cursor + dur)
            cursor += dur

    @staticmethod
    def _patch_gaps(out: List, tokens: List[str]):
        for i, item in enumerate(out):
            if item is None:
                prev_end = out[i - 1].end if i > 0 and out[i - 1] else 0.0
                next_start = None
                for j in range(i + 1, len(out)):
                    if out[j] is not None:
                        next_start = out[j].start
                        break
                if next_start is None:
                    next_start = prev_end + 0.3
                out[i] = WordTiming(tokens[i], prev_end, max(next_start, prev_end + 0.05))

    def map_to_display(self, spoken_timed: List[WordTiming], spoken_script: str, display_script: str) -> List[WordTiming]:
        """Map spoken-token timestamps onto display_script tokens, sentence by sentence.
        Sentence counts must match (enforced by the Sprint-1 prompt). Within a sentence: if
        token counts match, map 1:1; if they differ (numbers/currency expanded in spoken form),
        distribute display tokens proportionally across that sentence's time span."""
        spoken_sentences = _split_sentences(spoken_script)
        display_sentences = _split_sentences(display_script)

        if len(spoken_sentences) != len(display_sentences):
            # mismatch the Sprint-1 prompt was supposed to prevent - fall back to a single
            # whole-text proportional split rather than crashing
            display_tokens = _split_words(display_script)
            span_start = spoken_timed[0].start if spoken_timed else 0.0
            span_end = spoken_timed[-1].end if spoken_timed else 1.0
            result = [None] * len(display_tokens)
            self._fill_span(result, display_tokens, 0, len(display_tokens), span_start, span_end)
            return result

        result: List[WordTiming] = []
        spoken_cursor = 0
        for spoken_sent, display_sent in zip(spoken_sentences, display_sentences):
            spoken_toks = _split_words(spoken_sent)
            display_toks = _split_words(display_sent)
            sent_timed = spoken_timed[spoken_cursor: spoken_cursor + len(spoken_toks)]
            spoken_cursor += len(spoken_toks)

            if not sent_timed:
                continue

            if len(spoken_toks) == len(display_toks):
                for tok, timing in zip(display_toks, sent_timed):
                    result.append(WordTiming(tok, timing.start, timing.end))
            else:
                span_start = sent_timed[0].start
                span_end = sent_timed[-1].end
                slots = [None] * len(display_toks)
                self._fill_span(slots, display_toks, 0, len(display_toks), span_start, span_end)
                result.extend(slots)

        return result

    def align(self, wav_path: str, spoken_script: str, display_script: str) -> List[WordTiming]:
        whisper_words = self.transcribe_words(wav_path)
        spoken_tokens = _split_words(spoken_script)
        spoken_timed = self.align_spoken_tokens(whisper_words, spoken_tokens)
        return self.map_to_display(spoken_timed, spoken_script, display_script)


def _prev_end(out: List, j: int) -> float:
    for k in range(j - 1, -1, -1):
        if out[k] is not None:
            return out[k].end
    return 0.0


if __name__ == "__main__":
    import sys
    print("loading model...", flush=True)
    aligner = WordAligner(model_size="tiny.en")
    print("model loaded, transcribing + aligning...", flush=True)
    wav = sys.argv[1] if len(sys.argv) > 1 else "/tmp/brainrot_full_story.wav"
    spoken = sys.argv[2] if len(sys.argv) > 2 else open("/tmp/spoken.txt").read()
    display = sys.argv[3] if len(sys.argv) > 3 else open("/tmp/display.txt").read()
    timed = aligner.align(wav, spoken, display)
    print(f"done, {len(timed)} display tokens", flush=True)
    for t in timed:
        print(f"{t.start:6.2f} - {t.end:6.2f}  {t.word}", flush=True)
