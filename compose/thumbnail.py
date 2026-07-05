import cv2
import numpy as np


def extract_thumbnail(video_path: str, out_path: str, samples: int = 8) -> str:
    """Picks the sharpest frame across the reel as the IG thumbnail candidate."""
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    best_frame, best_score = None, -1.0
    for idx in np.linspace(0, max(total - 1, 0), samples, dtype=int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
        ret, frame = cap.read()
        if not ret:
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if score > best_score:
            best_score, best_frame = score, frame

    cap.release()
    if best_frame is None:
        raise RuntimeError(f"Could not extract any frame from {video_path}")

    cv2.imwrite(out_path, best_frame)
    return out_path
