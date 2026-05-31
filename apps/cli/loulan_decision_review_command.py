from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.loulan_decision_review_pack import (
    build_loulan_decision_review_pack,
    write_loulan_decision_review_pack,
)


def loulan_decision_review_pack_command(
    review_pack_path: Path = typer.Option(
        ...,
        "--review-pack",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Loulan human review pack JSON.",
    ),
    decisions_path: Path = typer.Option(
        ...,
        "--decisions",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Loulan decision template or filled decision JSON.",
    ),
    created_at: str = typer.Option(
        ...,
        "--created-at",
        help="ISO timestamp for the decision review pack.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/loulan_decision_review_pack/pack"),
        "--output",
        "-o",
        help="Ignored output directory for Loulan decision review artifacts.",
    ),
) -> None:
    """Write a no-call Loulan decision review pack without approving anything."""
    try:
        review_pack = json.loads(review_pack_path.read_text(encoding="utf-8-sig"))
        decisions = json.loads(decisions_path.read_text(encoding="utf-8-sig"))
        pack = build_loulan_decision_review_pack(review_pack, decisions, created_at=created_at)
        paths = write_loulan_decision_review_pack(pack, output_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"Loulan decision review pack failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Loulan decision review pack")
    typer.echo(f"Status: {pack['review_status']}")
    typer.echo(f"Decision slots: {pack['decision_summary']['decision_slots']}")
    typer.echo("Human acceptance: not recorded")
    typer.echo("Provider calls: not started")
    for path in paths:
        typer.echo(f"- {path.relative_to(output_dir).as_posix()}")
