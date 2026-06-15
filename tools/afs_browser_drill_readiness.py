from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def browser_drill_summary(evidence_root: Path) -> dict[str, Any]:
    path = evidence_root / "browser_qa_summary.json"
    if not path.is_file():
        return {}
    payload = _read_json(path)
    if payload.get("artifact_type") != "afs_browser_acceptance_drill_summary":
        return {}
    return payload


def browser_drill_provider_blockers(evidence_root: Path) -> list[dict[str, Any]]:
    return [
        blocker
        for blocker in (
            _image_blocker(evidence_root),
            _kling_blocker(evidence_root),
        )
        if blocker is not None
    ]


def browser_drill_role_checks(summary: dict[str, Any]) -> list[dict[str, str]]:
    checks = summary.get("role_checks")
    if not isinstance(checks, list):
        return []
    role_checks: list[dict[str, str]] = []
    for item in checks:
        if isinstance(item, dict):
            role_checks.append(
                {
                    "role_id": str(item.get("role_id") or "unknown"),
                    "status": str(item.get("status") or "missing_evidence"),
                    "evidence_ref": str(item.get("evidence_ref") or ""),
                }
            )
    return role_checks


def browser_drill_next_actions(summary: dict[str, Any]) -> list[str]:
    actions = summary.get("next_actions") if summary else []
    if not isinstance(actions, list):
        return []
    return [str(action) for action in actions if str(action).strip()]


def _image_blocker(evidence_root: Path) -> dict[str, Any] | None:
    manifests = sorted(evidence_root.glob("runtime_service/**/keyframe_generation_safe_manifest.json"))
    for path in manifests:
        manifest = _read_json(path)
        if (
            manifest.get("status") == "succeeded"
            and manifest.get("provider_calls_started") is True
            and int(manifest.get("output_count") or 0) > 0
        ):
            return None
    return _missing_blocker(
        "P1-IMAGE-BROWSER-SMOKE-MISSING",
        "runtime_service/**/keyframe_generation_safe_manifest.json with succeeded provider output",
    )


def _kling_blocker(evidence_root: Path) -> dict[str, Any] | None:
    manifests = sorted(evidence_root.glob("runtime_service/**/video_generation_safe_manifest.json"))
    for path in manifests:
        manifest = _read_json(path)
        if (
            manifest.get("status") == "succeeded"
            and manifest.get("provider_calls_started") is True
            and manifest.get("outputs")
        ):
            return None
    return _missing_blocker(
        "P1-KLING-BROWSER-SMOKE-MISSING",
        "runtime_service/**/video_generation_safe_manifest.json with succeeded provider output",
    )


def _missing_blocker(blocker_id: str, evidence_pattern: str) -> dict[str, Any]:
    return {
        "blocker_id": blocker_id,
        "status": "missing_evidence",
        "root_cause_block_id": "missing_evidence",
        "provider_calls_started": False,
        "retry_count": 0,
        "evidence_refs": [f"missing:{evidence_pattern}"],
    }


def _read_json(path: Path) -> dict[str, Any]:
    for encoding in ("utf-8", "utf-8-sig", "utf-16"):
        try:
            payload = json.loads(path.read_text(encoding=encoding))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        except OSError:
            return {}
        return payload if isinstance(payload, dict) else {}
    return {}
