from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.memory.production_operator_start_packet import (
    NEXT_OPERATOR_START_PACKET_KIND,
    build_next_operator_start_packet_from_check_path,
    write_next_operator_start_packet_report,
)
from narratocut.utils import write_json


NEXT_OPERATOR_START_PACKET_ARTIFACTS = [
    {
        "artifact_type": NEXT_OPERATOR_START_PACKET_KIND,
        "path": "next_operator_start_packet/next_operator_start_packet.json",
        "required": True,
    },
    {
        "artifact_type": "markdown_report",
        "path": "next_operator_start_packet/next_operator_start_packet.md",
        "required": True,
    },
]


def write_next_operator_start_packet_from_operator_loop(
    result: dict[str, Any],
    output_root: str | Path,
    *,
    generated_at: str,
) -> list[Path]:
    """Write the final post-check start packet and record it outside output_artifacts."""
    root = Path(output_root)
    check_path = root / "operator_run_package_check" / "operator_run_package_check.json"
    packet = build_next_operator_start_packet_from_check_path(
        check_path,
        generated_at=generated_at,
        artifact_root=root,
    )
    written_paths = write_next_operator_start_packet_report(packet, root / "next_operator_start_packet")
    result["next_operator_start_packet"] = packet
    manifest = result["manifest"]
    manifest["next_operator_start_packet"] = _start_packet_summary(packet)
    manifest["post_check_artifacts"] = _post_check_artifacts(manifest.get("post_check_artifacts"))
    write_json(root / "production_memory_operator_loop_run.json", manifest)
    return written_paths


def _start_packet_summary(packet: dict[str, Any]) -> dict[str, Any]:
    action = _dict(packet.get("next_operator_action"))
    return {
        "kind": packet.get("kind", NEXT_OPERATOR_START_PACKET_KIND),
        "start_packet_status": packet.get("start_packet_status", "unknown"),
        "ready_for_next_operator": packet.get("ready_for_next_operator") is True,
        "path": "next_operator_start_packet/next_operator_start_packet.json",
        "markdown_path": "next_operator_start_packet/next_operator_start_packet.md",
        "checked_package_item_count": packet.get("checked_package_item_count", 0),
        "next_operator_action": action.get("action", "unknown"),
        "provider_calls_started": packet.get("provider_calls_started") is True,
        "writes_long_term_memory": packet.get("writes_long_term_memory") is True,
        "writes_company_kb": packet.get("writes_company_kb") is True,
    }


def _post_check_artifacts(existing: Any) -> list[dict[str, Any]]:
    by_path = {
        str(_dict(item).get("path", "")): _dict(item)
        for item in _list(existing)
        if _dict(item).get("path")
    }
    for artifact in NEXT_OPERATOR_START_PACKET_ARTIFACTS:
        by_path[artifact["path"]] = dict(artifact)
    return list(by_path.values())


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "NEXT_OPERATOR_START_PACKET_ARTIFACTS",
    "write_next_operator_start_packet_from_operator_loop",
)
