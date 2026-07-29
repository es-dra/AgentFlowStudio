from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_studio_static import (
    studio_static_status,
    studio_legacy_static_status,
    studio_next_static_status,
)


def test_primary_studio_serves_react_build_with_legacy_and_next_aliases(tmp_path):
    legacy_root = tmp_path / "studio"
    legacy_src = legacy_root / "src"
    legacy_src.mkdir(parents=True)
    (legacy_root / "index.html").write_text(
        "<title>AFS Studio 创作图谱</title><h1>legacy studio</h1>",
        encoding="utf-8",
    )
    (legacy_src / "main.js").write_text("console.log('legacy')", encoding="utf-8")

    react_root = tmp_path / "studio-web" / "dist"
    react_assets = react_root / "assets"
    react_assets.mkdir(parents=True)
    (react_root / "index.html").write_text(
        '<title>AFS 制作工作区</title><h1>react studio</h1>'
        '<script type="module" src="/studio/assets/index.js"></script>',
        encoding="utf-8",
    )
    (react_assets / "index.js").write_text("console.log('react')", encoding="utf-8")

    app = create_runtime_app(
        runtime_root=tmp_path / "runtime",
        studio_root=legacy_root,
        studio_web_root=react_root,
    )
    client = TestClient(app)

    primary_redirect = client.get("/studio", follow_redirects=False)
    assert primary_redirect.status_code in {307, 308}
    assert primary_redirect.headers["location"] == "/studio/"

    primary = client.get("/studio/?project=legacy-project")
    assert primary.status_code == 200
    assert "AFS 制作工作区" in primary.text
    assert "react studio" in primary.text
    assert "legacy studio" not in primary.text
    assert "/studio/assets/index.js" in primary.text
    assert primary.headers["cache-control"] == "no-store"

    primary_asset = client.get("/studio/assets/index.js")
    assert primary_asset.status_code == 200
    assert "react" in primary_asset.text

    episode_workspace = client.get(
        "/studio/episode-workspace/?project=legacy-project&episode=episode-001&version=episode-001-v1",
        follow_redirects=False,
    )
    assert episode_workspace.status_code in {307, 308}
    assert (
        episode_workspace.headers["location"]
        == "/studio/?project_id=legacy-project&surface=storyboard"
    )

    next_redirect = client.get("/studio-next", follow_redirects=False)
    assert next_redirect.status_code in {307, 308}
    assert next_redirect.headers["location"] == "/studio-next/"

    next_alias = client.get("/studio-next/?project_id=canonical-project")
    assert next_alias.status_code == 200
    assert "AFS 制作工作区" in next_alias.text
    assert "/studio/assets/index.js" in next_alias.text

    next_alias_asset = client.get("/studio-next/assets/index.js")
    assert next_alias_asset.status_code == 200
    assert "react" in next_alias_asset.text

    legacy_redirect = client.get("/studio-legacy", follow_redirects=False)
    assert legacy_redirect.status_code in {307, 308}
    assert legacy_redirect.headers["location"] == "/studio-legacy/"

    legacy = client.get("/studio-legacy/?project=legacy-project")
    assert legacy.status_code == 200
    assert "AFS Studio 创作图谱" in legacy.text
    assert "legacy studio" in legacy.text
    assert "react studio" not in legacy.text

    legacy_asset = client.get("/studio-legacy/src/main.js")
    assert legacy_asset.status_code == 200
    assert "legacy" in legacy_asset.text

    api = client.get("/api/v1/projects/missing-project/studio")
    assert api.status_code == 404
    assert api.headers["content-type"].startswith("application/json")
    assert "react studio" not in api.text
    assert "legacy studio" not in api.text

    health = client.get("/health").json()
    assert health["studio_static"]["status"] == "ready"
    assert health["studio_static"]["route"] == "/studio/"
    assert health["studio_static"]["role"] == "primary"
    assert health["studio_static"]["assets_dir_exists"] is True
    assert health["studio_static"]["legacy"]["status"] == "ready"
    assert health["studio_static"]["legacy"]["route"] == "/studio-legacy/"
    assert health["studio_static"]["legacy"]["role"] == "legacy"
    assert health["studio_static"]["studio_next"]["status"] == "ready"
    assert health["studio_static"]["studio_next"]["route"] == "/studio-next/"
    assert health["studio_static"]["studio_next"]["role"] == "alias"


def test_studio_web_status_is_missing_until_react_build_exists(tmp_path):
    missing_root = tmp_path / "missing-dist"
    primary_status = studio_static_status(missing_root)
    status = studio_next_static_status(missing_root)
    assert primary_status["mounted"] is False
    assert primary_status["status"] == "missing"
    assert primary_status["role"] == "primary"
    assert status["mounted"] is False
    assert status["status"] == "missing"
    assert status["role"] == "alias"


def test_studio_legacy_status_is_missing_until_legacy_root_exists(tmp_path):
    missing_root = tmp_path / "missing-legacy"
    status = studio_legacy_static_status(missing_root)
    assert status["mounted"] is False
    assert status["status"] == "missing"
    assert status["role"] == "legacy"


def test_studio_primary_and_next_mounts_are_noop_without_react_index(tmp_path):
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

    assert client.get("/studio/").status_code == 404
    assert client.get("/studio-next/").status_code == 404
    assert client.get("/studio-legacy/").status_code == 200
    episode_workspace = client.get(
        "/studio/episode-workspace/?project=legacy-project",
        follow_redirects=False,
    )
    assert episode_workspace.status_code in {307, 308}
    assert (
        episode_workspace.headers["location"]
        == "/studio/?project_id=legacy-project&surface=storyboard"
    )


def test_runtime_service_registers_studio_command_routes(tmp_path):
    app = create_runtime_app(runtime_root=tmp_path / "runtime")
    paths = TestClient(app).get("/openapi.json").json()["paths"]

    assert "/api/v1/projects/{project_id}/studio/commands/rework/preview" in paths
    assert "/api/v1/projects/{project_id}/studio/commands/rework/confirm" in paths
