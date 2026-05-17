from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from pydantic import ValidationError

from narratocut import __version__
from narratocut.harness import inspect_run, review_run, write_review_report
from narratocut.roi_sop import analyze_hooks_from_text, generate_scripts_from_hooks
from narratocut.schemas import ClipPlan, Hook, ShortVideoScript
from narratocut.slicing_sop import (
    check_ffmpeg_available,
    generate_clip_plans_from_scripts,
    mock_slice_clip_plans,
)
from narratocut.utils import write_json
from narratocut.workflow_engine import (
    WorkflowContext,
    WorkflowRunner,
    default_node_registry,
    load_workflow,
)


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
        help="UTF-8 text file used as input_text_file.",
    ),
    output_dir: Path = typer.Option(
        ...,
        "--output",
        "-o",
        help="Directory for workflow artifacts.",
    ),
) -> None:
    """Run a minimal sequential workflow with local mock nodes."""
    workflow = load_workflow(workflow_path)
    context = WorkflowContext(
        run_id=output_dir.name,
        workflow_name=workflow.name,
        workflow_path=str(workflow_path),
        output_dir=output_dir,
        inputs={"input_text_file": str(input_path)},
    )
    run = WorkflowRunner(default_node_registry()).run(workflow, context)
    inspect_run(output_dir)
    manifest_path = context.output_path("manifest.json")
    typer.echo(f"Workflow {run.status}: {manifest_path}")
    if run.status == "failed":
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
    scripts = _load_scripts(scripts_path)
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
    clip_plans = _load_clip_plans(clip_plans_path)
    manifest = mock_slice_clip_plans(clip_plans, output_dir)
    typer.echo(f"Wrote {manifest['clip_count']} mock clips to {output_dir}")


@app.command(name="ffmpeg-check")
def ffmpeg_check_command(
    executable: str = typer.Option(
        "ffmpeg",
        "--executable",
        "-e",
        help="FFmpeg executable to probe.",
    ),
) -> None:
    """Check whether FFmpeg is callable on this machine."""
    info = check_ffmpeg_available(executable)
    if info.available:
        version = info.version or "unknown version"
        typer.echo(f"FFmpeg available: {info.executable} ({version})")
        return

    typer.echo(f"FFmpeg unavailable: {info.error}")


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
    inspection = inspect_run(run_dir)
    quality = inspection["quality_report"]
    passed = sum(1 for check in quality["checks"] if check["status"] == "pass")
    failed = sum(1 for check in quality["checks"] if check["status"] == "fail")
    warnings = len(quality["warnings"])

    typer.echo(f"Run: {inspection['run_id']}")
    typer.echo(f"Workflow: {inspection['workflow']}")
    typer.echo(f"Status: {inspection['status']}")
    typer.echo("")
    typer.echo("Artifacts:")
    for artifact in inspection["artifacts"]:
        typer.echo(f"  {artifact['path']:<24} {artifact['status']}")
    typer.echo("")
    typer.echo("Quality:")
    typer.echo(f"  {passed} passed")
    typer.echo(f"  {failed} failed")
    typer.echo(f"  {warnings} warnings")
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
    report = review_run(run_dir)
    report_path = write_review_report(run_dir, report)
    summary = report["summary"]

    typer.echo(f"Review report: {_display_ref(report_path)}")
    typer.echo(f"Status: {report['status']}")
    typer.echo(
        "Checks: "
        f"{summary['passed']} passed / "
        f"{summary['failed']} failed / "
        f"{summary['warnings']} warnings"
    )
    if report["status"] == "failed":
        raise typer.Exit(code=1)


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


def _load_scripts(scripts_path: Path) -> list[ShortVideoScript]:
    payload = _load_json_array(scripts_path, "Scripts")
    try:
        return [ShortVideoScript.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise typer.BadParameter(f"Scripts file failed ShortVideoScript schema validation: {exc}") from exc


def _load_clip_plans(clip_plans_path: Path) -> list[ClipPlan]:
    payload = _load_json_array(clip_plans_path, "Clip plans")
    try:
        return [ClipPlan.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise typer.BadParameter(f"Clip plans file failed ClipPlan schema validation: {exc}") from exc


def _load_json_array(path: Path, label: str) -> list[object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"{label} file is not valid JSON: {exc.msg}") from exc
    if not isinstance(payload, list):
        raise typer.BadParameter(f"{label} file must contain a JSON array.")
    return payload


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


if __name__ == "__main__":
    app()
