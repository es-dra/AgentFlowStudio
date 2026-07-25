from __future__ import annotations

import json
import subprocess

from studio_static_helpers import STUDIO_ROOT


def test_m1_topology_defaults_to_canvas_and_keeps_storyboard_read_only_deferred() -> None:
    shell = (STUDIO_ROOT / "src" / "product-shell.js").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    lifecycle = (STUDIO_ROOT / "src" / "agent-chat-lifecycle.js").read_text(encoding="utf-8")
    styles = (STUDIO_ROOT / "styles" / "product-shell.css").read_text(encoding="utf-8")

    assert 'let section = "canvas";' in shell
    assert shell.index('viewButton("canvas", "画布")') < shell.index('viewButton("storyboard", "故事板")')
    assert "productShell?.showCanvas();" in main
    assert "buildAgentChatPanel" in shell
    assert "buildAgentChat()" in shell
    assert "studio-agent-chat" in styles
    assert "studio-unified-workspace.canvas-empty-project" in styles
    assert "0 场景 · 0 镜头 · 尚未创建故事事实" in shell
    panel = (STUDIO_ROOT / "src" / "agent-chat-panel.js").read_text(encoding="utf-8")
    assert "agent-current-context" in panel
    assert "正在制作" in panel
    assert "agent-context-chip" not in panel
    assert 'storyboard_mode: "read_only_deferred"' in lifecycle
    assert 'context?.section === "storyboard_read_only"' in lifecycle
    assert "故事板当前只读取画布确认后的事实" in shell
    assert "FALLBACK_SCENES" not in shell
    for forbidden in ("巷口", "雨巷", "老宅", "4×15", "4x15"):
        assert forbidden not in shell + lifecycle


def test_agent_chat_panel_is_not_static_and_executes_confirmed_canvas_commands() -> None:
    panel = (STUDIO_ROOT / "src" / "agent-chat-panel.js").read_text(encoding="utf-8")
    lifecycle = (STUDIO_ROOT / "src" / "agent-chat-lifecycle.js").read_text(encoding="utf-8")

    for marker in (
        "session.pendingCommand",
        "submitAgentChatMessage",
        "executePendingAgentCommand",
        "undoAgentReceipt",
        "recordAgentCommandError",
        "store.set((state) => executePendingAgentCommand(session, state))",
        "确认更改",
        "执行回执",
        "撤销",
    ):
        assert marker in panel + lifecycle
    assert "runtime.spriteChat" not in panel
    assert "固定成功" not in panel + lifecycle

    script = r'''
import {
  agentChatContextKey,
  agentChatContextSnapshot,
  createAgentChatContextStore,
  executePendingAgentCommand,
  submitAgentChatMessage,
  undoAgentReceipt,
} from "./apps/studio/src/agent-chat-lifecycle.js";

const state = {
  meta: { projectId: "p1", projectName: "Demo", canvasName: "Canvas", seq: 7 },
  nodes: { n1: { id: "n1", type: "text", title: "旧标题", status: "failed", params: {} } },
  edges: {},
  order: ["n1"],
  assets: [],
  production: {},
  selection: { nodeIds: ["n1"], edgeId: null },
};
const context = agentChatContextSnapshot({
  project: { project_id: "p1", name: "Demo" },
  studioState: state,
  section: "canvas",
  selectedNode: state.nodes.n1,
  currentShot: { nodeId: "n1", title: "旧标题" },
});
const session = createAgentChatContextStore().get(agentChatContextKey(context));
const preview = submitAgentChatMessage(session, "/rename-selected 新标题", context);
const receipt = executePendingAgentCommand(session, state);
const renamed = state.nodes.n1.title;
const undo = undoAgentReceipt(session, receipt, state);
const restored = state.nodes.n1.title;
submitAgentChatMessage(session, "/recover-selected", {
  ...context,
  selected_node_status: state.nodes.n1.status,
  selected_node_title: state.nodes.n1.title,
});
const recovery = executePendingAgentCommand(session, state);
const storyboardContext = agentChatContextSnapshot({
  project: { project_id: "p1", name: "Demo" },
  studioState: state,
  section: "storyboard",
  selectedNode: state.nodes.n1,
  currentShot: { nodeId: "n1", title: state.nodes.n1.title },
});
const storyboardSession = createAgentChatContextStore().get(agentChatContextKey(storyboardContext));
const storyboardBlocked = submitAgentChatMessage(storyboardSession, "/rename-selected 禁止反写", storyboardContext);
process.stdout.write(JSON.stringify({
  previewStatus: preview.status,
  commandType: preview.command.command_type,
  storyboardWrite: preview.command.impact.storyboard_write,
  providerDispatchCount: preview.command.provider_dispatch_count,
  renamed,
  receiptStatus: receipt.status,
  undoStatus: undo.status,
  restored,
  recoveredStatus: state.nodes.n1.status,
  recoveredFrom: state.nodes.n1.params.agentRecoveredFrom,
  recoveryType: recovery.command_type,
  storyboardBlockedStatus: storyboardBlocked.status,
  storyboardRequiresConfirmation: storyboardBlocked.command.requires_confirmation,
  messages: session.messages.length,
  receipts: session.receipts.length,
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
        "commandType": "rename_selected_node",
        "storyboardWrite": False,
        "providerDispatchCount": 0,
        "renamed": "新标题",
        "receiptStatus": "executed",
        "undoStatus": "undone",
        "restored": "旧标题",
        "recoveredStatus": "draft",
        "recoveredFrom": "failed",
        "recoveryType": "recover_selected_node_error",
        "storyboardBlockedStatus": "blocked",
        "storyboardRequiresConfirmation": False,
        "messages": 8,
        "receipts": 3,
    }
