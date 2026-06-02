from __future__ import annotations

from pathlib import Path

import typer

from apps.cli.kling_common import display_ref
from agentflow_studio.model_gateway.company_secrets import (
    COMPANY_PROVIDER_CONFIG_ENV,
    load_company_provider_secrets,
)
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.minimax_image_smoke import run_minimax_image_smoke


def minimax_image_smoke_command(
    prompt: str = typer.Option(
        ...,
        "--prompt",
        help="Prompt to submit to MiniMax T2I.",
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Ignored run directory for generated images and safe manifest.",
    ),
    provider_config_path: Path | None = typer.Option(
        None,
        "--provider-config",
        help=f"Local ignored provider config JSON. Defaults to ${COMPANY_PROVIDER_CONFIG_ENV}.",
    ),
    service_id: str = typer.Option(
        "minimax_image",
        "--service",
        help="MiniMax image service id.",
    ),
    aspect_ratio: str = typer.Option(
        "9:16",
        "--aspect-ratio",
        help="Output aspect ratio.",
    ),
    model_name: str | None = typer.Option(
        None,
        "--model-name",
        help="Optional MiniMax model override.",
    ),
    candidate_count: int = typer.Option(
        1,
        "--candidate-count",
        help="Number of image candidates to request.",
    ),
) -> None:
    """Run a gated MiniMax image smoke and write only safe local artifacts."""
    try:
        store = load_company_provider_secrets(provider_config_path)
        manifest = run_minimax_image_smoke(
            store,
            service_id=service_id,
            prompt=prompt,
            output_dir=output_dir,
            aspect_ratio=aspect_ratio,
            model_name_override=model_name,
            candidate_count=candidate_count,
        )
    except ModelGatewayError as exc:
        typer.echo(f"MiniMax image smoke failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"MiniMax image smoke: {manifest['status']}")
    typer.echo(f"Manifest: {display_ref(output_dir / 'minimax_image_smoke_manifest.json')}")
    for output in manifest["outputs"]:
        typer.echo(f"Image: {output['image_path']}")
    typer.echo(f"Claim boundary: {manifest['claim_boundary']}")


def minimax_i2i_smoke_command(
    prompt: str = typer.Option(
        ...,
        "--prompt",
        help="Prompt to submit to MiniMax I2I.",
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
    output_dir: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Ignored run directory for generated images and safe manifest.",
    ),
    provider_config_path: Path | None = typer.Option(
        None,
        "--provider-config",
        help=f"Local ignored provider config JSON. Defaults to ${COMPANY_PROVIDER_CONFIG_ENV}.",
    ),
    service_id: str = typer.Option(
        "minimax_image",
        "--service",
        help="MiniMax image service id.",
    ),
    aspect_ratio: str = typer.Option(
        "9:16",
        "--aspect-ratio",
        help="Output aspect ratio.",
    ),
    model_name: str | None = typer.Option(
        None,
        "--model-name",
        help="Optional MiniMax model override.",
    ),
    candidate_count: int = typer.Option(
        1,
        "--candidate-count",
        help="Number of image candidates to request.",
    ),
) -> None:
    """Run a gated MiniMax image-to-image smoke and write only safe local artifacts."""
    try:
        store = load_company_provider_secrets(provider_config_path)
        manifest = run_minimax_image_smoke(
            store,
            service_id=service_id,
            prompt=prompt,
            output_dir=output_dir,
            aspect_ratio=aspect_ratio,
            model_name_override=model_name,
            candidate_count=candidate_count,
            subject_reference_image_path=subject_reference_image,
        )
    except ModelGatewayError as exc:
        typer.echo(f"MiniMax I2I smoke failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"MiniMax I2I smoke: {manifest['status']}")
    typer.echo(f"Manifest: {display_ref(output_dir / 'minimax_image_smoke_manifest.json')}")
    for output in manifest["outputs"]:
        typer.echo(f"Image: {output['image_path']}")
    typer.echo(f"Claim boundary: {manifest['claim_boundary']}")
