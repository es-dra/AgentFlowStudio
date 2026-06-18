from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

DEFAULT_SITE_ROOT = Path(__file__).resolve().parents[1] / "site"
DEFAULT_STUDIO_ROOT = Path(__file__).resolve().parents[1] / "studio"


class NoStoreStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope: dict) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-store"
        return response


def configure_site_static(app: FastAPI, site_root: Path = DEFAULT_SITE_ROOT) -> None:
    root = Path(site_root)
    index = root / "index.html"
    if not index.is_file():
        return

    @app.get("/", include_in_schema=False)
    def site_index() -> FileResponse:
        return FileResponse(index, headers={"Cache-Control": "no-store"})

    app.mount(
        "/site",
        NoStoreStaticFiles(directory=root, html=True),
        name="afs_site",
    )


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


__all__ = (
    "DEFAULT_SITE_ROOT",
    "DEFAULT_STUDIO_ROOT",
    "NoStoreStaticFiles",
    "configure_site_static",
    "configure_studio_static",
    "studio_static_status",
)
