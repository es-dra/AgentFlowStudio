from __future__ import annotations

import json
import subprocess

from studio_static_helpers import STUDIO_ROOT


def run_node_probe(script: str) -> dict:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(completed.stdout)


def test_p0_static_contract_restores_split_entry_without_legacy_breakdown() -> None:
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    shell = (STUDIO_ROOT / "src" / "product-shell.js").read_text(encoding="utf-8")
    store = (STUDIO_ROOT / "src" / "store.js").read_text(encoding="utf-8")
    store_notify = (STUDIO_ROOT / "src" / "store-notify-meta.js").read_text(encoding="utf-8")
    lifecycle = (STUDIO_ROOT / "src" / "agent-chat-lifecycle.js").read_text(encoding="utf-8")
    prompt_bar = (STUDIO_ROOT / "src" / "prompt-bar.js").read_text(encoding="utf-8")
    node_body = (STUDIO_ROOT / "src" / "canvas-node-body.js").read_text(encoding="utf-8")
    stable_input = (STUDIO_ROOT / "src" / "stable-text-input.js").read_text(encoding="utf-8")
    edges = (STUDIO_ROOT / "src" / "canvas-edges.js").read_text(encoding="utf-8")
    edge_css = (STUDIO_ROOT / "styles" / "canvas-edges.css").read_text(encoding="utf-8")
    edge_motion_css = (STUDIO_ROOT / "styles" / "canvas-edge-motion.css").read_text(encoding="utf-8")

    assert "renderScopes" in store_notify
    assert "mergeNotifyMeta" in store
    assert "canvas-local-edit" in main
    assert "isCanvasTextEditingActive" in main
    assert "options.render === false" in shell
    assert "syncSaveStatusElement" in shell
    assert "bindStableTextInputLifecycle" in node_body
    assert "bindStableTextInputLifecycle" in prompt_bar
    assert "compositionstart" in stable_input
    assert "compositionupdate" in stable_input
    assert "compositionend" in stable_input
    assert "beforeinput" in stable_input
    assert "paste" in stable_input
    assert 'renderScope: "canvas-local-edit"' in node_body
    assert 'renderScope: "canvas-local-edit"' in prompt_bar

    assert "自动拆分分镜" in prompt_bar
    assert "startEmbeddedCreativeAction" in prompt_bar
    assert '"shot_breakdown"' in prompt_bar
    assert "/plan-selected-script-shots" not in prompt_bar
    assert "request_story_plan_candidate" in lifecycle
    assert "需要智能规划器提交结构化候选" in lifecycle
    assert "planning_required" in lifecycle
    assert "splitTextNodeToStoryboardNodes" not in prompt_bar
    assert "structuredShotFromSegment" not in prompt_bar
    assert "扩写剧本" not in prompt_bar

    assert "touchesSelection" not in edges
    assert "edgeLifecycleState" in edges
    assert "edge-failed" in edge_css
    assert "edge-paused" in edge_css
    assert "prefers-reduced-motion: reduce" in edge_motion_css


def test_p0_store_notifies_canvas_local_edit_scope_without_full_shell_render() -> None:
    payload = run_node_probe(
        r'''
import { createStore } from "./apps/studio/src/store.js";
const store = createStore(`p0-notify-${Date.now()}`);
const observed = [];
store.subscribe((state, meta) => observed.push(meta));
store.set((state) => {
  state.nodes.n1 = { id: "n1", type: "text", title: "文本", x: 0, y: 0, w: 280, h: 280, content: "y", prompt: "y", status: "complete", params: {} };
  state.order = ["n1"];
  state.selection = { nodeIds: ["n1"], edgeId: null };
}, { history: false, renderScope: "canvas-local-edit" });
await Promise.resolve();
process.stdout.write(JSON.stringify(observed.at(-1)));
'''
    )
    assert payload == {"full": False, "renderScopes": ["canvas-local-edit"]}


def test_p0_fit_hidden_or_zero_canvas_returns_null() -> None:
    payload = run_node_probe(
        r'''
import { fitVisibleCanvasViewport, visibleCanvasFrame } from "./apps/studio/src/canvas-safe-area.js";
const root = {
  hidden: false,
  isConnected: true,
  getBoundingClientRect: () => ({ left: 0, top: 0, right: 0, bottom: 0, width: 0, height: 0 }),
};
globalThis.window = { getComputedStyle: () => ({ display: "block", visibility: "visible", pointerEvents: "auto" }) };
globalThis.document = {
  getElementById: (id) => id === "canvas-root" ? root : null,
  querySelector: () => null,
};
const frame = visibleCanvasFrame();
const fit = fitVisibleCanvasViewport({ n1: { x: 0, y: 0, w: 280, h: 280 } });
process.stdout.write(JSON.stringify({ frame, fit }));
'''
    )
    assert payload["frame"]["visible"] is False
    assert payload["fit"] is None


