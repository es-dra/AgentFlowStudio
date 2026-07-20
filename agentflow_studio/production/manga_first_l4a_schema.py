from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


MANGA_FIRST_CONTRACT_VERSION = "afs.manga_first_l4a.v0.1"
SAFE_ID = r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$"
SHA256 = r"^[a-f0-9]{64}$"
TARGET_MIN_SECONDS = Decimal("90.000")
TARGET_MAX_SECONDS = Decimal("120.000")
CHECKPOINT_STAGES = (
    "story",
    "keyframe",
    "video",
    "audio_wait",
    "compose",
    "technical_QA",
    "visual_creative_QA",
)
LEGACY_TEMPLATE_TERMS = (
    "pier",
    "lighthouse",
    "robot",
    "blue raincoat",
    "old pier",
    "failed lighthouse climb",
)
L3_P1_TITLES = (
    "Canonical story authority diverges before generation",
    "Main character identity and costume are not locked",
    "Exact 120-second editorial schedule is absent",
    "Shot-013 misses resolution action and breaks location continuity",
    "Shot-007 contains an unplanned internal scene transformation",
)


class MangaFirstError(ValueError):
    pass


class CheckpointStateError(RuntimeError):
    pass


class MangaFirstModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MangaCharacterBrief(MangaFirstModel):
    character_id: str = Field(pattern=SAFE_ID)
    name: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=1, max_length=120)
    visual_identity: str = Field(min_length=1, max_length=500)
    continuity_rules: tuple[str, ...] = Field(min_length=1, max_length=12)


class MangaSceneBrief(MangaFirstModel):
    scene_id: str = Field(pattern=SAFE_ID)
    name: str = Field(min_length=1, max_length=120)
    location_type: str = Field(min_length=1, max_length=160)
    visual_mood: str = Field(min_length=1, max_length=240)
    story_function: str = Field(min_length=1, max_length=240)


class MangaBeatBrief(MangaFirstModel):
    beat_id: str = Field(pattern=SAFE_ID)
    scene_id: str = Field(pattern=SAFE_ID)
    character_ids: tuple[str, ...] = Field(min_length=1, max_length=3)
    action: str = Field(min_length=1, max_length=500)
    emotional_turn: str = Field(min_length=1, max_length=240)
    duration_weight: Decimal = Field(default=Decimal("1.0"), gt=Decimal("0.1"), le=Decimal("3.0"))

    @field_validator("duration_weight", mode="before")
    @classmethod
    def duration_weight_to_decimal(cls, value: Any) -> Decimal:
        return Decimal(str(value))


class MangaFirstBrief(MangaFirstModel):
    project_id: str = Field(pattern=SAFE_ID)
    title: str = Field(min_length=1, max_length=160)
    logline: str = Field(min_length=1, max_length=800)
    style: Literal["anime", "manga", "manhua", "webtoon", "manga_drama"]
    target_duration_seconds: Decimal = Field(ge=TARGET_MIN_SECONDS, le=TARGET_MAX_SECONDS)
    characters: tuple[MangaCharacterBrief, ...] = Field(min_length=1, max_length=3)
    scenes: tuple[MangaSceneBrief, ...] = Field(min_length=2, max_length=4)
    beats: tuple[MangaBeatBrief, ...] = Field(min_length=12, max_length=15)
    audience: str = Field(min_length=1, max_length=200)
    tone: str = Field(min_length=1, max_length=240)
    owner_decision: Literal["manga_first"] = "manga_first"

    @field_validator("target_duration_seconds", mode="before")
    @classmethod
    def duration_to_decimal(cls, value: Any) -> Decimal:
        return Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)

    @model_validator(mode="after")
    def references_are_exact_and_brief_drives_all_shots(self) -> "MangaFirstBrief":
        character_ids = {item.character_id for item in self.characters}
        scene_ids = {item.scene_id for item in self.scenes}
        if len(character_ids) != len(self.characters):
            raise ValueError("characters must use unique ids")
        if len(scene_ids) != len(self.scenes):
            raise ValueError("scenes must use unique ids")
        seen_beats: set[str] = set()
        for beat in self.beats:
            if beat.beat_id in seen_beats:
                raise ValueError("beats must use unique ids")
            seen_beats.add(beat.beat_id)
            if beat.scene_id not in scene_ids:
                raise ValueError("beat scene_id must resolve to a scene in the brief")
            missing = [item for item in beat.character_ids if item not in character_ids]
            if missing:
                raise ValueError("beat character_ids must resolve to characters in the brief")
        return self


