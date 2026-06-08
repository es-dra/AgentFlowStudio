from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.harness.constants import FAILED, PASSED
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow.memory.production_operator_handoff import OPERATOR_HANDOFF_PACKET_KIND
from agentflow.memory.production_operator_manifest_check import OPERATOR_MANIFEST_CHECK_KIND
from agentflow.memory.production_operator_outputs import OPERATOR_LOOP_KIND
from agentflow.memory.production_operator_run_package_render import render_operator_run_package_markdown
from agentflow.harness.json_io import write_json

OPERATOR_RUN_PACKAGE_KIND = "agentflow_production_memory_operator_run_package"


def build_operator_run_package(
    manifest: dict[str, Any],
    *,
    manifest_check: dict[str, Any],
    handoff_packet: dict[str, Any],
    generated_at: str,
) -> dict[str, Any]:
    """Build the final no-provider operator run package for unattended handoff."""
    _validate_manifest(manifest)
    _validate_manifest_check(manifest_check)
    _validate_handoff_packet(handoff_packet)
    if not isinstance(generated_at, str) or not generated_at.strip():
        raise ValueError("generated_at is required")

    blocked_items = _blocked_items(manifest, manifest_check, handoff_packet)
    ready = not blocked_items
    package = {
        "kind": OPERATOR_RUN_PACKAGE_KIND,
        "artifact_type": OPERATOR_RUN_PACKAGE_KIND,
        "schema_version": manifest.get("schema_version", SCHEMA_VERSION),
        "package_id": f"operator-run-package:{manifest.get('loop_id', 'unknown')}",
        "generated_at": generated_at,
        "source_operator_loop_id": manifest.get("loop_id", "unknown"),
        "project_id": manifest.get("project_id", "unknown"),
        "package_status": "ready" if ready else "blocked",
        "manifest_chain_status": manifest.get("chain_status", "unknown"),
        "manifest_check_status": manifest_check.get("check_status", "unknown"),
        "handoff_status": handoff_packet.get("handoff_status", "unknown"),
        "checked_ref_count": manifest_check.get("checked_ref_count", 0),
        "output_artifact_count": len(_list(manifest.get("output_artifacts"))),
        "context_summary": _dict(manifest.get("context_summary")),
        "next_operator_action": _dict(handoff_packet.get("next_operator_action")),
        "provider_mode": "no-provider",
        "provider_calls_started": manifest.get("provider_calls_started") is True,
        "writes_long_term_memory": manifest.get("writes_long_term_memory") is True,
        "writes_company_kb": manifest.get("writes_company_kb") is True,
        "package_items": _package_items(manifest),
        "blocked_items": blocked_items,
        "controls": _controls(manifest, manifest_check, handoff_packet, ready),
        "non_claims": _non_claims(),
        "claim_boundaries": _claim_boundaries(manifest, manifest_check, handoff_packet),
    }
    acceptance_feedback_promotion = _dict(handoff_packet.get("acceptance_feedback_candidate_promotion"))
    if acceptance_feedback_promotion:
        package["acceptance_feedback_candidate_promotion"] = acceptance_feedback_promotion
    return package


def write_operator_run_package(package: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    json_path = write_json(output_root / "operator_run_package.json", package)
    markdown_path = output_root / "operator_run_package.md"
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_operator_run_package_markdown(package), encoding="utf-8")
    return [json_path, markdown_path]


def _validate_manifest(manifest: dict[str, Any]) -> None:
    if not isinstance(manifest, dict):
        raise ValueError("operator run package requires operator manifest JSON object")
    if manifest.get("kind") != OPERATOR_LOOP_KIND:
        raise ValueError(f"operator run package requires kind {OPERATOR_LOOP_KIND}")


def _validate_manifest_check(manifest_check: dict[str, Any]) -> None:
    if not isinstance(manifest_check, dict):
        raise ValueError("operator run package requires manifest check JSON object")
    if manifest_check.get("kind") != OPERATOR_MANIFEST_CHECK_KIND:
        raise ValueError(f"operator run package manifest check requires kind {OPERATOR_MANIFEST_CHECK_KIND}")


def _validate_handoff_packet(handoff_packet: dict[str, Any]) -> None:
    if not isinstance(handoff_packet, dict):
        raise ValueError("operator run package requires handoff packet JSON object")
    if handoff_packet.get("kind") != OPERATOR_HANDOFF_PACKET_KIND:
        raise ValueError(f"operator run package handoff requires kind {OPERATOR_HANDOFF_PACKET_KIND}")


