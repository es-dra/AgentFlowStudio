from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_studio_static import (
    studio_next_static_status,
)


def test_studio_next_static_mount_serves_react_build_without_replacing_legacy_studio(tmp_path):
    legacy_root = tmp_path / "studio"
    legacy_src = legacy_root / "src"
    legacy_src.mkdir(parents=True)
    (legacy_root / "index.html").write_text("<h1>legacy studio</h1>", encoding="utf-8")
    (legacy_src / "main.js").write_text("console.log('legacy')", encoding="utf-8")

    react_root = tmp_path / "studio-web" / "dist"
    react_assets = react_root / "assets"
    react_assets.mkdir(parents=True)
    (react_root / "index.html").write_text("<h1>react studio</h1>", encoding="utf-8")
    (react_assets / "index.js").write_text("console.log('react')", encoding="utf-8")

    app = create_runtime_app(
        runtime_root=tmp_path / "runtime",
        studio_root=legacy_root,
        studio_web_root=react_root,
    )
    client = TestClient(app)

    legacy = client.get("/studio/")
    assert legacy.status_code == 200
    assert "legacy studio" in legacy.text

    redirect = client.get("/studio-next", follow_redirects=False)
    assert redirect.status_code in {307, 308}
    assert redirect.headers["location"] == "/studio-next/"

    react = client.get("/studio-next/")
    assert react.status_code == 200
    assert "react studio" in react.text
    assert react.headers["cache-control"] == "no-store"

    health = client.get("/health").json()
    assert health["studio_static"]["status"] == "ready"
    assert health["studio_static"]["studio_next"]["status"] == "ready"
    assert health["studio_static"]["studio_next"]["route"] == "/studio-next/"


def test_studio_next_status_is_missing_until_react_build_exists(tmp_path):
    missing_root = tmp_path / "missing-dist"
    status = studio_next_static_status(missing_root)
    assert status["mounted"] is False
    assert status["status"] == "missing"


def test_studio_next_mount_is_noop_without_index(tmp_path):
    legacy_root = tmp_path / "legacy"
    legacy_src = legacy_root / "src"
    legacy_src.mkdir(parents=True)
    (legacy_root / "index.html").write_text("<h1>legacy</h1>", encoding="utf-8")
    (legacy_src / "main.js").write_text("console.log('legacy')", encoding="utf-8")

    app = create_runtime_app(
        runtime_root=tmp_path / "runtime",
        studio_root=legacy_root,
        studio_web_root=tmp_path / "empty-dist",
    )
    client = TestClient(app)

    assert client.get("/studio/").status_code == 200
    assert client.get("/studio-next/").status_code == 404


def test_runtime_service_registers_studio_command_routes(tmp_path):
    app = create_runtime_app(runtime_root=tmp_path / "runtime")
    paths = TestClient(app).get("/openapi.json").json()["paths"]

    assert "/api/v1/projects/{project_id}/studio/commands/rework/preview" in paths
    assert "/api/v1/projects/{project_id}/studio/commands/rework/confirm" in paths
