from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles


DEFAULT_WORKBENCH_ROOT = Path(__file__).resolve().parents[1] / "workbench"


def configure_workbench_static(app: FastAPI, workbench_root: Path = DEFAULT_WORKBENCH_ROOT) -> None:
    root = Path(workbench_root)
    if not root.exists():
        return

    @app.get("/workbench", include_in_schema=False)
    def workbench_redirect() -> RedirectResponse:
        return RedirectResponse(url="/workbench/")

    app.mount(
        "/workbench",
        StaticFiles(directory=root, html=True),
        name="afs_workbench",
    )


__all__ = ("DEFAULT_WORKBENCH_ROOT", "configure_workbench_static")
