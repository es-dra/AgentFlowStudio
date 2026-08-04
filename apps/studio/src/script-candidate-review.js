import { applyScriptCoreTruthProjection } from "./script-core-truth-projection.js";

export const SCRIPT_CANDIDATE_REVIEW_EVENT = "afs:studio-script-candidate-review";
const REVIEW_SCHEMA_VERSION = "afs.analysis_asset_review.v0.1";
const CORE_ASSET_COMMAND_SCHEMA_VERSION = "afs.core_asset_command.v0.1";

export function bindScriptCandidateReviewEvents({ getRuntime, store, formatError }) {
  window.addEventListener(SCRIPT_CANDIDATE_REVIEW_EVENT, (event) => {
    void handleScriptCandidateReview({
      action: event.detail?.action,
      label: event.detail?.label,
      node: event.detail?.node,
      runtime: getRuntime?.(),
      store,
      formatError,
    });
  });
}

export async function handleScriptCandidateReview({ action, label, node, runtime, store, formatError }) {
  const truth = node?.params?.coreAssetTruth || {};
  const scoped = reviewScope(truth);
  if (!runtime || !store || !scoped) return { ok: false, error: "candidate_scope_unavailable" };
  if (!["candidate", "modified"].includes(scoped.status)) {
    return { ok: false, error: scoped.status === "expired" ? "candidate_expired" : "candidate_not_reviewable" };
  }
  setReviewState(store, node.id, { busy: true, error: "", message: action === "edit" ? "正在保存修改…" : "正在保存审阅决定…" });
  try {
    let response;
    if (action === "edit") {
      const nextLabel = cleanLabel(label);
      if (!nextLabel) throw new Error("候选名称不能为空");
      response = await runtime.confirmCoreAssetCommand({
        project_id: scoped.project_id,
        revision_id: scoped.revision_id,
        source_digest: scoped.source_digest,
        schema_version: CORE_ASSET_COMMAND_SCHEMA_VERSION,
        command_type: "edit_asset",
        target_asset_id: scoped.asset_id,
        patch: { display_name: nextLabel },
        expected_asset_version: scoped.version,
        idempotency_key: reviewKey("edit", scoped, nextLabel),
        provider_dispatch_count: 0,
        remote_dispatch_count: 0,
      });
    } else if (action === "confirm" || action === "reject") {
      if (!runtime.loadProductionGraph || !runtime.reviewAnalysisAsset) throw new Error("审阅接口暂不可用");
      const graphResponse = await runtime.loadProductionGraph();
      response = await runtime.reviewAnalysisAsset(scoped.revision_id, scoped.asset_id, {
        project_id: scoped.project_id,
        revision_id: scoped.revision_id,
        source_digest: scoped.source_digest,
        candidate_id: scoped.candidate_id,
        asset_version_id: scoped.version_id,
        expected_asset_version: scoped.version,
        expected_graph_version: Number(graphResponse?.graph?.version || 0),
        idempotency_key: reviewKey(action, scoped),
        schema_version: REVIEW_SCHEMA_VERSION,
        decision: action,
        reason: action === "confirm" ? "Studio creator confirmed analysis candidate." : "Studio creator rejected analysis candidate.",
      });
    } else {
      throw new Error("未知审阅操作");
    }
    const truthResponse = response?.projection ? response : await runtime.loadScriptTruth();
    store.set((state) => applyScriptCoreTruthProjection(state, truthResponse?.projection || {}), {
      history: false,
      persist: false,
    });
    return { ok: true, action, response };
  } catch (error) {
    const message = typeof formatError === "function" ? formatError(error) : String(error?.message || error || "保存失败");
    setReviewState(store, node.id, { busy: false, error: message, message: "保存失败，可重试。" });
    return { ok: false, error: message };
  }
}

function reviewScope(value) {
  const scoped = value && typeof value === "object" ? value : {};
  const result = {
    project_id: cleanToken(scoped.project_id, 128),
    revision_id: cleanToken(scoped.revision_id, 140),
    source_digest: cleanDigest(scoped.source_digest),
    candidate_id: cleanToken(scoped.candidate_id, 160),
    asset_id: cleanToken(scoped.asset_id, 160),
    version_id: cleanToken(scoped.version_id, 160),
    version: Math.max(1, Number(scoped.version || 1)),
    status: cleanToken(scoped.status, 80),
  };
  return Object.values({
    project_id: result.project_id,
    revision_id: result.revision_id,
    source_digest: result.source_digest,
    candidate_id: result.candidate_id,
    asset_id: result.asset_id,
    version_id: result.version_id,
  }).every(Boolean) ? result : null;
}

function setReviewState(store, nodeId, value) {
  store.set((state) => {
    const target = state.nodes?.[nodeId];
    if (!target?.params?.coreAssetTruth) return;
    target.params.coreAssetReview = { ...(target.params.coreAssetReview || {}), ...value };
  }, { history: false, persist: false });
}

function reviewKey(action, scoped, label = "") {
  const suffix = [...cleanLabel(label).toLowerCase()]
    .slice(0, 24)
    .map((character) => character.codePointAt(0).toString(36))
    .join("-");
  return ["studio", action, scoped.asset_id, scoped.version_id, suffix].filter(Boolean).join(":").slice(0, 160);
}

function cleanToken(value, limit) {
  return String(value || "").replace(/[^A-Za-z0-9_.:-]/g, "").slice(0, limit);
}

function cleanDigest(value) {
  const text = String(value || "").trim().toLowerCase();
  return /^[a-f0-9]{64}$/.test(text) ? text : "";
}

function cleanLabel(value) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, 120);
}
