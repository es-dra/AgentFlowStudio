from __future__ import annotations

import json
from pathlib import Path
from typing import Any


UNSAFE_SUMMARY_FRAGMENTS = ("D:\\", "C:\\", "file://", "Bearer ", "signed_url", "token=", "api_key", "secret_key", ".mp4", ".mov")
PROJECT_AUDIT_SUMMARY_KEYS = {
    "manifest_reference_audit": (
        "json_files_checked",
        "registry_assets",
        "errors",
        "missing_sha256",
        "missing_files",
        "absolute_refs",
        "secret_like_refs",
        "manifest_string_issues",
        "invalid_asset_types",
        "invalid_statuses",
    ),
    "text_encoding_audit": ("text_files_checked", "decode_errors", "marker_hits", "errors"),
    "asset_governance_phase_audit": (
        "phases",
        "passed",
        "blocked_expected",
        "failures",
        "registry_assets",
        "eligible_context_refs",
        "blocked_context_refs",
        "pending_b01_decisions",
    ),
}


def project_audits(root: Path, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        "manifest_reference": _project_audit(root, manifest, "manifest_reference_audit"),
        "text_encoding": _project_audit(root, manifest, "text_encoding_audit"),
        "phase_gate": _project_audit(root, manifest, "asset_governance_phase_audit"),
    }


def _project_audit(root: Path, manifest: dict[str, Any], field: str) -> dict[str, Any]:
    audit = {
        "status": str(manifest.get(f"{field}_status") or "not_provided"),
        "artifact_ref": _safe_project_ref(manifest.get(field)),
        "report_ref": _safe_project_ref(manifest.get(f"{field}_report")),
    }
    summary = _safe_audit_summary(root, audit["artifact_ref"], PROJECT_AUDIT_SUMMARY_KEYS[field])
    if summary:
        audit["summary"] = summary
    return audit


def _safe_project_ref(value: Any) -> str:
    text = str(value or "")
    if text.startswith(("D:\\", "C:\\", "file://", "http://", "https://")):
        return ""
    return text.replace("\\", "/")


def _safe_audit_summary(root: Path, artifact_ref: str, keys: tuple[str, ...]) -> dict[str, Any]:
    audit_path = _safe_project_path(root, artifact_ref)
    if audit_path is None or not audit_path.exists():
        return {}
    try:
        payload = json.loads(audit_path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}
    source = payload.get("summary")
    if not isinstance(source, dict):
        return {}
    summary: dict[str, Any] = {}
    for key in keys:
        value = source.get(key)
        if isinstance(value, (str, int, float, bool)) and _safe_summary_value(value):
            summary[key] = value
    return summary


def _safe_project_path(root: Path, ref: str) -> Path | None:
    if not ref:
        return None
    if ref.startswith("/") or ".." in Path(ref).parts:
        return None
    root_resolved = root.resolve()
    candidate = (root_resolved / ref).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        return None
    return candidate


def _safe_summary_value(value: str | int | float | bool) -> bool:
    text = str(value)
    return not any(fragment.lower() in text.lower() for fragment in UNSAFE_SUMMARY_FRAGMENTS)
