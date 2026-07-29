from __future__ import annotations

from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

DEFAULT_SITE_ROOT = Path(__file__).resolve().parents[1] / "site"
DEFAULT_STUDIO_ROOT = Path(__file__).resolve().parents[1] / "studio"
DEFAULT_STUDIO_WEB_ROOT = Path(__file__).resolve().parents[1] / "studio-web" / "dist"


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


def configure_studio_static(app: FastAPI, studio_web_root: Path = DEFAULT_STUDIO_WEB_ROOT) -> None:
    root = Path(studio_web_root)
    index = root / "index.html"

    @app.get("/studio/episode-workspace", include_in_schema=False)
    @app.get("/studio/episode-workspace/", include_in_schema=False)
    def studio_episode_workspace_redirect(request: Request) -> RedirectResponse:
        return RedirectResponse(url=_episode_workspace_redirect_url(request))

    if not index.is_file():
        return

    @app.get("/studio", include_in_schema=False)
    def studio_redirect() -> RedirectResponse:
        return RedirectResponse(url="/studio/")

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon_redirect() -> RedirectResponse:
        return RedirectResponse(url="/studio-legacy/favicon.svg")

    app.mount(
        "/studio",
        NoStoreStaticFiles(directory=root, html=True),
        name="afs_studio",
    )


def _episode_workspace_redirect_url(request: Request) -> str:
    params: dict[str, str] = {}
    project_id = (
        request.query_params.get("project_id")
        or request.query_params.get("project")
        or ""
    ).strip()
    if project_id:
        params["project_id"] = project_id
    params["surface"] = "storyboard"
    return f"/studio/?{urlencode(params)}"


def configure_studio_next_static(app: FastAPI, studio_web_root: Path = DEFAULT_STUDIO_WEB_ROOT) -> None:
    root = Path(studio_web_root)
    index = root / "index.html"
    if not index.is_file():
        return

    @app.get("/studio-next", include_in_schema=False)
    def studio_next_redirect() -> RedirectResponse:
        return RedirectResponse(url="/studio-next/")

    app.mount(
        "/studio-next",
        NoStoreStaticFiles(directory=root, html=True),
        name="afs_studio_next",
    )


def configure_studio_legacy_static(app: FastAPI, studio_root: Path = DEFAULT_STUDIO_ROOT) -> None:
    root = Path(studio_root)
    if not root.exists():
        return

    @app.get("/studio-legacy", include_in_schema=False)
    def studio_legacy_redirect() -> RedirectResponse:
        return RedirectResponse(url="/studio-legacy/")

    app.mount(
        "/studio-legacy",
        NoStoreStaticFiles(directory=root, html=True),
        name="afs_studio_legacy",
    )


def studio_static_status(
    studio_web_root: Path = DEFAULT_STUDIO_WEB_ROOT,
) -> dict[str, bool | str]:
    return _studio_web_static_status(studio_web_root, route="/studio/", role="primary")


def studio_next_static_status(
    studio_web_root: Path = DEFAULT_STUDIO_WEB_ROOT,
) -> dict[str, bool | str]:
    return _studio_web_static_status(studio_web_root, route="/studio-next/", role="alias")


def studio_legacy_static_status(
    studio_root: Path = DEFAULT_STUDIO_ROOT,
) -> dict[str, bool | str]:
    root = Path(studio_root)
    root_exists = root.exists()
    index_exists = (root / "index.html").is_file()
    entry_js_exists = (root / "src" / "main.js").is_file()
    ready = root_exists and index_exists and entry_js_exists
    status = "ready" if ready else "missing" if not root_exists else "incomplete"
    return {
        "mounted": ready,
        "root_exists": root_exists,
        "index_exists": index_exists,
        "entry_js_exists": entry_js_exists,
        "status": status,
        "route": "/studio-legacy/",
        "role": "legacy",
    }


def _studio_web_static_status(studio_web_root: Path, *, route: str, role: str) -> dict[str, bool | str]:
    root = Path(studio_web_root)
    root_exists = root.exists()
    index_exists = (root / "index.html").is_file()
    assets_dir_exists = (root / "assets").is_dir()
    ready = root_exists and index_exists and assets_dir_exists
    status = "ready" if ready else "missing" if not root_exists else "incomplete"
    return {
        "mounted": ready,
        "root_exists": root_exists,
        "index_exists": index_exists,
        "assets_dir_exists": assets_dir_exists,
        "status": status,
        "route": route,
        "role": role,
    }


__all__ = (
    "DEFAULT_SITE_ROOT",
    "DEFAULT_STUDIO_ROOT",
    "DEFAULT_STUDIO_WEB_ROOT",
    "NoStoreStaticFiles",
    "configure_site_static",
    "configure_studio_legacy_static",
    "configure_studio_next_static",
    "configure_studio_static",
    "studio_legacy_static_status",
    "studio_next_static_status",
    "studio_static_status",
)
