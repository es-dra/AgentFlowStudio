from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.memory.production_operator_run_package_acceptance_check import (
    acceptance_feedback_candidate_promotion_failed_controls,
    check_acceptance_feedback_candidate_promotion,
)
from agentflow.memory.production_operator_run_package import OPERATOR_RUN_PACKAGE_KIND
from agentflow.memory.production_operator_run_package_check_render import (
    render_operator_run_package_check_markdown,
    write_operator_run_package_check_markdown,
)
from agentflow.harness.json_io import write_json

OPERATOR_RUN_PACKAGE_CHECK_KIND = "agentflow_production_memory_operator_run_package_check"


def load_operator_run_package(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("operator run package must be a JSON object")
    return payload


def check_operator_run_package(
    package_path: str | Path,
    *,
    artifact_root: str | Path | None = None,
) -> dict[str, Any]:
    package_ref = Path(package_path)
    package = load_operator_run_package(package_ref)
    if package.get("kind") != OPERATOR_RUN_PACKAGE_KIND:
        raise ValueError(f"operator run package check requires kind {OPERATOR_RUN_PACKAGE_KIND}")

    root = Path(artifact_root) if artifact_root is not None else _default_artifact_root(package_ref)
    checked_items, missing_refs, mismatched_refs, unsafe_refs = _check_package_items(package, root)
    blocked_items = _blocked_items(package)
    acceptance_feedback_candidate_promotion_check = check_acceptance_feedback_candidate_promotion(package, root)
    failed_controls = _dedupe_controls(
        _failed_controls(package)
        + acceptance_feedback_candidate_promotion_failed_controls(acceptance_feedback_candidate_promotion_check)
    )
    check_status = (
        FAILED
        if (
            package.get("package_status") != "ready"
            or missing_refs
            or mismatched_refs
            or unsafe_refs
            or blocked_items
            or failed_controls
        )
        else PASSED
    )
    return {
        "kind": OPERATOR_RUN_PACKAGE_CHECK_KIND,
        "artifact_type": OPERATOR_RUN_PACKAGE_CHECK_KIND,
        "schema_version": package.get("schema_version", SCHEMA_VERSION),
        "package_kind": package.get("kind", "unknown"),
        "package_path": _display_path(package_ref),
        "artifact_root": _display_path(root),
        "check_status": check_status,
        "package_status": package.get("package_status", "unknown"),
        "source_operator_loop_id": package.get("source_operator_loop_id", "unknown"),
        "project_id": package.get("project_id", "unknown"),
        "manifest_check_status": package.get("manifest_check_status", "unknown"),
        "handoff_status": package.get("handoff_status", "unknown"),
        "provider_mode": package.get("provider_mode", "unknown"),
        "provider_calls_started": package.get("provider_calls_started") is True,
        "writes_long_term_memory": package.get("writes_long_term_memory") is True,
        "writes_company_kb": package.get("writes_company_kb") is True,
        "ready_for_handoff": check_status == PASSED,
        "checked_item_count": len(checked_items),
        "checked_items": checked_items,
        "missing_refs": missing_refs,
        "mismatched_refs": mismatched_refs,
        "unsafe_refs": unsafe_refs,
        "blocked_items": blocked_items,
        "failed_controls": failed_controls,
        "acceptance_feedback_candidate_promotion_check": acceptance_feedback_candidate_promotion_check,
        "next_operator_action": _dict(package.get("next_operator_action")),
        "claim_boundaries": {
            "structure_verification": "machine_checked" if check_status == PASSED else "blocked",
            "runtime_verification": "package_refs_checked" if check_status == PASSED else "blocked",
            "human_acceptance": "not_claimed",
            "business_validation": "not_claimed",
            "durable_memory": "not_written",
            "company_kb_write": "not_written",
            "provider_success": "not_claimed",
        },
    }


def write_operator_run_package_check(check: dict[str, Any], output_path: str | Path) -> Path:
    return write_json(output_path, check)


def write_operator_run_package_check_report(check: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_operator_run_package_check(check, output_root / "operator_run_package_check.json")
    markdown_path = write_operator_run_package_check_markdown(check, output_root / "operator_run_package_check.md")
    return [json_path, markdown_path]


def _check_package_items(
    package: dict[str, Any],
    artifact_root: Path,
) -> tuple[list[dict[str, str]], list[str], list[dict[str, str]], list[str]]:
    checked_items: list[dict[str, str]] = []
    missing_refs: list[str] = []
    mismatched_refs: list[dict[str, str]] = []
    unsafe_refs: list[str] = []
    for item in _list(package.get("package_items")):
        value = _dict(item)
        path_ref = str(value.get("path", "")).replace("\\", "/")
        expected_type = str(value.get("artifact_type", "unknown"))
        if _unsafe_ref(path_ref):
            unsafe_refs.append(path_ref)
            continue
        full_path = artifact_root / path_ref
        if not full_path.exists():
            missing_refs.append(path_ref)
            continue
        checked_items.append(
            {
                "path": path_ref,
                "artifact_type": expected_type,
                "role": str(value.get("role", "unknown")),
            }
        )
        if expected_type == "markdown_report":
            continue
        actual_type = _artifact_type(full_path)
        if actual_type != expected_type:
            mismatched_refs.append(
                {
                    "path": path_ref,
                    "expected_artifact_type": expected_type,
                    "actual_artifact_type": actual_type,
                }
            )
    return checked_items, missing_refs, mismatched_refs, unsafe_refs


def _failed_controls(package: dict[str, Any]) -> list[dict[str, str]]:
    failed = [_control_failed(item) for item in _list(package.get("controls")) if _dict(item).get("status") != PASSED]
    failed.extend(
        [
            _control("package_status_ready", package.get("package_status") == "ready"),
            _control("operator_manifest_check_passed", package.get("manifest_check_status") == PASSED),
            _control("operator_handoff_ready", package.get("handoff_status") == "ready"),
            _control("provider_calls_not_started", package.get("provider_calls_started") is False),
            _control("long_term_memory_write_disabled", package.get("writes_long_term_memory") is False),
            _control("company_kb_write_disabled", package.get("writes_company_kb") is False),
        ]
    )
    return _dedupe_controls([item for item in failed if item["status"] != PASSED])


def _blocked_items(package: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "ref": str(_dict(item).get("ref", "unknown")),
            "reason": str(_dict(item).get("reason", "blocked")),
        }
        for item in _list(package.get("blocked_items"))
    ]


def _artifact_type(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return "invalid_json"
    if not isinstance(payload, dict):
        return "non_object_json"
    return str(payload.get("kind") or payload.get("artifact_type") or "missing_artifact_type")


def _default_artifact_root(package_ref: Path) -> Path:
    if package_ref.parent.name == "operator_run_package":
        return package_ref.parent.parent
    return package_ref.parent


def _unsafe_ref(path_ref: str) -> bool:
    path = Path(path_ref)
    return not path_ref or path.is_absolute() or path_ref.startswith("../") or "/../" in path_ref


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


def _control_failed(value: Any) -> dict[str, str]:
    item = _dict(value)
    return {"control_id": str(item.get("control_id", "unknown")), "status": str(item.get("status", FAILED))}


def _dedupe_controls(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for item in items:
        control_id = item["control_id"]
        if control_id in seen:
            continue
        seen.add(control_id)
        deduped.append(item)
    return deduped


def _display_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "OPERATOR_RUN_PACKAGE_CHECK_KIND",
    "check_operator_run_package",
    "load_operator_run_package",
    "render_operator_run_package_check_markdown",
    "write_operator_run_package_check",
    "write_operator_run_package_check_markdown",
    "write_operator_run_package_check_report",
)
