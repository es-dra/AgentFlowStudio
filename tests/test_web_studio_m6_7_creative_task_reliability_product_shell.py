from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_m6_7_split_label_and_node_running_feedback_contract() -> None:
    canvas = _read("apps/studio/src/canvas-view.js")
    prompt = _read("apps/studio/src/prompt-bar.js")
    lifecycle = _read("apps/studio/src/agent-chat-lifecycle.js")
    node_css = _read("apps/studio/styles/canvas-node-text.css")

    creator_sources = "\n".join([canvas, prompt, lifecycle])
    assert "自动拆分分镜" not in creator_sources
    assert "拆分分镜" in canvas
    assert "拆分分镜" in prompt
    assert 'title: "拆分分镜"' in lifecycle
    assert '"shot_breakdown"' in prompt
    assert '"dynamic_shot_breakdown"' in prompt

    assert "embedded-task-running" in canvas
    assert "dataset.embeddedTaskState" in canvas
    assert "dataset.embeddedTaskAction" in canvas
    assert "is-busy" in canvas
    assert "分镜任务生成中" in canvas

    assert ".node.embedded-task-running::after" in node_css
    assert "@keyframes embeddedTaskPerimeterSweep" in node_css
    assert "--embedded-task-angle" in node_css
    assert "conic-gradient" in node_css
    assert "transform: rotate" not in node_css
    assert "prefers-reduced-motion: reduce" in node_css


def test_m6_7_product_shell_project_account_menu_contract() -> None:
    shell = _read("apps/studio/src/product-shell.js")
    main = _read("apps/studio/src/main.js")
    css = _read("apps/studio/styles/product-shell.css")
    embedded = _read("apps/studio/src/embedded-creative-actions.js")

    assert 'src="./favicon.svg"' in shell
    assert "studio-brand-logo" in shell
    assert "studio-stage-button" not in shell
    assert "projectDrawerOpen = !projectDrawerOpen" not in shell

    assert "studio-project-switch-list" in shell
    assert "studio-project-search" in shell
    assert "studio-project-create" in shell
    assert "studio-project-settings" in shell
    assert "studio-project-delete" in shell
    assert "options.onDeleteProject?.(snapshot.project)" in shell
    assert "onDeleteProject" in main
    assert "projectController?.deleteProject(project)" in main
    assert "filterProjectMenu" in shell

    assert 'window.addEventListener("pointerdown"' in shell
    assert ".studio-project-context" in shell
    assert ".studio-account-context" in shell
    assert ".studio-help-context" in shell
    assert "accountMenuOpen = false" in shell
    assert "mobileAgentOpen || helpOpen || accountMenuOpen" in shell

    assert "studio-live-notice" not in shell
    assert "studio-header-notice" in shell
    assert "studio-header-notice" in css
    assert "studio-account-identity" in css
    assert "grid-template-columns: auto minmax(180px, 280px) 276px minmax(120px, 1fr) auto" in css
    assert "grid-template-columns: minmax(0, 1fr) auto" in css
    assert ".studio-header-actions .studio-account-context" in css
    assert ".studio-account-menu" in css and "position: fixed" in css
    assert "--z-shell-header: 90" in css
    assert "z-index: 96" in css

    open_task_handler = shell.split('window.addEventListener("afs:agent-chat-open-task"', 1)[1].split("});", 1)[0]
    assert "setAgentChatExpanded(true)" in open_task_handler
    assert "当前节点任务已开始" not in open_task_handler
    finished_task_handler = shell.split('window.addEventListener("afs:embedded-creative-task-finished"', 1)[1].split("});", 1)[0]
    assert "isNarrowAgentLayout()" in finished_task_handler
    assert "closeResponsiveAgentOverlay()" in finished_task_handler
    assert 'dispatchBrowserEvent("afs:embedded-creative-task-finished"' in embedded
    assert 'status: "cancelled"' in embedded
    assert 'status: "applied"' in embedded


def test_m6_7_1_visual_correction_contract() -> None:
    shell = _read("apps/studio/src/product-shell.js")
    main = _read("apps/studio/src/main.js")
    embedded = _read("apps/studio/src/embedded-creative-actions.js")
    panel = _read("apps/studio/src/agent-chat-panel.js")
    node_css = _read("apps/studio/styles/canvas-node-text.css")
    css = _read("apps/studio/styles/product-shell.css")

    assert "shotCandidateLayout" in embedded
    assert "layout_role: \"scene_lane\"" in embedded
    assert "layout_role: \"shot_grid_item\"" in embedded
    assert "frameCandidateSubgraph" in embedded
    assert "__afsSuppressNextSafeAreaFit" in embedded
    assert "nodesBounds" in embedded
    assert "layout_column" in embedded and "layout_row" in embedded

    assert "__afsSuppressNextSafeAreaFit" in main
    assert "fitCanvasProjection(state)" in main

    assert "hasCanvasContent()" in shell
    assert "if (existingCanvas && !planningPanelOpen) return buildInlinePlanAction(status)" in shell
    assert "buildInlinePlanAction" in shell
    assert "planning-required ${existingCanvas ? \"contextual\" : \"empty-entry\"}" in shell
    assert ".graph-canvas-status.planning-required.contextual-inline" in css
    assert "notice = \"当前节点任务已开始" not in shell

    assert "taskStatePhaseSummary" in panel
    assert "ordered.includes(phase)" in panel

    assert "embeddedTaskPerimeterSweep" in node_css
    assert "embeddedTaskPerimeterRotate" not in node_css
    assert "transform: none" in node_css
    assert "inset: -3px" in node_css


