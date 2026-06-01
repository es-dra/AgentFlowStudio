from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.loulan_package import build_loulan_memory_package, write_loulan_memory_package


def loulan_memory_package_command(
    project_root: Path = typer.Option(
        ...,
        "--project-root",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="LoulanSceneAssets project root to read as an explicit local pilot package.",
    ),
    created_at: str = typer.Option(
        ...,
        "--created-at",
        help="ISO timestamp for the package artifact.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/loulan_memory_package"),
        "--output",
        "-o",
        help="Ignored output directory for Loulan memory package artifacts.",
    ),
) -> None:
    """Write a no-call Loulan pilot memory package from explicit local manifests."""
    try:
        package = build_loulan_memory_package(project_root, created_at=created_at)
        paths = write_loulan_memory_package(package, output_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"Loulan memory package failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Loulan memory package")
    typer.echo(f"Project: {package['project']['project_id']}")
    typer.echo(f"Shots: {package['shot_summary']['total_shots']}")
    typer.echo(f"Overall gate: {package['promotion_gates']['overall_status']}")
    audits = package["project_audits"]
    manifest_summary = audits["manifest_reference"].get("summary", {})
    text_summary = audits["text_encoding"].get("summary", {})
    phase_summary = audits["phase_gate"].get("summary", {})
    typer.echo(
        "Manifest audit: "
        f"{audits['manifest_reference']['status']}; "
        f"errors {manifest_summary.get('errors', 'unknown')}; "
        f"invalid asset types {manifest_summary.get('invalid_asset_types', 'unknown')}; "
        f"invalid statuses {manifest_summary.get('invalid_statuses', 'unknown')}"
    )
    typer.echo(f"Text encoding audit: {audits['text_encoding']['status']}; errors {text_summary.get('errors', 'unknown')}")
    typer.echo(
        "Phase gate audit: "
        f"{audits['phase_gate']['status']}; "
        f"failures {phase_summary.get('failures', 'unknown')}; "
        f"pending B01 {phase_summary.get('pending_b01_decisions', 'unknown')}"
    )
    typer.echo("Provider calls: not started")
    for path in paths:
        typer.echo(f"- {path.relative_to(output_dir).as_posix()}")
