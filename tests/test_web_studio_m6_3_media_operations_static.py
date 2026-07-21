from __future__ import annotations

from studio_static_helpers import STUDIO_ROOT


def test_m6_3_media_operations_stays_inside_canvas_storyboard_shell() -> None:
    shell = (STUDIO_ROOT / "src" / "product-shell.js").read_text(encoding="utf-8")
    agent_chat = (STUDIO_ROOT / "src" / "agent-chat-panel.js").read_text(encoding="utf-8")
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    styles = (STUDIO_ROOT / "styles" / "product-shell.css").read_text(encoding="utf-8")
    controller = (STUDIO_ROOT / "src" / "studio-project-controller.js").read_text(encoding="utf-8")
    controller_policy = (STUDIO_ROOT / "src" / "studio-project-controller-policy.js").read_text(encoding="utf-8")
    startup = (STUDIO_ROOT / "src" / "studio-startup-project.js").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    store = (STUDIO_ROOT / "src" / "store.js").read_text(encoding="utf-8")

    assert 'viewButton("canvas", "画布")' in shell
    assert 'viewButton("storyboard", "故事板")' in shell
    assert 'section === "review"' not in shell
    assert "buildMediaOperationsContent()" in shell
    assert "production_media_operations" in shell
    assert "visible_in_same_studio_shell: true" in shell
    assert "mediaOperationsReady() ? \"media-operations-ready\"" in shell
    assert "activeProjectSummary" in shell
    assert "shouldLoadMediaOperations(project, activeProjectSummary)" in shell
    assert 'project_type || summary?.project_type || "") === "m6_2_paid_image_video_asset_reuse"' in shell
    assert "adaptiveCanvasOperations" in runtime_client
    assert "/adaptive-canvas-v2/operations-review" in runtime_client
    assert "previewAdaptiveCanvasOperation" in runtime_client
    assert "/adaptive-canvas-v2/operations/command-preview" in runtime_client
    assert ".media-operations-workspace" in styles
    assert ".media-evidence-drawer" in styles
    assert ".media-viewer video" in styles
    assert "isReadOnlyProjectionProject" in controller
    assert "isReadOnlyProjectionProject" in controller_policy
    assert "currentProjectIsReadOnlyProjection" in controller
    assert 'projectType === READ_ONLY_PROJECTION_PROJECT_TYPE' in controller_policy
    assert 'persistenceMode: readOnlyProjection ? "production_graph_read_only" : "studio_state"' in controller
    assert "hydrateStartupProject" in main
    assert "currentProjectIsReadOnlyProjection" in startup
    assert "createProjectReadyHandler" in main
    assert "export function createProjectReadyHandler" in startup
    assert "async function switchProject(projectId, runtime, options = {})" in store


def test_m6_3_read_only_evidence_startup_is_named_and_fail_closed() -> None:
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    startup = (STUDIO_ROOT / "src" / "studio-startup-project.js").read_text(encoding="utf-8")

    assert "hydrateStartupProject({" in main
    assert "await store.hydrateRuntime(runtime); await" not in main
    assert "export async function hydrateStartupProject" in startup
    assert 'store.setRuntimePersistenceMode?.("production_graph_read_only")' in startup
    assert "await store.hydrateRuntime(runtime)" in startup
    assert startup.index("currentProjectIsReadOnlyProjection") < startup.index("await store.hydrateRuntime(runtime)")


def test_m6_3_media_operations_copy_keeps_cost_recovery_and_nonclaim_boundaries() -> None:
    shell = (STUDIO_ROOT / "src" / "product-shell.js").read_text(encoding="utf-8")
    agent_chat = (STUDIO_ROOT / "src" / "agent-chat-panel.js").read_text(encoding="utf-8")

    for marker in (
        "确认前不会改动制作事实或产生费用",
        "确认前不会扣费",
        "重复提交不会重复生成或扣费",
        "重复提交保护已开启",
        "不会发起生成或产生费用",
        "不是人工验收、媒体商业质量验证或公开发布",
        "生成调用",
    ):
        assert marker in shell
    assert "媒体制作" in agent_chat
    assert "从已确认脚本、分镜和资产 Bible 只读投影" in agent_chat
    assert "idempotency_key" not in shell
    for forbidden in (
        "window.confirm(",
        "raw stdout",
        "signed_url",
        "api_key",
        "secondTruth",
        "card-stack",
    ):
        assert forbidden not in shell


def test_m6_3_owner_review_responsive_chat_and_title_contract() -> None:
    shell = (STUDIO_ROOT / "src" / "product-shell.js").read_text(encoding="utf-8")
    styles = (STUDIO_ROOT / "styles" / "product-shell.css").read_text(encoding="utf-8")
    topbar = (STUDIO_ROOT / "src" / "studio-topbar.js").read_text(encoding="utf-8")
    browser_qa = (STUDIO_ROOT.parent.parent / "tools" / "studio_m6_3_production_media_operations_browser_qa.py").read_text(encoding="utf-8")
    evaluator = (STUDIO_ROOT.parent.parent / "tools" / "evaluate_m6_3_production_media_operations_ux.py").read_text(encoding="utf-8")

    assert "function syncResponsiveAgentState" in shell
    assert "function setAgentChatExpanded" in shell
    assert "function closeResponsiveAgentOverlay" in shell
    assert "agent-responsive-compact" in shell
    assert "buildAgentMobileBackdrop" in shell
    assert "studio-current-project-summary" in shell
    assert "当前项目：" in shell
    assert "buildMediaShotSelector" in shell
    assert "media-shot-selector" in styles
    assert ".agent-mobile-backdrop" in styles
    assert "storyboard-section.agent-responsive-compact.agent-collapsed .studio-storyboard" in styles
    assert "width\": 390, \"height\": 844" in browser_qa
    assert "verify_responsive_agent_chat" in browser_qa
    assert "verify_project_title_discovery" in browser_qa
    assert "primary_review_unclipped" in browser_qa
    assert "phone_reviewer_flow" in evaluator
    assert "project_title_discoverable" in evaluator
    assert "\"P2\": p2_open" in evaluator
    assert "title.setAttribute(\"aria-label\", `当前项目：" in topbar
