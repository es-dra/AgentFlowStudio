import { studioActionVocabularyEntry } from "./studio-entity-status-vocabulary.js";
import { containsUnsafeText, redactUnsafeText } from "./safe-text-redaction.js";

export const ASSET_REUSE_CONTRACT_VERSION = "p0-asset-reuse-ux-20260704";

export const ASSET_REUSE_STATES = Object.freeze([
  "recognized",
  "reused",
  "graph-bound",
  "blocked",
  "conflicted",
  "reversed/unbound",
]);

const NON_CLAIMS = Object.freeze([
  "not provider smoke",
  "not generated media QA",
  "not human acceptance",
  "not fixed asset promotion",
  "not durable memory promotion",
  "not business validation",
  "not legal readiness",
]);

const REPLACE_CAPABLE_ENTITIES = new Set([
  "project_asset",
  "reference_input",
  "keyframe_version",
  "video_revision",
  "binding",
  "lineage",
]);

export function assetReuseLocalContract(state, node) {
  const items = assetReuseSummariesForNode(state, node);
  return {
    artifact_type: "studio_asset_reuse_local_contract",
    contract_version: ASSET_REUSE_CONTRACT_VERSION,
    node_id: safeId(node?.id),
    states: [...ASSET_REUSE_STATES],
    summary: {
      item_count: items.length,
      recognized_count: items.filter((item) => item.state === "recognized").length,
      reused_count: items.filter((item) => item.state === "reused").length,
      graph_bound_count: items.filter((item) => item.state === "graph-bound").length,
      blocked_count: items.filter((item) => item.state === "blocked").length,
      conflicted_count: items.filter((item) => item.state === "conflicted").length,
      reversed_unbound_count: items.filter((item) => item.state === "reversed/unbound").length,
    },
    items,
    safety_boundary: safetyBoundary(),
    non_claims: [...NON_CLAIMS],
  };
}

export function assetReuseSummariesForNode(state, node) {
  const targetNode = node || {};
  const params = targetNode.params || {};
  const reversals = reversalMap(params.assetReuseReversals);
  const items = [];
  const seen = new Set();
  const add = (item) => {
    const normalized = applyRecordedReversal(item, reversals);
    const key = normalized.reuse_id || `${normalized.state}:${items.length}`;
    if (seen.has(key)) return;
    seen.add(key);
    items.push(normalized);
  };

  for (const upload of list(params.uploads)) add(uploadSummary(targetNode, upload));
  for (const asset of list(params.visualAssets)) add(visualAssetSummary(targetNode, asset));
  for (const candidate of generationCandidates(params)) add(generationCandidateSummary(targetNode, candidate));
  for (const graph of assetBindingGraphs(state, targetNode)) {
    for (const suggestion of list(graph.binding_suggestions)) add(graphBindingSummary(targetNode, graph, suggestion));
    for (const blocked of list(graph.blocked_candidates)) add(blockedGraphSummary(targetNode, graph, blocked));
  }
  for (const ref of nodeReferenceStackRefs(params)) add(referenceStackSummary(targetNode, ref));

  return items.filter(Boolean).slice(0, 24);
}

export function assetReuseReversalForSummary(summary) {
  const entity = safeEntity(summary?.studio_entity_id || summary?.reference_type || "reference_input");
  const action = reversalActionForEntity(entity);
  return {
    reversible: true,
    action,
    studio_entity_id: entity,
    action_applies_to_entity: Boolean(studioActionVocabularyEntry(action)?.appliesTo?.includes(entity)),
    resulting_state: action === "reject" ? "rejected" : "reversed/unbound",
    preserve_lineage: true,
    deletes_asset: false,
    deletes_media: false,
    deletes_provider_artifact: false,
    deletes_source_evidence: false,
    deletes_candidate_record: false,
    destructive_asset_write: false,
  };
}

