from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from pydantic import ValidationError

from narratocut import __version__
from narratocut.roi_sop import analyze_hooks_from_text, generate_scripts_from_hooks
from narratocut.schemas import Hook
from narratocut.utils import write_json


app = typer.Typer(
    help="NarratoCut command line interface.",
    no_args_is_help=True,
)


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        help="Show the NarratoCut version and exit.",
        is_eager=True,
    ),
) -> None:
    if version:
        typer.echo(__version__)
        raise typer.Exit()


@app.command(name="version")
def version_command() -> None:
    """Print the NarratoCut version."""
    typer.echo(__version__)


@app.command(name="analyze-hooks")
def analyze_hooks_command(
    input_path: Path = typer.Option(
        ...,
        "--input",
        "-i",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="UTF-8 text file to analyze.",
    ),
    output_path: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Path to write hooks JSON.",
    ),
) -> None:
    """Analyze text with the local mock ROI pipeline and write hooks JSON."""
    input_text = input_path.read_text(encoding="utf-8")
    hooks = analyze_hooks_from_text(input_text)
    write_json(output_path, hooks)
    typer.echo(f"Wrote {len(hooks)} hooks to {output_path}")


@app.command(name="generate-scripts")
def generate_scripts_command(
    hooks_path: Path = typer.Option(
        ...,
        "--hooks",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to hooks JSON.",
    ),
    output_path: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Path to write scripts JSON.",
    ),
) -> None:
    """Generate mock short-video scripts from hooks JSON."""
    hooks = _load_hooks(hooks_path)
    scripts = generate_scripts_from_hooks(hooks)
    write_json(output_path, scripts)
    typer.echo(f"Wrote {len(scripts)} scripts to {output_path}")


def _load_hooks(hooks_path: Path) -> list[Hook]:
    try:
        payload = json.loads(hooks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Hooks file is not valid JSON: {exc.msg}") from exc
    if not isinstance(payload, list):
        raise typer.BadParameter("Hooks file must contain a JSON array.")
    try:
        return [Hook.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise typer.BadParameter(f"Hooks file failed Hook schema validation: {exc}") from exc


if __name__ == "__main__":
    app()
