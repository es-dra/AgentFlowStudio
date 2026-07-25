from __future__ import annotations

import json
import subprocess

from studio_static_helpers import STUDIO_ROOT


def test_canvas_m2_1_single_shell_structure_and_empty_state_contract() -> None:
    bootstrap = (STUDIO_ROOT / "src" / "studio-product-bootstrap.js").read_text(encoding="utf-8")
    shell = (STUDIO_ROOT / "src" / "product-shell.js").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    onboarding = (STUDIO_ROOT / "src" / "studio-canvas-onboarding.js").read_text(encoding="utf-8")
    panel = (STUDIO_ROOT / "src" / "agent-chat-panel.js").read_text(encoding="utf-8")
    safe_area = (STUDIO_ROOT / "src" / "canvas-safe-area.js").read_text(encoding="utf-8")
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")
    canvas = (STUDIO_ROOT / "src" / "canvas-view.js").read_text(encoding="utf-8")
    styles = (STUDIO_ROOT / "styles" / "product-shell.css").read_text(encoding="utf-8")

    for legacy_shell_id in ('id="topbar"', 'id="drawer"', 'id="inspector"', 'id="dock"', 'id="starter-row"', 'id="sprite-root"'):
        assert legacy_shell_id not in bootstrap
    assert 'id="canvas-root"' in bootstrap
    assert 'id="canvas-empty-hint"' in bootstrap
    assert 'class="canvas-empty-onboarding"' in bootstrap
    assert "输入想法" in bootstrap
    assert "导入剧本" in bootstrap
    assert "空白节点" in bootstrap
    assert "询问智能体" not in bootstrap
    assert 'data-empty-action="ask-agent"' not in bootstrap
    for fake_card in ("故事到关键帧", "角色设定卡", "首帧到视频", "视频片段复用"):
        assert fake_card not in bootstrap

    assert 'let section = "canvas";' in shell
    assert "studio-context-drawer" in shell
    assert "buildProjectDrawer()" in shell
    assert "if (section === \"storyboard\" && !emptyCanvas) shell.appendChild(buildSceneRail())" in shell
    assert "buildAgentChat()" in shell
    assert '"打开 Agent Chat"' not in shell
    assert "onResizeStart: bindAgentResize" in shell
    assert "Escape" in shell
    assert "afs:agent-chat-submit" in shell
    assert "afs:agent-chat-focus" in shell

    assert 'from "./studio-canvas-onboarding.js"' in main
    assert "bindCanvasEmptyOnboarding(store)" in main
    assert "`/idea ${text}`" in onboarding
    assert "importScriptFileIntoTextNode(store, node)" in onboarding
    assert 'createEmptyTextNode(store, "故事文本")' in onboarding
    assert "visibleCanvasCenter()" in onboarding
    assert "afs:canvas-safe-area-changed" in main

    assert "agent-resize-handle" in panel
    assert "raw_command_text" in panel
    assert "planStateLabel" in panel
    assert "\"待规划\"" in panel
    assert "planning_required" in panel
    assert 'evidenceDetails("诊断信息"' in panel
    assert 'el("summary", "", "项目与制作详情")' in panel
    assert "diffPreview(command.preview_diff)" in panel

    assert "startEmbeddedCreativeAction" in prompt_bar
    assert '"script_revision"' in prompt_bar
    assert '"shot_breakdown"' in prompt_bar
    assert "优化提示词" in prompt_bar
    assert "拆分分镜" in prompt_bar
    assert "/optimize-selected-default" not in prompt_bar
    assert "/plan-selected-script-shots" not in prompt_bar
    assert "expandTextIdeaToScript" not in prompt_bar
    assert "splitTextNodeToStoryboardNodes" not in prompt_bar
    assert "扩写剧本" not in prompt_bar
    assert "扩写当前文本" not in node_menu
    assert "拆分为分镜" not in node_menu
    assert 'data-role="run-action"' in canvas
    assert "runBtn.hidden = true;" in canvas

    assert ".studio-unified-workspace.storyboard-section" in styles
    assert ".studio-unified-workspace.agent-collapsed" in styles
    assert ".studio-unified-workspace.agent-mobile-open" in styles
    assert ".studio-context-drawer" in styles
    assert ".agent-resize-handle" in styles
    assert ".studio-unified-workspace:not(.agent-collapsed) .canvas-workspace-stage #canvas-empty-hint" in styles
    assert "grid-template-columns: minmax(0, 1fr) minmax(360px, var(--agent-chat-width, 392px));" in styles
    assert "@media (max-width: 1180px)" in styles
    assert "overflow: hidden" in styles
    assert ".studio-agent-chat" in safe_area
    assert ".studio-context-drawer" in safe_area


