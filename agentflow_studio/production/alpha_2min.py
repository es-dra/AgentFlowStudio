from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


SCHEMA_VERSION = "afs.alpha_2min.v0.1"
SAFE_ID = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$"
SHA256 = r"^[a-f0-9]{64}$"
MEDIA_MODALITIES = ("image", "video", "audio")
PROTECTED_NON_CLAIMS = {
    "provider_smoke": False,
    "generated_media_quality": False,
    "human_acceptance": False,
    "business_validation": False,
    "public_release": False,
    "legal_readiness": False,
    "saas_readiness": False,
    "alpha_readiness": False,
    "durable_aos_promotion": False,
}
_UNSAFE_TEXT = re.compile(
    r"(?i)(?:"
    r"api[-_]?key|access[-_]?token|authorization=|client[-_]?secret|"
    r"credential=|file:|signed[-_]?url|/home/|/opt/|/tmp/|[A-Za-z]:[\\/]"
    r")"
)


class Alpha2MinModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Alpha2MinBrief(Alpha2MinModel):
    schema_version: Literal["afs.alpha_2min.v0.1"] = SCHEMA_VERSION
    brief_id: str = Field(pattern=SAFE_ID)
    project_title: str = Field(min_length=1, max_length=160)
    logline: str = Field(min_length=1, max_length=800)
    target_audience: str = Field(default="internal alpha reviewer", max_length=160)
    tone: str = Field(default="grounded", max_length=120)
    genre: str = Field(default="near-future drama", max_length=120)
    core_theme: str = Field(default="choice under pressure", max_length=200)
    must_include: tuple[str, ...] = Field(default_factory=tuple, max_length=8)
    constraints: tuple[str, ...] = Field(default_factory=tuple, max_length=8)
    target_duration_seconds: int = Field(default=96, ge=90, le=120, strict=True)

    @field_validator(
        "project_title",
        "logline",
        "target_audience",
        "tone",
        "genre",
        "core_theme",
    )
    @classmethod
    def safe_text(cls, value: str) -> str:
        return _safe_text(value)

    @field_validator("must_include", "constraints")
    @classmethod
    def safe_text_tuple(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        cleaned = tuple(_safe_text(value) for value in values if str(value).strip())
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("brief text lists must not contain duplicates")
        return cleaned


class Alpha2MinStoryboardFrame(Alpha2MinModel):
    frame_id: str = Field(pattern=SAFE_ID)
    shot_id: str = Field(pattern=SAFE_ID)
    scene_id: str = Field(pattern=SAFE_ID)
    sequence: int = Field(ge=1, strict=True)
    duration_seconds: int = Field(ge=1, le=120, strict=True)
    beat: str = Field(min_length=1, max_length=240)
    visual_summary: str = Field(min_length=1, max_length=600)
    audio_summary: str = Field(min_length=1, max_length=400)


class Alpha2MinRecipeShot(Alpha2MinModel):
    shot_id: str = Field(pattern=SAFE_ID)
    scene_id: str = Field(pattern=SAFE_ID)
    sequence: int = Field(ge=1, strict=True)
    duration_seconds: int = Field(ge=1, le=120, strict=True)
    storyboard_frame_id: str = Field(pattern=SAFE_ID)
    reference_asset_ids: tuple[str, ...] = Field(min_length=1, max_length=16)
    image_prompt: str = Field(min_length=1, max_length=800)
    video_prompt: str = Field(min_length=1, max_length=800)
    audio_prompt: str = Field(min_length=1, max_length=800)
    acceptance_checks: tuple[str, ...] = Field(min_length=1, max_length=12)


class Alpha2MinProductionRecipe(Alpha2MinModel):
    schema_version: Literal["afs.alpha_2min.production_recipe.v0.1"] = (
        "afs.alpha_2min.production_recipe.v0.1"
    )
    recipe_id: str = Field(pattern=SAFE_ID)
    source_brief_id: str = Field(pattern=SAFE_ID)
    reference_set_id: str = Field(pattern=SAFE_ID)
    target_duration_seconds: int = Field(ge=90, le=120, strict=True)
    media_modalities: tuple[Literal["image", "video", "audio"], ...] = MEDIA_MODALITIES
    shots: tuple[Alpha2MinRecipeShot, ...] = Field(min_length=1, max_length=16)
    provider_policy: dict[str, bool]
    estimated_cost_cents: int = Field(default=0, ge=0, le=0, strict=True)
    readiness_boundary: Literal["pending_fixture_review"] = "pending_fixture_review"

    @model_validator(mode="after")
    def shot_inventory_matches_duration(self) -> "Alpha2MinProductionRecipe":
        if sum(shot.duration_seconds for shot in self.shots) != self.target_duration_seconds:
            raise ValueError("recipe shot durations must sum to the target duration")
        if self.provider_policy != {
            "allow_remote_llm": False,
            "allow_remote_image": False,
            "allow_remote_video": False,
            "allow_remote_audio": False,
            "allow_external_download": False,
        }:
            raise ValueError("alpha_2min recipe must keep every provider gate closed")
        return self


class Alpha2MinCandidateManifest(Alpha2MinModel):
    schema_version: Literal["afs.alpha_2min.candidate_manifest.v0.1"] = (
        "afs.alpha_2min.candidate_manifest.v0.1"
    )
    candidate_id: str = Field(pattern=SAFE_ID)
    shot_id: str = Field(pattern=SAFE_ID)
    modality: Literal["image", "video", "audio"]
    placeholder_kind: Literal["deterministic_metadata_only"] = "deterministic_metadata_only"
    prompt_digest: str = Field(pattern=SHA256)
    contains_media_bytes: bool = False
    contains_private_path: bool = False
    contains_signed_url: bool = False
    provider_calls: int = Field(default=0, ge=0, le=0, strict=True)
    model_calls: int = Field(default=0, ge=0, le=0, strict=True)
    media_calls: int = Field(default=0, ge=0, le=0, strict=True)


def build_alpha_2min_storyboard(
    brief: Alpha2MinBrief,
    *,
    scene_ids: tuple[str, ...],
    shot_ids: tuple[str, ...],
) -> tuple[Alpha2MinStoryboardFrame, ...]:
    durations = _durations(brief.target_duration_seconds, len(shot_ids))
    beats = (
        "hook",
        "orientation",
        "pressure",
        "choice",
        "consequence",
        "handoff",
    )
    frames = []
    for index, (shot_id, duration) in enumerate(zip(shot_ids, durations), start=1):
        scene_id = scene_ids[(index - 1) // 2]
        beat = beats[index - 1] if index <= len(beats) else f"beat-{index:02d}"
        frames.append(
            Alpha2MinStoryboardFrame(
                frame_id=f"alpha-frame-{index:03d}",
                shot_id=shot_id,
                scene_id=scene_id,
                sequence=index,
                duration_seconds=duration,
                beat=beat,
                visual_summary=(
                    f"{brief.project_title}: {beat} frame for the fixture slice; "
                    f"preserve {brief.tone} tone and exact reference continuity."
                ),
                audio_summary=(
                    f"Fixture dialogue, room tone, and cue for {beat}; no voice provider call."
                ),
            )
        )
    return tuple(frames)


def build_alpha_2min_recipe(
    brief: Alpha2MinBrief,
    *,
    reference_set_id: str,
    reference_asset_ids: tuple[str, ...],
    storyboard: tuple[Alpha2MinStoryboardFrame, ...],
) -> Alpha2MinProductionRecipe:
    shots = tuple(
        Alpha2MinRecipeShot(
            shot_id=frame.shot_id,
            scene_id=frame.scene_id,
            sequence=frame.sequence,
            duration_seconds=frame.duration_seconds,
            storyboard_frame_id=frame.frame_id,
            reference_asset_ids=reference_asset_ids,
            image_prompt=(
                f"Metadata-only image placeholder for {frame.shot_id}: {frame.visual_summary}"
            ),
            video_prompt=(
                f"Metadata-only video placeholder for {frame.shot_id}: "
                f"{frame.duration_seconds}s, {frame.visual_summary}"
            ),
            audio_prompt=(
                f"Metadata-only audio placeholder for {frame.shot_id}: {frame.audio_summary}"
            ),
            acceptance_checks=(
                "uses exact shot and reference set ids",
                "contains no generated media bytes",
                "keeps provider dispatch count at zero",
            ),
        )
        for frame in storyboard
    )
    return Alpha2MinProductionRecipe(
        recipe_id="alpha-2min-production-recipe-001",
        source_brief_id=brief.brief_id,
        reference_set_id=reference_set_id,
        target_duration_seconds=brief.target_duration_seconds,
        shots=shots,
        provider_policy={
            "allow_remote_llm": False,
            "allow_remote_image": False,
            "allow_remote_video": False,
            "allow_remote_audio": False,
            "allow_external_download": False,
        },
    )


def build_alpha_2min_candidate_manifest(
    recipe: Alpha2MinProductionRecipe,
    *,
    shot_id: str,
    modality: Literal["image", "video", "audio"],
    candidate_id: str,
) -> Alpha2MinCandidateManifest:
    shot = next(item for item in recipe.shots if item.shot_id == shot_id)
    prompt = {
        "image": shot.image_prompt,
        "video": shot.video_prompt,
        "audio": shot.audio_prompt,
    }[modality]
    return Alpha2MinCandidateManifest(
        candidate_id=candidate_id,
        shot_id=shot_id,
        modality=modality,
        prompt_digest=digest(prompt),
    )


def build_alpha_2min_export_manifest(
    brief: Alpha2MinBrief,
    *,
    recipe: Alpha2MinProductionRecipe,
    storyboard: tuple[Alpha2MinStoryboardFrame, ...],
    candidate_refs: tuple[dict[str, Any], ...],
    selection_refs: tuple[dict[str, Any], ...],
    delivery_ref: dict[str, Any],
    aggregate_version: int,
) -> dict[str, Any]:
    return {
        "schema_version": "afs.alpha_2min.export_manifest.v0.1",
        "artifact_type": "alpha_2min_export_manifest",
        "source_brief_id": brief.brief_id,
        "project_title": brief.project_title,
        "target_duration_seconds": brief.target_duration_seconds,
        "aggregate_version": aggregate_version,
        "production_recipe": recipe.model_dump(mode="json"),
        "storyboard": [item.model_dump(mode="json") for item in storyboard],
        "candidate_refs": list(candidate_refs),
        "selection_refs": list(selection_refs),
        "delivery_ref": delivery_ref,
        "compose": {
            "mode": "deterministic_placeholder_manifest",
            "image_candidate_count": _count_modality(candidate_refs, "image"),
            "video_candidate_count": _count_modality(candidate_refs, "video"),
            "audio_candidate_count": _count_modality(candidate_refs, "audio"),
            "contains_media_bytes": False,
            "contains_private_path": False,
            "contains_signed_url": False,
        },
        "review_gate": {
            "status": "pending_fixture_review",
            "human_acceptance_claimed": False,
            "generated_media_quality_claimed": False,
        },
        "call_counters": {
            "provider_calls": 0,
            "model_calls": 0,
            "media_calls": 0,
            "external_downloads": 0,
        },
        "non_claims": dict(PROTECTED_NON_CLAIMS),
    }


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _durations(total: int, count: int) -> tuple[int, ...]:
    base = total // count
    remainder = total % count
    return tuple(base + (1 if index < remainder else 0) for index in range(count))


def _safe_text(value: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        raise ValueError("text must not be empty")
    if _UNSAFE_TEXT.search(text):
        raise ValueError("alpha_2min text contains unsafe storage or credential content")
    return text


def _count_modality(candidate_refs: tuple[dict[str, Any], ...], modality: str) -> int:
    return sum(1 for item in candidate_refs if item.get("modality") == modality)


__all__ = (
    "MEDIA_MODALITIES",
    "PROTECTED_NON_CLAIMS",
    "Alpha2MinBrief",
    "Alpha2MinCandidateManifest",
    "Alpha2MinProductionRecipe",
    "Alpha2MinStoryboardFrame",
    "build_alpha_2min_candidate_manifest",
    "build_alpha_2min_export_manifest",
    "build_alpha_2min_recipe",
    "build_alpha_2min_storyboard",
    "digest",
)