def _blocked_items(
    manifest: dict[str, Any],
    manifest_check: dict[str, Any],
    handoff_packet: dict[str, Any],
) -> list[dict[str, str]]:
    blocked: list[dict[str, str]] = []
    if manifest.get("chain_status") != "ready":
        blocked.append({"ref": "operator_loop", "reason": "operator manifest chain is not ready"})
    if manifest_check.get("check_status") != PASSED:
        blocked.append({"ref": "operator_manifest_check", "reason": "operator manifest check did not pass"})
    if handoff_packet.get("handoff_status") != "ready":
        blocked.append({"ref": "operator_handoff", "reason": "operator handoff packet is not ready"})
    if not _handoff_source_matches_manifest(manifest, handoff_packet):
        blocked.append({"ref": "operator_handoff", "reason": "operator handoff source does not match manifest"})
    if manifest.get("provider_calls_started") is True:
        blocked.append({"ref": "provider_calls", "reason": "provider calls started before no-provider run package"})
    if manifest.get("writes_long_term_memory") is True:
        blocked.append({"ref": "long_term_memory", "reason": "operator run writes durable memory"})
    if manifest.get("writes_company_kb") is True:
        blocked.append({"ref": "company_kb", "reason": "operator run writes Company KB"})
    blocked.extend({"ref": str(item), "reason": "missing operator artifact ref"} for item in _list(manifest_check.get("missing_refs")))
    blocked.extend({"ref": str(item), "reason": "unsafe operator artifact ref"} for item in _list(manifest_check.get("unsafe_refs")))
    blocked.extend(_blocked_ref(item, "mismatched operator artifact type") for item in _list(manifest_check.get("mismatched_refs")))
    blocked.extend(_blocked_ref(item, "operator node failed") for item in _list(manifest_check.get("failed_nodes")))
    blocked.extend(_blocked_ref(item, "operator control failed") for item in _list(manifest_check.get("failed_controls")))
    blocked.extend(_dedupe_handoff_blockers(handoff_packet.get("blocked_items")))
    return _dedupe_blockers(blocked)


def _package_items(manifest: dict[str, Any]) -> list[dict[str, str]]:
    items = [
        _package_item("production_memory_operator_loop_run.json", OPERATOR_LOOP_KIND, "core_manifest"),
        _package_item("operator_manifest_check/operator_manifest_check.json", OPERATOR_MANIFEST_CHECK_KIND, "manifest_check"),
        _package_item("operator_handoff/operator_handoff_packet.json", OPERATOR_HANDOFF_PACKET_KIND, "operator_handoff"),
        _package_item("operator_handoff/operator_handoff_packet.md", "markdown_report", "operator_handoff"),
    ]
    seen = {item["path"] for item in items}
    for artifact in _list(manifest.get("output_artifacts")):
        path = str(_dict(artifact).get("path", "unknown")).replace("\\", "/")
        if path in seen:
            continue
        items.append(
            _package_item(
                path,
                str(_dict(artifact).get("artifact_type", "unknown")),
                "operator_output",
                required=_dict(artifact).get("required", True),
            )
        )
        seen.add(path)
    return items


def _controls(
    manifest: dict[str, Any],
    manifest_check: dict[str, Any],
    handoff_packet: dict[str, Any],
    ready: bool,
) -> list[dict[str, str]]:
    return [
        _control("manifest_chain_ready", manifest.get("chain_status") == "ready"),
        _control("operator_manifest_check_passed", manifest_check.get("check_status") == PASSED),
        _control("operator_handoff_ready", handoff_packet.get("handoff_status") == "ready"),
        _control("operator_handoff_source_matches_manifest", _handoff_source_matches_manifest(manifest, handoff_packet)),
        _control("provider_calls_not_started", manifest.get("provider_calls_started") is False),
        _control("long_term_memory_write_disabled", manifest.get("writes_long_term_memory") is False),
        _control("company_kb_write_disabled", manifest.get("writes_company_kb") is False),
        _control("operator_run_package_ready", ready),
    ]


def _claim_boundaries(
    manifest: dict[str, Any],
    manifest_check: dict[str, Any],
    handoff_packet: dict[str, Any],
) -> dict[str, str]:
    boundaries = dict(_dict(manifest.get("non_claim_boundaries")))
    boundaries.update(
        {
            "structure_verification": "machine_checked" if manifest_check.get("check_status") == PASSED else "blocked",
            "runtime_verification": "artifact_refs_checked" if handoff_packet.get("handoff_status") == "ready" else "blocked",
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
        "not human acceptance",
        "not business validation",
        "not durable memory",
        "not Company KB promotion",
        "not provider success",
    ]


def _handoff_source_matches_manifest(manifest: dict[str, Any], handoff_packet: dict[str, Any]) -> bool:
    return handoff_packet.get("source_operator_loop_id") == manifest.get("loop_id")


def _package_item(path: str, artifact_type: str, role: str, *, required: Any = True) -> dict[str, str]:
    return {
        "path": path,
        "artifact_type": artifact_type,
        "role": role,
        "required": str(required).lower(),
        "status": "expected",
    }


def _blocked_ref(item: Any, reason: str) -> dict[str, str]:
    value = _dict(item)
    ref = value.get("path") or value.get("node_id") or value.get("control_id") or "unknown"
    return {"ref": str(ref), "reason": reason}


def _dedupe_handoff_blockers(value: Any) -> list[dict[str, str]]:
    return [{"ref": str(_dict(item).get("ref", "unknown")), "reason": str(_dict(item).get("reason", "blocked"))} for item in _list(value)]


def _dedupe_blockers(items: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, str]] = []
    for item in items:
        key = (item["ref"], item["reason"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _control(control_id: str, passed: bool) -> dict[str, str]:
    return {"control_id": control_id, "status": PASSED if passed else FAILED}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "OPERATOR_RUN_PACKAGE_KIND",
    "build_operator_run_package",
    "render_operator_run_package_markdown",
    "write_operator_run_package",
)
