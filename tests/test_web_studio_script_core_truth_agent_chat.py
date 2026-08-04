from __future__ import annotations

import json
import subprocess

from studio_static_helpers import STUDIO_ROOT


def test_script_core_truth_frontend_contract_has_no_production_pollution() -> None:
    production_files = [
        STUDIO_ROOT / "src" / "agent-chat-lifecycle.js",
        STUDIO_ROOT / "src" / "agent-chat-panel.js",
        STUDIO_ROOT / "src" / "script-core-truth-projection.js",
        STUDIO_ROOT / "src" / "runtime-client.js",
        STUDIO_ROOT / "src" / "script-candidate-review.js",
        STUDIO_ROOT / "src" / "canvas-input.js",
        STUDIO_ROOT / "src" / "panels" / "inspector-panel.js",
    ]
    runtime_file = "apps/api/runtime_script_core_truth.py"
    combined = "\n".join(path.read_text(encoding="utf-8") for path in production_files)
    combined += "\n" + open(runtime_file, encoding="utf-8").read()
    for marker in ("KNOWN_", "_HINTS", "FALLBACK_SCENES", "巷口", "雨巷", "老宅", "4x15", "4×15"):
        assert marker not in combined
    assert "script_revision_truth_contract" in combined
    assert "core_asset_truth_runtime_commands" in combined
    assert "createScriptRevision" in combined
    assert "confirmCoreAssetCommand" in combined
    assert "undoCoreAssetCommand" in combined
    assert "reviewAnalysisAsset" in combined
    assert "loadProductionGraph" in combined
    assert "候选审阅" in combined
    assert "opensCandidateReview" in combined
    assert "s.ui.inspectorOpen = true" in combined
    assert "agent-script-candidate-review" in combined
    assert "handleScriptCandidateReview" in combined
    assert "auto_props: 0" in combined


