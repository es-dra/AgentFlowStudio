from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_operator_start_packet import (
    build_next_operator_start_packet_from_check_path,
    write_next_operator_start_packet_report,
)


def production_memory_loop_next_operator_start_packet_command(
    package_check_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to operator_run_package_check.json.",
    ),
    generated_at: str = typer.Option(
        ...,
        "--generated-at",
        help="ISO-8601 timestamp for the generated start packet.",
    ),
    artifact_root: Path | None = typer.Option(
        None,
        "--artifact-root",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Optional operator loop artifact root. Defaults to the root recorded by the check.",
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Directory for next_operator_start_packet.json and .md.",
    ),
) -> None:
    """Build a checked no-provider start packet for the next operator."""
    try:
        packet = build_next_operator_start_packet_from_check_path(
            package_check_path,
            generated_at=generated_at,
            artifact_root=artifact_root,
        )
        write_next_operator_start_packet_report(packet, output_dir)
    except ValueError as exc:
        typer.echo(f"Next operator start packet failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    action = packet["next_operator_action"]["action"]
    typer.echo(f"Next operator start packet: {packet['start_packet_status']}")
    typer.echo(f"Package check: {packet['package_check_status']}")
    typer.echo(f"Next operator action: {action}")
    typer.echo("Provider calls: not started" if not packet["provider_calls_started"] else "Provider calls: started")
    typer.echo("Writes long-term memory: false" if not packet["writes_long_term_memory"] else "Writes long-term memory: true")
    typer.echo("Writes Company KB: false" if not packet["writes_company_kb"] else "Writes Company KB: true")
    typer.echo(f"Wrote: {str(output_dir / 'next_operator_start_packet.json').replace(chr(92), '/')}")
    typer.echo(f"Wrote: {str(output_dir / 'next_operator_start_packet.md').replace(chr(92), '/')}")


__all__ = ("production_memory_loop_next_operator_start_packet_command",)
