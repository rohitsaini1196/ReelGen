import requests
from typing import List
from config import settings
from models import Asset


def search(query: str, per_page: int = 6) -> List[Asset]:
    if not settings.PEXELS_API_KEY:
        return []

    url = "https://api.pexels.com/videos/search"
    headers = {"Authorization": settings.PEXELS_API_KEY}
    params = {"query": query, "orientation": "portrait", "per_page": per_page}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"   Pexels search error for '{query}': {e}")
        return []

    assets = []
    for v in data.get("videos", []):
        video_files = v.get("video_files", [])
        best_file = next((f for f in video_files if f.get("width") == 1080 and f.get("height") == 1920), None)
        if not best_file:
            best_file = next((f for f in video_files if (f.get("height") or 0) >= 1080), None)
        if not best_file and video_files:
            best_file = video_files[0]

        if best_file:
            assets.append(Asset(
                id=str(v["id"]),
                source="pexels",
                url=best_file["link"],
                duration=v.get("duration", 0.0),
            ))
    return assets
