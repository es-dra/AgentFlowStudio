from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from agentflow.harness.json_io import write_json
from agentflow.memory.promotion import validate_evidence_reuse_review


def memory_evidence_reuse_review_command(
    review_path: Path = typer.Option(
        ...,
        "--review",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to agentflow_memory_evidence_reuse_review JSON.",
    ),
    candidate_path: Path = typer.Option(
        ...,
        "--candidate",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to agentflow_memory_candidate JSON.",
    ),
    decision_path: Path = typer.Option(
        ...,
        "--decision",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to agentflow_memory_promotion_decision JSON.",
    ),
    output_path: Path | None = typer.Option(
        None,
        "--output",
        help="Optional explicit path to write validation JSON. Omit for stdout-only review.",
    ),
) -> None:
    """Validate memory evidence reuse without execution, providers, or durable writes."""
    validation = validate_evidence_reuse_review(
        evidence_reuse_review=_read_json_object(review_path),
        memory_candidate=_read_json_object(candidate_path),
        memory_promotion_decision=_read_json_object(decision_path),
    )
    if output_path is not None:
        write_json(output_path, validation)

    status = validation["overall_status"]
    typer.echo(f"Memory evidence reuse review: {status}")
    typer.echo("Review-only: true")
    typer.echo("Writes long-term memory: false")
    typer.echo("Provider calls: not started")
    typer.echo(f"Output file: {'written' if output_path is not None else 'not written'}")
    _echo_failed_checks(validation)

    if status != "passed":
        raise typer.Exit(code=1)


def _read_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise typer.BadParameter("expected a JSON object")
    return payload


def _echo_failed_checks(validation: dict[str, Any]) -> None:
    failed = [check for check in validation.get("checks", []) if check.get("status") == "failed"]
    if not failed:
        return
    typer.echo("Failed checks:")
    for check in failed:
        typer.echo(f"- {check.get('check_id')}: {check.get('message')}")


__all__ = ("memory_evidence_reuse_review_command",)