def test_agent_chat_runtime_script_revision_projection_and_core_asset_undo() -> None:
    script = r'''
import {
  agentChatContextKey,
  agentChatContextSnapshot,
  createAgentChatContextStore,
  executePendingAgentCommandWithRuntime,
  submitAgentChatMessage,
  undoAgentReceiptWithRuntime,
} from "./apps/studio/src/agent-chat-lifecycle.js";

const revision = {
  revision_id: "scrrev_frontend",
  source_kind: "script",
  source_digest: "a".repeat(64),
  source_length: 42,
  analysis_state: "analysis_required",
};
const baseProjection = {
  schema_version: "afs.script_core_truth.v0.1",
  project_id: "p1",
  current_revision_id: revision.revision_id,
  current_revision: revision,
  revision_history: [revision],
  assets: [],
  asset_counts: { characters: 0, main_scenes: 0, manual_props: 0, auto_props: 0, style_assets: 0, action_event_assets: 0 },
  analysis_state: "analysis_required",
  provider_dispatch_count: 0,
  remote_dispatch_count: 0,
};
const characterAsset = {
  asset_id: "char_frontend",
  asset_type: "character",
  source_mode: "analysis_candidate",
  status: "confirmed",
  project_id: "p1",
  revision_id: revision.revision_id,
  source_digest: revision.source_digest,
  display_name: "Ari",
  name: "Ari",
  aliases: [],
  pronoun_links: [],
  evidence_spans: [{ start: 0, end: 3, quote: "Ari" }],
  confidence: 0.93,
  lineage: {},
};
const pendingScene = {
  asset_id: "scene_frontend",
  asset_type: "main_scene",
  source_mode: "analysis_candidate",
  status: "pending_confirmation",
  project_id: "p1",
  revision_id: revision.revision_id,
  source_digest: revision.source_digest,
  display_name: "Archive",
  name: "Archive",
  aliases: [],
  pronoun_links: [],
  evidence_spans: [{ start: 12, end: 19, quote: "Archive" }],
  confidence: 0.7,
  lineage: {},
};
function projectionWithAssets(assets, analysisState = "pending_confirmation") {
  return {
    ...baseProjection,
    assets,
    analysis_state: analysisState,
    current_revision: { ...revision, analysis_state: analysisState },
    asset_counts: {
      characters: assets.filter((item) => item.asset_type === "character" && item.status !== "retired").length,
      main_scenes: assets.filter((item) => item.asset_type === "main_scene" && item.status !== "retired").length,
      manual_props: assets.filter((item) => item.asset_type === "prop" && item.status !== "retired").length,
      auto_props: 0,
      style_assets: 0,
      action_event_assets: 0,
    },
  };
}

const state = {
  meta: { projectId: "p1", projectName: "Frontend", canvasName: "Canvas", seq: 1 },
  viewport: { x: 0, y: 0, scale: 1 },
  nodes: {},
  edges: {},
  groups: {},
  order: [],
  assets: [],
  production: {},
  selection: { nodeIds: [], edgeId: null },
  ui: {},
};
const store = {
  get: () => state,
  set: (mutator) => mutator(state),
};
let lastPreviewPayload = null;
let lastConfirmPayload = null;
const runtime = {
  createScriptRevision: async (payload) => {
    if (!payload.source_text.includes("Ari")) throw new Error("source text was not sent to runtime");
    return { project_id: "p1", revision, projection: baseProjection, analysis_state: "analysis_required" };
  },
  loadScriptTruth: async () => ({ project_id: "p1", projection: projectionWithAssets([characterAsset, pendingScene]) }),
  previewCoreAssetCommand: async (payload) => {
    lastPreviewPayload = payload;
    return { command: { status: "preview" }, projection: projectionWithAssets([characterAsset, pendingScene]) };
  },
  confirmCoreAssetCommand: async (payload) => {
    lastConfirmPayload = payload;
    const prop = {
      asset_id: "prop_frontend",
      asset_type: "prop",
      source_mode: "manual",
      status: "confirmed",
      project_id: "p1",
      revision_id: revision.revision_id,
      source_digest: revision.source_digest,
      display_name: payload.patch.display_name || "prop",
      name: payload.patch.display_name || "prop",
      aliases: [],
      pronoun_links: [],
      evidence_spans: [],
      confidence: 1,
      lineage: {},
    };
    const aliases = payload.command_type === "merge_alias" ? ["A"] : [];
    const updatedCharacter = { ...characterAsset, aliases };
    const assets = payload.command_type === "create_manual_prop" ? [updatedCharacter, pendingScene, prop] : [updatedCharacter, pendingScene];
    return {
      receipt: {
        receipt_id: "runtime_receipt_1",
        command_type: payload.command_type,
        status: "executed",
        summary: "runtime changed canonical truth",
        revision_id: revision.revision_id,
        source_digest: revision.source_digest,
        affected_asset_ids: [payload.target_asset_id || "prop_frontend"],
        undo_available: true,
      },
      projection: projectionWithAssets(assets),
    };
  },
  undoCoreAssetCommand: async () => ({
    receipt: { receipt_id: "runtime_undo_1", command_type: "undo", status: "undone", summary: "runtime undo" },
    projection: projectionWithAssets([characterAsset, pendingScene]),
  }),
};

let context = agentChatContextSnapshot({
  project: { project_id: "p1", name: "Frontend" },
  studioState: state,
  section: "canvas",
});
const session = createAgentChatContextStore().get(agentChatContextKey(context));
const createPreview = submitAgentChatMessage(session, "/script-revision Ari enters the Archive.", context);
const createReceipt = await executePendingAgentCommandWithRuntime(session, store, runtime);
const revisionNodes = state.order.filter((id) => id.startsWith("script_truth_revision_"));

context = agentChatContextSnapshot({ project: { project_id: "p1", name: "Frontend" }, studioState: state, section: "canvas" });
submitAgentChatMessage(session, "/refresh-script-truth", context);
const refreshReceipt = await executePendingAgentCommandWithRuntime(session, store, runtime);
const assetNodeId = state.order.find((id) => id.includes("char_frontend"));
state.selection = { nodeIds: [assetNodeId], edgeId: null };
context = agentChatContextSnapshot({
  project: { project_id: "p1", name: "Frontend" },
  studioState: state,
  section: "canvas",
  selectedNode: state.nodes[assetNodeId],
});
const aliasPreview = submitAgentChatMessage(session, "/merge-alias A", context);
const aliasReceipt = await executePendingAgentCommandWithRuntime(session, store, runtime);
const aliasRuntimePreviewType = lastPreviewPayload.command_type;
const aliasRuntimeConfirmType = lastConfirmPayload.command_type;
const aliasAfter = state.nodes[assetNodeId].content;
const undoReceipt = await undoAgentReceiptWithRuntime(session, aliasReceipt, store, runtime);
const aliasUndone = state.nodes[assetNodeId].content;

context = agentChatContextSnapshot({ project: { project_id: "p1", name: "Frontend" }, studioState: state, section: "canvas" });
submitAgentChatMessage(session, "/manual-prop brass key", context);
const propReceipt = await executePendingAgentCommandWithRuntime(session, store, runtime);
const propNodeExists = state.order.some((id) => id.includes("prop_frontend"));
const storyboardContext = agentChatContextSnapshot({ project: { project_id: "p1", name: "Frontend" }, studioState: state, section: "storyboard" });
const storyboardBlocked = submitAgentChatMessage(session, "/manual-prop blocked", storyboardContext);

process.stdout.write(JSON.stringify({
  createStatus: createPreview.status,
  createType: createPreview.command.command_type,
  createReceiptStatus: createReceipt.status,
  createUndoAvailable: createReceipt.undo_available,
  revisionNodes: revisionNodes.length,
  analysisState: state.production.script_core_truth_projection.analysis_state,
  refreshStatus: refreshReceipt.status,
  assetNodeCount: state.order.filter((id) => id.startsWith("script_truth_asset_")).length,
  aliasPreviewStatus: aliasPreview.status,
  runtimePreviewType: aliasRuntimePreviewType,
  runtimeConfirmType: aliasRuntimeConfirmType,
  aliasReceiptRuntimeId: aliasReceipt.runtime_receipt_id,
  aliasAfterHasAlias: aliasAfter.includes("别名：A"),
  undoStatus: undoReceipt.status,
  aliasUndone: !aliasUndone.includes("别名：A"),
  propReceiptStatus: propReceipt.status,
  propNodeExists,
  storyboardBlockedStatus: storyboardBlocked.status,
  storyboardRequiresConfirmation: storyboardBlocked.command.requires_confirmation,
  providerDispatchCount: createReceipt.provider_dispatch_count + refreshReceipt.provider_dispatch_count + aliasReceipt.provider_dispatch_count + propReceipt.provider_dispatch_count,
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
        "createStatus": "preview",
        "createType": "create_script_revision",
        "createReceiptStatus": "executed",
        "createUndoAvailable": False,
        "revisionNodes": 1,
        "analysisState": "pending_confirmation",
        "refreshStatus": "executed",
        "assetNodeCount": 3,
        "aliasPreviewStatus": "preview",
        "runtimePreviewType": "merge_alias",
        "runtimeConfirmType": "merge_alias",
        "aliasReceiptRuntimeId": "runtime_receipt_1",
        "aliasAfterHasAlias": True,
        "undoStatus": "undone",
        "aliasUndone": True,
        "propReceiptStatus": "executed",
        "propNodeExists": True,
        "storyboardBlockedStatus": "blocked",
        "storyboardRequiresConfirmation": False,
        "providerDispatchCount": 0,
    }


def test_studio_candidate_review_edits_confirms_rejects_and_refreshes_projection() -> None:
    script = r'''
