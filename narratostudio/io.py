from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from narratostudio.schemas import (
    CreativeBrief,
    EpisodeOutline,
    ProductionHandoff,
    PromptPack,
    ScenePlan,
    ShotPlan,
    StoryBible,
)


T = TypeVar("T", bound=BaseModel)


def load_creative_brief(path: str | Path) -> CreativeBrief:
    return _load_model(Path(path), CreativeBrief, "creative brief")


def load_story_bible(path: str | Path) -> StoryBible:
    return _load_model(Path(path), StoryBible, "story bible")


def load_episode_outline(path: str | Path) -> EpisodeOutline:
    return _load_model(Path(path), EpisodeOutline, "episode outline")


def load_scene_plan(path: str | Path) -> ScenePlan:
    return _load_model(Path(path), ScenePlan, "scene plan")


def load_shot_plan(path: str | Path) -> ShotPlan:
    return _load_model(Path(path), ShotPlan, "shot plan")


def load_prompt_pack(path: str | Path) -> PromptPack:
    return _load_model(Path(path), PromptPack, "prompt pack")


def load_production_handoff(path: str | Path) -> ProductionHandoff:
    return _load_model(Path(path), ProductionHandoff, "production handoff")


def _load_model(path: Path, model: type[T], label: str) -> T:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} artifact is not valid JSON: {path}") from exc
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise ValueError(f"{label} artifact failed schema validation: {path}") from exc
