from __future__ import annotations

from tests.web_static_helpers import (
    read_web_file as _read_web_file,
    read_web_shell_source as _read_web_shell_source,
)


def test_web_declares_review_and_memory_modes() -> None:
    html = _read_web_shell_source()
    app = _read_web_file("app.js")
    elements = _read_web_file("app-elements.js")

    assert 'id="mode-review"' in html
    assert 'id="mode-memory"' in html
    assert 'id="memory-workbench"' in html
    assert 'src="app.js?v=m4-memory-canvas-tools"' in html
    assert "setMode" in app
    assert "initialMode" in app
    assert "window.location?.hash" in app
    assert "production-workbench" not in elements
    assert "memory-workbench" in elements
    assert 'from "./app-elements.js"' in app
    assert 'from "./feedback-wiring.js"' in app
    assert "production-mode.js" not in app

def test_web_memory_workbench_declares_canvas_regions_and_states() -> None:
    html = _read_web_shell_source()
    app = _read_web_file("app.js")
    elements = _read_web_file("app-elements.js")
    renderer = _read_web_file("memory-workbench-render.js")
    studio_renderer = _read_web_file("memory-workbench-studio-render.js")
    controller = _read_web_file("memory-workbench-controller.js")
    demo_render = _read_web_file("memory-workbench-demo-render.js")
    checklist = _read_web_file("memory-workbench-demo-checklist.js")
    checklist_render = _read_web_file("memory-workbench-demo-checklist-render.js")
    demo_summary = _read_web_file("memory-workbench-demo-summary.js")
    inspector = _read_web_file("memory-workbench-inspector.js")
    feedback = _read_web_file("memory-workbench-feedback.js")
    sample = _read_web_file("memory-workbench-sample.js")
    adapter = _read_web_file("memory-workbench-package.js")
    package_refs = _read_web_file("memory-workbench-package-refs.js")
    fixture = _read_web_file("memory-workbench-fixture.js")
    css = (
        _read_web_file("memory-workbench.css")
        + _read_web_file("memory-workbench-layout.css")
        + _read_web_file("memory-workbench-canvas.css")
        + _read_web_file("memory-workbench-panels.css")
        + _read_web_file("memory-workbench-responsive.css")
    )
    demo_css = _read_web_file("memory-workbench-demo.css")
    studio_css = _read_web_file("memory-workbench-studio.css")
    combined = html + app + elements + renderer + studio_renderer + controller + demo_render + checklist + checklist_render + demo_summary + inspector + feedback + sample + adapter + package_refs + fixture + css + demo_css + studio_css

    for token in [
        "Memory Workbench",
        'memory-workbench.css?v=m4-memory-canvas-tools',
        'memory-workbench-demo.css?v=m4-memory-demo-summary',
        'memory-workbench-studio.css?v=m5-studio-canvas',
        "AgentFlow Studio Canvas",
        "RHTV",
        "LibTV",
        "Evidence-first",
        "Load -> Compare -> Feedback",
        "选择 Memory JSON",
        "Evidence Canvas",
        "Load sample bundle",
        "memory-sample-bundle",
        "memory-source-status",
        "memory-focus-summary",
        "memory-demo-summary",
        "memory-demo-checklist",
        "Demo-ready checklist",
        "Can present",
        "Evidence gaps",
        "Do not claim",
        "可讲内容",
        "待补缺口",
        "禁止宣称",
        "memoryStudioStatus",
        "renderStudioStatus",
        "memory-checklist-group",
        "memory-checklist-group-heading",
        "memory-checklist-group-items",
        "Operator Gate",
        "no execution",
        "Demo Evidence Summary",
        "talk track",
        "Same task, assets, route, duration, and storyboard are held constant.",
        "memory-protocol-summary",
        "Experiment Protocol",
        "Baseline parity protocol",
        "only memory context differs",
        "human acceptance",
        "memory-toolbar",
        "memory-view-button",
        "data-memory-view",
        "Flow",
        "Compare",
        "Operator Command Dock",
        "Brief -> Assets -> Memory -> Generate -> Compare -> Feedback",
        "memory-operator-dock",
        "memoryOperatorDock",
        "memory-operator-step",
        "renderOperatorDock",
        "local controls",
        "Sample bundle",
        "Selected files",
        "Artifact Inspector",
        "Feedback Draft",
        "memory-feedback-preview",
        "memory-feedback-output",
        "memory-feedback-copy",
        "memory-canvas",
        "memory-canvas-stage",
        "memory-provenance-panel",
        "memory-artifact-inspector",
        "memory-bundle-summary",
        "memory-action-strip",
        "Workflow Actions",
        "Load package",
        "Inspect evidence",
        "Compare lanes",
        "Capture feedback",
        "Prepare next pass",
        "dataset.focusTarget",
        "focus_targets",
        "focusMemoryInspector",
        "aria-pressed",
        "buildMemoryWorkbenchView",
        "attachMemoryWorkbenchHandlers",
        "memorySourceForArtifacts",
        "memory-run-timeline",
        "baseline-lane",
        "memory-lane",
        "Project",
        "Assets",
        "Memory Loaded",
        "Baseline Run",
        "Memory-backed Run",
        "Review",
        "Feedback",
        "Next Pass",
        "no plan",
        "planned",
        "generating",
        "review ready",
        "feedback captured",
        "memory candidate drafted",
        "promotion decision ready",
        "blocked",
        "renderMemoryWorkbench",
        "renderDemoEvidenceSummary",
        "renderDemoReadyChecklist",
        "buildDemoReadyChecklist",
        "buildDemoEvidenceSummary",
        "renderProtocolSummary",
        "buildMemoryWorkbenchPackageView",
        "buildMemoryArtifactInspector",
        "buildMemoryFeedbackDraft",
        "memoryWorkbenchSampleFiles",
        "Evidence Bundle",
        "agentflow_memory_video_pipeline_package",
        "draft_not_persisted",
        "browser_generated_only",
        "memoryWorkbenchFixture",
    ]:
        assert token in combined

