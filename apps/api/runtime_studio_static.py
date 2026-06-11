from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

DEFAULT_STUDIO_ROOT = Path(__file__).resolve().parents[1] / "studio"


class NoStoreStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store"
        return response


def configure_studio_static(app: FastAPI, studio_root: Path = DEFAULT_STUDIO_ROOT) -> None:
    root = Path(studio_root)
    if not root.exists():
        return

    @app.get("/studio", include_in_schema=False)
    def studio_redirect() -> RedirectResponse:
        return RedirectResponse(url="/studio/")

    app.mount(
        "/studio",
        NoStoreStaticFiles(directory=root, html=True),
        name="afs_studio",
    )


__all__ = ("DEFAULT_STUDIO_ROOT", "NoStoreStaticFiles", "configure_studio_static")
