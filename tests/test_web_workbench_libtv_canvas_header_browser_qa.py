from __future__ import annotations

from pathlib import Path


SCRIPT = Path("tools/workbench_libtv_canvas_header_browser_qa.py")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_canvas_header_browser_qa_contract() -> None:
    assert SCRIPT.exists()
    source = _read(SCRIPT)

    for marker in [
        "agentflow_workbench_libtv_canvas_header_browser_qa",
        "--base-url",
        "--output-dir",
        "--viewport",
        "VIEWPORTS",
        "desktop",
        "tablet",
        "mobile",
        "data-studio-title-input",
        "data-studio-canvas-menu",
        "data-studio-canvas-id='canvas-2'",
        "data-studio-canvas-action='new_canvas'",
        "title_value_after_input",
        "canvas_menu_visible",
        "canvas_select_clicks",
        "receipt_text",
        "provider_request_urls",
        "forbidden_matches",
        "screenshot",
    ]:
        assert marker in source


def test_libtv_canvas_header_browser_qa_keeps_claim_boundaries() -> None:
    source = _read(SCRIPT)

    for marker in [
        "api_key",
        "signed_url",
        "provider_config",
        "AFS_ALLOW_REMOTE",
        "not human acceptance",
        "not business validation",
        "not provider smoke",
    ]:
        assert marker in source
