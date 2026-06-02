from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.production_operator_handoff import (
    build_operator_handoff_packet,
    write_operator_handoff_packet,
)


def production_memory_loop_operator_handoff_packet_command(
    manifest_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to production_memory_operator_loop_run.json.",
    ),
    manifest_check_path: Path | None = typer.Option(
        None,
        "--manifest-check",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Optional path to operator_manifest_check.json. Required for ready handoff status.",
    ),
    generated_at: str = typer.Option(..., "--generated-at", help="ISO timestamp for the handoff packet."),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/production_memory_loop/operator_handoff"),
        "--output",
        "-o",
        help="Directory for operator handoff packet artifacts.",
    ),
) -> None:
    """Write a no-provider handoff packet from an operator manifest and check report."""
    try:
        manifest = _load_json_object(manifest_path, "operator manifest")
        manifest_check = _load_json_object(manifest_check_path, "operator manifest check") if manifest_check_path else None
        packet = build_operator_handoff_packet(
            manifest,
            manifest_check=manifest_check,
            generated_at=generated_at,
        )
        written_paths = write_operator_handoff_packet(packet, output_dir)
    except ValueError as exc:
        typer.echo(f"Production memory operator handoff failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Production memory operator handoff: {packet['handoff_status']}")
    typer.echo(f"Manifest check: {packet['manifest_check_status']}")
    typer.echo(f"Next operator action: {packet['next_operator_action']['action']}")
    typer.echo(f"Provider calls: {_bool_label(packet['provider_calls_started'])}")
    typer.echo(f"Writes long-term memory: {_bool_label(packet['writes_long_term_memory'])}")
    typer.echo(f"Writes Company KB: {_bool_label(packet['writes_company_kb'])}")
    for path in written_paths:
        typer.echo(f"Wrote: {_display_ref(path)}")

    if packet["handoff_status"] != "ready":
        raise typer.Exit(code=1)


def _load_json_object(path: Path, label: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object")
    return payload


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


def _bool_label(value: bool) -> str:
    return str(value).lower()


__all__ = ("production_memory_loop_operator_handoff_packet_command",)
