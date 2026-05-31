from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.loulan_api_workbench import (
    build_loulan_api_workbench_plan,
    write_loulan_api_workbench_plan,
)


def loulan_api_workbench_plan_command(
    package_path: Path = typer.Option(
        ...,
        "--package",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Loulan memory package JSON produced by loulan-memory-package.",
    ),
    created_at: str = typer.Option(
        ...,
        "--created-at",
        help="ISO timestamp for the dry-run API workbench plan.",
    ),
    provider_adapter_id: str = typer.Option(
        "openai_compatible_image",
        "--provider-adapter",
        help="Image provider adapter slot name for request preview only.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/loulan_api_workbench/plan"),
        "--output",
        "-o",
        help="Ignored output directory for Loulan API workbench preview artifacts.",
    ),
) -> None:
    """Write a no-call Loulan API workbench request preview from a package."""
    try:
        package = json.loads(package_path.read_text(encoding="utf-8-sig"))
        plan = build_loulan_api_workbench_plan(
            package,
            created_at=created_at,
            provider_adapter_id=provider_adapter_id,
        )
        paths = write_loulan_api_workbench_plan(plan, output_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"Loulan API workbench plan failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Loulan API workbench plan")
    typer.echo(f"Package: {plan['package_id']}")
    typer.echo(f"Reference pack: {plan['reference_pack']['status']}")
    typer.echo(f"Requests previewed: {len(plan['request_manifest']['requests'])}")
    typer.echo("Provider calls: not started")
    for path in paths:
        typer.echo(f"- {path.relative_to(output_dir).as_posix()}")