def test_web_memory_workbench_studio_canvas_layout_is_low_friction() -> None:
    html = _read_web_shell_source()
    renderer = _read_web_file("memory-workbench-render.js")
    studio_renderer = _read_web_file("memory-workbench-studio-render.js")
    css = _read_web_file("memory-workbench-studio.css")
    combined = html + renderer + studio_renderer + css

    for token in [
        "memory-studio-header",
        "memory-studio-status",
        "memory-load-actions",
        "memory-primary-action",
        "memory-canvas-caption",
        "AgentFlow Studio Canvas",
        "Evidence-first",
        "Load -> Compare -> Feedback",
        "Local read-only",
        "选择 Memory JSON",
        "节点只负责聚焦证据，不启动模型、不写入记忆。",
        "--node-x",
        "--node-y",
        "grid-template-columns: repeat(7",
        "grid-template-rows: repeat(3",
    ]:
        assert token in combined

    for forbidden in [
        "dragstart",
        "drop",
        "localStorage",
        "fetch(",
        "WebSocket",
        "showSaveFilePicker",
    ]:
        assert forbidden not in combined

def test_web_memory_workbench_fixture_is_safe_and_memory_specific() -> None:
    fixture = _read_web_file("memory-workbench-fixture.js")

    for token in [
        "agentflow_memory_video_pipeline_package",
        "character_design_reference",
        "storyboard_adherence",
        "visual_consistency",
        "feedback_to_next_pass",
        "promotion_status",
        "request_projection",
        "source_evidence_refs",
    ]:
        assert token in fixture

    for forbidden in [
        "https://",
        "http://",
        "Authorization",
        "Bearer ",
        "api_key",
        "secret",
        "signed_url",
        "data:image/",
        "data/processed/runs/",
        "D:\\",
        "D:/",
        ".mp4",
        ".mov",
        ".webm",
        ".png",
        ".jpg",
        ".jpeg",
    ]:
        assert forbidden not in fixture

def test_web_memory_workbench_does_not_add_provider_or_persistence_paths() -> None:
    app = _read_web_file("app.js")
    workspace_render = _read_web_file("app-workspace-render.js")
    controller = _read_web_file("memory-workbench-controller.js")
    renderer = _read_web_file("memory-workbench-render.js")
    studio_renderer = _read_web_file("memory-workbench-studio-render.js")
    adapter = _read_web_file("memory-workbench-package.js")
    inspector = _read_web_file("memory-workbench-inspector.js")
    feedback = _read_web_file("memory-workbench-feedback.js")
    sample = _read_web_file("memory-workbench-sample.js")
    fixture = _read_web_file("memory-workbench-fixture.js")
    package_refs = _read_web_file("memory-workbench-package-refs.js")
    combined = app + workspace_render + controller + renderer + studio_renderer + adapter + package_refs + inspector + feedback + sample + fixture

    for forbidden in [
        "fetch(",
        "XMLHttpRequest",
        "WebSocket",
        "EventSource",
        "navigator.sendBeacon",
        "localStorage",
        "indexedDB",
        "document.cookie",
        "showSaveFilePicker",
        "createWritable",
        "FileSystemWritableFileStream",
    ]:
        assert forbidden not in combined

def test_web_memory_workbench_versions_parser_import_chain_for_browser_cache() -> None:
    app = _read_web_file("app.js")
    controller = _read_web_file("memory-workbench-controller.js")
    workspace = _read_web_file("artifact-workspace.js")
    ledgers = _read_web_file("artifact-ledgers.js")

    for source in [app, controller]:
        assert './artifact-workspace.js?v=m4-memory-canvas-tools' in source
    for source in [workspace, ledgers]:
        assert "?v=m4-memory-canvas-tools" in source