import { applyScriptCoreTruthProjection } from "./apps/studio/src/script-core-truth-projection.js";
import { handleScriptCandidateReview } from "./apps/studio/src/script-candidate-review.js";

const digest = "a".repeat(64);
const revision = {
  project_id: "p1", revision_id: "rev1", source_kind: "script", source_digest: digest,
  source_length: 20, source_text: "Mira enters the hall.", analysis_state: "pending_confirmation",
};
function projection(status, version, versionId, label = "Mira") {
  return {
    schema_version: "afs.script_core_truth.v0.1", project_id: "p1", current_revision_id: "rev1",
    current_revision: revision, revision_history: [revision], analysis_state: status === "confirmed" ? "confirmed" : "pending_confirmation",
    asset_counts: { characters: 1, main_scenes: 0, manual_props: 0, auto_props: 0, style_assets: 0, action_event_assets: 0 },
    assets: [{
      asset_id: "char1", asset_type: "character", source_mode: "analysis_candidate", status,
      project_id: "p1", revision_id: "rev1", source_digest: digest, candidate_id: "candidate1",
      version, version_id: versionId, parent_version_id: version > 1 ? `v${version - 1}` : "",
      display_name: label, name: label, aliases: [], pronoun_links: [], confidence: 0.99,
      evidence_spans: [{ start: 0, end: 4, quote: "Mira" }], lineage: {},
    }],
  };
}
function harness(initial) {
  const state = {
    meta: { projectId: "p1" }, nodes: {}, edges: {}, groups: {}, order: [], assets: [], production: {},
    selection: { nodeIds: [], edgeId: null }, ui: {}, viewport: { x: 0, y: 0, scale: 1 },
  };
  applyScriptCoreTruthProjection(state, initial);
  state.selection = { nodeIds: ["script_truth_asset_char1"], edgeId: null };
  const store = { get: () => state, set: (mutator) => mutator(state) };
  return { state, store, node: state.nodes["script_truth_asset_char1"] };
}

