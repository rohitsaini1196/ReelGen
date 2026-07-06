import os
import random
import subprocess
from dataclasses import dataclass
from typing import List, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_LOCAL_FFMPEG = os.path.join(_HERE, "bin", "ffmpeg")
FFMPEG = _LOCAL_FFMPEG if os.path.exists(_LOCAL_FFMPEG) else "ffmpeg"

RESOLUTION = (1080, 1920)
MIN_SLICE = 4.0  # short enough that 8-20s videos still get more than one cut
MAX_SLICE = 10.0
MAX_FILE_BYTES = 50 * 1024 * 1024  # Instagram + Telegram bot API cap


@dataclass
class Slice:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start


def pick_gameplay_source(library_dir: str = None) -> str:
    library_dir = library_dir or os.path.join(_HERE, "library", "gameplay")
    candidates = [
        os.path.join(library_dir, f)
        for f in os.listdir(library_dir)
        if f.lower().endswith((".mp4", ".mov"))
    ]
    if not candidates:
        raise RuntimeError(f"no gameplay footage found in {library_dir}")
    return random.choice(candidates)


def probe_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
        capture_output=True, text=True,
    )
    if out.returncode != 0 or not out.stdout.strip():
        raise RuntimeError(f"could not probe duration of {path}: {out.stderr.strip()}")
    return float(out.stdout.strip())


def _overlaps(a: Tuple[float, float], b: Tuple[float, float]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def pick_slices(
    source_duration: float,
    target_duration: float,
    min_len: float = MIN_SLICE,
    max_len: float = MAX_SLICE,
    seed: int = None,
) -> List[Slice]:
    """Pick random, non-overlapping slices from the source that sum to target_duration."""
    rng = random.Random(seed)
    used: List[Tuple[float, float]] = []
    slices: List[Slice] = []
    total = 0.0
    attempts = 0
    max_attempts = 500

    while total < target_duration - 0.05 and attempts < max_attempts:
        attempts += 1
        remaining = target_duration - total
        length = rng.uniform(min_len, max_len)
        if remaining < min_len:
            length = remaining
        length = min(length, source_duration, max(remaining, 0.1))
        if length <= 0:
            break
        start_max = source_duration - length
        if start_max <= 0:
            continue
        start = rng.uniform(0, start_max)
        candidate = (start, start + length)
        if any(_overlaps(candidate, r) for r in used):
            continue
        used.append(candidate)
        slices.append(Slice(candidate[0], candidate[1]))
        total += length

    if total < target_duration - 0.5:
        # source is too short to fill the target without overlap (e.g. a long story over
        # short gameplay footage) - loop-wrap instead of crashing: allow overlaps/repeats to
        # cover the remaining duration, sourced independently at random each time.
        while total < target_duration - 0.05:
            remaining = target_duration - total
            length = min(rng.uniform(min_len, max_len), source_duration, max(remaining, 0.1)) if remaining >= min_len else remaining
            length = max(length, 0.1)
            start_max = max(source_duration - length, 0.0)
            start = rng.uniform(0, start_max) if start_max > 0 else 0.0
            slices.append(Slice(start, start + length))
            total += length

    return slices


def _run_ffmpeg(cmd: List[str]):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-2000:]}")


def _enforce_size_limit(path: str, max_bytes: int = MAX_FILE_BYTES, max_attempts: int = 3):
    """Instagram (and Telegram's bot API) cap uploads at 50MB. Re-encode at a lower bitrate if over."""
    crf = 20
    for _ in range(max_attempts):
        if os.path.getsize(path) <= max_bytes:
            return
        crf += 4
        tmp_path = path + ".compressed.mp4"
        _run_ffmpeg([
            FFMPEG, "-y", "-i", path,
            "-c:v", "libx264", "-crf", str(crf), "-preset", "slow", "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            tmp_path,
        ])
        os.replace(tmp_path, path)
    if os.path.getsize(path) > max_bytes:
        print(f"Warning: {path} still over {max_bytes // (1024*1024)}MB after {max_attempts} compression attempts")


def build_video(
    gameplay_path: str,
    audio_path: str,
    ass_path: str,
    out_path: str,
    target_duration: float,
    resolution: Tuple[int, int] = RESOLUTION,
    seed: int = None,
) -> str:
    source_duration = probe_duration(gameplay_path)
    slices = pick_slices(source_duration, target_duration, seed=seed)

    fonts_dir = os.path.join(_HERE, "..", "fonts")
    w, h = resolution

    filter_parts = []
    concat_inputs = []
    for i, sl in enumerate(slices):
        filter_parts.append(
            f"[0:v]trim=start={sl.start:.3f}:end={sl.end:.3f},setpts=PTS-STARTPTS[v{i}]"
        )
        concat_inputs.append(f"[v{i}]")

    concat_str = "".join(concat_inputs) + f"concat=n={len(slices)}:v=1:a=0[vcat]"
    # landscape source -> portrait target: scale to cover target height, then center-crop width
    scale_crop = f"[vcat]scale=-2:{h},crop={w}:{h}[vscaled]"
    ass_filter = f"[vscaled]ass={ass_path}:fontsdir={fonts_dir}[vout]"

    filter_complex = ";".join(filter_parts + [concat_str, scale_crop, ass_filter])

    cmd = [
        FFMPEG, "-y",
        "-i", gameplay_path,
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "1:a",
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        out_path,
    ]
    _run_ffmpeg(cmd)
    _enforce_size_limit(out_path)
    return out_path


if __name__ == "__main__":
    import sys
    gameplay = sys.argv[1] if len(sys.argv) > 1 else "library/gameplay/4.mp4"
    audio = sys.argv[2] if len(sys.argv) > 2 else "/tmp/brainrot_full_story.wav"
    ass = sys.argv[3] if len(sys.argv) > 3 else "/tmp/brainrot_captions.ass"
    out = sys.argv[4] if len(sys.argv) > 4 else "/tmp/brainrot_final.mp4"
    dur = probe_duration(audio)
    print(f"target duration: {dur:.2f}s")
    build_video(gameplay, audio, ass, out, dur)
    print(f"wrote {out}")
