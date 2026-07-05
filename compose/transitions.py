import os
import subprocess
import uuid

from config import settings

_ENERGY = {"calm": 1, "dreamy": 1, "neutral": 2, "energetic": 3, "raw": 3}


def pick_transition(mood_a: str, mood_b: str) -> str:
    ea, eb = _ENERGY.get(mood_a, 2), _ENERGY.get(mood_b, 2)
    diff = abs(ea - eb)
    if diff == 0:
        return "hard-cut"  # same energy tier, even if the mood label differs (calm vs dreamy)
    if diff >= 2:
        return "whip-pan"  # big energy jump (calm/dreamy <-> energetic/raw)
    return "crossfade"  # one tier apart (either side <-> neutral)


def _run_ffmpeg(args: list, timeout: int = 120):
    result = subprocess.run(["ffmpeg", "-y", *args], capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-2000:]}")


def concat_with_transitions(segment_paths, segment_durations, moods, fps=None) -> str:
    """Joins segments using hard cuts, crossfades, or whip-pans chosen by mood shift between beats."""
    fps = fps or settings.DEFAULT_FPS
    run_id = uuid.uuid4().hex[:8]

    current = segment_paths[0]
    current_duration = segment_durations[0]
    current_is_owned = False
    step = 0

    for i in range(1, len(segment_paths)):
        transition = pick_transition(moods[i - 1], moods[i])
        next_path = segment_paths[i]
        next_duration = segment_durations[i]
        step += 1
        out_path = os.path.join(settings.TEMP_DIR, f"join_{run_id}_{step}.mp4")

        if transition == "hard-cut":
            list_path = os.path.join(settings.TEMP_DIR, f"joinlist_{run_id}_{step}.txt")
            with open(list_path, "w") as f:
                f.write(f"file '{current}'\nfile '{next_path}'\n")
            _run_ffmpeg(["-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", out_path])
            os.remove(list_path)
            new_duration = current_duration + next_duration
        else:
            overlap = min(0.4, next_duration * 0.3, current_duration * 0.3, 1.0)
            offset = max(0.0, current_duration - overlap)
            xfade_name = "fade" if transition == "crossfade" else "slideleft"
            _run_ffmpeg([
                "-i", current,
                "-i", next_path,
                "-filter_complex",
                f"[0:v][1:v]xfade=transition={xfade_name}:duration={overlap}:offset={offset},format=yuv420p[v]",
                "-map", "[v]",
                "-r", str(fps),
                "-c:v", "libx264", "-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p",
                out_path,
            ])
            new_duration = current_duration + next_duration - overlap

        if current_is_owned and os.path.exists(current):
            os.remove(current)

        current = out_path
        current_duration = new_duration
        current_is_owned = True

    return current