def test_m6_7_3_embedded_creative_failure_recovery_contract() -> None:
    embedded = _read("apps/studio/src/embedded-creative-actions.js")
    panel = _read("apps/studio/src/agent-chat-panel.js")
    body = _read("apps/studio/src/canvas-node-body.js")
    lifecycle = _read("apps/studio/src/agent-chat-lifecycle.js")
    task_contract = _read("apps/studio/src/creative-task-contract.js")

    assert "failureFromPreviewResponse" in embedded
    assert "normalizeFailurePayload" in embedded
    assert "action.provider_lineage = { provider_calls_started: false }" not in embedded
    assert "provider_dispatch_count" in embedded
    assert "stale_node_version" in embedded

    assert "syncEmbeddedCreativeAssistantMessages" in panel
    assert "结果会在当前任务区审阅" in panel
    assert "重新预览" in panel
    assert "重新生成" not in panel.split("function currentTaskActions", 1)[1].split("function screenplayReview", 1)[0]
    assert "creativeActionFailureInfo(action)" in panel
    assert "aria-live" in panel and 'role", "status"' in panel

    unavailable_panel = body.split('if (action.status === "unavailable")', 1)[1].split('if (action.status === "preview")', 1)[0]
    assert "creativeActionFailureInfo(action)" in unavailable_panel
    assert "请在 AI 创作搭档中重新预览。" in unavailable_panel
    assert "retry: true" not in unavailable_panel

    assert "selected_screenplay_summary" in lifecycle
    assert "screenplaySummaryForNode" in lifecycle
    assert "isSceneContextNode" in lifecycle
    assert "m6_6_scene_candidate" in lifecycle
    assert "m6_6_shot_candidate" in lifecycle
    assert "creativeActionFailureInfo" in task_contract
    assert "error_detail" in task_contract


def test_m6_7_3_creative_task_failure_info_is_safe_and_actionable() -> None:
    script = """
      import assert from "node:assert/strict";
      import { creativeActionFailureInfo, failCreativeTask, normalizeCreativeTask } from "./apps/studio/src/creative-task-contract.js";

      const base = normalizeCreativeTask({
        task_id: "task_1",
        node_id: "story_text",
        node_version: "story_text:text:42:node_revision_1",
        action_type: "shot_breakdown",
        state: "running",
        phase: "dispatching"
      });
      const failed = failCreativeTask(base, "provider_output_validation", {
        error_owner: "provider_output_validation",
        error_detail: "schema failed at /opt/private/raw-response.json"
      });
      const info = creativeActionFailureInfo({
        action_type: "shot_breakdown",
        creative_task: failed,
        graph_mutation: { mutated: false, scope: "preview_only" }
      });

      assert.equal(failed.error_category, "provider_output_validation");
      assert.equal(failed.error_owner, "provider_output_validation");
      assert.match(failed.error_detail, /<local-path-redacted>/);
      assert.equal(info.label, "AI 输出结构未通过校验");
      assert.match(info.preserved_state, /ProductionGraph 未改变/);
      assert.match(info.next_action, /重新预览分镜/);
    """
    subprocess.run(["node", "--input-type=module", "-e", script], cwd=ROOT, check=True)


def test_m6_7_2_readable_shot_graph_and_nonempty_shell_contract() -> None:
    embedded = _read("apps/studio/src/embedded-creative-actions.js")
    edges = _read("apps/studio/src/canvas-edges.js")
    edge_buttons = _read("apps/studio/src/canvas-edge-relation-buttons.js")
    view = _read("apps/studio/src/canvas-view.js")
    node_css = _read("apps/studio/styles/canvas-node-text.css")
    shell = _read("apps/studio/src/product-shell.js")
    css = _read("apps/studio/styles/product-shell.css")

    assert "const columns = narrow ? 1 : 3" in embedded
    assert "const rowGap = narrow ? 64 : 80" in embedded
    assert "const targetScale = clampScale(0.86)" in embedded
    assert "first_shot_node_id" in embedded
    assert "suppressLabel: true" in embedded
    assert "compactShotText" in embedded

    assert 'edge.suppress_label === true ? "" : relationLabel(relation)' in edges
    assert "edge.suppress_label === true" in edge_buttons
    assert "shot-candidate-card" in view and "scene-candidate-lane" in view
    assert ".node.shot-candidate-card .text-content-view" in node_css

    assert "buildInlinePlanAction" in shell
    assert "从一个想法开始" in shell
    assert "可自由开始" not in shell
    assert "contextual-inline" in css
    assert "plan-inline-action" in css
