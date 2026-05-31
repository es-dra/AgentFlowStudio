from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.loulan_decision_template import (
    build_loulan_decision_template,
    write_loulan_decision_template,
)


def loulan_decision_template_command(
    review_pack_path: Path = typer.Option(
        ...,
        "--review-pack",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Loulan human review pack JSON.",
    ),
    created_at: str = typer.Option(
        ...,
        "--created-at",
        help="ISO timestamp for the decision template.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/loulan_decision_template/template"),
        "--output",
        "-o",
        help="Ignored output directory for Loulan human decision template artifacts.",
    ),
) -> None:
    """Write a fillable Loulan human-decision template without approving anything."""
    try:
        review_pack = json.loads(review_pack_path.read_text(encoding="utf-8-sig"))
        template = build_loulan_decision_template(review_pack, created_at=created_at)
        paths = write_loulan_decision_template(template, output_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"Loulan decision template failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Loulan decision template")
    typer.echo(f"Decision slots: {len(template['decisions'])}")
    typer.echo("Human acceptance: not recorded")
    typer.echo("Provider calls: not started")
    for path in paths:
        typer.echo(f"- {path.relative_to(output_dir).as_posix()}")
