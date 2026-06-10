from __future__ import annotations

from pathlib import Path


SCRIPT = Path("tools/workbench_libtv_add_node_browser_qa.py")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_add_node_browser_qa_script_contract() -> None:
    assert SCRIPT.exists()
    source = _read(SCRIPT)

    for marker in [
        "agentflow_workbench_libtv_add_node_browser_qa",
        "--base-url",
        "--output-dir",
        "--viewport",
        "VIEWPORTS",
        "desktop",
        "tablet",
        "mobile",
        "viewport_id",
        "viewport",
        "STATE_CASES",
        "text",
        "image",
        "video",
        "audio",
        "script",
        "director",
        "video_merge",
        "upload",
        "history",
        "data-studio-tool='add'",
        "data-add-node-kind",
        "data-add-resource-kind",
        "console_errors",
        "overflow_nodes",
        "forbidden_matches",
        "provider_calls_started",
        "screenshot",
    ]:
        assert marker in source


def test_libtv_browser_qa_keeps_provider_and_secret_claims_out_of_scope() -> None:
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
