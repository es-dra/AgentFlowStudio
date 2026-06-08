from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_asset_provider_validation_gate import run_provider_validation_gate


def asset_provider_validation_gate_command(
    asset_profile_seed_path: Path = typer.Option(
        ...,
        "--asset-profile-seed",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to asset profile seed JSON.",
    ),
    generated_at: str = typer.Option(
        "2026-06-04T02:00:00+08:00",
        "--generated-at",
        help="ISO timestamp for provider validation gate artifacts.",
    ),
    request_provider_validation: bool = typer.Option(
        False,
        "--request-validation",
        help="Request provider validation planning. This does not start provider calls.",
    ),
    run_provider_validation: bool = typer.Option(
        False,
        "--run-provider-validation",
        help="Attempt live provider validation only if capability gates and inputs are present.",
    ),
    provider_config_path: Path | None = typer.Option(
        None,
        "--provider-config",
        help="Local ignored provider config JSON. The path is not persisted.",
    ),
    project_materials_path: Path | None = typer.Option(
        None,
        "--project-materials",
        help="Explicit local ignored project materials path. The path is not persisted.",
    ),
    character_reference_image_path: Path | None = typer.Option(
        None,
        "--character-reference-image",
        help="Explicit local ignored character reference image path. The path is not persisted.",
    ),
    image_service: str = typer.Option("minimax_image", "--image-service", help="Image service id for provider smoke."),
    video_service: str = typer.Option("kling_i2v", "--video-service", help="Video service id for provider smoke."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/local_internal_test/provider_validation_gate"),
        "--output",
        "-o",
        help="Ignored runtime directory for provider validation gate artifacts.",
        show_default=False,
    ),
) -> None:
    """Write provider validation gate evidence without starting live providers by default."""
    try:
        report = run_provider_validation_gate(
            asset_profile_seed_path=asset_profile_seed_path,
            output_dir=output_dir,
            generated_at=generated_at,
            request_provider_validation=request_provider_validation,
            run_provider_validation=run_provider_validation,
            provider_config_path=provider_config_path,
            project_materials_path=project_materials_path,
            character_reference_image_path=character_reference_image_path,
            image_service=image_service,
            video_service=video_service,
        )
    except ValueError as exc:
        typer.echo(f"Provider validation gate failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Provider validation gate: {report['status']}")
    typer.echo("Provider calls: started" if report["provider_calls_started"] else "Provider calls: not started")
    typer.echo("Business validation: not claimed")
    typer.echo("Human acceptance: not claimed")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    typer.echo(f"Wrote: {str(output_dir / 'provider_validation_report.md').replace(chr(92), '/')}")


__all__ = ("asset_provider_validation_gate_command",)
