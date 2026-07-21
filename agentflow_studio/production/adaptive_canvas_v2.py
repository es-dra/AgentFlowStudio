from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, Literal

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.provider_adapter import (
    ProviderDispatchRequest,
    ProviderRegistry,
    load_provider_registry,
    structured_output_schema_digest,
)
from agentflow_studio.production.runtime_safe_io import read_json, safe_id


GenerationStrategy = Literal["text_to_video", "image_to_video"]
ScriptSourceType = Literal["provider", "agent_authored_test_input"]
MediaPromptStyle = Literal["anime", "cinematic_live_action"]
Callback = Callable[[dict[str, Any]], None]
ADAPTIVE_SCHEMA_VERSION = "afs.adaptive_canvas_v2.production_run.v0.1"
LEDGER_SCHEMA_VERSION = "afs.adaptive_canvas_v2.charge_ledger.v0.1"
AGENT_SCRIPT_INPUT_SCHEMA_VERSION = "afs.adaptive_canvas_v2.agent_authored_script_input.v0.1"
SCRIPT_TRUTH_AGGREGATE_VERSION = "afs.adaptive_canvas_v2.script_truth.aggregate.v0.2"
DEFAULT_PROVIDER_ATTEMPT_CAP = 20
IMAGE_PROVIDER_SERVICE_ID = "image_relay"
VIDEO_PROVIDER_SERVICE_ID = "seedance_i2v"
SCRIPT_V3_CONTRACT_ID = "adaptive_canvas_script_v3"
AGENT_SCRIPT_INPUT_FILENAME = "agent_authored_script_input.json"


class AdaptiveCanvasError(RuntimeError):
    pass


class PaidAttemptLimitExceeded(AdaptiveCanvasError):
    pass


class ProviderArtifactRetryExceeded(AdaptiveCanvasError):
    pass


@dataclass(frozen=True)
class AdaptiveShotSpec:
    shot_id: str
    summary: str
    location: str
    characters: tuple[str, ...]
    action: str
    camera: str
    duration_sec: float
    generation_strategy: GenerationStrategy
    strategy_reason: str
    continuity_in: str
    continuity_out: str


@dataclass(frozen=True)
class AdaptiveProductionProfile:
    project_type: str
    title: str
    logline: str
    style_bible: str
    characters: tuple[dict[str, Any], ...]
    scenes: tuple[dict[str, Any], ...]
    shots: tuple[AdaptiveShotSpec, ...]
    llm_service_id: str = "prompt_optimizer"
    script_candidate_id: str = "script-v1"
    script_contract_id: str | None = None
    script_source_type: ScriptSourceType = "provider"
    script_decision_source: str | None = None
    provider_supported_video_durations_sec: tuple[int, ...] = (10, 5)
    reference_sheet_required: bool = True
    max_paid_attempts: int = DEFAULT_PROVIDER_ATTEMPT_CAP
    media_prompt_style: MediaPromptStyle = "anime"
    media_aspect_ratio: str = "9:16"
    video_resolution: str = "480p"
    video_motion: str = "smooth anime camera motion; maintain story continuity"
    media_negative_locks: tuple[str, ...] = ()

    @property
    def target_duration_sec(self) -> float:
        return round(sum(float(shot.duration_sec) for shot in self.shots), 3)

    @property
    def shot_count(self) -> int:
        return len(self.shots)

    def validate(self) -> None:
        if not self.llm_service_id.strip():
            raise AdaptiveCanvasError("llm_service_id must be non-empty")
        if not self.script_candidate_id.strip():
            raise AdaptiveCanvasError("script_candidate_id must be non-empty")
        if self.script_contract_id is not None and not self.script_contract_id.strip():
            raise AdaptiveCanvasError("script_contract_id must be non-empty when provided")
        if self.script_source_type not in {"provider", "agent_authored_test_input"}:
            raise AdaptiveCanvasError("unsupported script source type")
        if self.script_source_type == "agent_authored_test_input":
            if not str(self.script_decision_source or "").strip():
                raise AdaptiveCanvasError("agent-authored script requires a decision source")
            if self.script_contract_id is not None:
                raise AdaptiveCanvasError("agent-authored script must not declare a Provider contract")
        elif self.script_candidate_id == "script-v3" and self.script_contract_id != SCRIPT_V3_CONTRACT_ID:
            raise AdaptiveCanvasError("script-v3 requires the adaptive_canvas_script_v3 contract")
        if not self.shots:
            raise AdaptiveCanvasError("profile requires at least one shot")
        if self.max_paid_attempts > DEFAULT_PROVIDER_ATTEMPT_CAP:
            raise AdaptiveCanvasError("paid provider attempt cap cannot exceed 20")
        if self.media_prompt_style not in {"anime", "cinematic_live_action"}:
            raise AdaptiveCanvasError("unsupported media prompt style")
        left, sep, right = self.media_aspect_ratio.partition(":")
        if sep != ":" or not left.isdigit() or not right.isdigit() or int(left) <= 0 or int(right) <= 0:
            raise AdaptiveCanvasError("media_aspect_ratio must use positive N:N format")
        if not self.video_resolution.strip():
            raise AdaptiveCanvasError("video_resolution must be non-empty")
        if not self.video_motion.strip():
            raise AdaptiveCanvasError("video_motion must be non-empty")
        if any(float(shot.duration_sec) <= 0 for shot in self.shots):
            raise AdaptiveCanvasError("all shot durations must be positive")
        supported = sorted({int(value) for value in self.provider_supported_video_durations_sec if int(value) > 0})
        if not supported:
            raise AdaptiveCanvasError("provider supported durations must be non-empty")
        ids = [shot.shot_id for shot in self.shots]
        if len(set(ids)) != len(ids):
            raise AdaptiveCanvasError("shot ids must be unique")


@dataclass(frozen=True)
class AdaptiveRunOptions:
    runtime_root: Path
    project_id: str
    run_id: str
    profile: AdaptiveProductionProfile
    mode: Literal["real", "fake"] = "real"
    provider_config_path: Path | None = None
    video_poll_interval_sec: float = 15.0
    video_poll_timeout_sec: float = 5400.0


class ChargeLedger:
    def __init__(self, path: Path, *, project_id: str, run_id: str, max_paid_attempts: int) -> None:
        self.path = path
        self.project_id = project_id
        self.run_id = run_id
        self.max_paid_attempts = int(max_paid_attempts)
        if path.exists():
            self.payload = read_json(path)
        else:
            self.payload = {
                "schema_version": LEDGER_SCHEMA_VERSION,
                "project_id": project_id,
                "run_id": run_id,
                "max_paid_attempts": self.max_paid_attempts,
                "paid_attempt_count": 0,
                "attempts": [],
                "does_not_store_secrets": True,
                "does_not_store_provider_raw_responses": True,
            }
            self.save()

    @property
    def paid_attempt_count(self) -> int:
        return int(self.payload.get("paid_attempt_count") or 0)

    @property
    def attempts(self) -> list[dict[str, Any]]:
        attempts = self.payload.setdefault("attempts", [])
        if not isinstance(attempts, list):
            raise AdaptiveCanvasError("charge ledger attempts must be a list")
        return attempts

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        write_json(self.path, self.payload)

    def fingerprint(
        self,
        *,
        stage: str,
        shot_id: str | None,
        chunk_id: str | None,
        candidate_id: str,
        prompt: str,
        contract_id: str | None = None,
        contract_schema_digest: str | None = None,
    ) -> str:
        material = {
            "project_id": self.project_id,
            "run_id": self.run_id,
            "stage": stage,
            "shot_id": shot_id or "",
            "chunk_id": chunk_id or "",
            "candidate_id": candidate_id,
            "prompt_sha256": sha256_text(prompt),
        }
        if contract_id:
            material["contract_id"] = contract_id
        if contract_schema_digest:
            material["contract_schema_digest"] = contract_schema_digest
        return sha256_text(json.dumps(material, sort_keys=True, separators=(",", ":")))

    def successful_attempt(self, fingerprint: str) -> dict[str, Any] | None:
        for attempt in reversed(self.attempts):
            if attempt.get("charge_fingerprint") == fingerprint and attempt.get("status") == "succeeded":
                return dict(attempt)
        return None

    def reserve(
        self,
        *,
        stage: str,
        shot_id: str | None,
        chunk_id: str | None,
        candidate_id: str,
        capability: str,
        service_id: str,
        prompt: str,
        contract_id: str | None = None,
        contract_schema_digest: str | None = None,
        max_provider_starts: int = 2,
    ) -> dict[str, Any]:
        fingerprint = self.fingerprint(
            stage=stage,
            shot_id=shot_id,
            chunk_id=chunk_id,
            candidate_id=candidate_id,
            prompt=prompt,
            contract_id=contract_id,
            contract_schema_digest=contract_schema_digest,
        )
        started = [
            attempt
            for attempt in self.attempts
            if attempt.get("charge_fingerprint") == fingerprint and attempt.get("provider_calls_started") is True
        ]
        if max_provider_starts <= 0:
            raise ValueError("max_provider_starts must be positive")
        if len(started) >= max_provider_starts:
            raise ProviderArtifactRetryExceeded(f"artifact retry limit exceeded for {stage}:{shot_id}:{chunk_id}")
        if self.paid_attempt_count >= self.max_paid_attempts:
            raise PaidAttemptLimitExceeded(f"paid provider attempt cap reached: {self.max_paid_attempts}")
        attempt_index = len(started) + 1
        attempt = {
            "attempt_id": safe_id(
                f"{self.project_id}-{self.run_id}-{stage}-{shot_id or 'global'}-{chunk_id or 'whole'}-"
                f"{candidate_id}-{fingerprint[:12]}-attempt-{attempt_index}"
            ),
            "project_id": self.project_id,
            "run_id": self.run_id,
            "stage": stage,
            "shot_id": shot_id,
            "chunk_id": chunk_id,
            "candidate_id": candidate_id,
            "attempt_index": attempt_index,
            "capability": capability,
            "service_id": service_id,
            "prompt_sha256": sha256_text(prompt),
            "charge_fingerprint": fingerprint,
            "contract_id": contract_id,
            "contract_schema_digest": contract_schema_digest,
            "status": "reserved",
            "provider_calls_started": False,
            "created_at": utc_now(),
        }
        if any(existing.get("attempt_id") == attempt["attempt_id"] for existing in self.attempts):
            raise AdaptiveCanvasError("charge ledger attempt id collision")
        self.attempts.append(attempt)
        self.save()
        return dict(attempt)

    def mark_started(self, attempt_id: str) -> None:
        for attempt in self.attempts:
            if attempt.get("attempt_id") == attempt_id:
                if attempt.get("status") in {"failed", "succeeded"}:
                    raise AdaptiveCanvasError("completed provider attempt cannot be restarted")
                if not attempt.get("provider_calls_started"):
                    attempt["provider_calls_started"] = True
                    attempt["status"] = "started"
                    attempt["started_at"] = utc_now()
                    self.payload["paid_attempt_count"] = self.paid_attempt_count + 1
                    self.save()
                return
        raise KeyError(attempt_id)

    def mark_submitted(self, attempt_id: str, *, provider_task_id: str, provider_poll_task: dict[str, Any]) -> None:
        for attempt in self.attempts:
            if attempt.get("attempt_id") == attempt_id:
                if attempt.get("status") in {"failed", "succeeded"}:
                    raise AdaptiveCanvasError("completed provider attempt cannot be marked submitted")
                if not attempt.get("provider_calls_started"):
                    raise AdaptiveCanvasError("provider attempt must be marked started before submit recovery")
                if not str(provider_task_id or "").strip():
                    raise AdaptiveCanvasError("provider task id is required for submit recovery")
                attempt["status"] = "submitted"
                attempt["submitted_at"] = utc_now()
                attempt["provider_task_id"] = provider_task_id
                attempt["provider_task_id_sha256"] = sha256_text(provider_task_id)
                attempt["provider_poll_task"] = _safe_provider_poll_task(provider_poll_task)
                self.save()
                return
        raise KeyError(attempt_id)

    def mark_succeeded(self, attempt_id: str, artifact: dict[str, Any], *, provider_task_id: str | None = None) -> None:
        for attempt in self.attempts:
            if attempt.get("attempt_id") == attempt_id:
                if attempt.get("status") == "failed":
                    raise AdaptiveCanvasError("failed provider attempt cannot be marked succeeded")
                attempt["status"] = "succeeded"
                attempt["completed_at"] = utc_now()
                attempt["artifact_version_id"] = artifact.get("artifact_version_id")
                attempt["artifact_sha256"] = artifact.get("sha256")
                attempt["artifact_kind"] = artifact.get("kind")
                if provider_task_id:
                    attempt["provider_task_id_sha256"] = sha256_text(provider_task_id)
                attempt.pop("safe_error", None)
                self.save()
                return
        raise KeyError(attempt_id)

    def resumable_submitted_attempt(self, fingerprint: str) -> dict[str, Any] | None:
        for attempt in reversed(self.attempts):
            if attempt.get("charge_fingerprint") != fingerprint:
                continue
            if attempt.get("status") != "submitted":
                continue
            poll_task = attempt.get("provider_poll_task")
            if isinstance(poll_task, dict) and str(attempt.get("provider_task_id") or "").strip():
                return dict(attempt)
        return None

    def mark_failed(self, attempt_id: str, error: Exception) -> None:
        for attempt in self.attempts:
            if attempt.get("attempt_id") == attempt_id:
                attempt["status"] = "failed"
                attempt["completed_at"] = utc_now()
                attempt["safe_error"] = safe_error(error)
                self.save()
                return
        raise KeyError(attempt_id)

    def record_fake_success(
        self,
        *,
        stage: str,
        shot_id: str | None,
        chunk_id: str | None,
        candidate_id: str,
        capability: str,
        prompt: str,
        artifact: dict[str, Any],
    ) -> None:
        fingerprint = self.fingerprint(
            stage=stage,
            shot_id=shot_id,
            chunk_id=chunk_id,
            candidate_id=candidate_id,
            prompt=prompt,
        )
        if self.successful_attempt(fingerprint):
            return
        self.attempts.append(
            {
                "attempt_id": safe_id(
                    f"{self.project_id}-{self.run_id}-{stage}-{shot_id or 'global'}-"
                    f"{chunk_id or 'whole'}-{candidate_id}-fake"
                ),
                "project_id": self.project_id,
                "run_id": self.run_id,
                "stage": stage,
                "shot_id": shot_id,
                "chunk_id": chunk_id,
                "candidate_id": candidate_id,
                "attempt_index": 0,
                "capability": capability,
                "service_id": "fake_no_provider",
                "prompt_sha256": sha256_text(prompt),
                "charge_fingerprint": fingerprint,
                "status": "succeeded",
                "provider_calls_started": False,
                "artifact_version_id": artifact.get("artifact_version_id"),
                "artifact_sha256": artifact.get("sha256"),
                "artifact_kind": artifact.get("kind"),
                "created_at": utc_now(),
                "completed_at": utc_now(),
            }
        )
        self.save()


