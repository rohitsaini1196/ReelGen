import requests
from typing import List
from config import settings
from models import Asset


def search(query: str, per_page: int = 6) -> List[Asset]:
    if not settings.PIXABAY_API_KEY:
        return []

    url = "https://pixabay.com/api/videos/"
    params = {
        "key": settings.PIXABAY_API_KEY,
        "q": query,
        "per_page": max(per_page, 3),  # Pixabay minimum is 3
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"   Pixabay search error for '{query}': {e}")
        return []

    assets = []
    for hit in data.get("hits", []):
        videos = hit.get("videos", {})
        # Prefer largest vertical-ish rendition available; Pixabay video tiers: large, medium, small, tiny
        best = None
        for tier in ("large", "medium", "small", "tiny"):
            v = videos.get(tier)
            if v and v.get("url"):
                best = v
                break

        if best:
            assets.append(Asset(
                id=str(hit["id"]),
                source="pixabay",
                url=best["url"],
                duration=hit.get("duration", 0.0),
            ))
    return assets[:per_page]
