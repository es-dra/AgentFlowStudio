from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.memory.production_asset_profile_promotion import ASSET_PROFILE_VERSION_KIND
from agentflow.memory.production_asset_profile_promotion_utils import (
    list_value,
    reject_unsafe_asset_profile_promotion,
)
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.harness.json_io import write_json

ASSET_PROFILE_CONTEXT_PROJECTION_KIND = "agentflow_production_memory_asset_profile_context_projection"


def load_asset_profile_version(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("asset profile version must be a JSON object")
    reject_unsafe_asset_profile_promotion(payload)
    return payload


def build_asset_profile_context_projection(
    *,
    asset_profile_versions: list[dict[str, Any]],
    generated_at: str,
) -> dict[str, Any]:
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("generated_at is required")
    for version in asset_profile_versions:
        reject_unsafe_asset_profile_promotion(version)

    superseded = _superseded_profile_refs(asset_profile_versions)
    included_refs: list[dict[str, Any]] = []
    blocked_refs = _superseded_blocked_refs(superseded)
    for version in asset_profile_versions:
        profile_id = _profile_id(version)
        if version.get("kind") != ASSET_PROFILE_VERSION_KIND:
            blocked_refs.append(_blocked(_artifact_ref(version), "invalid_profile_version_kind"))
            continue
        if profile_id in superseded:
            blocked_refs.append(_blocked(profile_id, "superseded_by_newer_profile_version", superseded_by=superseded[profile_id]))
            continue
        version_blockers = _version_blockers(version)
        if version_blockers:
            blocked_refs.extend(version_blockers)
            continue
        included_refs.append(_included_ref(version))

    blocked_refs = _dedupe_blocked_refs(blocked_refs)
    status = "ready" if included_refs else "blocked"
    projection = {
        "kind": ASSET_PROFILE_CONTEXT_PROJECTION_KIND,
        "artifact_type": ASSET_PROFILE_CONTEXT_PROJECTION_KIND,
        "schema_version": SCHEMA_VERSION,
        "projection_id": "asset-profile-context-projection:no-provider",
        "generated_at": generated_at,
        "projection_status": status,
        "project_id": _project_id(asset_profile_versions),
        "source_profile_version_count": len(asset_profile_versions),
        "included_refs": included_refs,
        "blocked_refs": blocked_refs,
        "context_payload": {
            "asset_profile_refs": included_refs,
            "blocked_asset_profile_refs": blocked_refs,
            "context_projection_policy": "profile_version_is_inclusion_authority",
        },
        "controls": _controls(asset_profile_versions, included_refs, blocked_refs),
        "provider_mode": "no-provider",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": [
            "not human acceptance",
            "not business validation",
            "not durable Memory OS",
            "not Company KB promotion",
            "not provider success",
            "not provider execution",
        ],
    }
    reject_unsafe_asset_profile_promotion(projection)
    return projection


def write_asset_profile_context_projection(projection: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "asset_profile_context_projection.json", projection)
    md_path = output_root / "asset_profile_context_projection.md"
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_asset_profile_context_projection_markdown(projection), encoding="utf-8")
    return [json_path, md_path]


def render_asset_profile_context_projection_markdown(projection: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Production Memory Asset Profile Context Projection",
            "",
            f"Status: {projection.get('projection_status', 'unknown')}",
            f"Included refs: {len(list_value(projection.get('included_refs')))}",
            f"Blocked refs: {len(list_value(projection.get('blocked_refs')))}",
            "Provider calls: not started",
            "Writes long-term memory: false",
            "Writes Company KB: false",
            "",
            "## Included refs",
            "",
            _refs_table(projection.get("included_refs")),
            "",
            "## Blocked refs",
            "",
            _refs_table(projection.get("blocked_refs"), reason=True),
            "",
        ]
    )


def _version_blockers(version: dict[str, Any]) -> list[dict[str, Any]]:
    profile = _profile(version)
    profile_id = _profile_id(version)
    blockers: list[dict[str, Any]] = []
    if version.get("profile_version_applied") is not True:
        blockers.append(_blocked(profile_id, "profile_version_not_applied"))
    if version.get("usable_for_next_context") is not True:
        blockers.append(_blocked(profile_id, "profile_version_not_usable_for_next_context"))
    if not isinstance(version.get("version_change_summary"), dict):
        blockers.append(_blocked(profile_id, "missing_version_change_summary"))
    if not profile:
        blockers.append(_blocked(profile_id, "missing_embedded_profile"))
        return blockers
    if profile.get("profile_status") != "promoted":
        blockers.append(_blocked(profile_id, "profile_not_promoted"))
    if profile.get("context_eligibility") != "included":
        blockers.append(_blocked(profile_id, "profile_context_not_included"))
    if list_value(profile.get("blockers")):
        blockers.append(_blocked(profile_id, "profile_has_blockers"))
    if profile.get("writes_long_term_memory") is not False:
        blockers.append(_blocked(profile_id, "profile_writes_long_term_memory"))
    if profile.get("writes_company_kb") is not False:
        blockers.append(_blocked(profile_id, "profile_writes_company_kb"))
    if version.get("source_decision_id") not in _decision_refs(profile):
        blockers.append(_blocked(str(version.get("source_decision_id", "unknown")), "missing_profile_version_decision_ref"))
    return blockers


