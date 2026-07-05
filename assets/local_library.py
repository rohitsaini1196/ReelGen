import json
import os
import shutil
import subprocess
from typing import List, Optional

import cv2

from config import settings
from models import Asset
from assets import clip_matcher

INDEX_PATH = os.path.join(settings.LIBRARY_DIR, "index.json")


def _load_index() -> List[dict]:
    if not os.path.exists(INDEX_PATH):
        return []
    with open(INDEX_PATH) as f:
        return json.load(f)


def _save_index(entries: List[dict]):
    with open(INDEX_PATH, "w") as f:
        json.dump(entries, f, indent=2)


def _probe_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def _extract_metadata(path: str):
    cap = cv2.VideoCapture(path)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    dominant_colors = []
    if total > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(total * 0.5))
        ret, frame = cap.read()
        if ret:
            small = cv2.resize(frame, (50, 50))
            pixels = small.reshape(-1, 3).astype(float)
            k = 3
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
            _, labels, centers = cv2.kmeans(pixels.astype("float32"), k, None, criteria, 5, cv2.KMEANS_RANDOM_CENTERS)
            for c in centers:
                b, g, r = c.astype(int)
                dominant_colors.append(f"#{r:02x}{g:02x}{b:02x}")

    cap.release()
    return {"width": w, "height": h, "dominant_colors": dominant_colors}


def add_clip(file_path: str, tags: List[str]) -> dict:
    filename = os.path.basename(file_path)
    dest = os.path.join(settings.LIBRARY_DIR, filename)
    if os.path.abspath(file_path) != os.path.abspath(dest):
        shutil.copyfile(file_path, dest)

    entry = {
        "filename": filename,
        "tags": tags,
        "duration": _probe_duration(dest),
        **_extract_metadata(dest),
    }
    entries = _load_index()
    entries = [e for e in entries if e["filename"] != filename]
    entries.append(entry)
    _save_index(entries)
    return entry


def search_library(description: str, min_score: float = 0.5) -> Optional[Asset]:
    """Checks the local library for a semantic match before falling back to stock APIs."""
    entries = _load_index()
    best_entry, best_path, best_score = None, None, 0.0

    for entry in entries:
        path = os.path.join(settings.LIBRARY_DIR, entry["filename"])
        if not os.path.exists(path):
            continue
        score = clip_matcher.match_score(path, description)
        if score > best_score:
            best_entry, best_path, best_score = entry, path, score

    if best_entry and best_score >= min_score:
        return Asset(
            id=best_entry["filename"],
            source="local",
            local_path=best_path,
            duration=best_entry["duration"],
            clip_score=best_score,
            qa_score=1.0,
            final_score=best_score,
        )
    return None


if __name__ == "__main__":
    import sys
    print(json.dumps(_load_index(), indent=2))
