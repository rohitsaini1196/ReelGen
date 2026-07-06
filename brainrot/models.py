from typing import List
from pydantic import BaseModel, Field, field_validator

MOODS = ("funny", "touchy", "self_realization")


class BrainrotStory(BaseModel):
    title: str
    mood: str = "funny"  # funny | touchy | self_realization
    spoken_script: str = ""  # TTS-facing text: numbers/currency/emoji spelled out
    display_script: str = ""  # caption-facing text: natural formatting ("$13.60", emoji, etc.)
    target_duration: float = 12.0  # seconds, rough estimate at ~2.5 words/sec (hard cap 20s, usual 8-16s)
    tags: List[str] = Field(default_factory=list)

    @field_validator("mood")
    @classmethod
    def _check_mood(cls, mood: str) -> str:
        mood = mood.strip().lower()
        return mood if mood in MOODS else "funny"

    @field_validator("tags")
    @classmethod
    def _clamp_tags(cls, tags: List[str]) -> List[str]:
        seen = set()
        cleaned = []
        for tag in tags:
            tag = tag.strip().lstrip("#").replace(" ", "")
            if tag and tag.lower() not in seen:
                seen.add(tag.lower())
                cleaned.append(tag)
        return cleaned[:15]
