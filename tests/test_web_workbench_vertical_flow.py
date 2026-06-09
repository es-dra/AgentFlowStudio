from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_workbench_vertical_flow_has_empty_project_start_and_next_action_feedback() -> None:
    render = _read(WORKBENCH_ROOT / "src" / "render.js")
    actions = _read(WORKBENCH_ROOT / "src" / "render-actions.js")
    labels = _read(WORKBENCH_ROOT / "src" / "display-labels.js")
    project_hub = _read(WORKBENCH_ROOT / "src" / "render-project-hub.js")
    studio = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")
    workspace_config = _read(WORKBENCH_ROOT / "src" / "workspace-config.js")
    browser_smoke = _read(Path("tools/workbench_vertical_flow_browser_smoke.py"))
    board_css = _read(WORKBENCH_ROOT / "styles-production-board.css")
    command_css = _read(WORKBENCH_ROOT / "styles-command-hub.css")

    assert 'renderActionPanel(state, ["project", "result"])' in render
    assert 'Settings: ["project", "import", "assets", "scene", "review", "runtime", "result"]' in workspace_config
    assert "groups.includes(\"import\")" in actions
    assert "result.flow" in actions
    assert "下一步：${displayText(flow.current_action_label" in actions
    assert "高级运行参数" in actions
    assert "资产 profile seed" not in actions
    assert 'ready_for_next_round: "可进入下一轮"' in labels
    assert 'record_review_note: "record-review-decision"' in _read(WORKBENCH_ROOT / "src" / "render-readiness.js")
    assert 'button("Pending", "", "ghost")' not in project_hub
    assert "command.enabled && command.view" in studio
    assert "dataset: { view: command.view }" in studio
    assert ".production-board {\n  grid-column: 1 / 3;" in board_css
    assert "repeat(auto-fit, minmax(150px, 1fr))" in board_css
    assert ".command-hub {\n  grid-column: 1 / 3;" in command_css
    assert "_open_diagnostics(page)" in browser_smoke
    assert "_wait_for_action(page, \"run-asset-test\")" in browser_smoke
    assert "Browser-driven safe brief summary" not in browser_smoke
    assert "Run first generation check" not in browser_smoke
