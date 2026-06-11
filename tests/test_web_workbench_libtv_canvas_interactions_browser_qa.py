from __future__ import annotations

from pathlib import Path


SCRIPT = Path("tools/workbench_libtv_canvas_interactions_browser_qa.py")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_canvas_interactions_browser_qa_contract() -> None:
    assert SCRIPT.exists()
    source = _read(SCRIPT)

    for marker in [
        "agentflow_workbench_libtv_canvas_interactions_browser_qa",
        "--base-url",
        "double-click add menu",
        "pending Bezier edge",
        "marquee did not select multiple nodes",
        "bottom_safe_drag",
        "selected_node_clear_of_dock",
        "connection-success-ripple",
        "not human acceptance",
        "not business validation",
        "not provider smoke",
    ]:
        assert marker in source
