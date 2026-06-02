from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow.memory.production_operator_action_result_output import write_next_operator_action_result_from_operator_loop
from agentflow.memory.production_operator_start_event_output import write_next_operator_start_event_from_operator_loop
from agentflow.memory.production_operator_start_packet_output import write_next_operator_start_packet_from_operator_loop


def validate_post_check_output_options(
    *,
    write_run_package: bool,
    write_run_package_check: bool,
    write_next_operator_start_packet: bool,
    write_next_operator_start_event: bool,
    write_next_operator_action_result: bool,
    next_operator_start_event_decision: str | None,
    next_operator_start_event_summary: str | None,
    next_operator_action_result_decision: str | None,
    next_operator_action_result_summary: str | None,
    next_operator_action_result_refs: list[str] | None,
) -> None:
    if write_run_package_check and not write_run_package:
        raise ValueError("write_run_package_check requires write_run_package")
    if write_next_operator_start_packet and not write_run_package_check:
        raise ValueError("write_next_operator_start_packet requires write_run_package_check")
    if write_next_operator_start_event and not write_next_operator_start_packet:
        raise ValueError("write_next_operator_start_event requires write_next_operator_start_packet")
    if write_next_operator_start_event and not (next_operator_start_event_decision or "").strip():
        raise ValueError("next_operator_start_event_decision is required")
    if write_next_operator_start_event and not (next_operator_start_event_summary or "").strip():
        raise ValueError("next_operator_start_event_summary is required")
    if write_next_operator_action_result and not write_next_operator_start_event:
        raise ValueError("write_next_operator_action_result requires write_next_operator_start_event")
    if write_next_operator_action_result and not (next_operator_action_result_decision or "").strip():
        raise ValueError("next_operator_action_result_decision is required")
    if write_next_operator_action_result and not (next_operator_action_result_summary or "").strip():
        raise ValueError("next_operator_action_result_summary is required")
    if (
        write_next_operator_action_result
        and next_operator_action_result_decision == "completed"
        and not _list(next_operator_action_result_refs)
    ):
        raise ValueError("completed next_operator_action_result requires result refs")


def write_post_check_outputs(
    result: dict[str, Any],
    output_root: str | Path,
    *,
    write_next_operator_start_packet: bool,
    write_next_operator_start_event: bool,
    write_next_operator_action_result: bool,
    next_operator_start_event_decision: str | None,
    next_operator_start_event_summary: str | None,
    next_operator_start_event_operator_role: str,
    next_operator_action_result_decision: str | None,
    next_operator_action_result_summary: str | None,
    next_operator_action_result_refs: list[str] | None,
    next_operator_action_result_operator_role: str,
) -> list[Path]:
    root = Path(output_root)
    generated_at = str(result["manifest"].get("generated_at", ""))
    written_paths: list[Path] = []
    if write_next_operator_start_packet:
        written_paths.extend(
            write_next_operator_start_packet_from_operator_loop(
                result,
                root,
                generated_at=generated_at,
            )
        )
    if write_next_operator_start_event:
        written_paths.extend(
            write_next_operator_start_event_from_operator_loop(
                result,
                root,
                decision=str(next_operator_start_event_decision),
                summary=str(next_operator_start_event_summary),
                operator_role=next_operator_start_event_operator_role,
                recorded_at=generated_at,
            )
        )
    if write_next_operator_action_result:
        written_paths.extend(
            write_next_operator_action_result_from_operator_loop(
                result,
                root,
                decision=str(next_operator_action_result_decision),
                summary=str(next_operator_action_result_summary),
                result_refs=next_operator_action_result_refs,
                operator_role=next_operator_action_result_operator_role,
                recorded_at=generated_at,
            )
        )
    return written_paths


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


__all__ = (
    "validate_post_check_output_options",
    "write_post_check_outputs",
)
