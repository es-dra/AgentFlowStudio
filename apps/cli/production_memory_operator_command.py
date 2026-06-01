from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)


def production_memory_loop_run_operator_no_provider_command(
    loop_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to agentflow_production_memory_loop JSON.",
    ),
    generated_at: str = typer.Option(..., "--generated-at", help="ISO timestamp for generated loop artifacts."),
    source_kb_status: str = typer.Option(
        "restructuring_or_unknown",
        "--source-kb-status",
        help="Current source Company KB state label; metadata only.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/operator_loop"),
        "--output",
        "-o",
        help="Directory for the full no-provider operator loop artifact chain.",
    ),
) -> None:
    """Run the generic production-memory operator loop without provider access."""
    try:
        loop = load_production_memory_loop(loop_path)
        result = build_production_memory_operator_loop_run(
            loop,
            generated_at=generated_at,
            source_kb_status=source_kb_status,
        )
        written_paths = write_production_memory_operator_loop_run(result, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory operator loop failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    manifest = result["manifest"]
    typer.echo(f"Production memory operator loop: {manifest['chain_status']}")
    typer.echo("Provider calls: not started")
    typer.echo("Writes long-term memory: false")
    typer.echo("Writes Company KB: false")
    typer.echo(f"Included refs: {manifest['context_summary']['included_ref_count']}")
    typer.echo(f"Blocked refs: {manifest['context_summary']['blocked_ref_count']}")
    typer.echo(f"Company KB candidates: {manifest['company_kb_feedback']['promotion_status']}")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")

    if manifest["chain_status"] != "ready":
        raise typer.Exit(code=1)


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


__all__ = ("production_memory_loop_run_operator_no_provider_command",)
