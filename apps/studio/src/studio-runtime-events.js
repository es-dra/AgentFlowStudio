import { openGenerationPanel } from "./panels/generation-panel.js";
import { openCreationProcessPanel } from "./panels/creation-process-panel.js";
import { fixNodeVisualAsset, startNodeGeneration } from "./node-actions.js";
import { HUMAN_GATE_DECISION_EVENT, HUMAN_GATE_DECISION_RESULT_EVENT } from "./human-gate.js";

const VIDEO_ASSET_CARD_DRAFT_EVENT = "afs:video-asset-card-draft";

export function bindStudioWorkflowEvents({ store, runtimeRef }) {
  window.addEventListener("afs:studio-open-generation-panel", (event) => {
    openGenerationForNode(event.detail?.node, store, runtimeRef);
  });
  window.addEventListener("afs:studio-open-creation-process", (event) => {
    const node = resolveEventNode(event, store);
    if (node) openCreationProcessPanel(store.get(), node);
  });
  window.addEventListener("afs:studio-fix-visual-asset", (event) => {
    const node = resolveEventNode(event, store);
    if (node) fixNodeVisualAsset(store, runtimeRef, node);
  });
  window.addEventListener("afs:studio-select-node", (event) => {
    const node = resolveEventNode(event, store);
    if (!node) return;
    store.set((s) => {
      s.selection = { nodeIds: [node.id], edgeId: null };
    }, { history: false, persist: false });
  });
}

export function bindVideoAssetCardDraft({ getRuntime, store, safeError }) {
  window.addEventListener(VIDEO_ASSET_CARD_DRAFT_EVENT, (event) => {
    void handleVideoAssetCardDraft(event, { getRuntime, store, safeError });
  });
}

export function bindHumanGateDecisionEvents({ getRuntime, store, safeError }) {
  window.addEventListener(HUMAN_GATE_DECISION_EVENT, (event) => {
    void handleHumanGateDecision(event, { getRuntime, store, safeError });
  });
}

function openGenerationForNode(inputNode, store, runtimeRef) {
  const node = inputNode?.id ? store.get().nodes[inputNode.id] : selectedNode(store);
  if (!node) return null;
  return openGenerationPanel({ store, node, onRun: (fresh) => startNodeGeneration(store, runtimeRef, fresh) });
}

function resolveEventNode(event, store) {
  const nodeId = String(event.detail?.node_id || event.detail?.node?.id || "");
  if (!nodeId) return selectedNode(store);
  return store.get().nodes[nodeId] || null;
}

function selectedNode(store) {
  const id = store.get().selection.nodeIds[0];
  return id ? store.get().nodes[id] || null : null;
}

async function handleVideoAssetCardDraft(event, { getRuntime, store, safeError }) {
  const runtime = getRuntime();
  const node = resolveEventNode(event, store) || event.detail?.node;
  const nodeId = String(node?.id || event.detail?.node_id || "");
  if (!nodeId || !runtime?.draftAssetCard) return;
  const sourceVideoArtifactId = String(node?.params?.lastVideoArtifactId || node?.params?.lastVideoJobId || "").trim();
  if (!sourceVideoArtifactId) {
    store.set((s) => {
      const current = s.nodes[nodeId];
      if (!current) return;
      current.result = `${current.result || ""}\n请先生成视频，再识别视频资产卡。`.trim();
    });
    return;
  }
  store.set((s) => {
    const current = s.nodes[nodeId];
    if (!current) return;
    current.params.lastVideoAssetCardDraftStatus = "running";
    current.result = `${current.result || ""}\n正在识别视频资产卡...`.trim();
  }, { history: false, persist: false });
  try {
    const response = await runtime.draftAssetCard({
      asset_type: "video",
      source_video_artifact_id: sourceVideoArtifactId,
      sampled_image_asset_refs: [],
      node_id: nodeId,
      prompt_text: node.prompt || node.result || node.title || "",
      provider_service_id: "vision_video",
      generated_at: new Date().toISOString(),
    });
    store.set((s) => {
      const current = s.nodes[nodeId];
      if (!current) return;
      current.params.lastVideoAssetCardDraft = response?.draft || null;
      current.params.lastVideoAssetCardDraftStatus = response?.job?.status || "unknown";
      current.result = `${current.result || ""}\n视频资产卡草稿：${response?.job?.status || "unknown"}`.trim();
    });
  } catch (error) {
    store.set((s) => {
      const current = s.nodes[nodeId];
      if (!current) return;
      current.params.lastVideoAssetCardDraftStatus = "failed";
      current.result = `${current.result || ""}\n视频资产卡识别失败：${safeError(error)}`.trim();
    });
  }
}

async function handleHumanGateDecision(event, { getRuntime, store, safeError }) {
  const requestId = String(event.detail?.request_id || "");
  const payload = event.detail?.payload;
  try {
    if (!payload || typeof payload !== "object") throw new Error("human gate payload is empty");
    const response = await getRuntime().recordHumanGateDecision(payload);
    const humanGateId = response?.human_gate_decision?.human_gate_id || response?.artifact?.artifact_id || "";
    recordHumanGateDecisionOnNode(payload, humanGateId, response?.job?.status || "succeeded", store);
    window.dispatchEvent(new CustomEvent(HUMAN_GATE_DECISION_RESULT_EVENT, {
      detail: { request_id: requestId, ok: true, human_gate_id: humanGateId },
    }));
  } catch (error) {
    window.dispatchEvent(new CustomEvent(HUMAN_GATE_DECISION_RESULT_EVENT, {
      detail: { request_id: requestId, ok: false, error: safeError(error) },
    }));
  }
}

function recordHumanGateDecisionOnNode(payload, humanGateId, status, store) {
  const nodeId = String(payload?.node_id || "");
  if (!nodeId) return;
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    const decisions = Array.isArray(node.params.humanGateDecisions) ? node.params.humanGateDecisions : [];
    node.params.humanGateDecisions = [
      ...decisions,
      {
        human_gate_id: String(humanGateId || ""),
        target_type: String(payload.target_type || ""),
        target_id: String(payload.target_id || ""),
        decision: String(payload.decision || ""),
        status: String(status || ""),
        recorded_at: new Date().toISOString(),
        writes_long_term_memory: false,
      },
    ].slice(-12);
  }, { history: false });
}