def test_agent_chat_text_optimization_command_fails_closed_without_template_mutation() -> None:
    script = r'''
import {
  agentChatContextKey,
  agentChatContextSnapshot,
  createAgentChatContextStore,
  submitAgentChatMessage,
} from "./apps/studio/src/agent-chat-lifecycle.js";

const oldDigest = "a".repeat(64);
const newDigest = "b".repeat(64);
const state = {
  meta: { projectId: "p1", projectName: "UX QA", canvasName: "Canvas", seq: 3 },
  nodes: {
    n1: {
      id: "n1",
      type: "text",
      title: "故事文本",
      content: "林夏在清晨的修理铺发现一台旧收音机，里面传来十年后的自己留下的求救信息。",
      prompt: "",
      status: "complete",
      params: {},
    },
  },
  edges: {},
  groups: {},
  order: ["n1"],
  assets: [],
  production: {
    script_core_truth_projection: {
      schema_version: "afs.script_core_truth.v0.1",
      project_id: "p1",
      current_revision_id: "rev_old",
      source_digest: oldDigest,
      analysis_state: "confirmed",
      asset_counts: { characters: 0, main_scenes: 0, manual_props: 0, auto_props: 0, style_assets: 0, action_event_assets: 0 },
      assets: [],
      revision_history: [{ revision_id: "rev_old", source_digest: oldDigest }],
    },
  },
  selection: { nodeIds: ["n1"], edgeId: null },
  ui: {},
};
const store = { get: () => state, set: (mutator) => mutator(state) };
const originalContent = state.nodes.n1.content;
const originalNodeCount = state.order.length;

const context = agentChatContextSnapshot({
  project: { project_id: "p1", name: "UX QA" },
  studioState: state,
  section: "canvas",
  selectedNode: state.nodes.n1,
});
const session = createAgentChatContextStore().get(agentChatContextKey(context));
const preview = submitAgentChatMessage(session, "/optimize-selected-default", context);
const instructedPreview = submitAgentChatMessage(session, "/optimize-selected 按用户要求压缩节奏并保留结尾", context);
const visibleRawCommandLeak = session.messages.some((message) => String(message.text || "").includes("/optimize-selected"));
process.stdout.write(JSON.stringify({
  previewStatus: preview.status,
  commandType: preview.command.command_type,
  title: preview.command.title,
  actionType: preview.command.action_type,
  mode: preview.command.mode,
  impactRelation: preview.command.impact.relation,
  rawCommandPreserved: preview.command.raw_command_text === "/optimize-selected-default",
  visibleRawCommandLeak,
  providerDispatchCount: preview.command.provider_dispatch_count,
  nodeCountAfterPreview: state.order.length,
  nodeIdentityPreserved: state.order.length === originalNodeCount,
  revisionCountAfterPreview: state.nodes.n1.params.revisions?.length || 0,
  contentChangedAfterPreview: state.nodes.n1.content !== originalContent,
  sourceIncludesTemplateHeading: String(preview.command.after_text || "").includes("核心意图"),
  errorMessage: preview.command.error_message || null,
  restoredContent: state.nodes.n1.content,
  instructedStatus: instructedPreview.status,
  instructedTitle: instructedPreview.command.title,
  hasLocalAfterText: Boolean(preview.command.after_text),
}));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    assert payload == {
        "previewStatus": "preview",
        "commandType": "start_embedded_creative_action",
        "title": "优化当前节点",
        "actionType": "script_revision",
        "mode": "professional_expansion",
        "impactRelation": "same_node_revision_preview",
        "rawCommandPreserved": True,
        "visibleRawCommandLeak": False,
        "providerDispatchCount": 0,
        "nodeCountAfterPreview": 1,
        "nodeIdentityPreserved": True,
        "revisionCountAfterPreview": 0,
        "contentChangedAfterPreview": False,
        "sourceIncludesTemplateHeading": False,
        "errorMessage": None,
        "restoredContent": "林夏在清晨的修理铺发现一台旧收音机，里面传来十年后的自己留下的求救信息。",
        "instructedStatus": "preview",
        "instructedTitle": "按要求优化当前节点",
        "hasLocalAfterText": False,
    }