def _included_ref(version: dict[str, Any]) -> dict[str, Any]:
    profile = _profile(version)
    return {
        "ref_id": str(version["profile_id"]),
        "ref_kind": "asset_profile",
        "profile_kind": profile.get("profile_kind", version.get("profile_kind", "unknown")),
        "profile_version": version.get("profile_version", profile.get("profile_version", "unknown")),
        "source_version_id": version.get("version_id", "unknown"),
        "source_profile_id": version.get("source_profile_id", "unknown"),
        "source_decision_id": version.get("source_decision_id", "unknown"),
        "summary": profile.get("display_name", version.get("profile_id", "asset profile")),
        "allowed_variations": list_value(profile.get("allowed_variations")),
        "negative_constraints": list_value(profile.get("negative_constraints")),
        "evidence_refs": list_value(profile.get("evidence_refs")),
        "version_change_summary": version.get("version_change_summary", {}),
    }


def _superseded_profile_refs(versions: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for version in versions:
        if version.get("kind") != ASSET_PROFILE_VERSION_KIND:
            continue
        source_profile_id = str(version.get("source_profile_id", "")).strip()
        profile_id = _profile_id(version)
        if source_profile_id and source_profile_id != "unknown" and profile_id:
            result[source_profile_id] = profile_id
    return result


def _superseded_blocked_refs(superseded: dict[str, str]) -> list[dict[str, Any]]:
    return [
        _blocked(ref_id, "superseded_by_profile_version", superseded_by=superseded_by)
        for ref_id, superseded_by in superseded.items()
    ]


def _controls(
    versions: list[dict[str, Any]],
    included_refs: list[dict[str, Any]],
    blocked_refs: list[dict[str, Any]],
) -> list[dict[str, str]]:
    included_ids = {str(item.get("ref_id")) for item in included_refs}
    blocked_ids = {str(item.get("ref_id")) for item in blocked_refs}
    return [
        _control("asset_profile_versions_loaded", bool(versions)),
        _control("profile_version_is_inclusion_authority", True),
        _control("included_refs_present", bool(included_refs)),
        _control("blocked_refs_excluded", not (included_ids & blocked_ids)),
        _control("provider_calls_not_started", True),
        _control("writes_no_long_term_memory", True),
        _control("writes_no_company_kb", True),
    ]


def _artifact_ref(version: dict[str, Any]) -> str:
    for field in ("version_id", "decision_id", "profile_id", "candidate_id"):
        value = version.get(field)
        if value:
            return str(value)
    return "unknown-profile-version-artifact"


def _profile(version: dict[str, Any]) -> dict[str, Any]:
    profile = version.get("profile")
    return profile if isinstance(profile, dict) else {}


def _profile_id(version: dict[str, Any]) -> str:
    profile = _profile(version)
    return str(version.get("profile_id") or profile.get("profile_id") or _artifact_ref(version))


def _decision_refs(profile: dict[str, Any]) -> set[str]:
    return {
        *(str(item) for item in list_value(profile.get("promotion_decision_refs"))),
        *(str(item) for item in list_value(profile.get("profile_version_decision_refs"))),
    }


def _project_id(versions: list[dict[str, Any]]) -> str:
    for version in versions:
        project_id = version.get("project_id")
        if project_id:
            return str(project_id)
    return "unknown"


def _dedupe_blocked_refs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result = []
    for item in items:
        key = (str(item.get("ref_id", "")), str(item.get("reason", "")))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _blocked(ref_id: str, reason: str, **extra: Any) -> dict[str, Any]:
    return {"ref_id": ref_id, "reason": reason, **extra}


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


def _refs_table(value: Any, *, reason: bool = False) -> str:
    refs = list_value(value)
    if not refs:
        return "- none"
    if reason:
        return "\n".join(f"- {item.get('ref_id', 'unknown')}: {item.get('reason', 'blocked')}" for item in refs)
    return "\n".join(f"- {item.get('ref_id', 'unknown')}: {item.get('summary', 'included')}" for item in refs)


__all__ = (
    "ASSET_PROFILE_CONTEXT_PROJECTION_KIND",
    "build_asset_profile_context_projection",
    "load_asset_profile_version",
    "render_asset_profile_context_projection_markdown",
    "write_asset_profile_context_projection",
)
