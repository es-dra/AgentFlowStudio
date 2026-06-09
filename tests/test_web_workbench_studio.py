from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_studio_workspace_frontend_contract_is_wired() -> None:
    index = _read(WORKBENCH_ROOT / "index.html")
    state = _read(WORKBENCH_ROOT / "src" / "workbench-state.js")
    render = _read(WORKBENCH_ROOT / "src" / "render.js")
    renderer = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")
    canvas = _read(WORKBENCH_ROOT / "src" / "render-studio-canvas.js")
    inspector = _read(WORKBENCH_ROOT / "src" / "render-studio-inspector.js")
    side_rail = _read(WORKBENCH_ROOT / "src" / "render-studio-side-rail.js")
    normalizer = _read(WORKBENCH_ROOT / "src" / "studio-workspace-state.js")

    assert '<link rel="stylesheet" href="./styles-studio-workspace.css" />' in index
    assert "normalizeStudioWorkspace" in state
    assert "source.studio_workspace" in state
    assert "studio_workspace: normalizeStudioWorkspace(source.studio_workspace)" in state
    assert 'import { renderStudioWorkspace } from "./render-studio-workspace.js";' in render
    assert "renderStudioWorkspace(workbench.studio_workspace, state)" in render
    assert 'return withWindow("Create", [' in render
    assert "renderStudioWorkspace(workbench.studio_workspace, state)" in render
    assert "...common,\n    renderStudioWorkspace(workbench.studio_workspace, state)" not in render
    assert "studio-command-strip" in renderer
    assert "renderStudioCanvas" in renderer
    assert "renderStudioInspector" in renderer
    assert "renderStudioSideRail" in renderer
    assert "studio-canvas-toolbar" in canvas
    assert "studio-node-flow" in canvas
    assert "studio-node-connector" in canvas
    assert "studio-empty-flow" in canvas
    assert "studio-inspector-facts" in inspector
    assert "studio-side-rail" in side_rail
    assert "studio-filmstrip" in canvas
    assert "canOpenView" in renderer
    assert "dataset: { view: command.view }" in renderer
    assert "打开 ${displayText(command.view)}" in renderer
    assert "command.blocked_reason" in renderer
    assert "primary_command" in normalizer
    assert "operations_summary" in normalizer
