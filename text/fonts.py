import os
from config import settings

# category -> (font file, variable-font instance name or None for static fonts)
FONT_REGISTRY = {
    "clean": ("PlusJakartaSans.ttf", "Bold"),
    "editorial": ("PlayfairDisplay.ttf", "Bold"),
    "bold-impact": ("Montserrat.ttf", "Black"),
    "handwritten": ("Caveat.ttf", "Bold"),
    "impact-static": ("BebasNeue-Regular.ttf", None),
}

# beat.mood -> font category
MOOD_FONT_MAP = {
    "calm": "editorial",
    "dreamy": "handwritten",
    "energetic": "bold-impact",
    "raw": "impact-static",
    "neutral": "clean",
}


def category_for_mood(mood: str) -> str:
    return MOOD_FONT_MAP.get(mood, "clean")


def font_path(category: str) -> str:
    filename, _ = FONT_REGISTRY.get(category, FONT_REGISTRY["clean"])
    return os.path.join(settings.FONTS_DIR, filename)


def font_variation(category: str):
    _, variation = FONT_REGISTRY.get(category, FONT_REGISTRY["clean"])
    return variation
