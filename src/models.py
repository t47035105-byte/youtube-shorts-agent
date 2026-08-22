from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Source:
    title: str
    url: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Source":
        return cls(title=str(value["title"]).strip(), url=str(value["url"]).strip())


@dataclass(frozen=True)
class Scene:
    caption: str
    visual_prompt: str
    duration_s: float

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Scene":
        duration = max(2.5, min(12.0, float(value["duration_s"])))
        return cls(
            caption=str(value["caption"]).strip(),
            visual_prompt=str(value["visual_prompt"]).strip(),
            duration_s=duration,
        )


@dataclass(frozen=True)
class ShortPlan:
    title: str
    hook: str
    narration: str
    description: str
    hashtags: tuple[str, ...]
    scenes: tuple[Scene, ...]
    sources: tuple[Source, ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ShortPlan":
        scenes = tuple(Scene.from_dict(item) for item in value["scenes"])
        if not 4 <= len(scenes) <= 8:
            raise ValueError("A short must contain 4 to 8 scenes")
        sources = tuple(Source.from_dict(item) for item in value.get("sources", []))
        return cls(
            title=str(value["title"]).strip(),
            hook=str(value["hook"]).strip(),
            narration=str(value["narration"]).strip(),
            description=str(value["description"]).strip(),
            hashtags=tuple(str(item).strip().lstrip("#") for item in value["hashtags"]),
            scenes=scenes,
            sources=sources,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "hook": self.hook,
            "narration": self.narration,
            "description": self.description,
            "hashtags": list(self.hashtags),
            "scenes": [scene.__dict__ for scene in self.scenes],
            "sources": [source.__dict__ for source in self.sources],
        }

