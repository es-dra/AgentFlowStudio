from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_studio_workspace_frontend_contract_is_wired() -> None:
    index = _read(WORKBENCH_ROOT / "index.html")
    state = _read(WORKBENCH_ROOT / "src" / "workbench-state.js")
    app = _read(WORKBENCH_ROOT / "src" / "app.js")
    app_state = _read(WORKBENCH_ROOT / "src" / "state.js")
    render = _read(WORKBENCH_ROOT / "src" / "render.js")
    renderer = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")
    canvas = _read(WORKBENCH_ROOT / "src" / "render-studio-canvas.js")
    inspector = _read(WORKBENCH_ROOT / "src" / "render-studio-inspector.js")
    side_rail = _read(WORKBENCH_ROOT / "src" / "render-studio-side-rail.js")
    normalizer = _read(WORKBENCH_ROOT / "src" / "studio-workspace-state.js")
    css = _read(WORKBENCH_ROOT / "styles-studio-canvas-v2.css") + _read(WORKBENCH_ROOT / "styles-studio-canvas-focus.css")

    assert '<link rel="stylesheet" href="./styles-studio-workspace.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-canvas-v2.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-canvas-focus.css" />' in index
    assert "normalizeStudioWorkspace" in state
    assert "source.studio_workspace" in state
    assert "studio_workspace: normalizeStudioWorkspace(source.studio_workspace)" in state
    assert 'studioFocus: "canvas"' in app_state
    assert "[data-studio-focus]" in app
    assert "state.studioFocus = node.dataset.studioFocus" in app
    assert 'import { renderStudioWorkspace } from "./render-studio-workspace.js";' in render
    assert "workspace-canvas-v2" in render
    assert "renderStudioWorkspace(workbench.studio_workspace, state)" in render
    assert 'return withWindow("Create", [' in render
    assert "renderStudioWorkspace(workbench.studio_workspace, state)" in render
    assert "state.artifact ? renderArtifactPanel(state) : null" in render
    assert "...common,\n    renderStudioWorkspace(workbench.studio_workspace, state)" not in render
    assert "studio-command-strip" in renderer
    assert "canvas-v2" in renderer
    assert "studio-focus-${focus}" in renderer
    assert "renderStudioFocusTabs" in renderer
    assert "studio-focus-tab" in renderer
    assert "data-studio-focus" in renderer
    assert "生成能力 ${displayStatus" in renderer
    assert "Provider ${displayStatus" not in renderer
    assert "renderStudioCanvas" in renderer
    assert "renderStudioInspector" in renderer
    assert "renderStudioSideRail" in renderer
    assert "studio-canvas-toolbar" in canvas
    assert "studio-node-preview" in canvas
    assert "studio-media-frame" in canvas
    assert "mediaFrameLabel(card" in canvas
    assert "studio-node-flow" in canvas
    assert "studio-node-connector" in canvas
    assert "studio-empty-flow" in canvas
    assert "studio-inspector-hero" in inspector
    assert "studio-inspector-facts" in inspector
    assert "studio-side-rail" in side_rail
    assert "studio-side-section" in side_rail
    assert "studio-side-thumb" in side_rail
    assert "studio-filmstrip" in canvas
    assert "studio-filmstrip-preview" in canvas
    assert ".canvas-v2 .studio-stage" in css
    assert ".workspace-canvas-v2 > .workspace-header" in css
    assert ".canvas-v2.studio-focus-canvas .studio-side-rail" in css
    assert ".canvas-v2.studio-focus-assets .studio-canvas" in css
    assert ".canvas-v2.studio-focus-assets .studio-side-review" in css
    assert ".canvas-v2.studio-focus-review .studio-canvas" in css
    assert ".canvas-v2.studio-focus-review .studio-side-assets" in css
    assert ".canvas-v2.studio-focus-ops .studio-layout" in css
    assert ".canvas-v2 .studio-node-preview" in css
    assert ".canvas-v2 .studio-inspector-hero" in css
    assert "canOpenView" in renderer
    assert "dataset: { view: command.view }" in renderer
    assert "打开 ${displayText(command.view)}" in renderer
    assert "command.blocked_reason" in renderer
    assert "primary_command" in normalizer
    assert "operations_summary" in normalizer