def test_p0_port_geometry_converts_client_to_canvas_local_before_world() -> None:
    payload = run_node_probe(
        r'''
import { nodeFramePortWorldPoint } from "./apps/studio/src/interaction/port-geometry.js";
const rootRect = { left: 11, top: 68, right: 1011, bottom: 768, width: 1000, height: 700 };
const portRect = { left: 491, top: 330, width: 20, height: 20 };
const portEl = { getBoundingClientRect: () => portRect };
const nodeEl = { dataset: { nodeId: "n1" }, querySelector: () => portEl };
globalThis.document = {
  getElementById: (id) => id === "canvas-root" ? { getBoundingClientRect: () => rootRect } : null,
  querySelectorAll: () => [nodeEl],
};
const viewport = { x: 30, y: 40, scale: 0.5 };
const node = { id: "n1", x: 100, y: 200, w: 300, h: 280 };
const point = nodeFramePortWorldPoint(node, "out", viewport);
const expectedX = ((portRect.left + portRect.width / 2 - rootRect.left) - viewport.x) / viewport.scale;
const expectedY = ((portRect.top + portRect.height / 2 - rootRect.top) - viewport.y) / viewport.scale;
process.stdout.write(JSON.stringify({ point, expectedX, expectedY }));
'''
    )
    assert abs(payload["point"]["x"] - payload["expectedX"]) < 0.001
    assert abs(payload["point"]["y"] - payload["expectedY"]) < 0.001


def test_p0_agent_chat_auto_split_request_is_planning_required_and_provider_closed() -> None:
    payload = run_node_probe(
        r'''
import {
  agentChatContextKey,
  createAgentChatContextStore,
  executePendingAgentCommandWithRuntime,
  submitAgentChatMessage,
} from "./apps/studio/src/agent-chat-lifecycle.js";

const context = {
  project_id: "p0",
  project_name: "P0",
  section: "canvas",
  script_revision_id: "rev_current",
  script_source_digest: "a".repeat(64),
  selected_node_id: "n1",
  selected_node_type: "script",
  selected_node_title: "剧本文本",
  selected_node_text: "林夏走进车站，听见十年后的留言。",
  counts: { nodes: 1, scenes: 0, shots: 0 },
};
const session = createAgentChatContextStore().get(agentChatContextKey(context));
const preview = submitAgentChatMessage(session, "/plan-selected-script-shots", context);
const state = { meta: { projectId: "p0" }, nodes: {}, edges: {}, order: [], production: {}, viewport: { x: 0, y: 0, scale: 1 } };
const store = { get: () => state, set: (mutator) => mutator(state) };
const runtime = {
  loadProductionPlanTruth: async () => ({
    projection: {
      schema_version: "afs.dynamic_production_plan_projection.v0.1",
      project_id: "p0",
      planning_state: "planning_required",
      shots: [],
      chunks: [],
      provider_dispatch_count: 0,
      remote_dispatch_count: 0,
    },
    provider_dispatch_count: 0,
    remote_dispatch_count: 0,
  }),
};
const receipt = await executePendingAgentCommandWithRuntime(session, store, runtime);
const visibleRawLeak = session.messages.some((message) => String(message.text || "").includes("/plan-selected-script-shots"));
process.stdout.write(JSON.stringify({
  previewStatus: preview.status,
  commandType: preview.command.command_type,
  title: preview.command.title,
  rawPreserved: preview.command.raw_command_text === "/plan-selected-script-shots",
  visibleRawLeak,
  receiptStatus: receipt.status,
  receiptSummary: receipt.summary,
  runtimeDomain: receipt.runtime_domain,
  undoAvailable: receipt.undo_available,
  providerDispatchCount: preview.command.provider_dispatch_count + receipt.provider_dispatch_count,
  storyboardWrite: preview.command.impact.storyboard_write,
}));
'''
    )
    assert payload["previewStatus"] == "preview"
    assert payload["commandType"] == "request_story_plan_candidate"
    assert payload["title"] == "自动拆分分镜"
    assert payload["rawPreserved"] is True
    assert payload["visibleRawLeak"] is False
    assert payload["receiptStatus"] == "executed"
    assert payload["runtimeDomain"] == "production_plan"
    assert payload["undoAvailable"] is False
    assert "需要智能规划器" in payload["receiptSummary"]
    assert payload["providerDispatchCount"] == 0
    assert payload["storyboardWrite"] is False
