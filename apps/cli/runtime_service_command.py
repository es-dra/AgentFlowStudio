from __future__ import annotations

from pathlib import Path

import typer


def runtime_service_command(
    host: str = typer.Option("127.0.0.1", "--host", help="Host for the local Runtime Service."),
    port: int = typer.Option(8790, "--port", help="Port for the local Runtime Service."),
    runtime_root: Path = typer.Option(
        Path("data/processed/runs/runtime_service"),
        "--runtime-root",
        help="Ignored local runtime root for jobs and artifact refs.",
        show_default=False,
    ),
) -> None:
    """Run the local AFS Runtime Service API for frontend integration."""
    import uvicorn

    from apps.api.runtime_service import create_runtime_app

    app = create_runtime_app(runtime_root=runtime_root)
    typer.echo(f"AgentFlow Runtime Service listening on http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=False)


__all__ = ("runtime_service_command",)
