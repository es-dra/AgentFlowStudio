from __future__ import annotations

from tests.web_static_helpers import (
    read_web_file as _read_web_file,
    read_web_shell_source as _read_web_shell_source,
)


def test_static_viewer_uses_package_evidence_and_multiple_report_tabs() -> None:
    artifact_ledgers = _read_web_file("artifact-ledgers.js")
    workspace_render = _read_web_file("app-workspace-render.js")
    html = _read_web_shell_source()

    assert "package_manifest.evidence" in artifact_ledgers
    assert "addDeliveryReadinessRisks" in artifact_ledgers
    assert "addReviewSectionRisks" in artifact_ledgers
    assert 'id="report-tabs"' in html
    assert "renderReportTabs" in workspace_render
    assert "selectedReport" in workspace_render
    assert "const currentReport = selectedReport(workspace)" in workspace_render


def test_static_viewer_rendering_consumes_normalized_workspace_not_raw_payloads() -> None:
    app = _read_web_file("app.js")
    workspace_render = _read_web_file("app-workspace-render.js")

    assert "normalizeWorkspace(artifacts)" in app
    assert "renderWorkspace(elements, state.workspace, copy)" in app
    assert "workspace.evidenceMap" in workspace_render
    assert "workspace.riskLedger" in workspace_render
    assert "workspace.assetLedger" in workspace_render
    for raw_contract_fragment in [
        ".payload",
        "artifact_index",
        "schema_version",
        "finished_package_manifest",
    ]:
        assert raw_contract_fragment not in app + workspace_render


def test_static_viewer_app_keeps_local_read_only_boundary() -> None:
    app = (
        _read_web_file("app.js")
        + _read_web_file("app-workspace-render.js")
        + _read_web_file("artifact-workspace.js")
        + _read_web_file("artifact-contracts.js")
        + _read_web_file("artifact-ledgers.js")
        + _read_web_file("artifact-values.js")
        + _read_web_file("video-preview.js")
        + _read_web_file("feedback-event.js")
        + _read_web_file("ui-copy.js")
        + _read_web_file("render-helpers.js")
    )
    forbidden_patterns = [
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "EventSource",
        "navigator.sendBeacon",
        "showSaveFilePicker",
        "createWritable",
        "indexedDB",
        "localStorage.setItem",
        "FileSystemWritableFileStream",
        "OPENAI_API_KEY",
        "NARRATOCUT_OPENAI_API_KEY",
        "data/processed/runs/demo",
        "D:/Projects/NarratoCut/data",
        "D:\\Projects\\NarratoCut\\data",
    ]

    for pattern in forbidden_patterns:
        assert pattern not in app


def test_static_viewer_report_preview_uses_safe_text_rendering() -> None:
    app = _read_web_file("app.js") + _read_web_file("app-workspace-render.js") + _read_web_file("render-helpers.js")

    assert "textContent" in app
    assert ".innerHTML" not in app
    assert "script" not in app.lower()


def test_static_viewer_video_preview_is_explicit_local_file_only() -> None:
    html = _read_web_shell_source()
    video_preview = _read_web_file("video-preview.js")
    workspace_render = _read_web_file("app-workspace-render.js")

    assert ".mp4,.webm,.mov" in html
    assert "URL.createObjectURL" in video_preview
    assert "URL.revokeObjectURL" in video_preview
    assert "canPlayType" in video_preview
    assert "video/mp4" in video_preview
    assert "video/webm" in video_preview
    assert "video/quicktime" in video_preview
    assert "workspace.videos" in workspace_render
    assert "manifest" not in video_preview.lower()


def test_static_viewer_feedback_event_copy_does_not_write_files() -> None:
    html = _read_web_shell_source()
    feedback = _read_web_file("feedback-event.js")
    workspace_render = _read_web_file("app-workspace-render.js")

    assert "feedback_event" in feedback
    assert "narratocut_web_static_viewer" in feedback
    assert "navigator.clipboard.writeText" in feedback
    assert "feedback-output" in html
    assert "textarea" in html
    assert "renderFeedbackArtifacts" in workspace_render
    for forbidden in ["showSaveFilePicker", "createWritable", "fetch(", "sendBeacon"]:
        assert forbidden not in feedback


def test_static_viewer_readme_documents_boundaries() -> None:
    readme = _read_web_file("README.md").lower()

    for phrase in [
        "read-only",
        "local-only",
        "no upload",
        "no backend execution",
        "no persistence",
        "feedback event copy",
        "does not scan directories",
        "unknown_json",
        "unsupported_file",
        "schema_version",
        "warning",
        "local video preview",
        "no provider config",
        "no workflow execution",
        "terminal mojibake",
        "source files are utf-8",
        "m1.2.1",
        "m1.3",
        "m1.5",
        "m2",
    ]:
        assert phrase in readme

    assert "m1.2" in readme
    assert "default chinese" in readme
    assert "in-memory" in readme
