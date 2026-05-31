from __future__ import annotations

from pathlib import Path

import typer

from narratocut.model_gateway.company_secrets import (
    COMPANY_PROVIDER_CONFIG_ENV,
    load_company_provider_secrets,
)
from narratocut.model_gateway.errors import ModelGatewayError
from narratocut.model_gateway.kling_video_smoke import (
    resume_kling_video_task,
    run_kling_i2v_smoke,
    run_kling_t2v_smoke,
)

from apps.cli.kling_common import display_ref


def kling_i2v_smoke_command(
    prompt: str = typer.Option(
        ...,
        "--prompt",
        help="Prompt to submit to Kling I2V.",
    ),
    image_path: Path = typer.Option(
        ...,
        "--image",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Local source image for the I2V task.",
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Ignored run directory for the downloaded video and safe manifest.",
    ),
    provider_config_path: Path | None = typer.Option(
        None,
        "--provider-config",
        help=f"Local ignored provider config JSON. Defaults to ${COMPANY_PROVIDER_CONFIG_ENV}.",
    ),
    service_id: str = typer.Option(
        "kling_i2v",
        "--service",
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
    """Run a gated Kling I2V smoke and write only safe local artifacts."""
    try:
        store = load_company_provider_secrets(provider_config_path)
        manifest = run_kling_i2v_smoke(
            store,
            service_id=service_id,
            prompt=prompt,
            image_path=image_path,
            output_dir=output_dir,
            duration=duration,
            mode=mode,
            poll_interval_sec=poll_interval_sec,
            max_polls=max_polls,
            transport=transport,
        )
    except ModelGatewayError as exc:
        typer.echo(f"Kling I2V smoke failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Kling I2V smoke: {manifest['status']}")
    typer.echo(f"Manifest: {display_ref(output_dir / 'kling_i2v_smoke_manifest.json')}")
    typer.echo(f"Video: {manifest['outputs'][0]['video_path']}")
    typer.echo(f"Claim boundary: {manifest['claim_boundary']}")


def kling_video_resume_command(
    task_state_path: Path = typer.Option(
        ...,
        "--task-state",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Safe Kling video task state JSON written by a prior smoke run.",
    ),
    provider_config_path: Path | None = typer.Option(
        None,
        "--provider-config",
        help=f"Local ignored provider config JSON. Defaults to ${COMPANY_PROVIDER_CONFIG_ENV}.",
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
    """Resume a gated Kling video task from a safe local task-state file."""
    try:
        store = load_company_provider_secrets(provider_config_path)
        manifest = resume_kling_video_task(
            store,
            task_state_path=task_state_path,
            poll_interval_sec=poll_interval_sec,
            max_polls=max_polls,
            transport=transport,
        )
    except ModelGatewayError as exc:
        typer.echo(f"Kling video resume failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    api_family = str(manifest["api_family"])
    typer.echo(f"Kling video resume: {manifest['status']}")
    typer.echo(f"Manifest: {display_ref(task_state_path.parent / f'kling_{api_family}_smoke_manifest.json')}")
    typer.echo(f"Video: {manifest['outputs'][0]['video_path']}")
    typer.echo(f"Claim boundary: {manifest['claim_boundary']}")


def kling_t2v_smoke_command(
    prompt: str = typer.Option(
        ...,
        "--prompt",
        help="Prompt to submit to Kling T2V.",
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Ignored run directory for the downloaded video and safe manifest.",
    ),
    provider_config_path: Path | None = typer.Option(
        None,
        "--provider-config",
        help=f"Local ignored provider config JSON. Defaults to ${COMPANY_PROVIDER_CONFIG_ENV}.",
    ),
    service_id: str = typer.Option(
        "kling_t2v",
        "--service",
        help="Kling T2V service id.",
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
    aspect_ratio: str = typer.Option(
        "9:16",
        "--aspect-ratio",
        help="Output aspect ratio.",
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
    """Run a gated Kling T2V smoke and write only safe local artifacts."""
    try:
        store = load_company_provider_secrets(provider_config_path)
        manifest = run_kling_t2v_smoke(
            store,
            service_id=service_id,
            prompt=prompt,
            output_dir=output_dir,
            duration=duration,
            mode=mode,
            aspect_ratio=aspect_ratio,
            poll_interval_sec=poll_interval_sec,
            max_polls=max_polls,
            transport=transport,
        )
    except ModelGatewayError as exc:
        typer.echo(f"Kling T2V smoke failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Kling T2V smoke: {manifest['status']}")
    typer.echo(f"Manifest: {display_ref(output_dir / 'kling_t2v_smoke_manifest.json')}")
    typer.echo(f"Video: {manifest['outputs'][0]['video_path']}")
    typer.echo(f"Claim boundary: {manifest['claim_boundary']}")
