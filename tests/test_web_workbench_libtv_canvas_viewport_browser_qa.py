from __future__ import annotations

from pathlib import Path


SCRIPT = Path("tools/workbench_libtv_canvas_viewport_browser_qa.py")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_canvas_viewport_browser_qa_script_contract() -> None:
    assert SCRIPT.exists()
    source = _read(SCRIPT)

    for marker in [
        "agentflow_workbench_libtv_canvas_viewport_browser_qa",
        "--base-url",
        "--output-dir",
        "data-studio-tool='map'",
        "canvas-navigator-panel",
        "canvas-mini-map",
        "fit-view",
        "center-selection",
        "zoom-reset",
        "transform_after_fit",
        "selected_node_centered",
        "viewport_overflow",
        "provider_calls_started",
        "not human acceptance",
        "not business validation",
        "not provider smoke",
    ]:
        assert marker in source