export function recordAssetReuseReversal(node, summary) {
  if (!node.params || typeof node.params !== "object") node.params = {};
  const plan = assetReuseReversalForSummary(summary);
  const record = {
    reuse_id: safeId(summary?.reuse_id),
    action: plan.action,
    from_state: safeState(summary?.state),
    to_state: "reversed/unbound",
    target_ref: safeId(summary?.target_ref || summary?.asset?.asset_id || summary?.asset?.visual_asset_id),
    recorded_at: new Date().toISOString(),
    deletes_asset: false,
    deletes_media: false,
    deletes_provider_artifact: false,
    deletes_source_evidence: false,
    deletes_candidate_record: false,
  };
  const current = list(node.params.assetReuseReversals);
  node.params.assetReuseReversals = [
    record,
    ...current.filter((item) => safeId(item?.reuse_id) !== record.reuse_id),
  ].slice(0, 24);
  return record;
}

function uploadSummary(node, upload) {
  const assetId = safeId(upload?.asset_id || upload?.assetId);
  const role = safeId(upload?.role);
  const referenceTarget = safeId(upload?.reference_target);
  const firstFrameId = safeId(node?.params?.firstFrameImageAssetId);
  const lastFrameId = safeId(node?.params?.lastFrameImageAssetId);
  const boundAsFrame = assetId && (assetId === firstFrameId || assetId === lastFrameId);
  const draftCandidate = role === "asset_reference" && referenceTarget === "asset_card_draft";
  const entity = boundAsFrame ? "binding" : "reference_input";
  return summaryRecord({
    state: boundAsFrame ? "reused" : "recognized",
    referenceType: entity,
    targetNode: node,
    targetSlot: referenceTarget || role || "upload",
    targetRef: assetId,
    asset: {
      asset_id: assetId,
      label: safeText(upload?.label || upload?.filename),
      media_kind: safeId(upload?.media_kind),
      mime_type: safeMime(upload?.mime_type),
      role,
      reference_target: referenceTarget,
    },
    sourceEvidence: {
      source_mode: safeId(upload?.source_mode),
      source_asset_id: assetId,
      source_node_id: safeId(node?.id),
      user_intent: safeText(upload?.user_intent, 180),
    },
    confidence: upload?.confidence,
    reviewState: draftCandidate ? "draft" : boundAsFrame ? "bound" : "draft",
    selectedState: boundAsFrame ? "selected" : "candidate",
    draftCandidate,
    confirmedFixedAsset: false,
  });
}

function visualAssetSummary(node, asset) {
  const assetId = safeId(asset?.asset_id || asset?.visual_asset_id);
  return summaryRecord({
    state: "reused",
    referenceType: "binding",
    targetNode: node,
    targetSlot: "visual_assets",
    targetRef: assetId,
    asset: {
      visual_asset_id: assetId,
      asset_id: assetId,
      label: safeText(asset?.label || asset?.title),
      asset_type: safeId(asset?.asset_type),
    },
    sourceEvidence: safeSourceEvidence(asset?.source_evidence, {
      source_node_id: safeId(asset?.source_node_id),
    }),
    confidence: asset?.confidence,
    lockState: asset?.lock_state || (asset?.status === "fixed" ? "locked" : ""),
    reviewState: safeId(asset?.status || "fixed"),
    selectedState: "selected",
    confirmedFixedAsset: ["fixed", "ready"].includes(String(asset?.status || "fixed")),
  });
}

function graphBindingSummary(node, graph, suggestion) {
  if (suggestion?.binding_state !== "bound") return null;
  const fixedId = safeId(suggestion.fixed_visual_asset_id);
  return summaryRecord({
    state: "graph-bound",
    referenceType: "binding",
    targetNode: node,
    targetSlot: safeId(suggestion.graph_asset_id) || "asset_binding",
    targetRef: fixedId,
    asset: {
      visual_asset_id: fixedId,
      asset_id: fixedId,
      label: safeText(suggestion.label),
      asset_type: safeId(suggestion.asset_type),
    },
    sourceEvidence: safeSourceEvidence(suggestion.lineage_refs, {
      source_algorithm_id: safeId(graph.algorithm_id),
      source_relationship_type: "asset_auto_binding_established",
    }),
    confidence: suggestion.confidence,
    reviewState: "bound",
    selectedState: "selected",
    confirmedFixedAsset: Boolean(fixedId),
  });
}

