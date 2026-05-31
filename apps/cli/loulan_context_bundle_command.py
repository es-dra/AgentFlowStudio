from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.loulan_context_bundle import (
    build_loulan_context_bundle_projection,
    write_loulan_context_bundle_projection,
)


def loulan_context_bundle_command(
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
        help="Explicit human decision JSON for the Loulan review pack.",
    ),
    created_at: str = typer.Option(
        ...,
        "--created-at",
        help="ISO timestamp for the context bundle projection.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/loulan_context_bundle/projection"),
        "--output",
        "-o",
        help="Ignored output directory for Loulan context bundle projection artifacts.",
    ),
) -> None:
    """Project explicit Loulan human decisions into a no-call context bundle."""
    try:
        review_pack = json.loads(review_pack_path.read_text(encoding="utf-8-sig"))
        decisions = json.loads(decisions_path.read_text(encoding="utf-8-sig"))
        projection = build_loulan_context_bundle_projection(
            review_pack,
            decisions,
            created_at=created_at,
        )
        paths = write_loulan_context_bundle_projection(projection, output_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"Loulan context bundle projection failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Loulan context bundle projection")
    typer.echo(f"Decision audit: {projection['decision_audit']['status']}")
    typer.echo(f"Context bundle: {projection['context_bundle']['status']}")
    typer.echo("Provider calls: not started")
    for path in paths:
        typer.echo(f"- {path.relative_to(output_dir).as_posix()}")
