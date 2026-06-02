from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.memory.production_operator_handoff import OPERATOR_HANDOFF_PACKET_KIND
from agentflow.memory.production_operator_run_package import OPERATOR_RUN_PACKAGE_KIND
from agentflow.memory.production_operator_run_package_check import OPERATOR_RUN_PACKAGE_CHECK_KIND
from agentflow.memory.production_operator_start_packet_render import (
    render_next_operator_start_packet_markdown,
    write_next_operator_start_packet_report,
)

NEXT_OPERATOR_START_PACKET_KIND = "agentflow_production_memory_next_operator_start_packet"


def load_operator_run_package_check(path: str | Path) -> dict[str, Any]:
    return _load_json_object(Path(path), "operator run package check")


def build_next_operator_start_packet_from_check_path(
    check_path: str | Path,
    *,
    generated_at: str,
    artifact_root: str | Path | None = None,
) -> dict[str, Any]:
    check_ref = Path(check_path)
    check = load_operator_run_package_check(check_ref)
    root = Path(artifact_root) if artifact_root is not None else _artifact_root(check, check_ref)
    package = _load_json_object(root / "operator_run_package" / "operator_run_package.json", "operator run package")
    handoff = _load_json_object(root / "operator_handoff" / "operator_handoff_packet.json", "operator handoff packet")
    return build_next_operator_start_packet(
        check,
        package,
        handoff,
        generated_at=generated_at,
        check_path=check_ref,
        artifact_root=root,
    )


def build_next_operator_start_packet(
    package_check: dict[str, Any],
    package: dict[str, Any],
    handoff_packet: dict[str, Any],
    *,
    generated_at: str,
    check_path: str | Path | None = None,
    artifact_root: str | Path | None = None,
) -> dict[str, Any]:
    """Build a no-provider start packet only from a passed final run-package check."""
    _validate_inputs(package_check, package, handoff_packet, generated_at)
    action = _dict(package_check.get("next_operator_action"))
    checked_items = _checked_items(package_check)
    packet = {
        "kind": NEXT_OPERATOR_START_PACKET_KIND,
        "artifact_type": NEXT_OPERATOR_START_PACKET_KIND,
        "schema_version": package_check.get("schema_version", SCHEMA_VERSION),
        "start_packet_id": f"next-operator-start:{package_check.get('source_operator_loop_id', 'unknown')}",
        "generated_at": generated_at,
        "source_operator_loop_id": package_check.get("source_operator_loop_id", "unknown"),
        "project_id": package_check.get("project_id", "unknown"),
        "source_run_package_check_path": _display_path(Path(check_path)) if check_path is not None else "not_recorded",
        "artifact_root": _display_path(Path(artifact_root)) if artifact_root is not None else "not_recorded",
        "start_packet_status": "ready",
        "ready_for_next_operator": True,
        "package_check_status": package_check.get("check_status", "unknown"),
        "package_status": package.get("package_status", "unknown"),
        "handoff_status": handoff_packet.get("handoff_status", "unknown"),
        "next_operator_action": action,
        "operator_prompt": str(handoff_packet.get("handoff_prompt", "")),
        "checked_package_item_count": len(checked_items),
        "checked_package_items": checked_items,
        "blocked_items": [],
        "failed_controls": [],
        "acceptance_feedback_candidate_promotion_check": _dict(
            package_check.get("acceptance_feedback_candidate_promotion_check")
        ),
        "provider_mode": package_check.get("provider_mode", "no-provider"),
        "provider_calls_started": package_check.get("provider_calls_started") is True,
        "writes_long_term_memory": package_check.get("writes_long_term_memory") is True,
        "writes_company_kb": package_check.get("writes_company_kb") is True,
        "start_requirements": _start_requirements(action),
        "controls": _controls(package_check, package, handoff_packet),
        "non_claims": _non_claims(),
        "claim_boundaries": _claim_boundaries(package_check),
    }
    return packet


def _validate_inputs(
    package_check: dict[str, Any],
    package: dict[str, Any],
    handoff_packet: dict[str, Any],
    generated_at: str,
) -> None:
    if package_check.get("kind") != OPERATOR_RUN_PACKAGE_CHECK_KIND:
        raise ValueError(f"next operator start packet requires kind {OPERATOR_RUN_PACKAGE_CHECK_KIND}")
    if package.get("kind") != OPERATOR_RUN_PACKAGE_KIND:
        raise ValueError(f"next operator start packet requires kind {OPERATOR_RUN_PACKAGE_KIND}")
    if handoff_packet.get("kind") != OPERATOR_HANDOFF_PACKET_KIND:
        raise ValueError(f"next operator start packet requires kind {OPERATOR_HANDOFF_PACKET_KIND}")
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("generated_at is required")
    if package_check.get("check_status") != PASSED or package_check.get("ready_for_handoff") is not True:
        raise ValueError("next operator start packet requires passed operator run package check")
    if package.get("package_status") != "ready":
        raise ValueError("next operator start packet requires ready operator run package")
    if handoff_packet.get("handoff_status") != "ready":
        raise ValueError("next operator start packet requires ready operator handoff packet")
    if package_check.get("provider_calls_started") is not False:
        raise ValueError("next operator start packet requires provider_calls_started false")
    if package_check.get("writes_long_term_memory") is not False:
        raise ValueError("next operator start packet requires writes_long_term_memory false")
    if package_check.get("writes_company_kb") is not False:
        raise ValueError("next operator start packet requires writes_company_kb false")
    _validate_same_source(package_check, package, handoff_packet)
    _validate_same_action(package_check, package, handoff_packet)
    if _list(package_check.get("missing_refs")):
        raise ValueError("next operator start packet requires no missing package refs")
    if _list(package_check.get("mismatched_refs")):
        raise ValueError("next operator start packet requires no mismatched package refs")
    if _list(package_check.get("unsafe_refs")):
        raise ValueError("next operator start packet requires no unsafe package refs")
    if _list(package_check.get("blocked_items")):
        raise ValueError("next operator start packet requires no blocked package items")
    if _list(package_check.get("failed_controls")):
        raise ValueError("next operator start packet requires no failed package controls")