let editPayload = null;
const edited = harness(projection("candidate", 1, "v1"));
await handleScriptCandidateReview({
  action: "edit", label: "Mira Vale", node: edited.node, store: edited.store,
  runtime: {
    confirmCoreAssetCommand: async (payload) => { editPayload = payload; return { projection: projection("modified", 2, "v2", "Mira Vale") }; },
  },
});

const chineseEditKeys = [];
for (const label of ["米拉", "明月"]) {
  const localized = harness(projection("candidate", 1, "v1"));
  await handleScriptCandidateReview({
    action: "edit", label, node: localized.node, store: localized.store,
    runtime: {
      confirmCoreAssetCommand: async (payload) => {
        chineseEditKeys.push(payload.idempotency_key);
        return { projection: projection("modified", 2, "v2", label) };
      },
    },
  });
}

let confirmPayload = null;
const confirmed = harness(projection("modified", 2, "v2", "Mira Vale"));
await handleScriptCandidateReview({
  action: "confirm", node: confirmed.node, store: confirmed.store,
  runtime: {
    loadProductionGraph: async () => ({ graph: { version: 7 } }),
    reviewAnalysisAsset: async (_revisionId, _assetId, payload) => { confirmPayload = payload; return {}; },
    loadScriptTruth: async () => ({ projection: projection("confirmed", 3, "v3", "Mira Vale") }),
  },
});

let rejectPayload = null;
const rejected = harness(projection("candidate", 1, "v1"));
await handleScriptCandidateReview({
  action: "reject", node: rejected.node, store: rejected.store,
  runtime: {
    loadProductionGraph: async () => ({ graph: { version: 7 } }),
    reviewAnalysisAsset: async (_revisionId, _assetId, payload) => { rejectPayload = payload; return {}; },
    loadScriptTruth: async () => ({ projection: projection("rejected", 2, "v2") }),
  },
});

process.stdout.write(JSON.stringify({
  editType: editPayload.command_type,
  editExpectedVersion: editPayload.expected_asset_version,
  editedStatus: edited.state.nodes["script_truth_asset_char1"].params.coreAssetTruth.status,
  editedSelection: edited.state.selection.nodeIds,
  distinctChineseEditKeys: new Set(chineseEditKeys).size,
  confirmDecision: confirmPayload.decision,
  confirmGraphVersion: confirmPayload.expected_graph_version,
  confirmCandidateId: confirmPayload.candidate_id,
  confirmedStatus: confirmed.state.nodes["script_truth_asset_char1"].params.coreAssetTruth.status,
  rejectDecision: rejectPayload.decision,
  rejectedStatus: rejected.state.nodes["script_truth_asset_char1"].params.coreAssetTruth.status,
  evidence: confirmed.state.nodes["script_truth_asset_char1"].params.coreAssetTruth.evidence_spans[0].quote,
}));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert json.loads(completed.stdout) == {
        "editType": "edit_asset",
        "editExpectedVersion": 1,
        "editedStatus": "modified",
        "editedSelection": ["script_truth_asset_char1"],
        "distinctChineseEditKeys": 2,
        "confirmDecision": "confirm",
        "confirmGraphVersion": 7,
        "confirmCandidateId": "candidate1",
        "confirmedStatus": "confirmed",
        "rejectDecision": "reject",
        "rejectedStatus": "rejected",
        "evidence": "Mira",
    }
