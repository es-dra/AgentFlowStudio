from __future__ import annotations

import json
import subprocess


def test_agent_chat_m3_context_pack_preview_confirm_undo_has_human_ui_and_provider_closed() -> None:
    script = r'''
import {
  agentChatContextKey,
  agentChatContextSnapshot,
  createAgentChatContextStore,
  executePendingAgentCommandWithRuntime,
  submitAgentChatMessage,
  undoAgentReceiptWithRuntime,
} from "./apps/studio/src/agent-chat-lifecycle.js";

const digest = "a".repeat(64);
const state = {
  meta: { projectId: "m3-web-agent-chat", projectName: "M3 Web", canvasName: "Canvas", seq: 4 },
  viewport: { x: 0, y: 0, scale: 1 },
  nodes: {
    node_script: {
      id: "node_script",
      type: "script",
      title: "剧本",
      content: "Nia waits in the night workshop while Oren studies the locked drawer.",
      status: "ready",
    },
  },
  edges: {},
  groups: {},
  assets: [],
  order: ["node_script"],
  selection: { nodeIds: ["node_script"], edgeId: null },
  ui: {},
  production: {
    script_core_truth_projection: {
      current_revision_id: "scrrev_m3_web",
      source_digest: digest,
      analysis_state: "confirmed",
      current_revision: {
        revision_id: "scrrev_m3_web",
        source_kind: "script",
        source_digest: digest,
        source_length: 82,
      },
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    },
    dynamic_production_plan_projection: {
      plan_id: "plan_m3_web",
      plan_digest: "b".repeat(64),
      planning_state: "planned",
      plan_version: 2,
      shot_count: 4,
      chunk_count: 6,
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    },
  },
};
const context = agentChatContextSnapshot({ studioState: state, selectedNode: state.nodes.node_script, section: "canvas" });
const store = createAgentChatContextStore();
const session = store.get(agentChatContextKey(context));
const submission = submitAgentChatMessage(session, "构建精准上下文包：用于专业剧本和分镜审计", context);
if (submission.status !== "preview") throw new Error(`expected preview, got ${submission.status}`);
if (submission.command.command_type !== "build_m3_context_pack") throw new Error("wrong command type");
if (submission.command.schema_version !== "afs_agent_chat_lifecycle.v0.1") throw new Error("wrong lifecycle schema");
if (submission.command.project_id !== "m3-web-agent-chat") throw new Error("project id not bound");
if (submission.command.script_revision_id !== "scrrev_m3_web") throw new Error("script revision not bound");
if (!submission.command.upstream_refs.includes("scrrev_m3_web")) throw new Error("upstream revision missing");
if (!submission.command.downstream_refs.includes("story_plan_candidate")) throw new Error("downstream plan ref missing");
const firstHistory = session.messages.map((message) => message.text).join("\n");
if (firstHistory.includes("schema_version") || firstHistory.includes("raw_command") || firstHistory.includes("/m3-context-pack")) {
  throw new Error("raw command internals leaked to default chat");
}
let confirmPayload = null;
let undoPayload = null;
const runtime = {
  previewM3ContextPack: async (payload) => {
    if (payload.provider_gates.video !== false || payload.tool_gates.model_call !== false) {
      throw new Error("provider/tool gates opened in preview payload");
    }
    return { command: { status: "preview" }, context_pack: { context_pack_id: "ctx_web_m3" }, provider_dispatch_count: 0, remote_dispatch_count: 0 };
  },
  confirmM3ContextPack: async (payload) => {
    confirmPayload = payload;
    return {
      command: { status: "confirmed" },
      context_pack: {
        context_pack_id: "ctx_web_m3",
        canonical_truth_digest: "c".repeat(64),
        relevant_knowledge_refs: ["kp_director_shot_purpose_v1", "kp_context_privacy_injection_v1"],
        provider_dispatch_count: 0,
        remote_dispatch_count: 0,
      },
      receipt: {
        receipt_id: "receipt_web_m3",
        summary: "已确认精准上下文包；仅包含相关知识和当前制作事实，Provider 保持关闭。",
        undo_available: true,
        provider_dispatch_count: 0,
        remote_dispatch_count: 0,
      },
      projection: { context_pack_count: 1, provider_dispatch_count: 0, remote_dispatch_count: 0 },
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    };
  },
  undoM3ContextPack: async (payload) => {
    undoPayload = payload;
    return {
      receipt: { receipt_id: "receipt_web_m3_undo", status: "undone", summary: "精准上下文包选择已撤销。", provider_dispatch_count: 0, remote_dispatch_count: 0 },
      projection: { current_context_pack_id: "", provider_dispatch_count: 0, remote_dispatch_count: 0 },
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    };
  },
};
const stateStore = { get: () => state, set: (mutator) => mutator(state) };
const receipt = await executePendingAgentCommandWithRuntime(session, stateStore, runtime);
if (receipt.runtime_domain !== "m3_context") throw new Error("receipt runtime domain mismatch");
if (receipt.provider_dispatch_count !== 0 || receipt.remote_dispatch_count !== 0) throw new Error("receipt dispatched provider");
if (receipt.storyboard_write !== false) throw new Error("M3 context command wrote storyboard");
if (!confirmPayload || confirmPayload.source_digest !== digest || confirmPayload.token_budget !== 760) {
  throw new Error("runtime confirm payload lost revision/digest/token budget");
}
if (!confirmPayload.exclusions.includes("prompt_injection") || !confirmPayload.exclusions.includes("full_chat_history")) {
  throw new Error("context exclusions missing");
}
await undoAgentReceiptWithRuntime(session, receipt, stateStore, runtime);
if (!undoPayload || undoPayload.context_pack_id !== "ctx_web_m3") throw new Error("undo payload missing context pack");
const finalHistory = session.messages.map((message) => message.text).join("\n");
for (const forbidden of ["raw_command", "schema_version", "/m3-context-pack", "provider_dispatch_count"]) {
  if (finalHistory.includes(forbidden)) throw new Error(`internal term visible in default chat: ${forbidden}`);
}
console.log(JSON.stringify({
  status: "passed",
  contextPackId: receipt.context_pack_id,
  providerDispatchCount: receipt.provider_dispatch_count,
  remoteDispatchCount: receipt.remote_dispatch_count,
  storyboardWrite: receipt.storyboard_write,
  messageCount: session.messages.length,
}, null, 2));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout
    output = json.loads(completed.stdout)
    assert output["status"] == "passed"
    assert output["providerDispatchCount"] == 0
    assert output["remoteDispatchCount"] == 0
    assert output["storyboardWrite"] is False