class ProductionTruthManifest(MangaFirstModel):
    schema_version: Literal["afs.manga_first_l4a.v0.1"] = MANGA_FIRST_CONTRACT_VERSION
    project_id: str = Field(pattern=SAFE_ID)
    manifest_sha256: str = Field(pattern=SHA256)
    provider_dispatch_count: Literal[0] = 0
    owner_decision: Literal["manga_first"]
    story_bible: dict[str, Any]
    scenes: tuple[dict[str, Any], ...]
    shots: tuple[dict[str, Any], ...]
    reference_set: dict[str, Any]
    production_recipe: dict[str, Any]
    timeline: dict[str, Any]
    assembly_contract: dict[str, Any]
    fact_chain: dict[str, Any]
    checkpoints: tuple[dict[str, Any], ...]
    studio_projection: dict[str, Any]
    template_audit: dict[str, Any]
    evidence_boundaries: dict[str, Any]


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def json_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json_object(path: str | Path) -> dict[str, Any]:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MangaFirstError(f"JSON file is unreadable: {path}") from exc
    if not isinstance(value, dict):
        raise MangaFirstError("JSON file must contain an object")
    return value


def write_json_atomic(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    fd, tmp_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=str(target.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except OSError:
            pass


def decimal_string(value: Decimal) -> str:
    return str(Decimal(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def variable_schedule(
    *,
    count: int,
    target_seconds: Decimal,
    weights: tuple[Decimal, ...] | None = None,
    source_max_seconds: Decimal | None = None,
) -> tuple[tuple[Decimal, Decimal], ...]:
    target = Decimal(str(target_seconds)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if count <= 0:
        raise MangaFirstError("schedule count must be positive")
    if weights is None:
        pattern = (Decimal("0.96"), Decimal("1.04"), Decimal("0.93"), Decimal("1.07"), Decimal("0.99"))
        weights = tuple(pattern[index % len(pattern)] for index in range(count))
    if len(weights) != count:
        raise MangaFirstError("schedule weights must match shot count")
    total_weight = sum(weights)
    durations = [
        (target * weight / total_weight).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        for weight in weights
    ]
    if source_max_seconds is not None and any(item > source_max_seconds for item in durations):
        durations = _cap_durations(durations, source_max_seconds)
    correction = target - sum(durations)
    durations[-1] = (durations[-1] + correction).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if any(item <= 0 for item in durations):
        raise MangaFirstError("schedule produced non-positive duration")
    starts: list[tuple[Decimal, Decimal]] = []
    cursor = Decimal("0.000")
    for item in durations:
        end = (cursor + item).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
        starts.append((cursor, end))
        cursor = end
    if cursor != target:
        raise MangaFirstError("schedule does not sum exactly to target")
    return tuple(starts)


def _cap_durations(durations: list[Decimal], source_max_seconds: Decimal) -> list[Decimal]:
    overflow = Decimal("0")
    adjusted: list[Decimal] = []
    for item in durations:
        if item > source_max_seconds:
            overflow += item - source_max_seconds
            adjusted.append(source_max_seconds)
        else:
            adjusted.append(item)
    receivers = [index for index, item in enumerate(adjusted) if item < source_max_seconds]
    while overflow > 0 and receivers:
        changed = False
        for index in receivers:
            if overflow <= 0:
                break
            room = source_max_seconds - adjusted[index]
            if room <= 0:
                continue
            delta = min(room, overflow / Decimal(max(len(receivers), 1)))
            adjusted[index] = (adjusted[index] + delta).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
            overflow -= delta
            changed = True
        receivers = [index for index, item in enumerate(adjusted) if item < source_max_seconds]
        if not changed:
            break
    return adjusted


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
