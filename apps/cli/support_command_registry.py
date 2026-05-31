from __future__ import annotations

import typer

from apps.cli.kling_video_command import (
    kling_i2v_smoke_command,
    kling_t2v_smoke_command,
    kling_video_resume_command,
)
from apps.cli.memory_demo_commands import (
    memory_advantage_demo_012_i2i_runtime_command,
    memory_advantage_demo_012_i2v_runtime_command,
    memory_advantage_demo_012_plan_command,
    memory_advantage_demo_015_i2v_runtime_command,
    memory_advantage_demo_015_plan_command,
)
from apps.cli.minimax_image_command import minimax_i2i_smoke_command, minimax_image_smoke_command


def register_support_commands(app: typer.Typer) -> None:
    app.command(name="kling-i2v-smoke", hidden=True)(kling_i2v_smoke_command)
    app.command(name="kling-t2v-smoke", hidden=True)(kling_t2v_smoke_command)
    app.command(name="kling-video-resume", hidden=True)(kling_video_resume_command)
    app.command(name="minimax-image-smoke", hidden=True)(minimax_image_smoke_command)
    app.command(name="minimax-i2i-smoke", hidden=True)(minimax_i2i_smoke_command)
    app.command(name="memory-advantage-demo-012-plan", hidden=True)(memory_advantage_demo_012_plan_command)
    app.command(name="memory-advantage-demo-012-i2i-runtime", hidden=True)(
        memory_advantage_demo_012_i2i_runtime_command
    )
    app.command(name="memory-advantage-demo-012-i2v-runtime", hidden=True)(
        memory_advantage_demo_012_i2v_runtime_command
    )
    app.command(name="memory-advantage-demo-015-plan", hidden=True)(memory_advantage_demo_015_plan_command)
    app.command(name="memory-advantage-demo-015-i2v-runtime", hidden=True)(
        memory_advantage_demo_015_i2v_runtime_command
    )
