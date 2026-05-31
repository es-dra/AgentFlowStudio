from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.loulan_decision_intake import (
    build_loulan_decision_intake_report,
    write_loulan_decision_intake_report,
)


def loulan_decision_intake_command(
    decision_worksheet_path: Path = typer.Option(
        ...,
        "--decision-worksheet",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Loulan decision worksheet JSON.",
    ),
    decisions_path: Path = typer.Option(
        ...,
        "--decisions",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Manually filled Loulan decision JSON.",
    ),
    created_at: str = typer.Option(
        ...,
        "--created-at",
        help="ISO timestamp for the decision intake report.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/loulan_decision_intake/report"),
        "--output",
        "-o",
        help="Ignored output directory for Loulan decision intake artifacts.",
    ),
) -> None:
    """Validate manually filled Loulan decisions before context projection."""
    try:
        worksheet = json.loads(decision_worksheet_path.read_text(encoding="utf-8-sig"))
        decisions = json.loads(decisions_path.read_text(encoding="utf-8-sig"))
        report = build_loulan_decision_intake_report(worksheet, decisions, created_at=created_at)
        paths = write_loulan_decision_intake_report(report, output_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"Loulan decision intake failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Loulan decision intake")
    typer.echo(f"Status: {report['intake_status']}")
    typer.echo(f"Context bundle ready: {report['context_bundle_command_ready']}")
    typer.echo("Human acceptance: not recorded")
    typer.echo("Provider calls: not started")
    for path in paths:
        typer.echo(f"- {path.relative_to(output_dir).as_posix()}")
