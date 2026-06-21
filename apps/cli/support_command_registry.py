from __future__ import annotations

import typer

from apps.cli.kling_video_command import (
    kling_i2v_smoke_command,
    kling_t2v_smoke_command,
    kling_video_resume_command,
)


def register_support_commands(app: typer.Typer) -> None:
    app.command(name="kling-i2v-smoke", hidden=True)(kling_i2v_smoke_command)
    app.command(name="kling-t2v-smoke", hidden=True)(kling_t2v_smoke_command)
    app.command(name="kling-video-resume", hidden=True)(kling_video_resume_command)
