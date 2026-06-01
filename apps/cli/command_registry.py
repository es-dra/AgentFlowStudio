from __future__ import annotations

from pathlib import Path

import typer

from apps.cli.alpha_commands import alpha_smoke_command
from apps.cli.media_commands import ffmpeg_check_command
from apps.cli.memory_review_command import memory_evidence_reuse_review_command
from apps.cli.memory_video_pipeline_command import (
    memory_video_pipeline_observe_command,
    memory_video_pipeline_package_command,
    memory_video_pipeline_plan_command,
    memory_video_pipeline_present_command,
    memory_video_pipeline_review_command,
)
from apps.cli.production_memory_loop_command import (
    production_memory_loop_draft_feedback_command,
    production_memory_loop_review_promotion_command,
    production_memory_loop_run_no_provider_command,
    production_memory_loop_run_reviewed_feedback_no_provider_command,
    production_memory_loop_validate_command,
)
from apps.cli.production_memory_next_context_command import production_memory_loop_next_context_handoff_command
from apps.cli.production_memory_next_pass_review_command import production_memory_loop_review_next_pass_command
from apps.cli.production_memory_next_task_command import production_memory_loop_next_task_packet_command
from apps.cli.production_memory_operator_command import production_memory_loop_run_operator_no_provider_command
from apps.cli.production_memory_session_command import (
    production_memory_loop_company_kb_candidates_command,
    production_memory_loop_session_report_command,
)
from apps.cli.real_slicing_commands import slice_real_command
from apps.cli.report_commands import (
    delivery_readiness_command,
    inspect_run_output,
    package_report_command,
    review_run_output,
)
from apps.web_bridge.server import serve as serve_web_bridge


def register_commands(app: typer.Typer) -> None:
    register_product_commands(app)

    from apps.cli.support_command_registry import register_support_commands

    register_support_commands(app)


def register_product_commands(app: typer.Typer) -> None:
    app.command(name="slice-real")(slice_real_command)
    app.command(name="ffmpeg-check")(ffmpeg_check_command)
    app.command(name="inspect-run")(inspect_run_command)
    app.command(name="review-run")(review_run_command)
    app.command(name="package-report")(package_report_command)
    app.command(name="delivery-readiness")(delivery_readiness_command)
    app.command(name="alpha-smoke")(alpha_smoke_command)
    app.command(name="memory-video-pipeline-plan")(memory_video_pipeline_plan_command)
    app.command(name="memory-video-pipeline-review")(memory_video_pipeline_review_command)
    app.command(name="memory-video-pipeline-observe")(memory_video_pipeline_observe_command)
    app.command(name="memory-video-pipeline-present")(memory_video_pipeline_present_command)
    app.command(name="memory-video-pipeline-package")(memory_video_pipeline_package_command)
    app.command(name="memory-evidence-reuse-review")(memory_evidence_reuse_review_command)
    app.command(name="production-memory-loop-validate")(production_memory_loop_validate_command)
    app.command(name="production-memory-loop-run-no-provider")(production_memory_loop_run_no_provider_command)
    app.command(name="production-memory-loop-draft-feedback")(production_memory_loop_draft_feedback_command)
    app.command(name="production-memory-loop-review-promotion")(production_memory_loop_review_promotion_command)
    app.command(name="production-memory-loop-run-reviewed-feedback-no-provider")(
        production_memory_loop_run_reviewed_feedback_no_provider_command
    )
    app.command(name="production-memory-loop-run-operator-no-provider")(
        production_memory_loop_run_operator_no_provider_command
    )
    app.command(name="production-memory-loop-next-context-handoff")(
        production_memory_loop_next_context_handoff_command
    )
    app.command(name="production-memory-loop-next-task-packet")(production_memory_loop_next_task_packet_command)
    app.command(name="production-memory-loop-review-next-pass")(production_memory_loop_review_next_pass_command)
    app.command(name="production-memory-loop-session-report")(production_memory_loop_session_report_command)
    app.command(name="production-memory-loop-company-kb-candidates")(production_memory_loop_company_kb_candidates_command)
    app.command(name="web-bridge")(web_bridge_command)


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


def web_bridge_command(
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="Host for the local Web UI bridge.",
    ),
    port: int = typer.Option(
        8787,
        "--port",
        help="Port for the local Web UI bridge.",
    ),
) -> None:
    """Run the local Web UI bridge for supervised Production Mode."""
    serve_web_bridge(host=host, port=port)
