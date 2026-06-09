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
    normalizer = _read(WORKBENCH_ROOT / "src" / "studio-workspace-state.js")

    assert '<link rel="stylesheet" href="./styles-studio-workspace.css" />' in index
    assert "normalizeStudioWorkspace" in state
    assert "source.studio_workspace" in state
    assert "studio_workspace: normalizeStudioWorkspace(source.studio_workspace)" in state
    assert 'import { renderStudioWorkspace } from "./render-studio-workspace.js";' in render
    assert "renderStudioWorkspace(workbench.studio_workspace, state)" in render
    assert "return [\n    renderStudioWorkspace(workbench.studio_workspace, state)" in render
    assert "...common,\n    renderStudioWorkspace(workbench.studio_workspace, state)" not in render
    assert "Studio Workspace" in renderer
    assert "studio-command-strip" in renderer
    assert "studio-canvas" in renderer
    assert "studio-inspector" in renderer
    assert "studio-side-rail" in renderer
    assert "studio-filmstrip" in renderer
    assert "canOpenView" in renderer
    assert "dataset: { view: command.view }" in renderer
    assert "Open ${command.view}" in renderer
    assert "command.blocked_reason" in renderer
    assert "primary_command" in normalizer
    assert "operations_summary" in normalizer