function blockedGraphSummary(node, graph, blocked) {
  return summaryRecord({
    state: "blocked",
    referenceType: "binding",
    targetNode: node,
    targetSlot: safeId(blocked?.graph_asset_id) || "asset_binding",
    targetRef: safeId(blocked?.graph_asset_id),
    asset: {
      label: safeText(blocked?.label),
      asset_type: safeId(blocked?.asset_type),
    },
    sourceEvidence: { source_algorithm_id: safeId(graph?.algorithm_id) },
    confidence: blocked?.confidence,
    reviewState: "needs_attention",
    selectedState: "blocked",
    blockReasons: list(blocked?.block_reasons).map((item) => safeId(item)).filter(Boolean),
  });
}

function generationCandidateSummary(node, candidate) {
  const assetId = safeId(candidate?.asset_id || candidate?.candidate_id || candidate?.id);
  return summaryRecord({
    state: candidate?.status === "rejected" ? "reversed/unbound" : "recognized",
    referenceType: "generation_candidate",
    targetNode: node,
    targetSlot: safeId(candidate?.target_slot || "generation_candidate"),
    targetRef: assetId,
    asset: {
      asset_id: assetId,
      label: safeText(candidate?.label || candidate?.title),
      media_kind: safeId(candidate?.media_kind || "image"),
    },
    sourceEvidence: safeSourceEvidence(candidate?.source_evidence),
    confidence: candidate?.confidence,
    reviewState: safeId(candidate?.status || "succeeded"),
    selectedState: candidate?.status === "rejected" ? "reversed" : "candidate",
  });
}

function referenceStackSummary(node, ref) {
  const conflict = safeId(ref?.conflict_state);
  const referenceType = safeEntity(ref?.reference_type || ref?.studio_entity_id);
  return summaryRecord({
    state: conflict === "blocked" ? "blocked" : conflict === "shadowed" ? "conflicted" : "reused",
    referenceType,
    targetNode: node,
    targetSlot: safeId(ref?.target_slot),
    targetRef: safeId(ref?.target_ref),
    asset: {
      asset_id: safeId(ref?.target_ref),
      label: safeText(ref?.label || ref?.asset_label),
    },
    sourceEvidence: {
      source_algorithm_id: safeId(ref?.source_algorithm_id),
      source_relationship_type: safeId(ref?.source_relationship_type),
      source: safeId(ref?.source),
    },
    confidence: ref?.confidence,
    reviewState: safeId(ref?.status),
    selectedState: conflict || (ref?.selected ? "selected" : "candidate"),
    blockReasons: list(ref?.block_reasons).map((item) => safeId(item)).filter(Boolean),
  });
}

function summaryRecord(options) {
  if (!options) return null;
  const entity = safeEntity(options.referenceType);
  const state = safeState(options.state);
  const reversal = assetReuseReversalForSummary({ studio_entity_id: entity, state });
  const targetNodeId = safeId(options.targetNode?.id);
  const targetSlot = safeId(options.targetSlot);
  const targetRef = safeId(options.targetRef);
  const asset = safeAsset(options.asset);
  const nextAction = state === "blocked" || state === "conflicted" ? "view_evidence" : reversal.action;
  const reuseId = safeId(`${targetNodeId}:${entity}:${targetSlot}:${targetRef || asset.asset_id || asset.label}`);
  return {
    reuse_id: reuseId,
    state,
    studio_entity_id: entity,
    selected_state: safeId(options.selectedState) || "candidate",
    target_ref: targetRef,
    target: { node_id: targetNodeId, slot: targetSlot },
    asset,
    source_evidence: safeSourceEvidence(options.sourceEvidence),
    confidence: safeConfidence(options.confidence),
    lock_state: safeId(options.lockState || "reviewable"),
    review_state: safeId(options.reviewState || "needs_attention"),
    block_reasons: list(options.blockReasons).map((item) => safeId(item)).filter(Boolean).slice(0, 8),
    next_action: nextAction,
    reversal,
    explanation_summary: explanationSummary(state, asset, targetNodeId, targetSlot, nextAction),
    draft_candidate: Boolean(options.draftCandidate),
    confirmed_fixed_asset: Boolean(options.confirmedFixedAsset),
    safety_boundary: safetyBoundary(),
  };
}

function applyRecordedReversal(item, reversals) {
  if (!item || !reversals.has(item.reuse_id)) return item;
  return {
    ...item,
    state: "reversed/unbound",
    selected_state: "reversed",
    review_state: item.reversal.action === "reject" ? "rejected" : "unbound",
    next_action: "view_lineage",
    reversal: { ...item.reversal, applied: true },
  };
}

