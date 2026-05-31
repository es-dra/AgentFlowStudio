from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.loulan_decision_worksheet import (
    build_loulan_decision_worksheet,
    write_loulan_decision_worksheet,
)


def loulan_decision_worksheet_command(
    decision_review_pack_path: Path = typer.Option(
        ...,
        "--decision-review-pack",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Loulan decision review pack JSON.",
    ),
    created_at: str = typer.Option(
        ...,
        "--created-at",
        help="ISO timestamp for the decision worksheet.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/loulan_decision_worksheet/worksheet"),
        "--output",
        "-o",
        help="Ignored output directory for Loulan decision worksheet artifacts.",
    ),
) -> None:
    """Write a copy-only Loulan human decision worksheet."""
    try:
        decision_review_pack = json.loads(decision_review_pack_path.read_text(encoding="utf-8-sig"))
        worksheet = build_loulan_decision_worksheet(decision_review_pack, created_at=created_at)
        paths = write_loulan_decision_worksheet(worksheet, output_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"Loulan decision worksheet failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Loulan decision worksheet")
    typer.echo(f"Status: {worksheet['worksheet_status']}")
    typer.echo(f"Rows: {len(worksheet['decision_rows'])}")
    typer.echo("Human acceptance: not recorded")
    typer.echo("Provider calls: not started")
    for path in paths:
        typer.echo(f"- {path.relative_to(output_dir).as_posix()}")
