from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_asset_profiles import (
    build_asset_profile_test_package,
    load_asset_profile_seed,
    write_asset_profile_test_package,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


def production_memory_loop_asset_profile_readiness_command(
    operator_artifact_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to operator-loop manifest or operator run package JSON.",
    ),
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
        "2026-06-02T00:00:00+08:00",
        "--generated-at",
        help="ISO timestamp for generated asset profile artifacts.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/asset_profile_readiness"),
        "--output",
        "-o",
        help="Directory for asset profile readiness artifacts.",
        show_default=False,
    ),
) -> None:
    """Build tester-facing character/scene asset readiness from an operator artifact."""
    try:
        seed = load_asset_profile_seed(asset_profile_seed_path)
        bundle = build_asset_profile_test_package(
            operator_artifact_path=operator_artifact_path,
            asset_profile_seed=seed,
            generated_at=generated_at,
        )
        written_paths = write_asset_profile_test_package(bundle, output_dir)
    except ValueError as exc:
        typer.echo(f"Asset profile readiness failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    _echo_bundle(bundle, written_paths)
    if bundle["test_package"]["package_status"] != "ready_for_tester_review":
        raise typer.Exit(code=1)


def production_memory_loop_run_asset_test_package_command(
    loop_path: Path = typer.Option(
        Path("examples/agentflow/production_memory_loop.example.json"),
        "--loop",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to production-memory loop JSON.",
        show_default=False,
    ),
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
        "2026-06-02T00:00:00+08:00",
        "--generated-at",
        help="ISO timestamp for generated asset profile artifacts.",
    ),
    project_materials_path: Path | None = typer.Option(
        None,
        "--project-materials",
        help="Local ignored project materials path. The path is not persisted in package artifacts.",
    ),
    character_reference_image_path: Path | None = typer.Option(
        None,
        "--character-reference-image",
        help="Local ignored character reference image. The path is not persisted in package artifacts.",
    ),
    provider_config_path: Path | None = typer.Option(
        None,
        "--provider-config",
        help="Local ignored provider config JSON. Defaults to AFS_PROVIDER_CONFIG when provider validation runs.",
    ),
    run_provider_validation: bool = typer.Option(
        False,
        "--run-provider-validation",
        help="Attempt optional gated provider validation after the deterministic package is built.",
    ),
    image_service: str = typer.Option(
        "codex_image",
        "--image-service",
        help="Image service id for optional provider validation.",
    ),
    video_service: str = typer.Option(
        "seedance_i2v",
        "--video-service",
        help="Video service id for optional provider validation.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/asset_test_package"),
        "--output",
        "-o",
        help="Directory for the full no-provider asset test package.",
        show_default=False,
    ),
) -> None:
    """Run the no-provider operator loop and write a tester-facing asset package."""
    try:
        loop = load_production_memory_loop(loop_path)
        seed = load_asset_profile_seed(asset_profile_seed_path)
        operator_result = build_production_memory_operator_loop_run(
            loop,
            generated_at=generated_at,
            source_kb_status="restructuring_or_unknown",
            draft_next_pass_result=True,
        )
        write_production_memory_operator_loop_run(
            operator_result,
            output_dir / "operator_loop",
            write_run_package=True,
            write_run_package_check=True,
        )
        bundle = build_asset_profile_test_package(
            operator_artifact_path=output_dir / "operator_loop" / "production_memory_operator_loop_run.json",
            asset_profile_seed=seed,
            generated_at=generated_at,
            project_materials_path=project_materials_path,
            character_reference_image_path=character_reference_image_path,
            provider_config_path=provider_config_path,
            run_provider_validation=run_provider_validation,
            image_service=image_service,
            video_service=video_service,
            provider_validation_executor=_provider_validation_executor(run_provider_validation),
        )
        written_paths = write_asset_profile_test_package(bundle, output_dir)
    except ValueError as exc:
        typer.echo(f"Asset profile test package failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    _echo_bundle(bundle, written_paths)
    if bundle["test_package"]["package_status"] != "ready_for_tester_review":
        raise typer.Exit(code=1)


def _echo_bundle(bundle: dict, written_paths: list[Path]) -> None:
    readiness = bundle["readiness"]
    typer.echo(f"Asset profile test package: {readiness['readiness_status']}")
    typer.echo("Provider calls: not started by core package")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    provider_status = bundle["test_package"]["provider_validation"]["status"]
    typer.echo(f"Provider validation: {provider_status.replace('_', ' ')}")
    typer.echo(f"Profiles ready: {readiness['ready_profile_count']}/{readiness['profile_count']}")
    typer.echo(f"Blocked refs: {len(readiness['blocked_refs'])}")
    for path in written_paths:
        typer.echo(f"Wrote: {str(path).replace('\\', '/')}")


def _provider_validation_executor(run_provider_validation: bool):
    if not run_provider_validation:
        return None
    from agentflow_studio.model_gateway.asset_profile_provider_adapter import run_asset_profile_provider_validation

    return run_asset_profile_provider_validation


__all__ = (
    "production_memory_loop_asset_profile_readiness_command",
    "production_memory_loop_run_asset_test_package_command",
)
