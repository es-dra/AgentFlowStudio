from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import Field, field_validator

from agentflow_studio.schemas.base import Metadata, SchemaBase


SCHEMA_VERSION = "0.1.0"
CONTENT_MODE = "episodic_story_production"
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


class StudioArtifact(SchemaBase):
    schema_version: str = SCHEMA_VERSION
    artifact_type: str
    metadata: dict[str, Any] = Metadata

    @field_validator("schema_version")
    @classmethod
    def schema_version_must_be_semver(cls, value: str) -> str:
        if not SEMVER_RE.match(value):
            raise ValueError("schema_version must use semver, for example 0.1.0")
        if value != SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {SCHEMA_VERSION}")
        return value


class CreativeBrief(StudioArtifact):
    artifact_type: Literal["creative_brief"] = "creative_brief"
    brief_id: str
    project_title: str
    content_mode: Literal["episodic_story_production"] = CONTENT_MODE
    logline: str
    target_audience: str
    platform: str
    tone: str
    genre: str
    core_theme: str
    must_include: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    episode_count: int = Field(default=1, ge=1)
    target_episode_duration_sec: int = Field(default=90, ge=15)


class Character(SchemaBase):
    character_id: str
    name: str
    role: str
    motivation: str
    visual_notes: str


class StoryBible(StudioArtifact):
    artifact_type: Literal["story_bible"] = "story_bible"
    story_bible_id: str
    source_brief_id: str
    project_title: str
    content_mode: Literal["episodic_story_production"] = CONTENT_MODE
    world_rules: list[str]
    characters: list[Character] = Field(min_length=1)
    style_rules: list[str]
    continuity_rules: list[str]


class EpisodeBeat(SchemaBase):
    beat_id: str
    title: str
    purpose: str
    summary: str


class EpisodeOutline(StudioArtifact):
    artifact_type: Literal["episode_outline"] = "episode_outline"
    episode_outline_id: str
    source_brief_id: str
    story_bible_id: str
    project_title: str
    episode_number: int = Field(default=1, ge=1)
    beats: list[EpisodeBeat] = Field(min_length=1)
    cliffhanger: str


class Scene(SchemaBase):
    scene_id: str
    beat_id: str
    title: str
    location: str
    dramatic_purpose: str
    visual_mood: str


class ScenePlan(StudioArtifact):
    artifact_type: Literal["scene_plan"] = "scene_plan"
    scene_plan_id: str
    episode_outline_id: str
    scenes: list[Scene] = Field(min_length=1)


class Shot(SchemaBase):
    shot_id: str
    scene_id: str
    shot_type: str
    description: str
    duration_sec: int = Field(ge=1)
    production_notes: list[str] = Field(default_factory=list)


class ShotPlan(StudioArtifact):
    artifact_type: Literal["shot_plan"] = "shot_plan"
    shot_plan_id: str
    scene_plan_id: str
    shots: list[Shot] = Field(min_length=1)


class PromptItem(SchemaBase):
    prompt_id: str
    shot_id: str
    prompt_text: str
    negative_prompt: str = ""
    intended_use: str


class PromptPack(StudioArtifact):
    artifact_type: Literal["prompt_pack"] = "prompt_pack"
    prompt_pack_id: str
    shot_plan_id: str
    prompts: list[PromptItem] = Field(min_length=1)


class ProductionHandoff(StudioArtifact):
    artifact_type: Literal["production_handoff"] = "production_handoff"
    handoff_id: str
    project_title: str
    content_mode: Literal["episodic_story_production"] = CONTENT_MODE
    source_brief_id: str
    story_bible_id: str
    episode_outline_id: str
    scene_plan_id: str
    shot_plan_id: str
    prompt_pack_id: str
    ready_for: list[str] = Field(default_factory=list)
    open_risks: list[str] = Field(default_factory=list)
    artifact_refs: dict[str, str]


class MemoryCandidate(SchemaBase):
    id: str
    promotion_status: Literal["candidate"] = "candidate"
    memory_type: str
    statement: str
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class MemoryCandidateStore(StudioArtifact):
    artifact_type: Literal["memory_candidates"] = "memory_candidates"
    run_id: str
    candidates: list[MemoryCandidate] = Field(default_factory=list)


class CostQualityTrace(StudioArtifact):
    artifact_type: Literal["cost_quality_trace"] = "cost_quality_trace"
    run_id: str
    provider: str
    execution_mode: str
    estimated_cost: float = Field(ge=0)
    currency: str = "USD"
    input_artifacts: list[str] = Field(default_factory=list)
    output_artifacts: list[str] = Field(default_factory=list)
    quality_proxy: dict[str, float] = Field(default_factory=dict)
    applicable_scenario: str


class FeedbackSignalLog(StudioArtifact):
    artifact_type: Literal["feedback_signal_log"] = "feedback_signal_log"
    run_id: str
    source_of_truth: str = "feedback.jsonl"
    is_primary_feedback_store: Literal[False] = False
    signals: list[dict[str, Any]] = Field(default_factory=list)
