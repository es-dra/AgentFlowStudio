from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles


DEFAULT_WORKBENCH_ROOT = Path(__file__).resolve().parents[1] / "workbench"


class NoStoreStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store"
        return response


def configure_workbench_static(app: FastAPI, workbench_root: Path = DEFAULT_WORKBENCH_ROOT) -> None:
    root = Path(workbench_root)
    if not root.exists():
        return

    @app.get("/workbench", include_in_schema=False)
    def workbench_redirect() -> RedirectResponse:
        return RedirectResponse(url="/workbench/")

    app.mount(
        "/workbench",
        NoStoreStaticFiles(directory=root, html=True),
        name="afs_workbench",
    )


__all__ = ("DEFAULT_WORKBENCH_ROOT", "NoStoreStaticFiles", "configure_workbench_static")
