from __future__ import annotations

from pathlib import Path


WORKBENCH_ROOT = Path("apps/workbench")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_libtv_canvas_execution_scaffold_is_productized_without_provider() -> None:
    workspace = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")
    scaffold = _read(WORKBENCH_ROOT / "src" / "render-studio-execution-scaffold.js")
    css = _read(WORKBENCH_ROOT / "styles-studio-execution-scaffold.css")
    index = _read(WORKBENCH_ROOT / "index.html")

    assert 'import { renderExecutionScaffold } from "./render-studio-execution-scaffold.js";' in workspace
    assert "renderExecutionScaffold(cards, selectedCardId, state)" in workspace

    for marker in [
        "libtv-execution-scaffold",
        "libtv-execution-edges",
        "libtv-canvas-edge",
        "libtv-parameter-drawer",
        "libtv-action-queue",
        "data-execution-intent",
        "节点连接",
        "参数抽屉",
        "待执行动作",
        "生成预检",
        "登记执行意图",
        "等待能力授权",
        "只登记本地执行意图，不启动真实生成。",
    ]:
        assert marker in scaffold

    for marker in [
        ".libtv-execution-scaffold",
        ".libtv-execution-edges",
        ".libtv-canvas-edge",
        ".libtv-parameter-drawer",
        ".libtv-action-queue",
        ".libtv-action-queue button",
        "@media (max-width: 760px)",
    ]:
        assert marker in css

    assert '<link rel="stylesheet" href="./styles-studio-execution-scaffold.css" />' in index

    for forbidden in [
        "fetch(\"/provider",
        "fetch('/provider",
        "fetch(\"/generate",
        "showOpenFilePicker",
        "FileReader",
        "AFS_ALLOW_REMOTE",
        "OPENAI_API_KEY",
        "signed_url",
    ]:
        assert forbidden not in scaffold


def test_libtv_execution_scaffold_browser_qa_contract_exists() -> None:
    script = Path("tools/workbench_libtv_execution_scaffold_browser_qa.py")
    source = script.read_text(encoding="utf-8")

    for marker in [
        "agentflow_workbench_libtv_execution_scaffold_browser_qa",
        "libtv-execution-scaffold",
        "libtv-parameter-drawer",
        "libtv-action-queue",
        "required_labels_missing",
        "provider_request_urls",
        "not provider smoke",
    ]:
        assert marker in source


def test_libtv_execution_intent_flow_is_local_state_only() -> None:
    state = _read(WORKBENCH_ROOT / "src" / "state.js")
    app = _read(WORKBENCH_ROOT / "src" / "app.js")
    workspace = _read(WORKBENCH_ROOT / "src" / "render-studio-workspace.js")
    scaffold = _read(WORKBENCH_ROOT / "src" / "render-studio-execution-scaffold.js")
    css = _read(WORKBENCH_ROOT / "styles-studio-execution-scaffold.css")

    assert 'studioExecutionIntent: ""' in state
    assert "data-execution-intent" in app
    assert "studioExecutionIntent" in app
    assert "renderExecutionScaffold(cards, selectedCardId, state)" in workspace

    for marker in [
        "libtv-execution-status",
        "libtv-intent-flow",
        "本地意图已登记",
        "等待能力门授权",
        "未创建真实任务",
        "未启动 provider",
        "activeIntent",
    ]:
        assert marker in scaffold

    for marker in [
        ".libtv-action-queue button.active",
        ".libtv-execution-status",
        ".libtv-intent-flow",
    ]:
        assert marker in css

    for source in [state, app, workspace, scaffold, css]:
        for forbidden in [
            "fetch(\"/provider",
            "fetch('/provider",
            "fetch(\"/generate",
            "fetch('/generate",
            "AFS_ALLOW_REMOTE",
            "OPENAI_API_KEY",
            "signed_url",
        ]:
            assert forbidden not in source


def test_libtv_execution_intent_browser_qa_covers_click_status_flow() -> None:
    source = Path("tools/workbench_libtv_execution_scaffold_browser_qa.py").read_text(encoding="utf-8")

    for marker in [
        "intent_clicks",
        "active_button_visible",
        "receipt_text",
        "[data-execution-intent='preflight']",
        "[data-execution-intent='register']",
        "[data-execution-intent='wait_gate']",
        "本地意图已登记",
        "未创建真实任务",
        "未启动 provider",
    ]:
        assert marker in source
