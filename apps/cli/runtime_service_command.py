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


def runtime_service_openapi_export_command(
    output: Path = typer.Option(
        Path("docs/openapi/afs-runtime-service.openapi.json"),
        "--output",
        help="Output path for the Runtime Service OpenAPI schema.",
        show_default=False,
    ),
    runtime_root: Path = typer.Option(
        Path("data/processed/runs/runtime_service_openapi_export"),
        "--runtime-root",
        help="Ignored local runtime root used only while building the schema.",
        show_default=False,
    ),
) -> None:
    """Export Runtime Service OpenAPI JSON for frontend client generation."""
    from apps.api.openapi_export import export_openapi_schema

    path = export_openapi_schema(output, runtime_root=runtime_root)
    typer.echo(f"Runtime Service OpenAPI exported: {path.as_posix()}")


__all__ = ("runtime_service_command", "runtime_service_openapi_export_command")
