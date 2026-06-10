from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_canvas_header_state_flow_is_wired() -> None:
    header = WORKBENCH_ROOT / "src" / "render-studio-canvas-header.js"
    events = WORKBENCH_ROOT / "src" / "studio-canvas-header-events.js"
    css_file = WORKBENCH_ROOT / "styles-studio-canvas-header.css"
    assert header.exists()
    assert events.exists()
    assert css_file.exists()

    index = _read(WORKBENCH_ROOT / "index.html")
    state = _read(WORKBENCH_ROOT / "src" / "state.js")
    app = _read(WORKBENCH_ROOT / "src" / "app.js")
    workspace = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")
    source = _read(header) + _read(events)
    css = _read(css_file)

    assert '<link rel="stylesheet" href="./styles-studio-canvas-header.css" />' in index
    assert 'import { renderCanvasTopbar } from "./render-studio-canvas-header.js";' in workspace
    assert 'import { bindCanvasHeaderEvents } from "./studio-canvas-header-events.js";' in app
    assert "bindCanvasHeaderEvents(root, state, paint)" in app

    for marker in [
        'studioProjectTitle: ""',
        'studioCanvasMenuOpen: false',
        'studioActiveCanvasId: "canvas-1"',
        'studioCanvasIntent: ""',
    ]:
        assert marker in state

    for marker in [
        "data-studio-title-input",
        "data-studio-canvas-menu",
        "data-studio-canvas-id",
        "data-studio-canvas-action",
        "state.studioProjectTitle = node.value",
        "state.studioCanvasMenuOpen = !state.studioCanvasMenuOpen",
        "state.studioActiveCanvasId = node.dataset.studioCanvasId",
        "state.studioCanvasIntent = node.dataset.studioCanvasAction",
    ]:
        assert marker in source

    for marker in [
        "项目名称",
        "画布 1",
        "画布 2",
        "新建画布",
        "本地画布意图已登记",
        "未创建真实画布",
        "未启动 provider",
        "libtv-canvas-title-input",
        "libtv-canvas-menu",
        "libtv-canvas-intent-status",
        "activeCanvas",
    ]:
        assert marker in source

    for marker in [
        ".libtv-canvas-title-input",
        ".libtv-canvas-switcher",
        ".libtv-canvas-menu",
        ".libtv-canvas-menu button.active",
        ".libtv-canvas-intent-status",
    ]:
        assert marker in css
