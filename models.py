from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class Asset(BaseModel):
    id: str
    source: str  # pexels | pixabay | local
    url: Optional[str] = None
    local_path: Optional[str] = None
    duration: float = 0.0
    clip_score: float = 0.0
    qa_score: float = 0.0
    final_score: float = 0.0


class Beat(BaseModel):
    role: str = "body"  # hook | body | closer
    caption: str
    duration: float = 3.0
    search_queries: List[str] = Field(default_factory=list)
    visual_description: str = ""
    mood: str = "neutral"
    text_position: str = "center"  # top | center | bottom
    text_style: str = "pill"  # clean | pill | shadow | outline | frosted
    asset: Optional[Asset] = None


class ReelPlan(BaseModel):
    title: str = "Untitled Reel"
    hook: Beat
    hook_alt: Optional[Beat] = None  # alternate hook angle, footage-scored against `hook`, loser discarded
    beats: List[Beat] = Field(default_factory=list)
    closer: Beat
    color_palette: List[str] = Field(default_factory=lambda: ["#1a1a1a", "#f5f5f5", "#c9a24b"])
    overall_mood: str = "neutral"
    style_preset: str = "cool-minimal"
    music_suggestion: str = ""
    ig_caption: str = ""
    ig_hashtags: List[str] = Field(default_factory=list)
    total_duration: float = 20.0

    def all_beats(self) -> List[Beat]:
        return [self.hook] + self.beats + [self.closer]

    @field_validator("ig_hashtags")
    @classmethod
    def _clamp_hashtags(cls, tags: List[str]) -> List[str]:
        seen = set()
        cleaned = []
        for tag in tags:
            tag = tag.strip().lstrip("#").replace(" ", "")
            if tag and tag.lower() not in seen:
                seen.add(tag.lower())
                cleaned.append(tag)
        return cleaned[:20]  # IG best practice ceiling

    @field_validator("ig_caption")
    @classmethod
    def _clamp_caption(cls, caption: str) -> str:
        return caption[:2200]  # IG hard limit
