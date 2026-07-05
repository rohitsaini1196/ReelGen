import os
import requests
from typing import List, Optional

from config import settings
from models import Asset, Beat
from assets.sources import pexels, pixabay
from assets import visual_qa, clip_matcher, local_library

# Paths selected by earlier beats in this run - protected from cleanup below,
# since the same clip can surface as a candidate for more than one beat.
_selected_paths = set()


def _download(asset: Asset) -> Optional[str]:
    if not asset.url:
        return None
    filename = f"{asset.source}_{asset.id}.mp4"
    dest_path = os.path.join(settings.TEMP_DIR, filename)
    if os.path.exists(dest_path):
        return dest_path
    try:
        response = requests.get(asset.url, stream=True, timeout=60)
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return dest_path
    except Exception as e:
        print(f"   Download failed for {asset.source}_{asset.id}: {e}")
        return None


def _gather_candidates(beat: Beat) -> List[Asset]:
    seen = set()
    candidates: List[Asset] = []
    queries = beat.search_queries or [beat.visual_description or beat.caption]

    per_query = max(2, settings.CANDIDATES_PER_BEAT // max(len(queries), 1))
    for query in queries:
        for source_fn in (pexels.search, pixabay.search):
            for asset in source_fn(query, per_page=per_query):
                key = (asset.source, asset.id)
                if key not in seen:
                    seen.add(key)
                    candidates.append(asset)
        if len(candidates) >= settings.CANDIDATES_PER_BEAT:
            break

    return candidates[: settings.CANDIDATES_PER_BEAT]


def _score_candidates(candidates: List[Asset], description: str, palette: Optional[List[str]]) -> List[Asset]:
    scored: List[Asset] = []
    for asset in candidates:
        local_path = _download(asset)
        if not local_path:
            continue

        qa_score = visual_qa.score_clip(local_path)
        clip_score = clip_matcher.match_score(local_path, description)
        palette_score = visual_qa.match_palette(local_path, palette or [])
        motion_score = visual_qa.motion_stability(local_path)
        final_score = (
            settings.CLIP_MATCH_WEIGHT * clip_score
            + settings.VISUAL_QA_WEIGHT * qa_score
            + settings.PALETTE_MATCH_WEIGHT * palette_score
            + settings.MOTION_STABILITY_WEIGHT * motion_score
        )

        asset.local_path = local_path
        asset.qa_score = qa_score
        asset.clip_score = clip_score
        asset.final_score = final_score
        scored.append(asset)
    return scored


def fulfill_beat(beat: Beat, palette: Optional[List[str]] = None, director=None) -> Optional[Asset]:
    """Searches, downloads, scores candidates for a beat, and returns the best match."""
    print(f"Fulfilling beat '{beat.caption}' ({beat.search_queries})")

    description = beat.visual_description or beat.caption
    local_asset = local_library.search_library(description)
    if local_asset:
        print(f"   Using local library clip: {local_asset.id} (score={local_asset.final_score:.2f})")
        return local_asset

    candidates = _gather_candidates(beat)
    if not candidates:
        print(f"   No candidates found for '{beat.caption}'")
        return None

    scored = _score_candidates(candidates, description, palette)
    if not scored:
        return None

    scored.sort(key=lambda a: a.final_score, reverse=True)
    best = scored[0]

    if director and best.clip_score < settings.WEAK_MATCH_THRESHOLD:
        print(f"   Weak semantic match (clip={best.clip_score:.2f}), trying fallback queries...")
        fallback_queries = director.generate_fallback_queries(beat.caption, description, beat.search_queries)
        if fallback_queries:
            seen = {(a.source, a.id) for a in candidates}
            fallback_candidates = []
            for query in fallback_queries:
                for source_fn in (pexels.search, pixabay.search):
                    for asset in source_fn(query, per_page=3):
                        key = (asset.source, asset.id)
                        if key not in seen:
                            seen.add(key)
                            fallback_candidates.append(asset)

            fallback_scored = _score_candidates(fallback_candidates, description, palette)
            if fallback_scored:
                scored.extend(fallback_scored)
                scored.sort(key=lambda a: a.final_score, reverse=True)
                best = scored[0]

    _selected_paths.add(best.local_path)

    # Discard downloads of clips that weren't selected, to save disk space.
    # Skip anything already claimed by an earlier beat in this run.
    for asset in scored[1:]:
        if asset.local_path and asset.local_path not in _selected_paths and os.path.exists(asset.local_path):
            os.remove(asset.local_path)

    if best.final_score < settings.MIN_ACCEPT_SCORE:
        print(f"   Best candidate below threshold ({best.final_score:.2f}), using anyway")

    print(f"   Selected {best.source}_{best.id} (final={best.final_score:.2f}, clip={best.clip_score:.2f}, qa={best.qa_score:.2f})")
    return best


if __name__ == "__main__":
    test_beat = Beat(
        caption="Test",
        search_queries=["turquoise water overhead drone shot"],
        visual_description="aerial drone shot of turquoise ocean water",
    )
    result = fulfill_beat(test_beat)
    print(result)
