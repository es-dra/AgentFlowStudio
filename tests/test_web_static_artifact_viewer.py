from __future__ import annotations

from tests.web_static_helpers import (
    WEB_FIXTURE_ROOT,
    read_fixture_file as _read_fixture_file,
    read_web_file as _read_web_file,
    read_web_shell_source as _read_web_shell_source,
)


def test_static_viewer_html_declares_local_artifact_workbench() -> None:
    html = _read_web_shell_source()

    assert 'href="styles.css"' in html
    assert 'href="memory-workbench.css?v=m4-memory-canvas-tools"' in html
    assert 'href="memory-workbench-studio.css?v=m5-studio-canvas"' in html
    assert 'src="app.js?v=m4-memory-canvas-tools"' in html
    assert 'type="module"' in html
    assert 'lang="zh-CN"' in html
    assert 'id="app-root"' in html
    assert "mountAppShell" in html
    assert 'type="file"' in html
    assert "multiple" in html
    assert ".mp4,.webm,.mov" in html
    assert 'id="language-toggle"' in html
    assert "stat-strip" in html
    assert "内容生产验收" in html
    assert "<main" in html
    for landmark in [
        'id="artifact-inventory"',
        'id="summary-panel"',
        'id="inspector-panel"',
        'id="evidence-map-panel"',
        'id="risk-ledger-panel"',
        'id="asset-ledger-panel"',
        'id="video-preview-panel"',
        'id="feedback-panel"',
        'id="report-preview"',
    ]:
        assert landmark in html


def test_static_viewer_app_declares_artifact_aliases_and_normalized_types() -> None:
    app = _read_web_file("app.js")
    workspace_render = _read_web_file("app-workspace-render.js")
    artifact_workspace = _read_web_file("artifact-workspace.js")
    artifact_contracts = _read_web_file("artifact-contracts.js")
    artifact_ledgers = _read_web_file("artifact-ledgers.js")
    ui_copy = _read_web_file("ui-copy.js")
    render_helpers = _read_web_file("render-helpers.js")
    combined_source = app + workspace_render + artifact_workspace + artifact_contracts + artifact_ledgers + ui_copy + render_helpers

    assert 'from "./artifact-workspace.js?v=m4-memory-canvas-tools"' in app
    assert 'from "./app-workspace-render.js"' in app
    assert 'from "./ui-copy.js"' in app
    assert 'from "./render-helpers.js"' in workspace_render
    assert "ARTIFACT_ALIASES" in artifact_contracts
    assert "finished_package_manifest.json" in artifact_contracts
    assert "package_manifest.json" in artifact_contracts
    assert "package_manifest" in artifact_contracts
    assert "detectArtifactType" in artifact_workspace
    assert "normalizeWorkspace" in artifact_workspace
    for artifact_type in [
        "run_manifest",
        "package_manifest",
        "quality_report",
        "review_report",
        "delivery_readiness",
        "markdown_report",
        "selection_diagnostics",
        "highlight_score_report",
        "candidate_windows",
        "clip_plan",
        "real_slice_manifest",
        "final_video_manifest",
        "subtitle_manifest",
        "audio_mix_manifest",
        "cover_manifest",
    ]:
        assert artifact_type in combined_source


def test_static_viewer_real_fixture_covers_supported_artifact_shapes() -> None:
    expected_files = [
        "run_manifest.json",
        "finished_package_manifest.json",
        "quality_report.json",
        "review_report.json",
        "delivery_readiness.json",
        "package_report.md",
        "delivery_readiness.md",
    ]

    for name in expected_files:
        assert (WEB_FIXTURE_ROOT / name).is_file()

    assert '"artifact_index"' in _read_fixture_file("run_manifest.json")
    assert '"assets"' in _read_fixture_file("finished_package_manifest.json")
    assert '"checks"' in _read_fixture_file("quality_report.json")
    assert '"sections"' in _read_fixture_file("review_report.json")
    assert '"runs"' in _read_fixture_file("delivery_readiness.json")
    assert "<script>" in _read_fixture_file("package_report.md")


def test_static_viewer_declares_m11_artifact_classes_and_schema_warnings() -> None:
    artifact_workspace = _read_web_file("artifact-workspace.js")
    artifact_workspace_artifacts = _read_web_file("artifact-workspace-artifacts.js")
    artifact_contracts = _read_web_file("artifact-contracts.js")
    combined_source = artifact_workspace + artifact_workspace_artifacts + artifact_contracts
    workspace_render = _read_web_file("app-workspace-render.js")

    for source_token in [
        "artifactClass",
        "participatesInSummary",
        "schemaWarnings",
        "known_contract",
        "unknown_json",
        "unsupported_file",
        "parsed but not included in summary",
        "schema_version missing",
    ]:
        assert source_token in combined_source

    assert "artifact.artifactClass" in workspace_render
    assert "artifact.schemaWarnings" in workspace_render


def test_static_viewer_declares_m12_chinese_copy_and_in_memory_language_switch() -> None:
    app = _read_web_file("app.js")
    ui_copy = _read_web_file("ui-copy.js")
    render_helpers = _read_web_file("render-helpers.js")

    assert 'language: "zh"' in app
    assert 'state.language = state.language === "zh" ? "en" : "zh"' in app
    assert "localStorage" not in app + ui_copy + render_helpers
    assert "先看成品能否交付，再看证据和风险。" in ui_copy
    assert "交付总览" in ui_copy
    assert "审查 Inspector" in ui_copy
    assert "报告审阅" in ui_copy
    assert "Contract Inspector" in ui_copy
    assert "通过 pass" in ui_copy
    assert "警告 warning" in ui_copy
    assert "未知 unknown" in ui_copy
    assert "未找到详细检查项" in ui_copy
    assert "statusPill" in render_helpers
    assert "normalizeStatus" in render_helpers


def test_static_viewer_declares_m121_acceptance_metrics_and_empty_state_boundary() -> None:
    ui_copy = _read_web_file("ui-copy.js")
    artifact_workspace = _read_web_file("artifact-workspace.js")

    for phrase in ["已选文件", "参与验收", "风险提示", "解析错误"]:
        assert phrase in ui_copy

    assert "summaryArtifacts.length > 0" in artifact_workspace
    assert "Missing recommended artifact" in artifact_workspace


def test_static_viewer_declares_m14_productive_review_workbench_layout() -> None:
    html = _read_web_shell_source()
    css = (
        _read_web_file("styles.css")
        + _read_web_file("styles-base.css")
        + _read_web_file("styles-review-layout.css")
        + _read_web_file("styles-controls.css")
    )
    ui_copy = _read_web_file("ui-copy.js")

    for token in [
        'class="topbar"',
        'class="workflow-rail"',
        'class="content-stage"',
        'class="review-rail"',
        'id="recommended-artifacts"',
        'id="contract-inspector"',
    ]:
        assert token in html

    assert 'class="hero"' not in html
    assert "交付总览" in ui_copy
    assert "推荐文件组" in ui_copy
    assert "Contract Inspector" in ui_copy
    assert '@import url("./styles-base.css");' in css
    assert "topbar" in css
    assert "content-stage" in css
    assert "review-rail" in css
