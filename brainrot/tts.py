import os
os.environ.setdefault("HF_HUB_OFFLINE", "1")  # model already cached - skip network check (seen hanging)

import numpy as np
import soundfile as sf
from kokoro import KPipeline

from brainrot.text_norm import normalize_for_tts

SAMPLE_RATE = 24000
DEFAULT_VOICE = "am_adam"  # energetic male narrator - good fit for brainrot reads


class KokoroTTS:
    def __init__(self, lang_code: str = "a", voice: str = DEFAULT_VOICE):
        self.pipeline = KPipeline(lang_code=lang_code)
        self.voice = voice

    def synthesize(self, spoken_script: str, out_path: str, voice: str = None) -> float:
        """Synthesize spoken_script to a wav file at out_path. Returns duration in seconds."""
        clean_text = normalize_for_tts(spoken_script)
        chunks = []
        for _, _, audio in self.pipeline(clean_text, voice=voice or self.voice):
            chunks.append(audio)
        if not chunks:
            raise RuntimeError("Kokoro produced no audio for input text")
        full_audio = np.concatenate(chunks)
        sf.write(out_path, full_audio, SAMPLE_RATE)
        return len(full_audio) / SAMPLE_RATE


if __name__ == "__main__":
    import sys
    tts = KokoroTTS()
    text = sys.argv[1] if len(sys.argv) > 1 else "This is a test of the Kokoro text to speech system."
    duration = tts.synthesize(text, "/tmp/brainrot_tts_test.wav")
    print(f"wrote /tmp/brainrot_tts_test.wav, duration={duration:.2f}s")
