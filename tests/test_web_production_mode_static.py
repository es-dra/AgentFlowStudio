from __future__ import annotations

from tests.web_static_helpers import (
    read_web_file as _read_web_file,
    read_web_shell_source as _read_web_shell_source,
)


def test_web_production_mode_uses_local_bridge_only() -> None:
    production = _read_web_file("production-mode.js")
    bridge_client = _read_web_file("production-bridge-client.js")
    combined = production + bridge_client

    assert 'from "./production-bridge-client.js"' in production
    assert "http://127.0.0.1:8787" in bridge_client
    for endpoint in ["/health", "/workflows", "/plans", "/runs"]:
        assert endpoint in combined
    for forbidden in [
        "https://",
        "http://api.",
        "localStorage",
        "indexedDB",
        "showSaveFilePicker",
        "WebSocket",
        "EventSource",
        "navigator.sendBeacon",
    ]:
        assert forbidden not in combined

def test_web_production_mode_renders_supervision_controls() -> None:
    html = _read_web_shell_source()
    production = _read_web_file("production-mode.js")
    ui_copy = _read_web_file("ui-copy.js")

    for token in [
        "确认继续",
        "记录暂停意见",
        "记录重跑建议",
        "记录修改意见",
        "当前任务",
        "阻塞项",
        "Artifact Timeline",
    ]:
        assert token in html + production + ui_copy
    assert "renderProductionState" in production
    assert "workflow_plan.json" in production

def test_web_production_mode_declares_readiness_wizard_and_task_workspace() -> None:
    html = _read_web_shell_source()
    production = _read_web_file("production-mode.js")
    production_render = _read_web_file("production-render.js")
    production_css = _read_web_file("production.css")
    combined = html + production + production_render + production_css

    for token in [
        'id="production-readiness"',
        'id="readiness-checklist"',
        'id="production-acceptance-path"',
        'id="production-next-action"',
        "生产准备",
        "Local Alpha 0.4 operator loop",
        "本机环境",
        "输入诊断",
        "下一步动作",
        "当前任务",
        "阻塞项",
        "可交付物",
        "先连 bridge，再生成计划",
        "artifact inspection 后刷新验收报告",
        "feedback capture：生成 run_feedback_event JSON，只复制不写入。",
        "renderAcceptancePath",
        "renderReadinessWizard",
        "readiness-grid",
    ]:
        assert token in combined

def test_web_production_mode_declares_alpha_0_4_operator_loop_and_feedback_gate() -> None:
    html = _read_web_shell_source()
    production = _read_web_file("production-mode.js")
    production_render = _read_web_file("production-render.js")
    feedback = _read_web_file("feedback-event.js")
    feedback_wiring = _read_web_file("feedback-wiring.js")
    combined = html + production + production_render + feedback + feedback_wiring

    for token in [
        "Local Alpha 0.4",
        "operator loop",
        "workflow selection",
        "artifact inspection",
        "feedback capture",
        'id="operator-loop-status"',
        "feedbackCaptured",
        "recordRunFeedbackCaptured",
        "activeOperatorStepIndex",
        "onRunFeedbackCaptured",
        "review_status",
        "review_report",
        "quality_report",
    ]:
        assert token in combined

def test_web_production_mode_declares_production_video_review_and_run_feedback() -> None:
    html = _read_web_shell_source()
    app = _read_web_file("app.js")
    production = _read_web_file("production-mode.js")
    production_render = _read_web_file("production-render.js")
    feedback = _read_web_file("feedback-event.js")
    feedback_wiring = _read_web_file("feedback-wiring.js")
    combined = html + app + production + production_render + feedback + feedback_wiring

    for token in [
        'id="production-video-review"',
        'id="production-video-preview"',
        'id="production-asset-match"',
        "成片审看",
        "显式选择视频",
        "可能对应最终成片",
        "renderProductionVideoReview",
        "buildRunFeedbackEvent",
        "attachFeedbackHandlers",
        "run_dir",
        "workflow",
        "video_time_sec",
    ]:
        assert token in combined

def test_web_production_mode_uses_honest_supervision_labels() -> None:
    html = _read_web_shell_source()
    production_render = _read_web_file("production-render.js")
    combined = html + production_render

    for token in [
        "确认继续",
        "记录暂停意见",
        "记录重跑建议",
        "记录修改意见",
        "不直接中断已启动的本地 Python 步骤",
        "不伪装成 step-level rerun",
    ]:
        assert token in combined

