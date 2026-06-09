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
    WORKBENCH_ROOT / "src" / "display-labels.js",
    WORKBENCH_ROOT / "src" / "app-selection.js",
    WORKBENCH_ROOT / "src" / "app-actions.js",
    WORKBENCH_ROOT / "src" / "input-sync.js",
    WORKBENCH_ROOT / "src" / "polling.js",
    WORKBENCH_ROOT / "src" / "command-hub-state.js",
    WORKBENCH_ROOT / "src" / "project-hub-state.js",
    WORKBENCH_ROOT / "src" / "creation-workspace-state.js",
    WORKBENCH_ROOT / "src" / "memory-workspace-state.js",
    WORKBENCH_ROOT / "src" / "operations-workspace-state.js",
    WORKBENCH_ROOT / "src" / "studio-workspace-state.js",
    WORKBENCH_ROOT / "src" / "activity-state.js",
    WORKBENCH_ROOT / "src" / "production-board-state.js",
    WORKBENCH_ROOT / "src" / "readiness-state.js",
    WORKBENCH_ROOT / "src" / "state.js",
    WORKBENCH_ROOT / "src" / "workspace-config.js",
    WORKBENCH_ROOT / "src" / "workbench-state.js",
    WORKBENCH_ROOT / "src" / "render-actions.js",
    WORKBENCH_ROOT / "src" / "render-command-hub.js",
    WORKBENCH_ROOT / "src" / "render-project-hub.js",
    WORKBENCH_ROOT / "src" / "render-review-workspace.js",
    WORKBENCH_ROOT / "src" / "render-style-memory-workspace.js",
    WORKBENCH_ROOT / "src" / "render-operations-workspace.js",
    WORKBENCH_ROOT / "src" / "render-studio-canvas.js",
    WORKBENCH_ROOT / "src" / "render-studio-inspector.js",
    WORKBENCH_ROOT / "src" / "render-studio-side-rail.js",
    WORKBENCH_ROOT / "src" / "render-studio-workspace.js",
    WORKBENCH_ROOT / "src" / "render-storyboard-workspace.js",
    WORKBENCH_ROOT / "src" / "render-activity.js",
    WORKBENCH_ROOT / "src" / "render-production-board.js",
    WORKBENCH_ROOT / "src" / "render-assets.js",
    WORKBENCH_ROOT / "src" / "render-artifact.js",
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
        WORKBENCH_ROOT / "styles-app-shell.css",
        WORKBENCH_ROOT / "styles-components.css",
        WORKBENCH_ROOT / "styles-command-hub.css",
        WORKBENCH_ROOT / "styles-project-hub.css",
        WORKBENCH_ROOT / "styles-project-setup.css",
        WORKBENCH_ROOT / "styles-assets.css",
        WORKBENCH_ROOT / "styles-creation-workspace.css",
        WORKBENCH_ROOT / "styles-studio-workspace.css",
        WORKBENCH_ROOT / "styles-studio-canvas-v2.css",
        WORKBENCH_ROOT / "styles-studio-canvas-focus.css",
        WORKBENCH_ROOT / "styles-storyboard.css",
        WORKBENCH_ROOT / "styles-review-memory.css",
        WORKBENCH_ROOT / "styles-activity.css",
        WORKBENCH_ROOT / "styles-operations.css",
        WORKBENCH_ROOT / "styles-production-board.css",
        WORKBENCH_ROOT / "styles-readiness.css",
        WORKBENCH_ROOT / "styles-workflow.css",
        *WORKBENCH_JS,
    ]
    return "\n".join(_read(path) for path in files)
