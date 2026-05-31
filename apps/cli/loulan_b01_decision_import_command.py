from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.loulan_b01_decision_import import (
    build_loulan_b01_decision_import,
    write_loulan_b01_decision_import,
)


def loulan_b01_decision_import_command(
    review_pack_path: Path = typer.Option(
        ...,
        "--review-pack",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Loulan human review pack JSON.",
    ),
    b01_decisions_path: Path = typer.Option(
        ...,
        "--b01-decisions",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Local Loulan B01 human review decision JSON.",
    ),
    created_at: str = typer.Option(
        ...,
        "--created-at",
        help="ISO timestamp for the imported decision file.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/loulan_b01_decision_import/imported"),
        "--output",
        "-o",
        help="Ignored output directory for imported Loulan B01 decision artifacts.",
    ),
) -> None:
    """Import explicit local B01 shot decisions into an AFS decision file."""
    try:
        review_pack = json.loads(review_pack_path.read_text(encoding="utf-8-sig"))
        b01_decisions = json.loads(b01_decisions_path.read_text(encoding="utf-8-sig"))
        imported = build_loulan_b01_decision_import(
            review_pack,
            b01_decisions,
            created_at=created_at,
        )
        paths = write_loulan_b01_decision_import(imported, output_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"Loulan B01 decision import failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    summary = imported["import_summary"]
    typer.echo("Loulan B01 decision import")
    typer.echo(f"Imported ready decisions: {summary['imported_ready_decisions']}")
    typer.echo(f"Pending decisions: {summary['pending_decisions']}")
    typer.echo("Human acceptance: not recorded")
    typer.echo("Provider calls: not started")
    for path in paths:
        typer.echo(f"- {path.relative_to(output_dir).as_posix()}")
