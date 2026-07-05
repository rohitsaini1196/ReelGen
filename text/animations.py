def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def ease_out_back(t: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def envelope(frame_idx: int, total_frames: int, entrance_frames: int, exit_frames: int, style: str):
    """Returns (alpha 0-1, y_offset_px, scale) for a given output frame."""
    if frame_idx < entrance_frames:
        t = (frame_idx + 1) / entrance_frames
        if style == "pop-scale":
            return min(1.0, t), 0, max(0.0, ease_out_back(t))
        return ease_out_cubic(t), int((1 - ease_out_cubic(t)) * 20), 1.0

    exit_start = total_frames - exit_frames
    if exit_frames > 0 and frame_idx >= exit_start:
        t = (frame_idx - exit_start + 1) / exit_frames
        return max(0.0, 1 - t), 0, 1.0

    return 1.0, 0, 1.0


def animation_for_mood(mood: str) -> str:
    return "pop-scale" if mood in ("energetic", "raw") else "fade-up"