def test_workbench_shell_targets_runtime_service_contract() -> None:
    index = _read(WORKBENCH_ROOT / "index.html")
    source = _all_workbench_source()

    assert '<script type="module" src="./src/app.js?v=stage7-rc"></script>' in index
    assert '<html lang="zh-CN">' in index
    assert '<link rel="stylesheet" href="./styles-app-shell.css" />' in index
    assert '<link rel="stylesheet" href="./styles-components.css" />' in index
    assert '<link rel="stylesheet" href="./styles-command-hub.css" />' in index
    assert '<link rel="stylesheet" href="./styles-project-hub.css" />' in index
    assert '<link rel="stylesheet" href="./styles-project-setup.css" />' in index
    assert '<link rel="stylesheet" href="./styles-assets.css" />' in index
    assert '<link rel="stylesheet" href="./styles-creation-workspace.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-canvas-v2.css" />' in index
    assert '<link rel="stylesheet" href="./styles-studio-canvas-focus.css" />' in index
    assert '<link rel="stylesheet" href="./styles-storyboard.css" />' in index
    assert '<link rel="stylesheet" href="./styles-review-memory.css" />' in index
    assert '<link rel="stylesheet" href="./styles-activity.css" />' in index
    assert '<link rel="stylesheet" href="./styles-operations.css" />' in index
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

    for retired in ["render-jobs.js", "render-creation-workspace.js", "render-memory-workspace.js"]:
        assert not (WORKBENCH_ROOT / "src" / retired).exists()
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

    for pattern in [".innerHTML", "insertAdjacentHTML", "throw new Error(body"]:
        assert pattern not in js_source
    assert "运行服务请求失败" in js_source and "无法解析的 JSON" in js_source
    assert 'el("details", { className: "advanced" }' in js_source
    assert "visible_by_default" in source
    assert "feedback_is_memory: false" in source
    assert "safe summaries" in source
    assert all(marker in source for marker in ["STATUS_MAP[value]", "Add project materials before running a real generation pass."])
    assert all(marker in source.lower() for marker in ["content card", "filmstrip"])
    for marker in [
        "生成画布草稿", "draft-canvas", "项目设置向导", "创作画布", "分镜台",
        "素材库", "审片室", "项目记忆", "任务中心", "诊断", "产品发布", "脚本提纲",
        "素材准备", "运行首轮检查", "非人工验收",
        "project_hub", "studio_workspace", "creation_workspace", "memory_workspace",
        "operations_workspace", "project_readiness", "production_board", "command_hub",
        "reference-grid", "variant-grid", "job-progress", "activity_timeline",
        "studio-canvas-toolbar", "studio-node-flow", "studio-node-connector",
        "studio-media-frame", "studio-node-preview", "studio-inspector-hero",
        "studio-inspector-facts", "studio-empty-flow", "asset-groups",
        "asset-next-actions", "asset-empty-state", "storyboard-workspace",
        "storyboard-strip", "storyboard-preview", "storyboard-inspector",
        "review-workspace", "review-candidate-strip", "review-decision-dock",
        "style-memory-workspace", "style-preference-board", "style-next-round-panel",
        "set-review-intent",
        "candidateSummary(candidate)", "isEnglishFallback", "查看证据",
        "selected_card_id", "selected_candidate_id", "selected_job_id",
        "viewActionGroups", "configureJobPolling", "自动刷新", "保存检查器",
        "inspector-prompt", "reusable_preferences", "next_pass_usage",
        "保留方向", "标记修改", "拒绝候选", "record-review-decision",
    ]:
        assert marker in source
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
    assert "source.operations_workspace" in source
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
    workspace_config = _read(WORKBENCH_ROOT / "src" / "workspace-config.js")
    projects_block = render.split('if (activeView === "Projects") {', 1)[1].split('if (activeView === "Assets")', 1)[0]; assets_block = render.split('if (activeView === "Assets") {', 1)[1].split('if (activeView === "Storyboard")', 1)[0]; settings_block = render.split('if (activeView === "Settings") {', 1)[1].split('return withWindow("Create"', 1)[0]
    style_memory_block = render.split('if (activeView === "Style Memory") {', 1)[1].split('if (activeView === "Jobs")', 1)[0]
    jobs_block = render.split('if (activeView === "Jobs") {', 1)[1].split('if (activeView === "Settings")', 1)[0]

    assert 'activeView: "Projects"' in state_source
    assert "state.activeView = node.dataset.view" in app
    assert "function syncProjectInputs(projectId)" in app and "state.projectId = state.lastResult.project_id || state.projectId" in _read(WORKBENCH_ROOT / "src" / "app-actions.js")
    assert all(marker in app for marker in ["function selectAvailableProject()", "function preferredProject(projects)", 'project.status === "ready_for_next_round" ? 10000'])
    assert "run(refreshWorkbench);" in app
    assert 'root.querySelectorAll("#project-id-action, #project-id")' in app
    assert "syncProjectInputs(state.projectId)" in app
    assert "workspaceItems(items)" in render
    assert "viewActionGroups" in render
    assert "renderActionPanel(state, viewActionGroups(activeView))" in render
    assert projects_block.index("renderProjectHub") < projects_block.index("...common")
    assert assets_block.index("renderAssetLibrary") < assets_block.index("...common")
    assert "renderProjectReadiness" not in settings_block and "...common" not in settings_block
    assert "renderStudioWorkspace(workbench.studio_workspace, state)" in render
    assert "renderStoryboardWorkspace(workbench.studio_workspace, workbench.creation_workspace, state)" in render
    assert "renderReviewWorkspace(workbench.review_room, workbench.memory_workspace, state)" in render
    assert "renderStyleMemoryWorkspace(workbench.style_memory, workbench.memory_workspace)" in render
    assert "renderActivityTimeline" not in style_memory_block
    assert "renderOperationsWorkspace(workbench.operations_workspace)" in render
    for retired in ["renderMemoryWorkspace", "renderJobCenter", "renderCreationWorkspace"]:
        assert retired not in render
    assert "...common" not in jobs_block
    assert '"set-review-intent": () =>' in app
    assert "state.selectedVariantId = dataset.variantId || state.selectedVariantId" in app
    assert all(marker in actions for marker in ["function projectTitle(project)", "project.goal || project.project_type"]) and 'el("strong", { text: project.project_id || "project" })' not in actions
    assert 'id: "Storyboard"' in workspace_config
    assert 'label: "项目记忆"' in workspace_config
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
    assert "JSON 详情" in source
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
        WORKBENCH_ROOT / "styles-app-shell.css",
        WORKBENCH_ROOT / "styles-components.css",
        WORKBENCH_ROOT / "styles-project-setup.css",
        WORKBENCH_ROOT / "styles-assets.css",
        WORKBENCH_ROOT / "styles-studio-canvas-v2.css",
        WORKBENCH_ROOT / "styles-studio-canvas-focus.css",
        WORKBENCH_ROOT / "styles-storyboard.css",
        WORKBENCH_ROOT / "styles-review-memory.css",
        WORKBENCH_ROOT / "styles-activity.css",
        WORKBENCH_ROOT / "styles-operations.css",
        WORKBENCH_ROOT / "styles-readiness.css",
        WORKBENCH_ROOT / "styles-workflow.css",
        *WORKBENCH_JS,
    ]:
        lines = _read(path).splitlines()
        assert len(lines) <= 300, path

def test_workbench_uses_multi_tone_product_palette() -> None:
    css = _read(WORKBENCH_ROOT / "styles.css") + _read(WORKBENCH_ROOT / "styles-components.css") + _read(WORKBENCH_ROOT / "styles-app-shell.css")

    assert all(token in css for token in ["--accent: #1f6f5b", "--accent-2: #b45b39", "--ready: #315f99", "--blocked: #a83b32"])
    assert all(token in css for token in ["height: 100vh", "overflow: hidden", "overflow-y: auto", "overscroll-behavior: contain"])


def test_workbench_javascript_syntax() -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not available")

    for path in WORKBENCH_JS:
        subprocess.run([node, "--check", str(path)], check=True)