function reversalActionForEntity(entity) {
  if (entity === "binding") return "unbind";
  if (entity === "generation_candidate") return "reject";
  if (REPLACE_CAPABLE_ENTITIES.has(entity)) return "replace";
  return "view_evidence";
}

function assetBindingGraphs(state, node) {
  const params = node?.params || {};
  return [
    params.assetAutoBindingGraph,
    params.asset_auto_binding_graph,
    params.agentflow_asset_auto_binding_graph,
    params.storyboardBreakdown?.assetAutoBindingGraph,
    params.storyboardBreakdown?.asset_auto_binding_graph,
    state?.assetAutoBindingGraph,
    state?.asset_auto_binding_graph,
  ].filter((graph) => graph?.artifact_type === "agentflow_asset_auto_binding_graph");
}

function nodeReferenceStackRefs(params) {
  const stack = params.nodeReferenceStack || params.node_reference_stack || params.referenceStack || {};
  return [...list(stack.references), ...list(stack.reference_stack)];
}

function generationCandidates(params) {
  return [...list(params.generationCandidates), ...list(params.generation_candidates)];
}

function reversalMap(value) {
  return new Map(list(value).map((item) => [safeId(item?.reuse_id), item]).filter(([key]) => key));
}

function safeAsset(asset) {
  return {
    asset_id: safeId(asset?.asset_id),
    visual_asset_id: safeId(asset?.visual_asset_id),
    label: safeText(asset?.label, 80),
    asset_type: safeId(asset?.asset_type),
    media_kind: safeId(asset?.media_kind),
    mime_type: safeMime(asset?.mime_type),
    role: safeId(asset?.role),
    reference_target: safeId(asset?.reference_target),
  };
}

function safeSourceEvidence(value, extras = {}) {
  const source = { ...(typeof value === "object" && value ? value : {}), ...extras };
  return {
    source_mode: safeId(source.source_mode),
    source_asset_id: safeId(source.source_asset_id),
    source_node_id: safeId(source.source_node_id || source.fixed_source_node_id),
    artifact_id: safeId(source.artifact_id),
    source_contract: safeId(source.source_contract),
    source_stage: safeId(source.source_stage),
    source_algorithm_id: safeId(source.source_algorithm_id),
    source_relationship_type: safeId(source.source_relationship_type),
    source_asset_card_candidate_id: safeId(source.source_asset_card_candidate_id),
    source_human_gate_id: safeId(source.source_human_gate_id),
    user_intent: safeText(source.user_intent, 180),
  };
}

function explanationSummary(state, asset, nodeId, slot, nextAction) {
  const label = asset.label || asset.asset_id || asset.visual_asset_id || "asset";
  return `${state}: ${label} -> ${nodeId}/${slot}; next=${nextAction}`;
}

function safetyBoundary() {
  return {
    provider_calls_started: false,
    provider_raw_response_exposed: false,
    signed_url_exposed: false,
    local_absolute_path_exposed: false,
    media_bytes_exposed: false,
    writes_long_term_memory: false,
    writes_company_kb: false,
    readiness_claimed: false,
    human_acceptance_claimed: false,
    business_validation_claimed: false,
    legal_readiness_claimed: false,
  };
}

function safeState(value) {
  const state = String(value || "").trim();
  return ASSET_REUSE_STATES.includes(state) ? state : "recognized";
}

function safeEntity(value) {
  const entity = safeId(value);
  return entity || "reference_input";
}

function safeConfidence(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) return null;
  return Math.max(0, Math.min(Number(value.toFixed(3)), 1));
}

function safeMime(value) {
  const text = String(value || "").toLowerCase();
  return /^[a-z0-9.+-]+\/[a-z0-9.+-]+$/.test(text) ? text.slice(0, 80) : "";
}

function safeId(value) {
  const text = String(value || "").trim();
  if (containsUnsafeText(text)) return "";
  return text.replace(/[^0-9A-Za-z_.:-]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 160);
}

function safeText(value, limit = 160) {
  return redactUnsafeText(value, limit);
}

function list(value) {
  return Array.isArray(value) ? value : [];
}