def test_web_production_mode_has_no_mojibake_literals() -> None:
    combined = "\n".join(
        _read_web_file(name)
        for name in [
            "index.html",
            "app-shell-review-template.js",
            "app-shell-production-template.js",
            "app-shell-memory-template.js",
            "production-mode.js",
            "production-render.js",
            "production-workflows.js",
        ]
    )

    for mojibake in ["鐢", "楠", "鏈", "浜", "绛", "闃", "鏆", "鍙"]:
        assert mojibake not in combined

    for readable in [
        "生产准备",
        "本机演示",
        "完整成品包",
        "生成 workflow_plan.json",
        "刷新验收报告",
        "artifact inspection",
        "feedback capture",
    ]:
        assert readable in combined

def test_web_app_orchestration_is_split_from_feedback_wiring() -> None:
    app = _read_web_file("app.js")
    elements = _read_web_file("app-elements.js")
    feedback_wiring = _read_web_file("feedback-wiring.js")

    assert "collectAppElements" in app + elements
    assert "attachFeedbackHandlers" in app + feedback_wiring
    assert "buildRunFeedbackEvent" not in app
    assert "buildRunFeedbackEvent" in feedback_wiring
    assert "document.querySelector" not in app
    assert "document.querySelector" in elements

def test_web_production_mode_polls_background_run_status() -> None:
    production = _read_web_file("production-mode.js")
    production_render = _read_web_file("production-render.js")
    app = _read_web_file("app.js")
    html = _read_web_shell_source()
    production_css = _read_web_file("production.css")
    combined_production = production + production_render

    for token in [
        "RUN_POLL_INTERVAL_MS",
        "startRunPolling",
        "pollRunStatus",
        "bridge_status.json",
        "current_step",
        "input_check",
        "inputCheckText",
        "local_asr",
        "本地 ASR 依赖缺失",
        "runPollTimer",
        "recordSupervisionIntent",
    ]:
        assert token in combined_production
    assert "startRunPolling(elements, copy)" in production
    assert "button[data-supervision]" in app
    assert 'data-supervision="continue"' in html
    assert "production.css" in html
    assert ".production-path li.active" in production_css

def test_web_production_mode_defaults_match_preferred_workflow() -> None:
    html = _read_web_shell_source()
    production = _read_web_file("production-mode.js")
    production_render = _read_web_file("production-render.js")
    production_workflows = _read_web_file("production-workflows.js")

    combined = html + production + production_render + production_workflows

    assert "data/processed/local_alpha_0_4/video_script_local_asr_input.json" in html
    assert "data/processed/runs/local_alpha_0_4_product_loop" in html + production_workflows
    assert 'PRODUCT_WORKFLOW_NAME = "video_script_to_finished_package_local_asr"' in production_workflows
    assert "local_setup_blockers" in combined
    assert "docs/local_alpha_0_4_scenario_package.md" in combined
    assert "Local Alpha 0.4" in combined
    assert "video_to_finished_package_local_asr_input.example.json" in production_workflows
    assert "FALLBACK_WORKFLOW_INPUTS" in production_workflows
    assert "applyWorkflowDefaults" in production

def test_web_production_mode_has_demo_quick_start_without_storage() -> None:
    html = _read_web_shell_source()
    production = _read_web_file("production-mode.js")
    production_workflows = _read_web_file("production-workflows.js")
    production_css = _read_web_file("production.css")
    styles = _read_web_file("styles.css") + _read_web_file("styles-responsive.css")

    for token in [
        "quick-demo-button",
        "product-workflow-button",
        "本机演示",
        "完整成品",
        "mock_text_to_slices",
        "selectWorkflowByName",
        "renderWorkflowProfile",
        "web_profile",
        "examples/demo_text/story.txt",
    ]:
        assert token in html + production + production_workflows + production_css
    assert "localStorage" not in production + production_workflows
    assert '@import url("./styles-responsive.css");' in styles
    assert "@media (max-width: 1240px)" in styles
    assert ".topbar {\n    position: static;\n  }" in styles

def test_web_production_mode_blocks_asr_only_when_selected_workflow_requires_it() -> None:
    production = _read_web_file("production-mode.js")
    production_workflows = _read_web_file("production-workflows.js")

    assert "workflowRequires" in production + production_workflows
    assert 'workflowRequires(selectedWorkflow(), "local_asr")' in production
    assert "本地 ASR 依赖缺失" in production

def test_web_production_mode_keeps_select_and_state_in_sync() -> None:
    production = _read_web_file("production-mode.js")
    production_render = _read_web_file("production-render.js")

    assert "productionState.selectedWorkflowPath = renderWorkflowSelect" in production
    assert "selectedWorkflowPath(elements)" in production
    assert "const desired = selectedWorkflowPath || elements.workflowSelect.value" in production_render
