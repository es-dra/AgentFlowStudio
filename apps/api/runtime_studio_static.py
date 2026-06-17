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

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon_redirect() -> RedirectResponse:
        return RedirectResponse(url="/studio/favicon.svg")

    app.mount(
        "/studio",
        NoStoreStaticFiles(directory=root, html=True),
        name="afs_studio",
    )


def studio_static_status(studio_root: Path = DEFAULT_STUDIO_ROOT) -> dict[str, bool | str]:
    root = Path(studio_root)
    root_exists = root.exists()
    index_exists = (root / "index.html").is_file()
    entry_js_exists = (root / "src" / "main.js").is_file()
    ready = root_exists and index_exists and entry_js_exists
    status = "ready" if ready else "missing" if not root_exists else "incomplete"
    return {
        "mounted": root_exists,
        "root_exists": root_exists,
        "index_exists": index_exists,
        "entry_js_exists": entry_js_exists,
        "status": status,
    }


__all__ = ("DEFAULT_STUDIO_ROOT", "NoStoreStaticFiles", "configure_studio_static", "studio_static_status")