def compile_duration_chunks(target_duration_sec: float, supported_durations_sec: tuple[int, ...] = (10, 5)) -> list[dict[str, Any]]:
    target = round(float(target_duration_sec), 3)
    if target <= 0:
        raise AdaptiveCanvasError("target duration must be positive")
    supported = sorted({int(value) for value in supported_durations_sec if int(value) > 0}, reverse=True)
    if not supported:
        raise AdaptiveCanvasError("supported durations must be non-empty")
    chunks: list[dict[str, Any]] = []
    covered = 0.0
    max_supported = supported[0]
    ascending = sorted(supported)
    while covered < target - 0.001:
        remaining = round(target - covered, 3)
        if remaining <= max_supported:
            provider_duration = next((value for value in ascending if value >= remaining - 0.001), max_supported)
        else:
            provider_duration = max_supported
        used = min(float(provider_duration), remaining)
        chunk_index = len(chunks) + 1
        chunks.append(
            {
                "chunk_id": f"chunk-{chunk_index:02d}",
                "provider_duration_sec": int(provider_duration),
                "timeline_in_sec": round(covered, 3),
                "timeline_out_sec": round(covered + used, 3),
                "used_duration_sec": round(used, 3),
                "requires_continuity_anchor": chunk_index > 1,
            }
        )
        covered = round(covered + used, 3)
    return chunks


def build_script_truth_from_profile(profile: AdaptiveProductionProfile) -> dict[str, Any]:
    profile.validate()
    shots = []
    character_ids = {
        str(item.get("name") or ""): str(item.get("character_id") or safe_id(str(item.get("name") or "")))
        for item in profile.characters
    }
    scene_ids = {
        str(item.get("name") or ""): str(item.get("scene_id") or safe_id(str(item.get("name") or "")))
        for item in profile.scenes
    }
    for order, shot in enumerate(profile.shots, start=1):
        shots.append(
            {
                "shot_id": shot.shot_id,
                "order": order,
                "summary": shot.summary,
                "location": shot.location,
                "characters": list(shot.characters),
                "character_ids": [character_ids.get(name, safe_id(name)) for name in shot.characters],
                "scene_id": scene_ids.get(shot.location, safe_id(shot.location)),
                "action": shot.action,
                "camera": shot.camera,
                "target_duration_sec": float(shot.duration_sec),
                "generation_strategy": shot.generation_strategy,
                "strategy_reason": shot.strategy_reason,
                "continuity_in": shot.continuity_in,
                "continuity_out": shot.continuity_out,
                "keyframe_prompt": _keyframe_prompt_for(profile, shot),
                "video_prompt": _video_prompt_for(profile, shot),
                "chunk_plan": compile_duration_chunks(
                    shot.duration_sec,
                    supported_durations_sec=profile.provider_supported_video_durations_sec,
                ),
            }
        )
    return {
        "artifact_type": "afs_adaptive_canvas_script_truth",
        "schema_version": "0.1.0",
        "title": profile.title,
        "logline": profile.logline,
        "style_bible": profile.style_bible,
        "target_duration_sec": profile.target_duration_sec,
        "shot_count": profile.shot_count,
        "characters": list(profile.characters),
        "scenes": list(profile.scenes),
        "shots": shots,
        "asset_extraction": {
            "text_assets": ["script", "shot_summaries", "strategy_reasons"],
            "character_count": len(profile.characters),
            "scene_count": len(profile.scenes),
            "style_reference": "profile_style_bible",
        },
    }