def _validate_same_source(
    package_check: dict[str, Any],
    package: dict[str, Any],
    handoff_packet: dict[str, Any],
) -> None:
    source = package_check.get("source_operator_loop_id")
    if package.get("source_operator_loop_id") != source:
        raise ValueError("next operator start packet requires package source to match package check")
    if handoff_packet.get("source_operator_loop_id") != source:
        raise ValueError("next operator start packet requires handoff source to match package check")


def _validate_same_action(
    package_check: dict[str, Any],
    package: dict[str, Any],
    handoff_packet: dict[str, Any],
) -> None:
    action = _dict(package_check.get("next_operator_action"))
    if _dict(package.get("next_operator_action")) != action:
        raise ValueError("next operator start packet requires package action to match package check")
    if _dict(handoff_packet.get("next_operator_action")) != action:
        raise ValueError("next operator start packet requires handoff action to match package check")


def _artifact_root(check: dict[str, Any], check_path: Path) -> Path:
    recorded_root = str(check.get("artifact_root", "")).strip()
    if recorded_root:
        return Path(recorded_root)
    if check_path.parent.name == "operator_run_package_check":
        return check_path.parent.parent
    return check_path.parent


def _controls(
    package_check: dict[str, Any],
    package: dict[str, Any],
    handoff_packet: dict[str, Any],
) -> list[dict[str, str]]:
    return [
        _control("operator_run_package_check_passed", package_check.get("check_status") == PASSED),
        _control("operator_run_package_ready", package.get("package_status") == "ready"),
        _control("operator_handoff_ready", handoff_packet.get("handoff_status") == "ready"),
        _control("provider_calls_not_started", package_check.get("provider_calls_started") is False),
        _control("long_term_memory_write_disabled", package_check.get("writes_long_term_memory") is False),
        _control("company_kb_write_disabled", package_check.get("writes_company_kb") is False),
        _control("no_blocked_items", not _list(package_check.get("blocked_items"))),
        _control("no_failed_controls", not _list(package_check.get("failed_controls"))),
    ]


def _start_requirements(action: dict[str, Any]) -> list[str]:
    return [
        f"Execute next operator action: {action.get('action', 'unknown')}",
        "Use only checked package items and the embedded operator prompt.",
        "Do not use blocked refs, unpromoted candidates, or feedback events as memory.",
        "Do not call remote providers without an explicit provider gate.",
        "Do not write Company KB or durable memory from this start packet.",
    ]


def _claim_boundaries(package_check: dict[str, Any]) -> dict[str, str]:
    boundaries = dict(_dict(package_check.get("claim_boundaries")))
    boundaries.update(
        {
            "structure_verification": "machine_checked",
            "runtime_verification": "package_refs_checked",
            "human_acceptance": boundaries.get("human_acceptance", "not_claimed"),
            "business_validation": boundaries.get("business_validation", "not_claimed"),
            "durable_memory": "not_written",
            "company_kb_write": "not_written",
            "provider_success": "not_claimed",
        }
    )
    return boundaries


def _non_claims() -> list[str]:
    return [
        "not next-pass execution",
        "not human acceptance",
        "not business validation",
        "not durable memory",
        "not Company KB promotion",
        "not provider success",
    ]


def _checked_items(package_check: dict[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "path": str(_dict(item).get("path", "unknown")),
            "artifact_type": str(_dict(item).get("artifact_type", "unknown")),
            "role": str(_dict(item).get("role", "unknown")),
        }
        for item in _list(package_check.get("checked_items"))
    ]


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise ValueError(f"{label} not found: {_display_path(path)}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON: {_display_path(path)}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


def _display_path(path: Path) -> str:
    return str(path).replace("\\", "/")


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "NEXT_OPERATOR_START_PACKET_KIND",
    "build_next_operator_start_packet",
    "build_next_operator_start_packet_from_check_path",
    "load_operator_run_package_check",
    "render_next_operator_start_packet_markdown",
    "write_next_operator_start_packet_report",
)
