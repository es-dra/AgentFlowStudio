from __future__ import annotations

from pathlib import Path

import typer

from narratocut.memory_advantage_demo_012 import (
    DEFAULT_OUTPUT_DIR as DEMO_012_OUTPUT_DIR,
    DEFAULT_RUN_ROOT as DEMO_012_RUN_ROOT,
    build_demo_012_package,
    run_demo_012_i2v_storyboards,
    run_demo_012_i2i_keyframes,
    write_demo_012_package,
)
from narratocut.memory_advantage_demo_015 import (
    DEFAULT_OUTPUT_DIR as DEMO_015_OUTPUT_DIR,
    DEFAULT_RUN_ROOT as DEMO_015_RUN_ROOT,
    build_demo_015_package,
    run_demo_015_i2v_protocol,
    write_demo_015_package,
)
from narratocut.model_gateway.company_secrets import (
    COMPANY_PROVIDER_CONFIG_ENV,
    load_company_provider_secrets,
)
from narratocut.model_gateway.errors import ModelGatewayError


def memory_advantage_demo_012_plan_command(
    output_dir: Path = typer.Option(
        DEMO_012_OUTPUT_DIR,
        "--output",
        "-o",
        help="Ignored output directory for the safe six-image I2I consistency package.",
    ),
    subject_reference_image_ref: str = typer.Option(
        "yiqi_front.png",
        "--subject-reference-image-ref",
        help="Display-only reference image file name; no local path or image bytes are persisted.",
    ),
    provider_config_path: Path | None = typer.Option(
        None,
        "--provider-config",
        help=f"Local ignored provider config JSON. Defaults to ${COMPANY_PROVIDER_CONFIG_ENV}.",
    ),
) -> None:
    """Write the no-call fixed-asset I2I/I2V consistency experiment package."""
    try:
        store = load_company_provider_secrets(provider_config_path)
        package = build_demo_012_package(
            store,
            subject_reference_image_ref=subject_reference_image_ref,
        )
        paths = write_demo_012_package(package, output_dir)
    except ModelGatewayError as exc:
        typer.echo(f"AFS-MEMORY-ADVANTAGE-DEMO-012 plan failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("AFS-MEMORY-ADVANTAGE-DEMO-012 plan")
    typer.echo(f"Images planned: {package['image_budget']['total_keyframes']}")
    for path in paths:
        typer.echo(f"- {_display_ref(path)}")
    typer.echo("Provider calls: not started")


def memory_advantage_demo_012_i2i_runtime_command(
    run_dir: Path = typer.Option(
        DEMO_012_RUN_ROOT,
        "--run-dir",
        help="Ignored DEMO-012 run root for MiniMax I2I keyframes and image review.",
    ),
    subject_reference_image: Path = typer.Option(
        ...,
        "--subject-reference-image",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Local ignored JPG/PNG character reference image.",
    ),
    provider_config_path: Path | None = typer.Option(
        None,
        "--provider-config",
        help=f"Local ignored provider config JSON. Defaults to ${COMPANY_PROVIDER_CONFIG_ENV}.",
    ),
    image_service_id: str = typer.Option(
        "minimax_image",
        "--image-service",
        help="MiniMax image service id.",
    ),
) -> None:
    """Run gated DEMO-012 MiniMax I2I keyframes and write a side-by-side review."""
    try:
        store = load_company_provider_secrets(provider_config_path)
        summary = run_demo_012_i2i_keyframes(
            store,
            run_dir,
            subject_reference_image_path=subject_reference_image,
            image_service_id=image_service_id,
        )
    except (ModelGatewayError, OSError, KeyError, ValueError) as exc:
        typer.echo(f"AFS-MEMORY-ADVANTAGE-DEMO-012 I2I runtime failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("AFS-MEMORY-ADVANTAGE-DEMO-012 I2I runtime")
    typer.echo(f"Status: {summary['status']}")
    typer.echo(f"Images: {summary['generated_image_count']}")
    typer.echo(f"Review: {_display_ref(run_dir / summary['review_path'])}")
    typer.echo(f"HTML: {_display_ref(run_dir / summary['html_path'])}")
    typer.echo("Claim boundary: provider smoke is not creative quality validation")


def memory_advantage_demo_012_i2v_runtime_command(
    run_dir: Path = typer.Option(
        DEMO_012_RUN_ROOT,
        "--run-dir",
        help="Ignored DEMO-012 run root containing existing I2I keyframes.",
    ),
    provider_config_path: Path | None = typer.Option(
        None,
        "--provider-config",
        help=f"Local ignored provider config JSON. Defaults to ${COMPANY_PROVIDER_CONFIG_ENV}.",
    ),
    i2v_service_id: str = typer.Option(
        "kling_i2v",
        "--i2v-service",
        help="Kling I2V service id.",
    ),
    duration: str = typer.Option(
        "5",
        "--duration",
        help="Video duration in seconds.",
    ),
    mode: str = typer.Option(
        "pro",
        "--mode",
        help="Kling video mode.",
    ),
    poll_interval_sec: float = typer.Option(
        5.0,
        "--poll-interval-sec",
        help="Seconds to wait between provider status polls.",
    ),
    max_polls: int = typer.Option(
        120,
        "--max-polls",
        help="Maximum provider status polls before failing.",
    ),
    transport: str = typer.Option(
        "httpx",
        "--transport",
        help="HTTP transport for Kling live calls: httpx or curl.",
    ),
) -> None:
    """Run gated DEMO-012 Kling I2V storyboards from existing keyframes."""
    try:
        store = load_company_provider_secrets(provider_config_path)
        summary = run_demo_012_i2v_storyboards(
            store,
            run_dir,
            i2v_service_id=i2v_service_id,
            duration=duration,
            mode=mode,
            poll_interval_sec=poll_interval_sec,
            max_polls=max_polls,
            transport=transport,
        )
    except (ModelGatewayError, OSError, KeyError, ValueError) as exc:
        typer.echo(f"AFS-MEMORY-ADVANTAGE-DEMO-012 I2V runtime failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("AFS-MEMORY-ADVANTAGE-DEMO-012 I2V runtime")
    typer.echo(f"Status: {summary['status']}")
    typer.echo(f"Videos: {summary['generated_video_count']}")
    typer.echo(f"Review: {_display_ref(run_dir / summary['review_path'])}")
    typer.echo(f"HTML: {_display_ref(run_dir / summary['html_path'])}")
    typer.echo("Claim boundary: provider smoke is not creative quality validation")


def memory_advantage_demo_015_plan_command(
    output_dir: Path = typer.Option(
        DEMO_015_OUTPUT_DIR,
        "--output",
        "-o",
        help="Ignored output directory for the safe memory-backed production protocol package.",
    ),
    source_keyframe_ref: str = typer.Option(
        "demo_012_memory_desert_candidate_001.jpg",
        "--source-keyframe-ref",
        help="Display-only keyframe file name; no local path or image bytes are persisted.",
    ),
    provider_config_path: Path | None = typer.Option(
        None,
        "--provider-config",
        help=f"Local ignored provider config JSON. Defaults to ${COMPANY_PROVIDER_CONFIG_ENV}.",
    ),
) -> None:
    """Write the no-call DEMO-015 memory-backed desert I2V protocol package."""
    try:
        store = load_company_provider_secrets(provider_config_path)
        package = build_demo_015_package(store, source_keyframe_ref=source_keyframe_ref)
        paths = write_demo_015_package(package, output_dir)
    except ModelGatewayError as exc:
        typer.echo(f"AFS-MEMORY-ADVANTAGE-DEMO-015 plan failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("AFS-MEMORY-ADVANTAGE-DEMO-015 plan")
    typer.echo(f"Video requests planned: {len(package['video_requests'])}")
    for path in paths:
        typer.echo(f"- {_display_ref(path)}")
    typer.echo("Provider calls: not started")


def memory_advantage_demo_015_i2v_runtime_command(
    run_dir: Path = typer.Option(
        DEMO_015_RUN_ROOT,
        "--run-dir",
        help="Ignored DEMO-015 run root for Kling I2V outputs and review.",
    ),
    source_keyframe: Path = typer.Option(
        ...,
        "--source-keyframe",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Local ignored source keyframe image used for both DEMO-015 lanes.",
    ),
    provider_config_path: Path | None = typer.Option(
        None,
        "--provider-config",
        help=f"Local ignored provider config JSON. Defaults to ${COMPANY_PROVIDER_CONFIG_ENV}.",
    ),
    i2v_service_id: str = typer.Option(
        "kling_i2v",
        "--i2v-service",
        help="Kling I2V service id.",
    ),
    duration: str = typer.Option(
        "15",
        "--duration",
        help="Video duration in seconds.",
    ),
    mode: str = typer.Option(
        "pro",
        "--mode",
        help="Kling video mode.",
    ),
    poll_interval_sec: float = typer.Option(
        5.0,
        "--poll-interval-sec",
        help="Seconds to wait between provider status polls.",
    ),
    max_polls: int = typer.Option(
        120,
        "--max-polls",
        help="Maximum provider status polls before failing.",
    ),
    transport: str = typer.Option(
        "httpx",
        "--transport",
        help="HTTP transport for Kling live calls: httpx or curl.",
    ),
) -> None:
    """Run gated DEMO-015 Kling I2V protocol from one fixed source keyframe."""
    try:
        store = load_company_provider_secrets(provider_config_path)
        summary = run_demo_015_i2v_protocol(
            store,
            run_dir,
            source_keyframe_path=source_keyframe,
            i2v_service_id=i2v_service_id,
            duration=duration,
            mode=mode,
            poll_interval_sec=poll_interval_sec,
            max_polls=max_polls,
            transport=transport,
        )
    except (ModelGatewayError, OSError, KeyError, ValueError) as exc:
        typer.echo(f"AFS-MEMORY-ADVANTAGE-DEMO-015 I2V runtime failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("AFS-MEMORY-ADVANTAGE-DEMO-015 I2V runtime")
    typer.echo(f"Status: {summary['status']}")
    typer.echo(f"Videos: {summary['generated_video_count']}")
    typer.echo(f"Review: {_display_ref(run_dir / summary['review_path'])}")
    typer.echo(f"HTML: {_display_ref(run_dir / summary['html_path'])}")
    typer.echo("Claim boundary: provider runtime is not creative quality validation")


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")
