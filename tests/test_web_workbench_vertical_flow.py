from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_workbench_vertical_flow_has_empty_project_start_and_next_action_feedback() -> None:
    render = _read(WORKBENCH_ROOT / "src" / "render.js")
    actions = _read(WORKBENCH_ROOT / "src" / "render-actions.js")
    project_hub = _read(WORKBENCH_ROOT / "src" / "render-project-hub.js")
    studio = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")
    board_css = _read(WORKBENCH_ROOT / "styles-production-board.css")
    command_css = _read(WORKBENCH_ROOT / "styles-command-hub.css")

    assert 'renderActionPanel(state, ["project", "result"])' in render
    assert 'Settings: ["project", "import", "assets", "scene", "review", "runtime", "result"]' in render
    assert "groups.includes(\"import\")" in actions
    assert "result.flow" in actions
    assert "Next: ${flow.current_action_label" in actions
    assert 'record_review_note: "record-review-decision"' in _read(WORKBENCH_ROOT / "src" / "render-readiness.js")
    assert 'button("Pending", "", "ghost")' not in project_hub
    assert "command.enabled && command.view" in studio
    assert "dataset: { view: command.view }" in studio
    assert ".production-board {\n  grid-column: 1 / 3;" in board_css
    assert "repeat(auto-fit, minmax(150px, 1fr))" in board_css
    assert ".command-hub {\n  grid-column: 1 / 3;" in command_css
