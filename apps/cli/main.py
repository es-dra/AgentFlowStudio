from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from apps.cli.artifact_loaders import load_clip_plans, load_hooks, load_scripts
from apps.cli.media_commands import ffmpeg_check_command
from apps.cli.plan_commands import write_draft_plan_from_cli
from apps.cli.report_commands import inspect_run_output, package_report_command, review_run_output
from apps.cli.real_slicing_commands import slice_real_command
from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut import __version__
from narratocut.roi_sop import analyze_hooks_from_text, generate_scripts_from_hooks
from narratocut.slicing_sop import generate_clip_plans_from_scripts, mock_slice_clip_plans
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
    hooks = load_hooks(hooks_path)
    scripts = generate_scripts_from_hooks(hooks)
    write_json(output_path, scripts)
    typer.echo(f"Wrote {len(scripts)} scripts to {output_path}")


@app.command(name="run-workflow")
def run_workflow_command(
    workflow_path: Path = typer.Option(
        ...,
        "--workflow",
        "-w",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to workflow YAML.",
    ),
    input_path: Path = typer.Option(
        ...,
        "--input",
        "-i",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="UTF-8 text file or structured workflow input JSON.",
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Directory for workflow artifacts.",
    ),
) -> None:
    """Run a minimal sequential workflow with local mock nodes."""
    status, manifest_path = run_workflow_from_cli(workflow_path, input_path, output_dir)
    typer.echo(f"Workflow {status}: {manifest_path}")
    if status == "failed":
        raise typer.Exit(code=1)


@app.command(name="draft-plan")
def draft_plan_command(
    workflow_path: Path = typer.Option(
        ...,
        "--workflow",
        "-w",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to workflow YAML.",
    ),
    input_path: Path = typer.Option(
        ...,
        "--input",
        "-i",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="UTF-8 text file used as planned input.",
    ),
    output_path: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Path to write workflow_plan.json.",
    ),
    tool_catalog_path: Path = typer.Option(
        Path("configs/tool_catalog.yaml"),
        "--tool-catalog",
        help="Optional static tool catalog YAML.",
    ),
) -> None:
    """Write a static workflow_plan.json draft without executing the workflow."""
    plan, plan_path = write_draft_plan_from_cli(
        workflow_path,
        input_path,
        output_path,
        tool_catalog_path,
    )
    typer.echo(f"Workflow plan: {_display_ref(plan_path)}")
    typer.echo(f"Status: {plan['status']}")
    typer.echo(f"Steps: {len(plan['steps'])}")
    typer.echo("Execution: not started")
    if plan["status"] == "invalid":
        raise typer.Exit(code=1)


@app.command(name="generate-clip-plans")
def generate_clip_plans_command(
    scripts_path: Path = typer.Option(
        ...,
        "--scripts",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to scripts JSON.",
    ),
    output_path: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Path to write clip plans JSON.",
    ),
) -> None:
    """Generate deterministic mock clip plans from scripts JSON."""
    scripts = load_scripts(scripts_path)
    clip_plans = generate_clip_plans_from_scripts(scripts)
    write_json(output_path, clip_plans)
    typer.echo(f"Wrote {len(clip_plans)} clip plans to {output_path}")


@app.command(name="mock-slice")
def mock_slice_command(
    clip_plans_path: Path = typer.Option(
        ...,
        "--clip-plans",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to clip plans JSON.",
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Directory for mock slice outputs.",
    ),
) -> None:
    """Write mock slice outputs from clip plans JSON."""
    clip_plans = load_clip_plans(clip_plans_path)
    manifest = mock_slice_clip_plans(clip_plans, output_dir)
    typer.echo(f"Wrote {manifest['clip_count']} mock clips to {output_dir}")


app.command(name="slice-real")(slice_real_command)
app.command(name="ffmpeg-check")(ffmpeg_check_command)


@app.command(name="inspect-run")
def inspect_run_command(
    run_dir: Path = typer.Option(
        ...,
        "--run-dir",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Workflow run directory to inspect.",
    ),
) -> None:
    """Inspect a workflow run directory and write quality_report.json."""
    inspection, lines = inspect_run_output(run_dir)
    for line in lines:
        typer.echo(line)
    if inspection["status"] != "pass":
        raise typer.Exit(code=1)


@app.command(name="review-run")
def review_run_command(
    run_dir: Path = typer.Option(
        ...,
        "--run-dir",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Workflow run directory to review.",
    ),
) -> None:
    """Write an agent-readable review_report.json for a workflow run."""
    report, lines = review_run_output(run_dir)
    for line in lines:
        typer.echo(line)
    if report["status"] == "failed":
        raise typer.Exit(code=1)


app.command(name="package-report")(package_report_command)


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


if __name__ == "__main__":
    app()
