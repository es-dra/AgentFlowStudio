from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


WORKBENCH_ROOT = Path("apps/workbench")
WORKBENCH_JS = [
    WORKBENCH_ROOT / "src" / "dom.js",
    WORKBENCH_ROOT / "src" / "runtime-client.js",
    WORKBENCH_ROOT / "src" / "presets.js",
    WORKBENCH_ROOT / "src" / "app-selection.js",
    WORKBENCH_ROOT / "src" / "app-actions.js",
    WORKBENCH_ROOT / "src" / "input-sync.js",
    WORKBENCH_ROOT / "src" / "polling.js",
    WORKBENCH_ROOT / "src" / "command-hub-state.js",
    WORKBENCH_ROOT / "src" / "project-hub-state.js",
    WORKBENCH_ROOT / "src" / "creation-workspace-state.js",
    WORKBENCH_ROOT / "src" / "memory-workspace-state.js",
    WORKBENCH_ROOT / "src" / "activity-state.js",
    WORKBENCH_ROOT / "src" / "production-board-state.js",
    WORKBENCH_ROOT / "src" / "readiness-state.js",
    WORKBENCH_ROOT / "src" / "state.js",
    WORKBENCH_ROOT / "src" / "workbench-state.js",
    WORKBENCH_ROOT / "src" / "render-actions.js",
    WORKBENCH_ROOT / "src" / "render-command-hub.js",
    WORKBENCH_ROOT / "src" / "render-project-hub.js",
    WORKBENCH_ROOT / "src" / "render-creation-workspace.js",
    WORKBENCH_ROOT / "src" / "render-memory-workspace.js",
    WORKBENCH_ROOT / "src" / "render-activity.js",
    WORKBENCH_ROOT / "src" / "render-production-board.js",
    WORKBENCH_ROOT / "src" / "render-assets.js",
    WORKBENCH_ROOT / "src" / "render-artifact.js",
    WORKBENCH_ROOT / "src" / "render-jobs.js",
    WORKBENCH_ROOT / "src" / "render-readiness.js",
    WORKBENCH_ROOT / "src" / "render.js",
    WORKBENCH_ROOT / "src" / "app.js",
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _all_workbench_source() -> str:
    files = [
        WORKBENCH_ROOT / "README.md",
        WORKBENCH_ROOT / "index.html",
        WORKBENCH_ROOT / "styles.css",
        WORKBENCH_ROOT / "styles-components.css",
        WORKBENCH_ROOT / "styles-command-hub.css",
        WORKBENCH_ROOT / "styles-project-hub.css",
        WORKBENCH_ROOT / "styles-creation-workspace.css",
        WORKBENCH_ROOT / "styles-activity.css",
        WORKBENCH_ROOT / "styles-production-board.css",
        WORKBENCH_ROOT / "styles-readiness.css",
        WORKBENCH_ROOT / "styles-workflow.css",
        *WORKBENCH_JS,
    ]
    return "\n".join(_read(path) for path in files)


def test_workbench_shell_targets_runtime_service_contract() -> None:
    index = _read(WORKBENCH_ROOT / "index.html")
    source = _all_workbench_source()

    assert '<script type="module" src="./src/app.js"></script>' in index
    assert '<link rel="stylesheet" href="./styles-components.css" />' in index
    assert '<link rel="stylesheet" href="./styles-command-hub.css" />' in index
    assert '<link rel="stylesheet" href="./styles-project-hub.css" />' in index
    assert '<link rel="stylesheet" href="./styles-creation-workspace.css" />' in index
    assert '<link rel="stylesheet" href="./styles-activity.css" />' in index
    assert '<link rel="stylesheet" href="./styles-production-board.css" />' in index
    assert '<link rel="stylesheet" href="./styles-readiness.css" />' in index
    assert '<link rel="stylesheet" href="./styles-workflow.css" />' in index
    assert "http://127.0.0.1:8790" in source
    for endpoint in [
        "/health",
        "/capabilities",
        "/projects",
        "/source-assets",
        "/content-cards",
        "/canvas-draft",
        "/scene-inspector",
        "/review-decisions",
        "/workbench-state",
        "/runs/asset-test",
        "/feedback",
    ]:
        assert endpoint in source
    assert "/runs/two-round-validate" in source
    assert "/provider/validation-plan" in source
    assert "/artifacts/" in source
    assert "createRuntimeClient" in source
    assert "normalizeWorkbenchState" in source


def test_workbench_keeps_frontend_safety_boundary() -> None:
    source = _all_workbench_source()
    js_source = "\n".join(_read(path) for path in WORKBENCH_JS)

    forbidden_patterns = [
        "localStorage",
        "indexedDB",
        "showSaveFilePicker",
        "createWritable",
        "OPENAI_API_KEY",
        "AFS_OPENAI_API_KEY",
        "data/processed/runs",
        "D:\\",
        "C:\\",
        "provider_config",
        "signed_urls",
    ]
    for pattern in forbidden_patterns:
        assert pattern not in source

    for runtime_only_pattern in ["apps.cli", "web_bridge"]:
        assert runtime_only_pattern not in js_source

    assert ".innerHTML" not in js_source
    assert "insertAdjacentHTML" not in js_source
    assert 'el("details", { className: "advanced" }' in js_source
    assert "visible_by_default" in source
    assert "feedback_is_memory: false" in source
    assert "safe summaries" in source
    assert "content card" in source.lower()
    assert "filmstrip" in source.lower()
    assert "Draft Canvas" in source
    assert "draft-canvas" in source
    assert "Reference Library" in source
    assert "reference-grid" in source
    assert "apply-project-template" in source
    assert "apply-source-preset" in source
    assert "Product Launch" in source
    assert "Script outline" in source
    assert "Review Room" in source
    assert "variant-grid" in source
    assert "Job Center" in source
    assert "job-progress" in source
    assert "Activity Timeline" in source
    assert "activity_timeline" in source
    assert "activity-row" in source
    assert "Production Board" in source
    assert "production_board" in source
    assert "production-lane" in source
    assert "Command Hub" in source
    assert "command_hub" in source
    assert "command-card" in source
    assert "primary_command" in source
    assert "requires_input" in source
    assert "Project Hub" in source
    assert "project_hub" in source
    assert "project-hub-panel" in source
    assert "project-metric-grid" in source
    assert "recent_jobs" in source
    assert "Creation Workspace" in source
    assert "creation_workspace" in source
    assert "creation-canvas" in source
    assert "creation-inspector" in source
    assert "creation-run-controls" in source
    assert "creation-filmstrip" in source
    assert "selected_card_id" in source
    assert "selectedCardIdFor" in source
    assert "state.selectedCardId" in source
    assert "Memory Workspace" in source
    assert "memory_workspace" in source
    assert "memory-controls" in source
    assert "memory-profile-panel" in source
    assert "selected_candidate_id" in source
    assert "Project Readiness" in source
    assert "project_readiness" in source
    assert "current_action_label" in source
    assert "readiness-step" in source
    assert "activeView" in source
    assert "data-view" in source
    assert "viewActionGroups" in source
    assert "configureJobPolling" in source
    assert "auto refresh" in source
    assert "Save Inspector" in source
    assert "inspector-prompt" in source
    assert "reusable_preferences" in source
    assert "next_pass_usage" in source
    assert "keep / revise / reject" in source
    assert "record-review-decision" in source
    assert "ref_kind" not in js_source
    assert "provider_config" not in js_source


def test_workbench_normalizes_backend_state_shape() -> None:
    source = _read(WORKBENCH_ROOT / "src" / "workbench-state.js")

    assert "source.cards" in source
    assert "source.asset_library" in source
    assert "source.filmstrip" in source
    assert "source.style_memory" in source
    assert "source.review_room" in source
    assert "source.job_center" in source
    assert "source.activity_timeline" in source
    assert "source.production_board" in source
    assert "source.command_hub" in source
    assert "source.project_hub" in source
    assert "source.creation_workspace" in source
    assert "source.memory_workspace" in source
    assert "source.project_readiness" in source
    assert "source.inspector" in source
    assert "source.card_id" in source
    assert "source.primary_artifact_id" in source
    assert "evidence.artifact_ids" in source
    assert "source.event_id" in source


def test_workbench_navigation_drives_stage_views() -> None:
    app = _read(WORKBENCH_ROOT / "src" / "app.js")
    render = _read(WORKBENCH_ROOT / "src" / "render.js")
    actions = _read(WORKBENCH_ROOT / "src" / "render-actions.js")
    state_source = _read(WORKBENCH_ROOT / "src" / "state.js")

    assert 'activeView: "Create"' in state_source
    assert "state.activeView = node.dataset.view" in app
    assert "renderNav(state.workbench ? state.workbench.navigation : [], state.activeView)" in render
    assert "viewActionGroups" in render
    assert "renderActionPanel(state, viewActionGroups(activeView))" in render
    assert "renderProjectHub(workbench.project_hub)" in render
    assert "renderCreationWorkspace(workbench.creation_workspace, state)" in render
    assert "renderMemoryWorkspace(workbench.memory_workspace, state)" in render
    assert "groups.includes(\"project\")" in actions
    assert "groups.includes(\"runtime\")" in actions


def test_workbench_renders_artifact_specific_report_views() -> None:
    source = _read(WORKBENCH_ROOT / "src" / "render-artifact.js")

    for artifact_type in [
        "agentflow_project_manifest",
        "agentflow_real_asset_test_report",
        "agentflow_two_round_context_runtime_report",
        "agentflow_runtime_feedback_event",
        "agentflow_runtime_review_decision",
        "agentflow_provider_safe_manifest",
    ]:
        assert artifact_type in source
    assert "JSON Detail" in source
    assert "provider_calls_started" in source
    assert "writes_long_term_memory" in source


def test_workbench_artifact_ref_buttons_use_registered_handler() -> None:
    app = _read(WORKBENCH_ROOT / "src" / "app.js")

    assert "data-action='open-artifact-ref'" in app
    assert "state.selectedArtifactId = node.dataset.artifactId" in app
    assert 'run(actionHandlers["open-selected-artifact"])' in app
    assert "run(openSelectedArtifact)" not in app


def test_workbench_files_stay_below_maintenance_threshold() -> None:
    for path in [
        WORKBENCH_ROOT / "styles.css",
        WORKBENCH_ROOT / "styles-components.css",
        WORKBENCH_ROOT / "styles-activity.css",
        WORKBENCH_ROOT / "styles-readiness.css",
        WORKBENCH_ROOT / "styles-workflow.css",
        *WORKBENCH_JS,
    ]:
        lines = _read(path).splitlines()
        assert len(lines) <= 300, path


def test_workbench_uses_multi_tone_product_palette() -> None:
    css = _read(WORKBENCH_ROOT / "styles.css") + _read(WORKBENCH_ROOT / "styles-components.css")

    assert "--accent: #1f6f5b" in css
    assert "--accent-2: #b45b39" in css
    assert "--ready: #315f99" in css
    assert "--blocked: #a83b32" in css


def test_workbench_javascript_syntax() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available")

    for path in WORKBENCH_JS:
        subprocess.run([node, "--check", str(path)], check=True)
