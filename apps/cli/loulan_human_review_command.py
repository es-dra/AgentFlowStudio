from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.loulan_human_review_pack import (
    build_loulan_human_review_pack,
    write_loulan_human_review_pack,
)


def loulan_human_review_pack_command(
    package_path: Path = typer.Option(
        ...,
        "--package",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Loulan memory package JSON produced by loulan-memory-package.",
    ),
    api_plan_path: Path = typer.Option(
        ...,
        "--api-plan",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Loulan API workbench plan JSON produced by loulan-api-workbench-plan.",
    ),
    project_root: Path = typer.Option(
        ...,
        "--project-root",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Local LoulanSceneAssets root used only to read explicit review manifests.",
    ),
    block_id: str = typer.Option(
        "B01",
        "--block-id",
        help="Loulan block id to prepare for human review.",
    ),
    created_at: str = typer.Option(
        ...,
        "--created-at",
        help="ISO timestamp for the human review pack draft.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/loulan_human_review_pack/pack"),
        "--output",
        "-o",
        help="Ignored output directory for Loulan human review pack artifacts.",
    ),
) -> None:
    """Write a no-call Loulan human review pack without approving memory."""
    try:
        package = json.loads(package_path.read_text(encoding="utf-8-sig"))
        api_plan = json.loads(api_plan_path.read_text(encoding="utf-8-sig"))
        pack = build_loulan_human_review_pack(
            package,
            api_plan,
            project_root=project_root,
            block_id=block_id,
            created_at=created_at,
        )
        paths = write_loulan_human_review_pack(pack, output_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"Loulan human review pack failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Loulan human review pack")
    typer.echo(f"Block: {pack['review_scope']['block_id']}")
    typer.echo(f"Evidence status: {pack['review_scope']['evidence_status']}")
    typer.echo("Human acceptance: not recorded")
    typer.echo("Provider calls: not started")
    for path in paths:
        typer.echo(f"- {path.relative_to(output_dir).as_posix()}")
