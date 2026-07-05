from typing import List

import cv2
import numpy as np

from config import settings


def _sample_frames(video_path: str):
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    if total < 3:
        cap.release()
        return frames
    for idx in (int(total * 0.1), int(total * 0.5), int(total * 0.9)):
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            frames.append(frame)
    cap.release()
    return frames


def score_clip(video_path: str) -> float:
    """Returns 0-1 quality score: resolution (0.3) + sharpness (0.4) + brightness (0.3)."""
    frames = _sample_frames(video_path)
    if not frames:
        return 0.0

    min_dim = min(settings.DEFAULT_RESOLUTION)  # 1080
    per_frame_scores = []

    for frame in frames:
        h, w = frame.shape[:2]

        # Resolution: full credit at >=1080 on the short side, scaled down below that.
        res_score = min(min(h, w) / min_dim, 1.0)

        # Sharpness: Laplacian variance on grayscale. >150 = crisp, <40 = blurry.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        fm = cv2.Laplacian(gray, cv2.CV_64F).var()
        sharp_score = max(0.0, min(fm / 150.0, 1.0))

        # Brightness: penalize too dark or blown out. Ideal mean ~90-180 (0-255).
        mean_brightness = gray.mean()
        if mean_brightness < 30 or mean_brightness > 230:
            bright_score = 0.0
        elif mean_brightness < 60:
            bright_score = (mean_brightness - 30) / 30
        elif mean_brightness > 200:
            bright_score = (230 - mean_brightness) / 30
        else:
            bright_score = 1.0

        per_frame_scores.append(res_score * 0.3 + sharp_score * 0.4 + bright_score * 0.3)

    return sum(per_frame_scores) / len(per_frame_scores)


def is_acceptable(video_path: str, min_score: float = 0.4) -> bool:
    return score_clip(video_path) >= min_score


def _hex_to_rgb(hex_color: str):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def match_palette(video_path: str, target_hex_colors: List[str]) -> float:
    """Returns 0-1 score for how close the clip's dominant color is to the target palette."""
    frames = _sample_frames(video_path)
    if not frames or not target_hex_colors:
        return 0.5  # neutral score when there's nothing to compare against

    targets = np.array([_hex_to_rgb(c) for c in target_hex_colors], dtype=float)
    max_distance = 441.7  # euclidean distance across the full RGB cube (sqrt(255^2*3))

    scores = []
    for frame in frames:
        mean_bgr = frame.reshape(-1, 3).mean(axis=0)
        mean_rgb = mean_bgr[::-1]
        distances = np.linalg.norm(targets - mean_rgb, axis=1)
        min_distance = distances.min()
        scores.append(max(0.0, 1 - min_distance / max_distance))

    return sum(scores) / len(scores)


def motion_stability(video_path: str) -> float:
    """Returns 0-1 score; high variance in optical flow between sampled frames indicates shaky footage."""
    frames = _sample_frames(video_path)
    if len(frames) < 3:
        return 0.5

    grays = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) for f in frames]
    grays = [cv2.resize(g, (320, 568)) for g in grays]

    magnitudes = []
    for a, b in ((grays[0], grays[1]), (grays[1], grays[2])):
        flow = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        magnitudes.append(mag.mean())

    variance = float(np.var(magnitudes))
    return max(0.0, 1 - min(variance / 4.0, 1.0))


if __name__ == "__main__":
    import sys
    print(f"score: {score_clip(sys.argv[1]):.3f}")
