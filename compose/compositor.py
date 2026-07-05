import os
import shutil
import subprocess
import uuid

from config import settings
from models import ReelPlan
from style.presets import get_preset
from style.color_grade import build_filter_chain
from style.motion import build_zoompan
from text.renderer import render_beat_overlay
from compose.transitions import concat_with_transitions


def _run_ffmpeg(args: list, timeout: int = 120):
    result = subprocess.run(
        ["ffmpeg", "-y", *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-2000:]}")


def _grade_and_frame(input_path: str, duration: float, preset: dict, out_path: str):
    w, h = settings.DEFAULT_RESOLUTION
    fps = settings.DEFAULT_FPS
    vf = (
        f"scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},setsar=1,fps={fps},"
        f"{build_filter_chain(preset)},"
        f"{build_zoompan(duration, fps, w, h)}"
    )
    _run_ffmpeg([
        "-i", input_path,
        "-t", str(duration),
        "-vf", vf,
        "-an",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "slow",
        "-pix_fmt", "yuv420p",
        out_path,
    ])


def _overlay_text(base_path: str, overlay_path: str, out_path: str):
    _run_ffmpeg([
        "-i", base_path,
        "-i", overlay_path,
        "-filter_complex", "[0:v][1:v]overlay=0:0:format=auto[v]",
        "-map", "[v]",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "slow",
        "-pix_fmt", "yuv420p",
        out_path,
    ])


def assemble_reel(plan: ReelPlan, output_filename: str = "reel.mp4") -> str:
    """Assembles the final reel: color grade + motion + text overlay per beat, mood-aware transitions between beats."""
    run_id = uuid.uuid4().hex[:8]
    preset = get_preset(plan.style_preset)

    beats = [b for b in plan.all_beats() if b.asset and b.asset.local_path]
    if not beats:
        raise ValueError("No clips were assembled - every beat is missing an asset")

    segment_paths = []
    segment_durations = []
    segment_moods = []
    scratch_files = []

    for i, beat in enumerate(beats):
        graded_path = os.path.join(settings.TEMP_DIR, f"graded_{run_id}_{i}.mp4")
        _grade_and_frame(beat.asset.local_path, beat.duration, preset, graded_path)
        scratch_files.append(graded_path)

        # Weak footage match: footage won't visually reinforce the caption, so make text the anchor instead.
        text_style = "pill" if beat.asset.clip_score < 0.4 else beat.text_style

        overlay_path = render_beat_overlay(
            beat.caption, beat.mood, beat.text_position, text_style, beat.duration
        )
        scratch_files.append(overlay_path)

        final_seg_path = os.path.join(settings.TEMP_DIR, f"seg_{run_id}_{i}.mp4")
        _overlay_text(graded_path, overlay_path, final_seg_path)
        scratch_files.append(final_seg_path)

        segment_paths.append(final_seg_path)
        segment_durations.append(beat.duration)
        segment_moods.append(beat.mood)

    if len(segment_paths) == 1:
        joined_path = segment_paths[0]
    else:
        joined_path = concat_with_transitions(segment_paths, segment_durations, segment_moods)
        scratch_files.append(joined_path)

    output_path = os.path.join(settings.OUTPUT_DIR, output_filename)
    shutil.copyfile(joined_path, output_path)

    for f in scratch_files:
        if f != output_path and os.path.exists(f):
            os.remove(f)

    _enforce_size_limit(output_path)
    return output_path


def _enforce_size_limit(path: str, max_bytes: int = 50 * 1024 * 1024, max_attempts: int = 3):
    """Instagram (and Telegram's bot API) cap uploads at 50MB. Re-encode at a lower bitrate if we're over."""
    crf = 20
    for _ in range(max_attempts):
        if os.path.getsize(path) <= max_bytes:
            return
        crf += 4
        tmp_path = path + ".compressed.mp4"
        _run_ffmpeg([
            "-i", path,
            "-c:v", "libx264", "-crf", str(crf), "-preset", "slow", "-pix_fmt", "yuv420p",
            tmp_path,
        ])
        os.replace(tmp_path, path)


if __name__ == "__main__":
    pass
