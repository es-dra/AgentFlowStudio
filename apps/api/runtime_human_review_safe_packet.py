from __future__ import annotations

import json
import re
from typing import Any

from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload


FORBIDDEN_REVIEW_SURFACE_RE = re.compile(
    r"(?i)("
    r"api[\s_.-]*key|access[\s_.-]*token|refresh[\s_.-]*token|token|"
    r"client[\s_.-]*secret|secret[\s_.-]*key|private[\s_.-]*key|provider[\s_.-]*key|"
    r"secret|password|cookie|auth(?:orization)?|bearer\s+\S+|signed[\s_.-]*url|session|"
    r"provider.?raw|raw.?response|raw.?payload|media.?bytes|image.?bytes|file.?bytes|data.?base64|data:|"
    r"[a-z]:\\|/(?:home|users|tmp|var/lib/afs-runtime)/|\.mp4\b|\.mov\b"
    r")"
)


def select_safe_human_review_packet_sources(
    store: RuntimeStore,
    project_id: str,
    *,
    keyframe_safe_manifest_artifact_id: str,
    prompt_review_summary_artifact_id: str,
    keyframe_candidate_summary_artifact_id: str = "",
) -> dict[str, Any]:
    keyframe_manifest_ref = store.read_artifact(keyframe_safe_manifest_artifact_id)
    prompt_summary_ref = store.read_artifact(prompt_review_summary_artifact_id)
    candidate_summary = None
    if keyframe_candidate_summary_artifact_id:
        candidate_summary = store.read_artifact(keyframe_candidate_summary_artifact_id).get("payload")
    return build_safe_human_review_packet(
        project_id,
        keyframe_manifest_ref.get("payload"),
        prompt_summary_ref.get("payload"),
        keyframe_candidate_summary=candidate_summary,
        source_artifact_ids={
            "keyframe_safe_manifest": keyframe_safe_manifest_artifact_id,
            "prompt_review_summary": prompt_review_summary_artifact_id,
            "keyframe_candidate_summary": keyframe_candidate_summary_artifact_id,
        },
    )


def build_safe_human_review_packet(
    project_id: str,
    keyframe_safe_manifest: dict[str, Any] | None,
    prompt_review_summary: dict[str, Any] | None,
    *,
    keyframe_candidate_summary: dict[str, Any] | None = None,
    source_artifact_ids: dict[str, str] | None = None,
) -> dict[str, Any]:
    manifest = _dict(keyframe_safe_manifest, "keyframe safe manifest")
    prompt_summary = _dict(prompt_review_summary, "prompt review summary")
    _require_project(project_id, manifest, "keyframe safe manifest")
    _require_project(project_id, prompt_summary, "prompt review summary")
    preview_refs = _review_preview_refs(manifest)
    if keyframe_candidate_summary is not None:
        _require_project(project_id, keyframe_candidate_summary, "keyframe candidate summary", allow_missing=True)
        summary_refs = _review_preview_refs(keyframe_candidate_summary)
        if summary_refs != preview_refs:
            raise ValueError("keyframe review preview refs disagree between safe manifest and candidate summary")
    prompt_fields = _prompt_summary_fields(prompt_summary)
    source_ids = source_artifact_ids or {}
    packet = {
        "artifact_type": "agentflow_human_review_safe_packet_plan",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "packet_state": "ready_for_redacted_human_review_packet",
        "safe_surface_only": True,
        "source_artifact_ids": {
            "keyframe_safe_manifest": str(source_ids.get("keyframe_safe_manifest") or ""),
            "prompt_review_summary": str(source_ids.get("prompt_review_summary") or ""),
            "keyframe_candidate_summary": str(source_ids.get("keyframe_candidate_summary") or ""),
        },
        "keyframe_review_previews": preview_refs,
        "prompt_summary": prompt_fields,
        "controls": {
            "fail_closed_on_missing_preview_ref": True,
            "fail_closed_on_missing_prompt_summary": True,
            "local_path_control_passed": True,
            "expiring_url_control_passed": True,
            "provider_response_control_passed": True,
            "credential_control_passed": True,
            "binary_payload_control_passed": True,
        },
        "provider_calls_started": bool(manifest.get("provider_calls_started")),
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": [
            "packet plan only",
            "not human creative acceptance",
            "not generated media QA",
            "not provider smoke",
            "not product readiness",
        ],
    }
    _reject_forbidden_review_surface(packet)
    reject_unsafe_payload(packet)
    return packet


def _review_preview_refs(payload: dict[str, Any]) -> list[dict[str, Any]]:
    refs = payload.get("review_preview_refs")
    if not isinstance(refs, list) or not refs:
        raise ValueError("safe human review packet requires review_preview_refs")
    safe_refs = []
    for index, item in enumerate(refs, start=1):
        ref = _dict(item, f"review preview ref {index}")
        required = ("job_id", "candidate_id", "safe_preview_ref", "byte_count", "sha256", "width", "height")
        missing = [field for field in required if ref.get(field) in (None, "")]
        if missing:
            raise ValueError(f"review preview ref missing fields: {', '.join(missing)}")
        safe_refs.append(
            {
                "job_id": str(ref["job_id"]),
                "candidate_id": str(ref["candidate_id"]),
                "safe_preview_ref": str(ref["safe_preview_ref"]),
                "byte_count": int(ref["byte_count"]),
                "sha256": str(ref["sha256"]),
                "width": int(ref["width"]),
                "height": int(ref["height"]),
                "aspect_ratio": str(ref.get("aspect_ratio") or ""),
            }
        )
    return safe_refs


def _prompt_summary_fields(payload: dict[str, Any]) -> dict[str, Any]:
    required = ("optimized_prompt_char_count", "optimized_prompt_text", "source_artifact_id")
    missing = [field for field in required if payload.get(field) in (None, "")]
    if missing:
        raise ValueError(f"prompt review summary missing fields: {', '.join(missing)}")
    char_count = int(payload["optimized_prompt_char_count"])
    if char_count <= 0:
        raise ValueError("prompt review summary requires optimized_prompt_char_count > 0")
    return {
        "optimized_prompt_char_count": char_count,
        "optimized_prompt_text": str(payload["optimized_prompt_text"]),
        "optimized_prompt_text_truncated": bool(payload.get("optimized_prompt_text_truncated")),
        "source_artifact_id": str(payload["source_artifact_id"]),
        "source_artifact_role": str(payload.get("source_artifact_role") or ""),
    }


def _require_project(project_id: str, payload: dict[str, Any], label: str, *, allow_missing: bool = False) -> None:
    value = payload.get("project_id")
    if allow_missing and not value:
        return
    if value != project_id:
        raise ValueError(f"{label} is not scoped to project")


def _dict(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _reject_forbidden_review_surface(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    if FORBIDDEN_REVIEW_SURFACE_RE.search(serialized):
        raise ValueError("human review safe packet contains forbidden private or raw field")


__all__ = (
    "build_safe_human_review_packet",
    "select_safe_human_review_packet_sources",
)
