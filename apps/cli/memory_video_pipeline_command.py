from __future__ import annotations

import json
from pathlib import Path

import typer

from agentflow.memory.video_pipeline import build_memory_video_pipeline_plan, write_memory_video_pipeline_plan
from agentflow.memory.video_pipeline_observation import (
    build_memory_video_pipeline_observation,
    write_memory_video_pipeline_observation,
)
from agentflow.memory.video_pipeline_presentation import (
    build_memory_video_pipeline_presentation,
    write_memory_video_pipeline_presentation,
)
from agentflow.memory.video_pipeline_review import (
    build_memory_video_pipeline_review,
    write_memory_video_pipeline_review,
)
from agentflow.memory.video_pipeline_workflow import (
    build_memory_video_pipeline_package,
    write_memory_video_pipeline_package,
)


def memory_video_pipeline_plan_command(
    protocol_path: Path = typer.Option(
        ...,
        "--protocol",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Sanitized memory video pipeline protocol JSON.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/memory_video_pipeline/plan"),
        "--output",
        "-o",
        help="Ignored output directory for no-call plan artifacts.",
    ),
) -> None:
    """Write a no-call memory video pipeline plan from one protocol file."""
    try:
        protocol = _read_json(protocol_path)
        plan = build_memory_video_pipeline_plan(protocol)
        paths = write_memory_video_pipeline_plan(plan, output_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"Memory video pipeline plan failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Memory video pipeline plan")
    typer.echo(f"Protocol: {plan['protocol_id']}")
    typer.echo(f"Lanes planned: {len(plan['lane_plans'])}")
    typer.echo("Provider calls: not started")
    for path in paths:
        typer.echo(f"- {_display_ref(path)}")


def memory_video_pipeline_review_command(
    protocol_path: Path = typer.Option(
        ...,
        "--protocol",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Sanitized memory video pipeline protocol JSON.",
    ),
    artifacts_path: Path = typer.Option(
        ...,
        "--artifacts",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Explicit artifact manifest listing I2V manifest files to review.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/memory_video_pipeline/review"),
        "--output",
        "-o",
        help="Ignored output directory for no-call review artifacts.",
    ),
) -> None:
    """Write a no-call memory video pipeline review from explicit artifacts."""
    try:
        protocol = _read_json(protocol_path)
        artifacts = _read_json(artifacts_path)
        review = build_memory_video_pipeline_review(protocol, artifacts)
        paths = write_memory_video_pipeline_review(review, output_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"Memory video pipeline review failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Memory video pipeline review")
    typer.echo(f"Protocol: {review['protocol_id']}")
    typer.echo(f"Runs reviewed: {review['cross_run_stability']['run_count']}")
    typer.echo("Provider calls: not started")
    for path in paths:
        typer.echo(f"- {_display_ref(path)}")


def memory_video_pipeline_observe_command(
    review_path: Path = typer.Option(
        ...,
        "--review",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Memory video pipeline review JSON.",
    ),
    notes_path: Path = typer.Option(
        ...,
        "--notes",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Human visual observation notes JSON.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/memory_video_pipeline/observation"),
        "--output",
        "-o",
        help="Ignored output directory for bounded human-observation artifacts.",
    ),
) -> None:
    """Write a bounded human visual observation from a review artifact."""
    try:
        review = _read_json(review_path)
        notes = _read_json(notes_path)
        observation = build_memory_video_pipeline_observation(review, notes)
        paths = write_memory_video_pipeline_observation(observation, output_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"Memory video pipeline observation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Memory video pipeline human observation")
    typer.echo(f"Protocol: {observation['protocol_id']}")
    typer.echo(f"Observation status: {observation['observation_status']}")
    typer.echo("Provider calls: not started")
    for path in paths:
        typer.echo(f"- {_display_ref(path)}")


def memory_video_pipeline_present_command(
    protocol_path: Path = typer.Option(
        ...,
        "--protocol",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Sanitized memory video pipeline protocol JSON.",
    ),
    review_path: Path = typer.Option(
        ...,
        "--review",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Memory video pipeline review JSON.",
    ),
    observation_path: Path = typer.Option(
        ...,
        "--observation",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Memory video pipeline human observation JSON.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/memory_video_pipeline/presentation"),
        "--output",
        "-o",
        help="Ignored output directory for presentation-facing material.",
    ),
) -> None:
    """Write a presentation-facing package from protocol, review, and observation."""
    try:
        protocol = _read_json(protocol_path)
        review = _read_json(review_path)
        observation = _read_json(observation_path)
        package = build_memory_video_pipeline_presentation(protocol, review, observation)
        paths = write_memory_video_pipeline_presentation(package, output_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"Memory video pipeline presentation failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Memory video pipeline presentation package")
    typer.echo(f"Protocol: {package['protocol_id']}")
    typer.echo("Provider calls: not started")
    for path in paths:
        typer.echo(f"- {_display_ref(path)}")


def memory_video_pipeline_package_command(
    protocol_path: Path = typer.Option(
        ...,
        "--protocol",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Sanitized memory video pipeline protocol JSON.",
    ),
    artifacts_path: Path = typer.Option(
        ...,
        "--artifacts",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Explicit artifact manifest listing I2V manifest files to review.",
    ),
    notes_path: Path = typer.Option(
        ...,
        "--notes",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Human visual observation notes JSON.",
    ),
    created_at: str = typer.Option(
        ...,
        "--created-at",
        help="ISO timestamp for the feedback event draft.",
    ),
    output_dir: Path = typer.Option(
        Path("data/processed/runs/memory_video_pipeline/package"),
        "--output",
        "-o",
        help="Ignored output directory for the no-call package.",
    ),
) -> None:
    """Write the no-call product package for one memory video pipeline run."""
    try:
        protocol = _read_json(protocol_path)
        artifacts = _read_json(artifacts_path)
        notes = _read_json(notes_path)
        package = build_memory_video_pipeline_package(
            protocol,
            artifacts,
            notes,
            created_at=created_at,
        )
        paths = write_memory_video_pipeline_package(package, output_dir)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        typer.echo(f"Memory video pipeline package failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc
    typer.echo("Memory video pipeline package")
    typer.echo(f"Protocol: {package['protocol_id']}")
    typer.echo("Provider calls: not started")
    typer.echo("Feedback event draft: written")
    for path in paths:
        typer.echo(f"- {_display_ref(path)}")


def _display_ref(path: Path) -> str:
    return str(path).replace("\\", "/")


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))
