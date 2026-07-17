from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import typer

from agentflow_studio.production.adaptive_canvas_v2 import AdaptiveRunOptions, run_adaptive_canvas_production
from agentflow_studio.production.real_anime_4shot import real_anime_4shot_paid_profile


DEFAULT_RUNTIME_ROOT = Path(os.environ.get("AFS_RUNTIME_ROOT") or os.environ.get("AFS_RUNTIME_SERVICE_ROOT") or "/var/lib/afs-runtime")


def real_anime_4shot_paid_v1_command(
    runtime_root: Path = typer.Option(DEFAULT_RUNTIME_ROOT, "--runtime-root", help="RuntimeStore root."),
    project_id: str | None = typer.Option(None, "--project-id", help="Project id to create or reuse."),
    run_id: str | None = typer.Option(None, "--run-id", help="Production run id to create or resume."),
    mode: Literal["real", "fake"] = typer.Option("real", "--mode", help="real uses configured providers; fake is zero-cost validation."),
    provider_config: Path | None = typer.Option(None, "--provider-config", exists=True, dir_okay=False, help="Optional provider config path."),
    video_poll_interval_sec: float = typer.Option(15.0, "--video-poll-interval-sec", min=1.0),
    video_poll_timeout_sec: float = typer.Option(5400.0, "--video-poll-timeout-sec", min=60.0),
) -> None:
    """Run the current 4-shot paid anime profile through Adaptive Canvas v2."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ").lower()
    resolved_project_id = project_id or f"real-anime-4shot-paid-v1-{stamp}"
    resolved_run_id = run_id or f"run-{stamp}"
    profile = real_anime_4shot_paid_profile()

    def callback(event: dict[str, object]) -> None:
        stage = str(event.get("stage") or "")
        status = str(event.get("status") or "")
        tail = {key: value for key, value in event.items() if key not in {"stage", "status"}}
        typer.echo(f"{stage} {status} {json.dumps(tail, ensure_ascii=False, sort_keys=True)}")

    result = run_adaptive_canvas_production(
        AdaptiveRunOptions(
            runtime_root=runtime_root,
            project_id=resolved_project_id,
            run_id=resolved_run_id,
            profile=profile,
            mode=mode,
            provider_config_path=provider_config,
            video_poll_interval_sec=video_poll_interval_sec,
            video_poll_timeout_sec=video_poll_timeout_sec,
        ),
        callback=callback,
    )
    typer.echo(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