def build_agent_authored_script_input(profile: AdaptiveProductionProfile) -> dict[str, Any]:
    profile.validate()
    if profile.script_source_type != "agent_authored_test_input":
        raise AdaptiveCanvasError("profile is not approved for agent-authored script input")
    script_body = build_script_truth_from_profile(profile)
    script_body_sha256 = sha256_text(
        json.dumps(script_body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    return {
        "artifact_type": "afs_adaptive_canvas_agent_authored_script_input",
        "schema_version": AGENT_SCRIPT_INPUT_SCHEMA_VERSION,
        "aggregate_version": SCRIPT_TRUTH_AGGREGATE_VERSION,
        "script": script_body,
        "lineage": {
            "source_type": "agent_authored_test_input",
            "author_type": "agent",
            "provider_generated": False,
            "llm_success": False,
            "owner_acceptance": False,
            "purpose": "paid_media_vertical_slice",
            "decision_source": profile.script_decision_source,
            "script_body_sha256": script_body_sha256,
            "canonical_schema_version": AGENT_SCRIPT_INPUT_SCHEMA_VERSION,
            "aggregate_version": SCRIPT_TRUTH_AGGREGATE_VERSION,
        },
    }


def _validate_agent_authored_script_input(payload: dict[str, Any], profile: AdaptiveProductionProfile) -> None:
    if payload.get("artifact_type") != "afs_adaptive_canvas_agent_authored_script_input":
        raise AdaptiveCanvasError("agent-authored input artifact type is invalid")
    if payload.get("schema_version") != AGENT_SCRIPT_INPUT_SCHEMA_VERSION:
        raise AdaptiveCanvasError("agent-authored input schema version is invalid")
    if payload.get("aggregate_version") != SCRIPT_TRUTH_AGGREGATE_VERSION:
        raise AdaptiveCanvasError("agent-authored input aggregate version is invalid")
    lineage = payload.get("lineage")
    if not isinstance(lineage, dict):
        raise AdaptiveCanvasError("agent-authored input lineage is required")
    exact = {
        "source_type": "agent_authored_test_input",
        "author_type": "agent",
        "provider_generated": False,
        "llm_success": False,
        "owner_acceptance": False,
        "purpose": "paid_media_vertical_slice",
        "decision_source": profile.script_decision_source,
        "canonical_schema_version": AGENT_SCRIPT_INPUT_SCHEMA_VERSION,
        "aggregate_version": SCRIPT_TRUTH_AGGREGATE_VERSION,
    }
    for key, value in exact.items():
        if lineage.get(key) != value:
            raise AdaptiveCanvasError(f"agent-authored input lineage mismatch: {key}")
    script = payload.get("script")
    if not isinstance(script, dict):
        raise AdaptiveCanvasError("agent-authored input script must be an object")
    digest = sha256_text(json.dumps(script, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    if lineage.get("script_body_sha256") != digest:
        raise AdaptiveCanvasError("agent-authored input script hash mismatch")
    _validate_script(script, profile)
    expected_character_ids = {
        str(item.get("name") or ""): str(item.get("character_id") or safe_id(str(item.get("name") or "")))
        for item in profile.characters
    }
    expected_scene_ids = {
        str(item.get("name") or ""): str(item.get("scene_id") or safe_id(str(item.get("name") or "")))
        for item in profile.scenes
    }
    for order, (shot, expected) in enumerate(zip(script["shots"], profile.shots, strict=True), start=1):
        if int(shot.get("order") or 0) != order:
            raise AdaptiveCanvasError("agent-authored script shot order must match profile")
        expected_ids = [expected_character_ids.get(name, safe_id(name)) for name in expected.characters]
        if shot.get("character_ids") != expected_ids:
            raise AdaptiveCanvasError("agent-authored script character ids must match profile")
        if shot.get("scene_id") != expected_scene_ids.get(expected.location, safe_id(expected.location)):
            raise AdaptiveCanvasError("agent-authored script scene id must match profile")
        for key in ("action", "strategy_reason", "continuity_in", "continuity_out"):
            if not str(shot.get(key) or "").strip():
                raise AdaptiveCanvasError(f"agent-authored script field is required: {key}")


def _materialize_agent_authored_script(payload: dict[str, Any], profile: AdaptiveProductionProfile) -> dict[str, Any]:
    _validate_agent_authored_script_input(payload, profile)
    script = json.loads(json.dumps(payload["script"], ensure_ascii=False))
    script["aggregate_version"] = SCRIPT_TRUTH_AGGREGATE_VERSION
    script["provenance"] = dict(payload["lineage"])
    return script


def _ensure_agent_authored_script_truth(run_root: Path, profile: AdaptiveProductionProfile) -> tuple[dict[str, Any], bool]:
    expected = build_agent_authored_script_input(profile)
    input_path = run_root / AGENT_SCRIPT_INPUT_FILENAME
    if input_path.exists():
        canonical = read_json(input_path)
        _validate_agent_authored_script_input(canonical, profile)
        if canonical["lineage"]["script_body_sha256"] != expected["lineage"]["script_body_sha256"]:
            raise AdaptiveCanvasError("existing agent-authored input does not match approved profile")
    else:
        canonical = expected
        write_json(input_path, canonical)
    script = _materialize_agent_authored_script(canonical, profile)
    truth_path = run_root / "script_truth.json"
    if truth_path.exists():
        existing = read_json(truth_path)
        _validate_script(existing, profile)
        provenance = existing.get("provenance")
        existing_body = {
            key: value
            for key, value in existing.items()
            if key not in {"aggregate_version", "provenance"}
        }
        existing_digest = sha256_text(
            json.dumps(existing_body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        )
        if (
            not isinstance(provenance, dict)
            or provenance != script["provenance"]
            or existing_digest != provenance.get("script_body_sha256")
        ):
            raise AdaptiveCanvasError("existing script truth provenance does not match approved agent input")
        return existing, False
    write_json(truth_path, script)
    return script, True


def seed_agent_authored_script_truth(
    *,
    runtime_root: Path,
    project_id: str,
    run_id: str,
    profile: AdaptiveProductionProfile,
) -> dict[str, Any]:
    profile.validate()
    store = _runtime_store(runtime_root)
    _ensure_project(store, project_id, profile)
    run_root = _run_root(store, project_id, run_id)
    run_root.mkdir(parents=True, exist_ok=True)
    ledger_path = run_root / "charge_ledger.json"
    ledger_sha256_before = sha256_file(ledger_path) if ledger_path.exists() else None
    script, created = _ensure_agent_authored_script_truth(run_root, profile)
    ledger_sha256_after = sha256_file(ledger_path) if ledger_path.exists() else None
    if ledger_sha256_before != ledger_sha256_after:
        raise AdaptiveCanvasError("agent-authored script seeding must not mutate the charge ledger")
    ledger = read_json(ledger_path) if ledger_path.exists() else {"attempts": [], "paid_attempt_count": 0}
    return {
        "status": "seeded" if created else "reused",
        "project_id": project_id,
        "run_id": run_id,
        "source_type": script["provenance"]["source_type"],
        "script_body_sha256": script["provenance"]["script_body_sha256"],
        "script_truth_sha256": sha256_file(run_root / "script_truth.json"),
        "paid_attempt_count": int(ledger.get("paid_attempt_count") or 0),
        "attempt_count": len(ledger.get("attempts") or []),
        "ledger_mutated": False,
        "provider_dispatch_count": 0,
    }


def build_script_v3_output_schema(profile: AdaptiveProductionProfile) -> dict[str, Any]:
    profile.validate()
    string_field = {"type": "string", "minLength": 1}
    character_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["name", "continuity", "role"],
        "properties": {"name": string_field, "continuity": string_field, "role": string_field},
    }
    scene_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["name", "visual_mood", "story_function"],
        "properties": {"name": string_field, "visual_mood": string_field, "story_function": string_field},
    }
    shot_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "shot_id",
            "summary",
            "location",
            "characters",
            "action",
            "camera",
            "target_duration_sec",
            "generation_strategy",
            "strategy_reason",
            "continuity_in",
            "continuity_out",
        ],
        "properties": {
            "shot_id": {"type": "string", "enum": [shot.shot_id for shot in profile.shots]},
            "summary": string_field,
            "location": string_field,
            "characters": {"type": "array", "items": string_field, "minItems": 1},
            "action": string_field,
            "camera": string_field,
            "target_duration_sec": {"type": "number"},
            "generation_strategy": {"type": "string", "enum": ["text_to_video", "image_to_video"]},
            "strategy_reason": string_field,
            "continuity_in": string_field,
            "continuity_out": string_field,
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": ["title", "logline", "style_bible", "characters", "scenes", "shots"],
        "properties": {
            "title": string_field,
            "logline": string_field,
            "style_bible": string_field,
            "characters": {
                "type": "array",
                "items": character_schema,
                "minItems": len(profile.characters),
                "maxItems": len(profile.characters),
            },
            "scenes": {
                "type": "array",
                "items": scene_schema,
                "minItems": len(profile.scenes),
                "maxItems": len(profile.scenes),
            },
            "shots": {
                "type": "array",
                "items": shot_schema,
                "minItems": profile.shot_count,
                "maxItems": profile.shot_count,
            },
        },
    }


def run_adaptive_canvas_production(options: AdaptiveRunOptions, *, callback: Callback | None = None) -> dict[str, Any]:
    if options.mode not in {"real", "fake"}:
        raise ValueError("mode must be real or fake")
    options.profile.validate()
    store = _runtime_store(options.runtime_root)
    _ensure_project(store, options.project_id, options.profile)
    run_root = _run_root(store, options.project_id, options.run_id)
    run_root.mkdir(parents=True, exist_ok=True)
    ledger = ChargeLedger(
        run_root / "charge_ledger.json",
        project_id=options.project_id,
        run_id=options.run_id,
        max_paid_attempts=options.profile.max_paid_attempts,
    )
    state_path = run_root / "run_state.json"
    state = _load_or_init_state(state_path, options)
    _write_state(state_path, state, status="running")
    registry = load_provider_registry(options.provider_config_path) if options.mode == "real" else None
    try:
        script = _ensure_script(run_root, options, ledger, registry, callback)
        reference = _ensure_reference_sheet(run_root, options, ledger, registry, script, callback)
        keyframes = _ensure_keyframes(run_root, options, ledger, registry, script, reference, callback)
        chunks = _ensure_video_chunks(run_root, options, ledger, registry, script, keyframes, callback)
        shot_composes = _ensure_shot_composes(run_root, options, chunks, callback)
        final = _ensure_final_compose(run_root, options, shot_composes, callback)
        qa = _run_technical_qa(run_root, options, shot_composes, final, callback)
        registered = _register_delivery(store, run_root, options, script, reference, keyframes, chunks, shot_composes, final, qa, ledger)
        _write_state(state_path, state, status="succeeded", registered=registered)
        _emit(callback, "REGISTERED", "succeeded", project_id=options.project_id, run_id=options.run_id)
        return {
            "status": "succeeded",
            "project_id": options.project_id,
            "run_id": options.run_id,
            "run_root": str(run_root),
            "final_path": str(final["path"]),
            "final_sha256": final["sha256"],
            "final_duration_sec": final["duration_sec"],
            "paid_attempt_count": ledger.paid_attempt_count,
            "ledger_path": str(ledger.path),
            "registered": registered,
            "qa": qa,
        }
    except Exception as exc:
        _write_state(state_path, state, status="failed", safe_error=safe_error(exc))
        raise


def load_adaptive_workspace(store: RuntimeStore, *, project_id: str, run_id: str | None = None) -> dict[str, Any]:
    runs = store.list_production_runs(project_id)
    runs = [run for run in runs if run.get("artifact_type") == "afs_adaptive_canvas_v2_production_run"]
    if run_id is not None:
        runs = [run for run in runs if run.get("run_id") == run_id]
    if not runs:
        raise KeyError(project_id)
    run = sorted(runs, key=lambda item: str(item.get("created_at") or item.get("run_id") or ""))[-1]
    return {
        "schema_version": "afs.adaptive_canvas_v2.workspace.v0.1",
        "project_id": project_id,
        "run_id": run["run_id"],
        "script": run["script"],
        "assets": run["assets"],
        "shots": run["shots"],
        "timeline": run["timeline"],
        "final_demo": run["final_demo"],
        "qa": run["qa"],
        "provider_dispatch_count": run["attempts"]["paid_attempt_count"],
        "non_claims": run["non_claims"],
    }


def _ensure_project(store: RuntimeStore, project_id: str, profile: AdaptiveProductionProfile) -> None:
    if not store.project_manifest_path(project_id).exists():
        store.create_project_manifest(
            project_id=project_id,
            project_type=profile.project_type,
            goal=profile.logline,
            status="in_progress",
        )
    else:
        store.ensure_project_manifest(project_id)


def _run_root(store: RuntimeStore, project_id: str, run_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "adaptive_canvas_v2" / safe_id(run_id)


def _load_or_init_state(path: Path, options: AdaptiveRunOptions) -> dict[str, Any]:
    if path.exists():
        return read_json(path)
    return {
        "schema_version": ADAPTIVE_SCHEMA_VERSION,
        "project_id": options.project_id,
        "run_id": options.run_id,
        "mode": options.mode,
        "created_at": utc_now(),
        "does_not_store_secrets": True,
    }


def _write_state(path: Path, state: dict[str, Any], *, status: str, **updates: Any) -> None:
    now = utc_now()
    previous_safe_error = state.get("safe_error")
    if status in {"running", "succeeded"} and isinstance(previous_safe_error, dict):
        _append_safe_error_history(state, previous_safe_error, recorded_at=str(state.get("updated_at") or now))
        state.pop("safe_error", None)
    state.update(updates)
    if status == "failed" and isinstance(state.get("safe_error"), dict):
        _append_safe_error_history(state, state["safe_error"], recorded_at=now)
    state["status"] = status
    state["updated_at"] = now
    write_json(path, state)


def _append_safe_error_history(state: dict[str, Any], error: dict[str, Any], *, recorded_at: str) -> None:
    history = [item for item in state.get("error_history") or [] if isinstance(item, dict)]
    if history and history[-1].get("safe_error") == error:
        state["error_history"] = history[-20:]
        return
    history.append(
        {
            "status": "failed",
            "recorded_at": recorded_at,
            "safe_error": dict(error),
        }
    )
    state["error_history"] = history[-20:]


def _ensure_script(
    run_root: Path,
    options: AdaptiveRunOptions,
    ledger: ChargeLedger,
    registry: ProviderRegistry | None,
    callback: Callback | None,
) -> dict[str, Any]:
    if options.profile.script_source_type == "agent_authored_test_input":
        _emit(callback, "SCRIPT", "started", source_type="agent_authored_test_input")
        script, created = _ensure_agent_authored_script_truth(run_root, options.profile)
        _emit(
            callback,
            "SCRIPT",
            "succeeded" if created else "reused",
            source_type="agent_authored_test_input",
            provider_dispatch_count=0,
        )
        return script
    path = run_root / "script_truth.json"
    prompt = _script_prompt(options.profile)
    if path.exists():
        script = read_json(path)
        _validate_script(script, options.profile)
        _emit(callback, "SCRIPT", "reused")
        return script
    _emit(callback, "SCRIPT", "started")
    if options.mode == "fake":
        script = build_script_truth_from_profile(options.profile)
        write_json(path, script)
        ledger.record_fake_success(
            stage="script",
            shot_id=None,
            chunk_id=None,
            candidate_id=options.profile.script_candidate_id,
            capability="llm",
            prompt=prompt,
            artifact=_artifact_version("script", path, run_root, options.project_id, options.run_id),
        )
        _emit(callback, "SCRIPT", "succeeded", provider_dispatch_count=0)
        return script
    if registry is None:
        raise AdaptiveCanvasError("provider registry is required in real mode")
    contract_id = options.profile.script_contract_id
    output_schema = build_script_v3_output_schema(options.profile) if contract_id == SCRIPT_V3_CONTRACT_ID else None
    schema_digest = structured_output_schema_digest(output_schema) if output_schema is not None else None
    result = _real_provider_attempt(
        ledger,
        registry,
        capability="llm",
        service_id=options.profile.llm_service_id,
        stage="script",
        shot_id=None,
        chunk_id=None,
        candidate_id=options.profile.script_candidate_id,
        prompt=prompt,
        contract_id=contract_id,
        contract_schema_digest=schema_digest,
        max_provider_starts=1 if contract_id == SCRIPT_V3_CONTRACT_ID else 2,
        request=ProviderDispatchRequest(
            prompt=prompt,
            output_dir=run_root / "provider_outputs" / "script",
            task_type=contract_id,
            structured_output_contract_id=contract_id,
            structured_output_schema=output_schema,
            structured_output_schema_digest=schema_digest,
            timeout_sec=240.0,
        ),
    )
    try:
        if contract_id == SCRIPT_V3_CONTRACT_ID:
            structured = result.get("structured_output")
            if not isinstance(structured, dict):
                raise AdaptiveCanvasError("structured script final response is missing")
            _validate_script_v3_payload(structured, options.profile)
            script = _parse_script_payload(structured, options.profile)
        else:
            script = _parse_script_json(str(result.get("text") or ""), options.profile)
        _validate_script(script, options.profile)
        write_json(path, script)
        ledger.mark_succeeded(
            str(result["attempt_id"]),
            _artifact_version("script", path, run_root, options.project_id, options.run_id),
        )
    except Exception as exc:
        ledger.mark_failed(str(result["attempt_id"]), exc)
        raise
    _emit(callback, "SCRIPT", "succeeded", paid_attempt_count=ledger.paid_attempt_count)
    return script


def _ensure_reference_sheet(
    run_root: Path,
    options: AdaptiveRunOptions,
    ledger: ChargeLedger,
    registry: ProviderRegistry | None,
    script: dict[str, Any],
    callback: Callback | None,
) -> dict[str, Any] | None:
    if not _needs_reference(script, options.profile):
        _emit(callback, "REFERENCE", "not_required")
        return None
    path = run_root / "reference_sheet.png"
    prompt = _reference_prompt(script, options.profile)
    if path.exists():
        artifact = _image_artifact("reference_sheet", path, run_root, options.project_id, options.run_id)
        _emit(callback, "REFERENCE", "reused", sha256=artifact["sha256"])
        return artifact
    _emit(callback, "REFERENCE", "started")
    if options.mode == "fake":
        _fake_png(path, "0x172554")
        artifact = _image_artifact("reference_sheet", path, run_root, options.project_id, options.run_id)
        ledger.record_fake_success(
            stage="reference_sheet",
            shot_id=None,
            chunk_id=None,
            candidate_id="reference-v1",
            capability="image",
            prompt=prompt,
            artifact=artifact,
        )
        _emit(callback, "REFERENCE", "succeeded", provider_dispatch_count=0)
        return artifact
    if registry is None:
        raise AdaptiveCanvasError("provider registry is required in real mode")
    output_dir = run_root / "provider_outputs" / "reference_sheet"
    result = _real_provider_attempt(
        ledger,
        registry,
        capability="image",
        service_id=IMAGE_PROVIDER_SERVICE_ID,
        stage="reference_sheet",
        shot_id=None,
        chunk_id=None,
        candidate_id="reference-v1",
        prompt=prompt,
        request=ProviderDispatchRequest(
            prompt=prompt,
            output_dir=output_dir,
            image_operation="generate",
            aspect_ratio=options.profile.media_aspect_ratio,
            candidate_count=1,
            timeout_sec=360.0,
        ),
    )
    try:
        _copy_bytes(_first_output_path(output_dir, result, "image_path"), path)
        artifact = _image_artifact("reference_sheet", path, run_root, options.project_id, options.run_id)
        ledger.mark_succeeded(str(result["attempt_id"]), artifact)
    except Exception as exc:
        ledger.mark_failed(str(result["attempt_id"]), exc)
        raise
    _emit(callback, "REFERENCE", "succeeded", paid_attempt_count=ledger.paid_attempt_count)
    return artifact


def _ensure_keyframes(
    run_root: Path,
    options: AdaptiveRunOptions,
    ledger: ChargeLedger,
    registry: ProviderRegistry | None,
    script: dict[str, Any],
    reference: dict[str, Any] | None,
    callback: Callback | None,
) -> dict[str, dict[str, Any]]:
    keyframes: dict[str, dict[str, Any]] = {}
    reference_path = Path(str(reference["path"])) if reference else None
    for index, shot in enumerate(script["shots"], start=1):
        shot_id = str(shot["shot_id"])
        if shot["generation_strategy"] == "text_to_video":
            _emit(callback, f"KEYFRAME_{index}", "not_required", shot_id=shot_id)
            continue
        if reference_path is None:
            raise AdaptiveCanvasError("image_to_video shot requires a reference sheet")
        path = run_root / "keyframes" / f"{shot_id}.png"
        prompt = _shot_keyframe_prompt(script, shot, options.profile)
        if path.exists():
            artifact = _image_artifact("keyframe", path, run_root, options.project_id, options.run_id, shot_id=shot_id)
            keyframes[shot_id] = artifact
            _emit(callback, f"KEYFRAME_{index}", "reused", shot_id=shot_id, sha256=artifact["sha256"])
            continue
        _emit(callback, f"KEYFRAME_{index}", "started", shot_id=shot_id)
        if options.mode == "fake":
            _fake_png(path, _fake_color(index))
            artifact = _image_artifact("keyframe", path, run_root, options.project_id, options.run_id, shot_id=shot_id)
            ledger.record_fake_success(
                stage="keyframe",
                shot_id=shot_id,
                chunk_id=None,
                candidate_id="candidate-001",
                capability="image",
                prompt=prompt,
                artifact=artifact,
            )
            keyframes[shot_id] = artifact
            _emit(callback, f"KEYFRAME_{index}", "succeeded", provider_dispatch_count=0)
            continue
        if registry is None:
            raise AdaptiveCanvasError("provider registry is required in real mode")
        output_dir = run_root / "provider_outputs" / "keyframes" / shot_id
        result = _real_provider_attempt(
            ledger,
            registry,
            capability="image",
            service_id=IMAGE_PROVIDER_SERVICE_ID,
            stage="keyframe",
            shot_id=shot_id,
            chunk_id=None,
            candidate_id="candidate-001",
            prompt=prompt,
            request=ProviderDispatchRequest(
                prompt=prompt,
                output_dir=output_dir,
                image_operation="edit",
                edit_source_image_path=reference_path,
                edit_reference_image_paths=(reference_path,),
                image_input_fidelity="high",
                aspect_ratio=options.profile.media_aspect_ratio,
                candidate_count=1,
                timeout_sec=360.0,
            ),
        )
        try:
            _copy_bytes(_first_output_path(output_dir, result, "image_path"), path)
            artifact = _image_artifact("keyframe", path, run_root, options.project_id, options.run_id, shot_id=shot_id)
            ledger.mark_succeeded(str(result["attempt_id"]), artifact)
        except Exception as exc:
            ledger.mark_failed(str(result["attempt_id"]), exc)
            raise
        keyframes[shot_id] = artifact
        _emit(callback, f"KEYFRAME_{index}", "succeeded", paid_attempt_count=ledger.paid_attempt_count)
    return keyframes


def _ensure_video_chunks(
    run_root: Path,
    options: AdaptiveRunOptions,
    ledger: ChargeLedger,
    registry: ProviderRegistry | None,
    script: dict[str, Any],
    keyframes: dict[str, dict[str, Any]],
    callback: Callback | None,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for shot_index, shot in enumerate(script["shots"], start=1):
        shot_id = str(shot["shot_id"])
        first_frame = Path(str(keyframes[shot_id]["path"])) if shot_id in keyframes else None
        for chunk_index, chunk in enumerate(shot["chunk_plan"], start=1):
            chunk_id = str(chunk["chunk_id"])
            path = run_root / "video_chunks" / shot_id / f"{chunk_id}.mp4"
            prompt = _shot_video_prompt(script, shot, chunk_index, int(chunk["provider_duration_sec"]), options.profile)
            anchor = first_frame
            if chunk.get("requires_continuity_anchor"):
                previous = run_root / "video_chunks" / shot_id / f"chunk-{chunk_index - 1:02d}.mp4"
                anchor = run_root / "continuity_anchors" / shot_id / f"tail_after_chunk_{chunk_index - 1:02d}.png"
                if not anchor.exists():
                    _extract_tail_frame(previous, anchor)
            if path.exists():
                artifact = _video_artifact(
                    "video_chunk",
                    path,
                    run_root,
                    options.project_id,
                    options.run_id,
                    shot_id=shot_id,
                    chunk_id=chunk_id,
                    continuity_anchor_path=anchor,
                )
                chunks.append(artifact)
                _emit(callback, f"VIDEO_SHOT_{shot_index}_CHUNK_{chunk_index}", "reused", sha256=artifact["sha256"])
                continue
            _emit(callback, f"VIDEO_SHOT_{shot_index}_CHUNK_{chunk_index}", "started", duration_sec=chunk["provider_duration_sec"])
            if options.mode == "fake":
                _fake_video(path, duration_sec=int(chunk["provider_duration_sec"]), color=_fake_color(shot_index + chunk_index))
                artifact = _video_artifact(
                    "video_chunk",
                    path,
                    run_root,
                    options.project_id,
                    options.run_id,
                    shot_id=shot_id,
                    chunk_id=chunk_id,
                    continuity_anchor_path=anchor,
                )
                ledger.record_fake_success(
                    stage="video_chunk",
                    shot_id=shot_id,
                    chunk_id=chunk_id,
                    candidate_id="candidate-001",
                    capability="video",
                    prompt=prompt,
                    artifact=artifact,
                )
                chunks.append(artifact)
                _emit(callback, f"VIDEO_SHOT_{shot_index}_CHUNK_{chunk_index}", "succeeded", provider_dispatch_count=0)
                continue
            if registry is None:
                raise AdaptiveCanvasError("provider registry is required in real mode")
            if shot["generation_strategy"] == "text_to_video":
                descriptor = registry.descriptor(VIDEO_PROVIDER_SERVICE_ID)
                if descriptor.frame_slots.get("first_frame") == "required":
                    raise AdaptiveCanvasError("configured video provider requires image_to_video first-frame input")
            if shot["generation_strategy"] == "image_to_video" and anchor is None:
                raise AdaptiveCanvasError("image_to_video chunk requires selected keyframe or continuity anchor")
            result = _real_video_attempt(
                options,
                ledger,
                registry,
                shot_id=shot_id,
                chunk_id=chunk_id,
                prompt=prompt,
                first_frame=anchor,
                duration_sec=int(chunk["provider_duration_sec"]),
                output_dir=run_root / "provider_outputs" / "video_chunks" / shot_id / chunk_id,
            )
            try:
                _copy_bytes(
                    _first_output_path(
                        run_root / "provider_outputs" / "video_chunks" / shot_id / chunk_id,
                        result,
                        "video_path",
                    ),
                    path,
                )
                artifact = _video_artifact(
                    "video_chunk",
                    path,
                    run_root,
                    options.project_id,
                    options.run_id,
                    shot_id=shot_id,
                    chunk_id=chunk_id,
                    continuity_anchor_path=anchor,
                )
                ledger.mark_succeeded(
                    str(result["attempt_id"]),
                    artifact,
                    provider_task_id=str(result.get("provider_task_id") or ""),
                )
            except Exception as exc:
                ledger.mark_failed(str(result["attempt_id"]), exc)
                raise
            chunks.append(artifact)
            _emit(callback, f"VIDEO_SHOT_{shot_index}_CHUNK_{chunk_index}", "succeeded", paid_attempt_count=ledger.paid_attempt_count)
    return chunks


def _ensure_shot_composes(
    run_root: Path,
    options: AdaptiveRunOptions,
    chunks: list[dict[str, Any]],
    callback: Callback | None,
) -> list[dict[str, Any]]:
    shot_composes: list[dict[str, Any]] = []
    for shot_index, shot in enumerate(options.profile.shots, start=1):
        out = run_root / "shot_composes" / f"{shot.shot_id}.mp4"
        if not out.exists():
            _emit(callback, f"SHOT_COMPOSE_{shot_index}", "started", target_duration_sec=shot.duration_sec)
            chunk_paths = [Path(item["path"]) for item in chunks if item.get("shot_id") == shot.shot_id]
            if not chunk_paths:
                raise AdaptiveCanvasError(f"shot {shot.shot_id} requires at least one video chunk")
            _concat_videos(chunk_paths, out, duration_sec=shot.duration_sec)
        artifact = _video_artifact("shot_compose", out, run_root, options.project_id, options.run_id, shot_id=shot.shot_id)
        shot_composes.append(artifact)
        _emit(callback, f"SHOT_COMPOSE_{shot_index}", "succeeded", duration_sec=artifact["duration_sec"])
    return shot_composes


def _ensure_final_compose(
    run_root: Path,
    options: AdaptiveRunOptions,
    shot_composes: list[dict[str, Any]],
    callback: Callback | None,
) -> dict[str, Any]:
    out = run_root / "final" / "adaptive_canvas_v2_final.mp4"
    if not out.exists():
        _emit(callback, "FINAL_COMPOSE", "started", target_duration_sec=options.profile.target_duration_sec)
        _concat_videos([Path(item["path"]) for item in shot_composes], out, duration_sec=options.profile.target_duration_sec)
    artifact = _video_artifact("final_compose", out, run_root, options.project_id, options.run_id)
    _emit(callback, "FINAL_COMPOSE", "succeeded", duration_sec=artifact["duration_sec"], sha256=artifact["sha256"])
    return artifact


def _run_technical_qa(
    run_root: Path,
    options: AdaptiveRunOptions,
    shot_composes: list[dict[str, Any]],
    final: dict[str, Any],
    callback: Callback | None,
) -> dict[str, Any]:
    _emit(callback, "QA", "started")
    findings: list[dict[str, Any]] = []
    expected = {shot.shot_id: float(shot.duration_sec) for shot in options.profile.shots}
    for shot in shot_composes:
        target = expected[str(shot.get("shot_id"))]
        duration = float(shot.get("duration_sec") or 0.0)
        if abs(duration - target) > 0.75:
            findings.append({"severity": "P0", "scope": shot.get("shot_id"), "issue": "shot_duration_out_of_tolerance"})
        if int(shot.get("audio_stream_count") or 0) != 0:
            findings.append({"severity": "P0", "scope": shot.get("shot_id"), "issue": "shot_has_audio"})
    final_duration = float(final.get("duration_sec") or 0.0)
    if abs(final_duration - options.profile.target_duration_sec) > 1.5:
        findings.append({"severity": "P0", "scope": "final", "issue": "final_duration_out_of_tolerance"})
    if int(final.get("audio_stream_count") or 0) != 0:
        findings.append({"severity": "P0", "scope": "final", "issue": "final_has_audio"})
    decode = _decode_check(Path(final["path"]))
    if decode["status"] != "pass":
        findings.append({"severity": "P0", "scope": "final", "issue": "decode_failed", "details": decode})
    media_metrics = _video_quality_metrics(Path(final["path"]))
    if media_metrics["status"] != "pass":
        findings.append({"severity": "P0", "scope": "final", "issue": "media_metrics_failed", "details": media_metrics})
    if media_metrics.get("black_segment_count", 0) > 0:
        findings.append(
            {
                "severity": "P1",
                "scope": "final",
                "issue": "black_segment_detected",
                "count": media_metrics["black_segment_count"],
            }
        )
    if media_metrics.get("freeze_event_count", 0) > 0:
        findings.append(
            {
                "severity": "P1",
                "scope": "final",
                "issue": "freeze_or_repeated_frames_detected",
                "count": media_metrics["freeze_event_count"],
            }
        )
    contact_sheet = run_root / "qa" / "contact_sheet_1fps.jpg"
    _contact_sheet(Path(final["path"]), contact_sheet)
    qa_scores = _technical_qa_scores(findings, media_metrics)
    qa = {
        "artifact_type": "afs_adaptive_canvas_v2_technical_qa",
        "schema_version": "0.2.0",
        "project_id": options.project_id,
        "run_id": options.run_id,
        "status": "pass" if not any(item["severity"] in {"P0", "P1"} for item in findings) else "failed",
        "findings": findings,
        "final_duration_sec": final_duration,
        "shot_durations_sec": [float(item.get("duration_sec") or 0.0) for item in shot_composes],
        "final_sha256": final["sha256"],
        "final_decode_status": decode["status"],
        "media_metrics": media_metrics,
        "technical_scores": qa_scores,
        "contact_sheet_sha256": sha256_file(contact_sheet),
        "visual_qa_boundary": "automated technical decode, duration, resolution, fps, frame count, black/freeze event scan, hash, no-audio, and contact-sheet evidence only",
    }
    write_json(run_root / "qa" / "technical_qa.json", qa)
    _emit(callback, "QA", qa["status"], finding_count=len(findings))
    if qa["status"] != "pass":
        raise AdaptiveCanvasError("technical QA failed")
    return qa


def _register_delivery(
    store: RuntimeStore,
    run_root: Path,
    options: AdaptiveRunOptions,
    script: dict[str, Any],
    reference: dict[str, Any] | None,
    keyframes: dict[str, dict[str, Any]],
    chunks: list[dict[str, Any]],
    shot_composes: list[dict[str, Any]],
    final: dict[str, Any],
    qa: dict[str, Any],
    ledger: ChargeLedger,
) -> dict[str, Any]:
    final_ref = store.register_artifact(Path(final["path"]), role="adaptive_canvas_v2_final_video")
    qa_ref = store.register_artifact(run_root / "qa" / "technical_qa.json", role="adaptive_canvas_v2_technical_qa")
    ledger_ref = store.register_artifact(ledger.path, role="adaptive_canvas_v2_charge_ledger")
    delivery_manifest = {
        "artifact_type": "afs_adaptive_canvas_v2_delivery_manifest",
        "schema_version": "0.1.0",
        "project_id": options.project_id,
        "run_id": options.run_id,
        "status": "registered",
        "title": script["title"],
        "shot_count": len(script["shots"]),
        "target_duration_sec": options.profile.target_duration_sec,
        "final_duration_sec": final["duration_sec"],
        "final_sha256": final["sha256"],
        "reference_sha256": reference.get("sha256") if reference else None,
        "keyframe_count": len(keyframes),
        "video_chunk_count": len(chunks),
        "paid_attempt_count": ledger.paid_attempt_count,
        "final_artifact_id": final_ref["artifact_id"],
        "qa_artifact_id": qa_ref["artifact_id"],
        "ledger_artifact_id": ledger_ref["artifact_id"],
        "does_not_store_secrets": True,
        "does_not_store_private_paths": True,
    }
    delivery_path = run_root / "delivery_manifest.json"
    write_json(delivery_path, delivery_manifest)
    delivery_ref = store.register_artifact(delivery_path, role="adaptive_canvas_v2_delivery_manifest")
    run_payload = _production_run_payload(
        options=options,
        script=script,
        reference=reference,
        keyframes=keyframes,
        final=final,
        qa=qa,
        delivery_ref=delivery_ref,
        final_ref=final_ref,
        ledger_ref=ledger_ref,
        paid_attempt_count=ledger.paid_attempt_count,
    )
    store.write_production_run(options.project_id, run_payload)
    run_ref = store.register_artifact(store.production_run_path(options.project_id, options.run_id), role="production_run")
    store.update_project_manifest(
        options.project_id,
        {"packages": [delivery_ref, qa_ref, ledger_ref, run_ref]},
        status="ready_for_next_round",
    )
    return {
        "production_run_artifact_id": run_ref["artifact_id"],
        "delivery_manifest_artifact_id": delivery_ref["artifact_id"],
        "final_artifact_id": final_ref["artifact_id"],
        "qa_artifact_id": qa_ref["artifact_id"],
        "ledger_artifact_id": ledger_ref["artifact_id"],
    }


def _production_run_payload(
    *,
    options: AdaptiveRunOptions,
    script: dict[str, Any],
    reference: dict[str, Any] | None,
    keyframes: dict[str, dict[str, Any]],
    final: dict[str, Any],
    qa: dict[str, Any],
    delivery_ref: dict[str, Any],
    final_ref: dict[str, Any],
    ledger_ref: dict[str, Any],
    paid_attempt_count: int,
) -> dict[str, Any]:
    shots = []
    cursor = 0.0
    for shot in script["shots"]:
        duration = float(shot["target_duration_sec"])
        shots.append(
            {
                "shot_id": shot["shot_id"],
                "order": shot.get("order"),
                "summary": shot["summary"],
                "location": shot["location"],
                "characters": shot["characters"],
                "character_ids": shot.get("character_ids", []),
                "scene_id": shot.get("scene_id"),
                "action": shot["action"],
                "target_duration_sec": duration,
                "timeline_in_sec": round(cursor, 3),
                "timeline_out_sec": round(cursor + duration, 3),
                "generation_strategy": shot["generation_strategy"],
                "strategy_reason": shot["strategy_reason"],
                "continuity_in": shot["continuity_in"],
                "continuity_out": shot["continuity_out"],
                "reference_binding": _shot_reference_binding(shot, reference),
                "selected_keyframe": _shot_keyframe_binding(shot, keyframes),
                "chunk_plan": shot["chunk_plan"],
                "status": "selected_and_composed",
            }
        )
        cursor = round(cursor + duration, 3)
    return {
        "artifact_type": "afs_adaptive_canvas_v2_production_run",
        "schema_version": "0.1.0",
        "project_id": options.project_id,
        "run_id": options.run_id,
        "created_at": utc_now(),
        "status": "ready_for_review",
        "script": {
            "title": script["title"],
            "logline": script["logline"],
            "target_duration_sec": script["target_duration_sec"],
            "shot_count": script["shot_count"],
            "aggregate_version": script.get("aggregate_version"),
            "provenance": script.get("provenance"),
        },
        "assets": {
            "characters": script["characters"],
            "scenes": script["scenes"],
            "style_bible": script["style_bible"],
        },
        "shots": shots,
        "timeline": {
            "order": [item["shot_id"] for item in shots],
            "duration_sec": round(cursor, 3),
            "assembly_mode": "storyboard_order_simple_concat",
        },
        "final_demo": {
            "status": "silent_video_ready_for_owner_review",
            "artifact_id": final_ref["artifact_id"],
            "sha256": final["sha256"],
            "duration_sec": final["duration_sec"],
            "audio_stream_count": final["audio_stream_count"],
        },
        "qa": {"status": qa["status"], "delivery_manifest_artifact_id": delivery_ref["artifact_id"]},
        "attempts": {
            "paid_attempt_count": paid_attempt_count,
            "hard_cap": options.profile.max_paid_attempts,
            "ledger_artifact_id": ledger_ref["artifact_id"],
        },
        "non_claims": [
            "not_tts_or_audio",
            "not_human_creative_acceptance",
            "not_business_validation",
            "not_public_release",
        ],
    }


def _shot_reference_binding(shot: dict[str, Any], reference: dict[str, Any] | None) -> dict[str, Any]:
    if shot["generation_strategy"] != "image_to_video":
        return {"required": False, "status": "not_required"}
    if reference is None:
        return {"required": True, "status": "missing"}
    return {"required": True, "status": "selected", "reference_sha256": reference["sha256"]}


def _shot_keyframe_binding(shot: dict[str, Any], keyframes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if shot["generation_strategy"] != "image_to_video":
        return {"required": False, "status": "not_required"}
    keyframe = keyframes.get(str(shot["shot_id"]))
    if not keyframe:
        return {"required": True, "status": "missing"}
    return {"required": True, "status": "selected", "keyframe_sha256": keyframe["sha256"]}


def _real_provider_attempt(
    ledger: ChargeLedger,
    registry: ProviderRegistry,
    *,
    capability: str,
    service_id: str,
    stage: str,
    shot_id: str | None,
    chunk_id: str | None,
    candidate_id: str,
    prompt: str,
    request: ProviderDispatchRequest,
    contract_id: str | None = None,
    contract_schema_digest: str | None = None,
    max_provider_starts: int = 2,
) -> dict[str, Any]:
    if ledger.successful_attempt(
        ledger.fingerprint(
            stage=stage,
            shot_id=shot_id,
            chunk_id=chunk_id,
            candidate_id=candidate_id,
            prompt=prompt,
            contract_id=contract_id,
            contract_schema_digest=contract_schema_digest,
        )
    ):
        raise AdaptiveCanvasError("provider artifact is marked successful but output is missing from run root")
    attempt = ledger.reserve(
        stage=stage,
        shot_id=shot_id,
        chunk_id=chunk_id,
        candidate_id=candidate_id,
        capability=capability,
        service_id=service_id,
        prompt=prompt,
        contract_id=contract_id,
        contract_schema_digest=contract_schema_digest,
        max_provider_starts=max_provider_starts,
    )
    try:
        ledger.mark_started(str(attempt["attempt_id"]))
        result = registry.dispatch(capability, service_id, request)
        return {**result, "attempt_id": attempt["attempt_id"]}
    except Exception as exc:
        ledger.mark_failed(str(attempt["attempt_id"]), exc)
        raise


def _real_video_attempt(
    options: AdaptiveRunOptions,
    ledger: ChargeLedger,
    registry: ProviderRegistry,
    *,
    shot_id: str,
    chunk_id: str,
    prompt: str,
    first_frame: Path | None,
    duration_sec: int,
    output_dir: Path,
) -> dict[str, Any]:
    fingerprint = ledger.fingerprint(
        stage="video_chunk",
        shot_id=shot_id,
        chunk_id=chunk_id,
        candidate_id="candidate-001",
        prompt=prompt,
    )
    resumable = ledger.resumable_submitted_attempt(fingerprint)
    attempt = resumable or ledger.reserve(
        stage="video_chunk",
        shot_id=shot_id,
        chunk_id=chunk_id,
        candidate_id="candidate-001",
        capability="video",
        service_id=VIDEO_PROVIDER_SERVICE_ID,
        prompt=prompt,
    )
    try:
        if resumable:
            submitted = dict(resumable["provider_poll_task"])
            task_id = str(resumable.get("provider_task_id") or "")
        else:
            request = ProviderDispatchRequest(
                prompt=prompt,
                output_dir=output_dir,
                aspect_ratio=options.profile.media_aspect_ratio,
                candidate_count=1,
                timeout_sec=900.0,
                duration_sec=duration_sec,
                resolution=options.profile.video_resolution,
                motion=options.profile.video_motion,
                input_mode="first_frame" if first_frame else None,
                reference_image_paths=(first_frame,) if first_frame else (),
            )
            ledger.mark_started(str(attempt["attempt_id"]))
            submitted = registry.submit("video", VIDEO_PROVIDER_SERVICE_ID, request)
            task_id = str((submitted.get("task") or {}).get("task_id") or "")
            ledger.mark_submitted(str(attempt["attempt_id"]), provider_task_id=task_id, provider_poll_task=submitted)
        deadline = time.monotonic() + options.video_poll_timeout_sec
        while True:
            raw = registry.poll("video", VIDEO_PROVIDER_SERVICE_ID, submitted)
            if str(raw.get("status") or "") == "succeeded":
                return {**raw, "attempt_id": attempt["attempt_id"], "provider_task_id": task_id}
            if str(raw.get("status") or "") != "running":
                raise AdaptiveCanvasError(f"unexpected video provider status: {raw.get('status')}")
            if time.monotonic() >= deadline:
                raise AdaptiveCanvasError("video provider polling timed out")
            time.sleep(options.video_poll_interval_sec)
    except Exception as exc:
        ledger.mark_failed(str(attempt["attempt_id"]), exc)
        raise


def _script_prompt(profile: AdaptiveProductionProfile) -> str:
    profile_payload = {
        "title": profile.title,
        "logline": profile.logline,
        "style_bible": profile.style_bible,
        "characters": profile.characters,
        "scenes": profile.scenes,
        "shots": [
            {
                "shot_id": shot.shot_id,
                "target_duration_sec": shot.duration_sec,
                "generation_strategy": shot.generation_strategy,
                "story_intent": shot.summary,
            }
            for shot in profile.shots
        ],
    }
    return (
        "Return only strict JSON for one versioned Script/Story truth. Preserve the exact shot ids, durations, "
        "and generation_strategy values provided. Expand action/camera/continuity only; do not add shots. "
        "No dock, lighthouse, robot, blue raincoat. Profile JSON: "
        f"{json.dumps(profile_payload, ensure_ascii=False)}"
    )


def _parse_script_json(text: str, profile: AdaptiveProductionProfile) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise AdaptiveCanvasError("LLM did not return a JSON object")
    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise AdaptiveCanvasError("LLM script JSON must be an object")
    return _parse_script_payload(payload, profile)


def _validate_script_v3_payload(payload: dict[str, Any], profile: AdaptiveProductionProfile) -> None:
    shots = payload.get("shots")
    if not isinstance(shots, list) or len(shots) != profile.shot_count:
        raise AdaptiveCanvasError("structured script shot count must match profile")
    for supplied, expected in zip(shots, profile.shots, strict=True):
        if not isinstance(supplied, dict) or str(supplied.get("shot_id") or "") != expected.shot_id:
            raise AdaptiveCanvasError("structured script shot order must match profile")
        if float(supplied.get("target_duration_sec") or 0.0) != float(expected.duration_sec):
            raise AdaptiveCanvasError("structured script duration must match profile")
        if str(supplied.get("generation_strategy") or "") != expected.generation_strategy:
            raise AdaptiveCanvasError("structured script strategy must match profile")


def _parse_script_payload(payload: dict[str, Any], profile: AdaptiveProductionProfile) -> dict[str, Any]:
    fallback = build_script_truth_from_profile(profile)
    merged = {**fallback, **payload}
    shot_by_id = {str(shot.get("shot_id")): shot for shot in payload.get("shots", []) if isinstance(shot, dict)}
    shots = []
    for fallback_shot in fallback["shots"]:
        supplied = shot_by_id.get(str(fallback_shot["shot_id"]), {})
        merged_shot = {**fallback_shot, **{key: value for key, value in supplied.items() if value not in (None, "", [])}}
        merged_shot["target_duration_sec"] = fallback_shot["target_duration_sec"]
        merged_shot["generation_strategy"] = fallback_shot["generation_strategy"]
        merged_shot["strategy_reason"] = fallback_shot["strategy_reason"]
        merged_shot["chunk_plan"] = fallback_shot["chunk_plan"]
        shots.append(merged_shot)
    merged["shots"] = shots
    merged["artifact_type"] = "afs_adaptive_canvas_script_truth"
    merged["schema_version"] = "0.1.0"
    return merged


def _validate_script(script: dict[str, Any], profile: AdaptiveProductionProfile) -> None:
    shots = script.get("shots")
    if not isinstance(shots, list) or len(shots) != profile.shot_count:
        raise AdaptiveCanvasError("script shot count must match profile")
    forbidden = ("dock", "lighthouse", "robot", "blue raincoat")
    lowered = json.dumps(script, ensure_ascii=False).lower()
    for value in forbidden:
        if value in lowered:
            raise AdaptiveCanvasError(f"forbidden fixed template leaked into script: {value}")
    expected = {shot.shot_id: shot for shot in profile.shots}
    for shot in shots:
        shot_id = str(shot.get("shot_id") or "")
        if shot_id not in expected:
            raise AdaptiveCanvasError(f"unexpected shot id: {shot_id}")
        if float(shot.get("target_duration_sec") or 0.0) != float(expected[shot_id].duration_sec):
            raise AdaptiveCanvasError("shot duration must match profile")
        if str(shot.get("generation_strategy") or "") != expected[shot_id].generation_strategy:
            raise AdaptiveCanvasError("shot strategy must match profile")
        if not shot.get("chunk_plan"):
            raise AdaptiveCanvasError("shot must include chunk plan")


def _needs_reference(script: dict[str, Any], profile: AdaptiveProductionProfile) -> bool:
    if not profile.reference_sheet_required:
        return False
    return any(shot.get("generation_strategy") == "image_to_video" for shot in script.get("shots", []))


def _reference_prompt(script: dict[str, Any], profile: AdaptiveProductionProfile) -> str:
    if profile.media_prompt_style == "cinematic_live_action":
        return (
            "Create one cinematic storyboard animatic production reference board for all image-to-video shots. "
            "Show recurring fictional characters as simplified non-photoreal silhouettes, wardrobe color blocks, "
            "key environments, props, lighting palette, and continuity anchors. Avoid close facial detail. "
            "No celebrity likeness, no logos, no readable text, no smoke, no blood, no weapons. "
            f"{_negative_lock_sentence(profile)} "
            f"Script assets: {json.dumps({'characters': script['characters'], 'scenes': script['scenes'], 'style': script['style_bible']}, ensure_ascii=False)}"
        )
    return (
        "Create one compact vertical anime reference sheet for all image-to-video shots. Include recurring "
        "characters, key environments, wardrobe, props, and style palette. No text labels or subtitles. "
        f"{_negative_lock_sentence(profile)} "
        f"Script assets: {json.dumps({'characters': script['characters'], 'scenes': script['scenes'], 'style': script['style_bible']}, ensure_ascii=False)}"
    )


def _keyframe_prompt_for(profile: AdaptiveProductionProfile, shot: AdaptiveShotSpec) -> str:
    if profile.media_prompt_style == "cinematic_live_action":
        return (
            f"Cinematic storyboard animatic keyframe for {profile.title}, {shot.shot_id}: {shot.summary}. "
            f"Location: {shot.location}. Action: {shot.action}. Camera: {shot.camera}. "
            "Original fictional cast shown as simplified silhouettes, production-safe previsualization, "
            "no close facial likeness, no readable text, no logos."
        )
    return (
        f"Vertical anime keyframe for {profile.title}, {shot.shot_id}: {shot.summary}. "
        f"Location: {shot.location}. Action: {shot.action}. Camera: {shot.camera}."
    )


def _video_prompt_for(profile: AdaptiveProductionProfile, shot: AdaptiveShotSpec) -> str:
    if profile.media_prompt_style == "cinematic_live_action":
        return (
            f"Silent cinematic storyboard animatic video for {profile.title}, {shot.shot_id}. {shot.summary}. "
            f"Action: {shot.action}. Continue from {shot.continuity_in}; end with {shot.continuity_out}. "
            "Preserve the same simplified silhouettes, wardrobe color blocks, props, space, lighting direction, and camera intent."
        )
    return (
        f"Silent vertical anime video for {profile.title}, {shot.shot_id}. {shot.summary}. "
        f"Action: {shot.action}. Continue from {shot.continuity_in}; end with {shot.continuity_out}."
    )


def _shot_keyframe_prompt(script: dict[str, Any], shot: dict[str, Any], profile: AdaptiveProductionProfile) -> str:
    return (
        "Use the supplied reference sheet as visual identity anchor. "
        f"Story: {script['title']}. Shot: {shot['shot_id']}. {shot['keyframe_prompt']} "
        f"{_negative_lock_sentence(profile)}"
    )


def _shot_video_prompt(
    script: dict[str, Any],
    shot: dict[str, Any],
    chunk_index: int,
    duration_sec: int,
    profile: AdaptiveProductionProfile,
) -> str:
    continuity = shot["continuity_in"] if chunk_index == 1 else "continue directly from the prior tail frame"
    if profile.media_prompt_style == "cinematic_live_action":
        action = _video_safety_text(shot.get("action") or shot.get("summary") or "")
        camera = _video_safety_text(shot.get("camera") or "controlled camera move")
        summary = _video_safety_text(shot.get("summary") or "")
        return (
            f"{duration_sec} second silent cinematic storyboard animatic. Story: {script['title']}. "
            f"Shot: {shot['shot_id']}. Chunk {chunk_index}. "
            f"Scene intent: {summary}. Safe motion: {action}. "
            "Original fictional adult performers as simplified silhouettes in a controlled production previsualization. "
            f"Camera: {camera}. Movement should be gentle and physically plausible. "
            f"Continuity: {_video_safety_text(continuity)}. Maintain the same wardrobe color blocks, props, room layout, lighting direction, and camera intent. "
            f"{_negative_lock_sentence(profile)} No subtitles, no logos, no audio, no readable text, no close facial detail."
        )
    style = "silent vertical anime video"
    return (
        f"{duration_sec} second {style} chunk. Story: {script['title']}. "
        f"Shot: {shot['shot_id']}. Chunk {chunk_index}. Strategy: {shot['generation_strategy']}. "
        f"Continuity: {continuity}. {shot['video_prompt']} "
        f"{_negative_lock_sentence(profile)} No subtitles, no logos, no audio."
    )


def _video_safety_text(value: Any) -> str:
    text = " ".join(str(value or "").split())
    replacements = {
        "对峙": "professional conversation",
        "冲突": "production discussion",
        "危机": "production planning",
        "压力": "schedule focus",
        "旧镜头": "film reel prop",
        "删错": "editing issue",
        "失误": "editing issue",
        "限时": "timed production task",
        "倒计时": "timer display",
        "三分钟": "short time window",
        "失重": "low-gravity rehearsal",
        "倒置": "careful angled reach",
        "腰绳": "support line",
        "钢索": "support rail",
        "氧气": "life-support panel",
        "阀门": "control wheel",
        "阀盘": "control wheel",
        "氧气阀": "life-support control wheel",
        "束带": "colored marker band",
        "机械臂": "service arm",
        "维修槽": "service bay",
        "气闸": "door module",
        "裂纹": "surface mark",
        "告警": "status light",
        "红色": "warm color",
        "伤": "mark",
        "血": "red label",
        "武器": "tool",
        "烟": "soft haze lighting",
        "gore": "mark",
        "blood": "red label",
        "weapon": "tool",
        "smoke": "soft haze lighting",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text[:360]


def _negative_lock_sentence(profile: AdaptiveProductionProfile) -> str:
    locks = [str(item).strip() for item in profile.media_negative_locks if str(item).strip()]
    if not locks:
        return ""
    return "Negative locks: " + "; ".join(locks[:20]) + "."


def _artifact_version(
    kind: str,
    path: Path,
    run_root: Path,
    project_id: str,
    run_id: str,
    *,
    shot_id: str | None = None,
    chunk_id: str | None = None,
) -> dict[str, Any]:
    digest = sha256_file(path)
    return {
        "artifact_version_id": safe_id(f"{project_id}-{run_id}-{kind}-{shot_id or 'global'}-{chunk_id or 'whole'}-{digest[:12]}"),
        "kind": kind,
        "project_id": project_id,
        "run_id": run_id,
        "shot_id": shot_id,
        "chunk_id": chunk_id,
        "sha256": digest,
        "byte_count": path.stat().st_size,
        "path": str(path),
        "relative_path": path.relative_to(run_root).as_posix(),
    }


def _image_artifact(
    kind: str,
    path: Path,
    run_root: Path,
    project_id: str,
    run_id: str,
    *,
    shot_id: str | None = None,
) -> dict[str, Any]:
    artifact = _artifact_version(kind, path, run_root, project_id, run_id, shot_id=shot_id)
    probe = _probe(path)
    streams = probe.get("streams") if isinstance(probe.get("streams"), list) else []
    video = next((item for item in streams if item.get("codec_type") == "video"), {})
    return {**artifact, "width": int(video.get("width") or 0), "height": int(video.get("height") or 0)}


def _video_artifact(
    kind: str,
    path: Path,
    run_root: Path,
    project_id: str,
    run_id: str,
    *,
    shot_id: str | None = None,
    chunk_id: str | None = None,
    continuity_anchor_path: Path | None = None,
) -> dict[str, Any]:
    artifact = _artifact_version(kind, path, run_root, project_id, run_id, shot_id=shot_id, chunk_id=chunk_id)
    probe = _probe(path)
    streams = probe.get("streams") if isinstance(probe.get("streams"), list) else []
    video = next((item for item in streams if item.get("codec_type") == "video"), {})
    result = {
        **artifact,
        "duration_sec": float((probe.get("format") or {}).get("duration") or 0.0),
        "audio_stream_count": sum(1 for item in streams if item.get("codec_type") == "audio"),
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
    }
    if continuity_anchor_path is not None and continuity_anchor_path.exists():
        result["continuity_anchor_sha256"] = sha256_file(continuity_anchor_path)
    return result


def _probe(path: Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration:stream=codec_type,width,height,avg_frame_rate,r_frame_rate,nb_frames",
                "-of",
                "json",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise AdaptiveCanvasError("ffprobe executable not found") from exc
    payload = json.loads(proc.stdout or "{}")
    if not isinstance(payload, dict):
        raise AdaptiveCanvasError("ffprobe returned non-object JSON")
    return payload


def _video_quality_metrics(path: Path) -> dict[str, Any]:
    try:
        probe = _probe(path)
    except AdaptiveCanvasError as exc:
        return {"status": "failed", "error": str(exc)}
    streams = probe.get("streams") if isinstance(probe.get("streams"), list) else []
    video = next((item for item in streams if item.get("codec_type") == "video"), {})
    duration = float((probe.get("format") or {}).get("duration") or 0.0)
    fps = _parse_frame_rate(str(video.get("avg_frame_rate") or video.get("r_frame_rate") or "0/1"))
    frame_count = _coerce_int(video.get("nb_frames"))
    if frame_count <= 0 and fps > 0 and duration > 0:
        frame_count = int(round(duration * fps))
    scan = _video_event_scan(path)
    metrics = {
        "status": "pass",
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "duration_sec": duration,
        "fps": fps,
        "frame_count": frame_count,
        "black_segment_count": len(scan.get("black_segments") or []),
        "freeze_event_count": len(scan.get("freeze_events") or []),
        "repeat_or_freeze_event_count": len(scan.get("freeze_events") or []),
        "abnormal_frame_decode_status": scan.get("status"),
        "black_segments": scan.get("black_segments") or [],
        "freeze_events": scan.get("freeze_events") or [],
    }
    if metrics["width"] <= 0 or metrics["height"] <= 0 or metrics["fps"] <= 0 or metrics["frame_count"] <= 0:
        metrics["status"] = "failed"
        metrics["error"] = "missing resolution, fps, or frame count"
    if scan.get("status") != "pass":
        metrics["status"] = "failed"
        metrics["error"] = scan.get("stderr_tail") or scan.get("error") or "video event scan failed"
    return metrics


def _technical_qa_scores(findings: list[dict[str, Any]], media_metrics: dict[str, Any]) -> dict[str, Any]:
    severities = {str(item.get("severity")) for item in findings}
    integrity_score = 5 if not severities.intersection({"P0", "P1"}) else 3 if "P1" in severities else 0
    metrics_score = 5 if media_metrics.get("status") == "pass" else 0
    temporal_score = 5
    if media_metrics.get("black_segment_count", 0) or media_metrics.get("freeze_event_count", 0):
        temporal_score = 3
    return {
        "decode_duration_audio": integrity_score,
        "resolution_fps_frame_count": metrics_score,
        "black_freeze_repeat_anomaly": temporal_score,
        "contact_sheet_artifact": 5,
        "lineage_cost_artifacts": 5,
        "scale": "0-5",
        "boundary": "automated technical media QA scores; not Owner human acceptance or business validation",
    }


def _parse_frame_rate(value: str) -> float:
    if "/" not in value:
        try:
            return float(value)
        except ValueError:
            return 0.0
    numerator, denominator = value.split("/", 1)
    try:
        den = float(denominator)
        if den == 0:
            return 0.0
        return float(numerator) / den
    except ValueError:
        return 0.0


def _coerce_int(value: object) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def _video_event_scan(path: Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-v",
                "info",
                "-i",
                str(path),
                "-vf",
                "blackdetect=d=0.75:pic_th=0.98,freezedetect=n=-60dB:d=1",
                "-an",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return {"status": "failed", "stderr_tail": "ffmpeg executable not found"}
    if proc.returncode != 0:
        return {"status": "failed", "stderr_tail": proc.stderr[-1000:]}
    black_segments: list[dict[str, float]] = []
    freeze_events: list[dict[str, float]] = []
    for line in proc.stderr.splitlines():
        black = re.search(r"black_start:(?P<start>[0-9.]+)\s+black_end:(?P<end>[0-9.]+)\s+black_duration:(?P<duration>[0-9.]+)", line)
        if black:
            black_segments.append({key: float(value) for key, value in black.groupdict().items()})
        freeze = re.search(r"freeze_start:\s*(?P<start>[0-9.]+).*freeze_duration:\s*(?P<duration>[0-9.]+).*freeze_end:\s*(?P<end>[0-9.]+)", line)
        if freeze:
            freeze_events.append({key: float(value) for key, value in freeze.groupdict().items()})
    return {"status": "pass", "black_segments": black_segments, "freeze_events": freeze_events}


def _decode_check(path: Path) -> dict[str, Any]:
    try:
        proc = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "null", "-"], capture_output=True, text=True)
    except FileNotFoundError:
        return {"status": "failed", "stderr_tail": "ffmpeg executable not found"}
    return {"status": "pass" if proc.returncode == 0 else "failed", "stderr_tail": proc.stderr[-1000:]}


def _concat_videos(inputs: list[Path], output: Path, *, duration_sec: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    list_path = output.with_suffix(".concat.txt")
    list_path.write_text("\n".join(f"file {shlex.quote(str(item.resolve()))}" for item in inputs) + "\n", encoding="utf-8")
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-t",
            f"{float(duration_sec):.3f}",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )


def _contact_sheet(video: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-y", "-i", str(video), "-vf", "fps=1,scale=160:-1,tile=10x6", "-frames:v", "1", str(output)])


def _extract_tail_frame(video: Path, output: Path) -> None:
    if not video.exists():
        raise FileNotFoundError(str(video))
    output.parent.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(video), "-frames:v", "1", str(output)])


def _fake_png(path: Path, color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=160x284:d=1", "-frames:v", "1", str(path)])


def _fake_video(path: Path, *, duration_sec: int, color: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=160x284:d={duration_sec}:r=12",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ]
    )


def _first_output_path(output_dir: Path, result: dict[str, Any], key: str) -> Path:
    outputs = result.get("outputs")
    if not isinstance(outputs, list) or not outputs:
        raise AdaptiveCanvasError("provider result did not include outputs")
    rel = str(outputs[0].get(key) or "")
    if not rel:
        raise AdaptiveCanvasError(f"provider result did not include {key}")
    path = output_dir / rel
    if not path.is_file():
        raise FileNotFoundError(str(path))
    return path


def _copy_bytes(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    tmp.write_bytes(src.read_bytes())
    os.replace(tmp, dst)


def _run(cmd: list[str]) -> None:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise AdaptiveCanvasError(f"command executable not found: {cmd[0]}") from exc
    if proc.returncode != 0:
        raise AdaptiveCanvasError(f"command failed: {' '.join(cmd[:2])}: {proc.stderr[-1000:]}")


def _fake_color(index: int) -> str:
    colors = ["0x1d4ed8", "0x7c3aed", "0x059669", "0xdc2626", "0xf59e0b", "0x0891b2"]
    return colors[index % len(colors)]


def _emit(callback: Callback | None, stage: str, status: str, **fields: Any) -> None:
    if callback is not None:
        callback({"stage": stage, "status": status, **fields})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _runtime_store(runtime_root: Path) -> Any:
    return import_module("apps.api.runtime_store").RuntimeStore(runtime_root)


def safe_error(error: Exception) -> dict[str, str]:
    return {"type": type(error).__name__, "message": _safe_message(str(error))}


def _safe_message(value: str) -> str:
    text = re.sub(r"(?i)(api[_-]?key|authorization|bearer|token|secret)[^\\s,;]*", "[redacted]", value)
    return text[-1000:]


def _safe_provider_poll_task(payload: dict[str, Any]) -> dict[str, Any]:
    def normalize(value: Any) -> Any:
        if isinstance(value, Path):
            return str(value)
        if isinstance(value, tuple):
            return [normalize(item) for item in value]
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if isinstance(value, dict):
            return {str(key): normalize(item) for key, item in value.items() if _safe_poll_key(str(key))}
        if isinstance(value, (str, int, float, bool)) or value is None:
            return value
        return str(value)

    normalized = normalize(payload)
    if not isinstance(normalized, dict):
        raise AdaptiveCanvasError("provider poll task must normalize to an object")
    return normalized


def _safe_poll_key(key: str) -> bool:
    lowered = key.lower()
    return not any(marker in lowered for marker in ("api_key", "authorization", "bearer", "secret", "credential"))


__all__ = [
    "AdaptiveCanvasError",
    "AGENT_SCRIPT_INPUT_FILENAME",
    "AGENT_SCRIPT_INPUT_SCHEMA_VERSION",
    "IMAGE_PROVIDER_SERVICE_ID",
    "SCRIPT_V3_CONTRACT_ID",
    "SCRIPT_TRUTH_AGGREGATE_VERSION",
    "VIDEO_PROVIDER_SERVICE_ID",
    "AdaptiveProductionProfile",
    "AdaptiveRunOptions",
    "AdaptiveShotSpec",
    "ChargeLedger",
    "GenerationStrategy",
    "MediaPromptStyle",
    "PaidAttemptLimitExceeded",
    "ScriptSourceType",
    "build_agent_authored_script_input",
    "compile_duration_chunks",
    "build_script_truth_from_profile",
    "build_script_v3_output_schema",
    "load_adaptive_workspace",
    "run_adaptive_canvas_production",
    "seed_agent_authored_script_truth",
    "sha256_file",
]
