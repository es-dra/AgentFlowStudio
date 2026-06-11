from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_shell_default_user_flow_is_home_to_canvas_to_assets() -> None:
    state = _read(WORKBENCH_ROOT / "src" / "state.js")
    app = _read(WORKBENCH_ROOT / "src" / "app.js")
    render = _read(WORKBENCH_ROOT / "src" / "render.js")
    home = _read(WORKBENCH_ROOT / "src" / "render-project-hub.js")
    studio = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")
    assets = _read(WORKBENCH_ROOT / "src" / "render-visible-assets.js")

    assert 'activeView: "Projects"' in state
    assert 'selectedCardId: "script-input"' in state
    assert 'state.activeView = node.dataset.view' in app
    assert 'dataset: { view: "Create", studioStarter: "open" }' in home
    assert 'dataset: { view: "Assets" }' in studio
    assert 'dataset: { view: "Create" }' in assets

    assert 'if (activeView === "Create")' in render
    assert 'if (activeView === "Assets")' in render
    assert "renderProjectHub" in render
    assert "renderStudioWorkspace" in render
    assert "renderVisibleAssetsLibrary" in render


def test_debug_entry_is_hidden_behind_url_or_keyboard_toggle() -> None:
    app = _read(WORKBENCH_ROOT / "src" / "app.js")
    render = _read(WORKBENCH_ROOT / "src" / "render.js")

    assert 'get("debug") === "1"' in app
    assert 'event.altKey && event.key.toLowerCase() === "d"' in app
    assert "state.debugMode = !state.debugMode" in app
    assert "if (!state.debugMode) return null" in render
    assert "内部调试" in render
