import { imageSpecLabel, videoSpecLabel } from "./presets/specs.js";
import { cameraSummary } from "./presets/cameras.js";
import { directorPromptSummary, normalizeDirectorSetup, safeDirectorSetup } from "./director-data.js";
import { providerServiceForImageModel } from "./presets/models.js";
import { assetCardPromptText, safeAssetCardSnapshot } from "./asset-card-generation-prompt.js";
import { assetReuseLocalContract } from "./asset-reuse-contract.js";
import { containsUnsafeText, redactUnsafeText } from "./safe-text-redaction.js";
import {
  appendKeyframeConstraintPrompt,
  isKeyframeConstraintNode,
  keyframeConstraintsProviderSnapshot,
  temporaryAssetExclusionsForKeyframeConstraints,
} from "./keyframe-constraints.js";
import {
  assetCardNodeUploadImageRefs,
  assetCardReferenceImageRefs,
  assetCardRevisionImageRefs,
  safeAssetCardRevisionSnapshot,
} from "./asset-revision-references.js";
import { feedbackOverlayDecisionsForRequest } from "./feedback-context-overlays.js";

const GENERATION_TARGET = {
  text: "prompt",
  image: "image",
  video: "video",
  video_merge: "video",
  audio: "audio",
  script: "script",
  director: "prompt",
};

export function buildOptimizationRequest(state, node) {
  const directorSetup = linkedDirectorSetup(state, node);
  const nodeParameters = nodeParameterSnapshot(node, state);
  const assetRefs = safeAssetRefs(state, node);
  const contextSubgraph = buildContextSubgraph(state, node, "prompt_optimize");
  const referenceCount = assetRefs.length;
  const connectedReferences = connectedReferenceNodeSummaries(state, node);
  if (directorSetup) nodeParameters.director_summary = directorPromptSummary(normalizeDirectorSetup(directorSetup));
  if (referenceCount) nodeParameters.reference_image_count = referenceCount;
  if (connectedReferences.length) nodeParameters.connected_reference_nodes = connectedReferences;
  return {
    node_id: node.id,
    node_type: normalizeNodeType(node.type),
    prompt_text: primaryPromptText(node),
    generation_target: GENERATION_TARGET[node.type] || "prompt",
    target_platform: "short_video",
    style: node.params?.styleRef || "cinematic",
    asset_refs: assetRefs,
    director_setup: directorSetup ? safeDirectorSetup(directorSetup) : null,
    node_parameters: nodeParameters,
    context_subgraph: contextSubgraph,
    generated_at: new Date().toISOString(),
  };
}

function normalizeNodeType(type) {
  const allowed = ["text", "image", "video", "audio", "script", "director", "video_merge"];
  return allowed.includes(type) ? type : "text";
}

// 节点结构化参数快照：作为优化的硬约束上下文（后端按需消费，未知字段被忽略）。
function nodeParameterSnapshot(node, state = null) {
  const p = node.params || {};
  const snapshot = {
    model: p.model || null,
    llm_provider: "prompt_optimizer",
    llm_model: "prompt-optimizer",
    remote_optimizer_required: true,
  };
  if (p.nodeRole) snapshot.node_role = String(p.nodeRole).slice(0, 80);
  if (p.assetCardDraft) snapshot.asset_card_draft = safeAssetCardSnapshot(p.assetCardDraft);
  if (p.assetCardRevision) snapshot.asset_card_revision = safeAssetCardRevisionSnapshot(p.assetCardRevision);
  if (node.type === "image" && p.spec) {
    snapshot.spec = imageSpecLabel(p.spec);
    snapshot.panorama = Boolean(p.spec.panorama);
    if (p.camera) snapshot.camera = cameraSummary(p.camera);
  }
  if ((node.type === "video" || node.type === "video_merge") && p.spec) {
    snapshot.spec = videoSpecLabel(p.spec);
    snapshot.mode = p.spec.mode || null;
    if (p.motion) snapshot.motion = p.motion;
    if (p.effect) snapshot.effect = p.effect;
  }
  if (node.type === "video" || node.type === "video_merge") {
    if (p.firstFrameImageAssetId) snapshot.first_frame_image_asset_id = String(p.firstFrameImageAssetId);
    if (p.lastFrameImageAssetId) snapshot.last_frame_image_asset_id = String(p.lastFrameImageAssetId);
    if (p.spec?.duration) snapshot.duration = String(p.spec.duration);
  }
  if (p.styleRef) snapshot.style_ref = p.styleRef;
  if (p.directorSetup) snapshot.director_summary = directorPromptSummary(normalizeDirectorSetup(p.directorSetup));
  if (p.directorRef) snapshot.director_ref = String(p.directorRef);
  const overlayDecisions = feedbackOverlayDecisionsForRequest(p.feedbackOverlayDecisions);
  if (overlayDecisions.length) snapshot.feedback_context_overlay_decisions = overlayDecisions;
  if (p.nodeRole === "keyframe_generation") {
    const keyframeConstraints = keyframeConstraintsProviderSnapshot(p.keyframeConstraints);
    if (keyframeConstraints) snapshot.keyframe_constraints = keyframeConstraints;
  }
  const uploadedImages = uploadReferenceSummaries(node);
  if (uploadedImages.length) snapshot.uploaded_images = uploadedImages;
  const assetReuse = assetReuseLocalContract(state || { nodes: { [node.id]: node }, edges: {}, assets: [] }, node);
  if (assetReuse.items.length) snapshot.asset_reuse = assetReuse;
  return snapshot;
}

function primaryPromptText(node) {
  const assetPrompt = assetCardPromptText(node);
  if (assetPrompt) return assetPrompt;
  const explicit = String(node.prompt || "").trim();
  if (explicit) return keyframeProviderPromptText(explicit, node);
  const content = String(node.content || "").trim();
  if (content) return keyframeProviderPromptText(content, node);
  if (isKeyframeConstraintNode(node)) return keyframeProviderPromptText("", node);
  return "请根据当前节点生成专业创作提示词。";
}

export function buildKeyframeGenerationRequest(state, node) {
  const optimizationRequest = buildOptimizationRequest(state, node);
  const spec = node.params?.spec || {};
  const plainOptimizedPrompt = String(node.params?.lastOptimizedPromptPlain || "").trim();
  const optimizedPrompt = plainOptimizedPrompt
    ? keyframeProviderPromptText(plainOptimizedPrompt, node)
    : optimizationRequest.prompt_text;
  return {
    node_id: node.id,
    prompt_text: optimizationRequest.prompt_text,
    optimized_prompt: optimizedPrompt,
    target_platform: optimizationRequest.target_platform,
    style: optimizationRequest.style,
    aspect_ratio: safeImageAspectRatio(spec.ratio),
    candidate_count: Math.max(1, Math.min(Number(spec.count || 1), 4)),
    provider_service_id: providerServiceForImageModel(node.params?.model),
    asset_refs: optimizationRequest.asset_refs,
    director_setup: optimizationRequest.director_setup,
    node_parameters: generationNodeParameters(optimizationRequest.node_parameters),
    context_subgraph: buildContextSubgraph(state, node, "context_generate"),
    temporary_lock_overrides: node.params?.temporaryLockOverrides || [],
    temporary_asset_exclusions: temporaryAssetExclusionsForKeyframeConstraints(
      node.params?.keyframeConstraints,
      node.params?.temporaryAssetExclusions || [],
    ),
    seed: node.params?.seed ?? null,
    generated_at: new Date().toISOString(),
  };
}

function keyframeProviderPromptText(baseText, node) {
  if (!isKeyframeConstraintNode(node)) return String(baseText || "").trim();
  return appendKeyframeConstraintPrompt(baseText, node.params?.keyframeConstraints);
}

function generationNodeParameters(params) {
  const safe = { ...(params || {}) };
  delete safe.asset_reuse;
  return safe;
}

export function buildContextSubgraph(state, node, runtimeWorkMode = "context_generate") {
  const nodes = [];
  const edges = [];
  const seenNodes = new Set();
  const seenEdges = new Set();
  const visited = new Map();
  const queue = [{ id: node.id, costHop: 0, referenceDepth: 0 }];
  while (queue.length && nodes.length < 24) {
    const current = queue.shift();
    const item = state.nodes[current.id];
    if (!item || current.costHop > 3 || current.referenceDepth > 6) continue;
    const prior = visited.get(item.id);
    if (prior && prior.costHop <= current.costHop && prior.referenceDepth <= current.referenceDepth) continue;
    visited.set(item.id, { costHop: current.costHop, referenceDepth: current.referenceDepth });
    if (!seenNodes.has(item.id)) {
      seenNodes.add(item.id);
      nodes.push(safeContextNode(item));
    }
    for (const edge of Object.values(state.edges)) {
      if (edge.to !== item.id || seenEdges.has(edge.id) || edges.length >= 32) continue;
      const relation = safeRelation(edge.relation_type || edge.relationType);
      const nextCostHop = relation === "reference" ? current.costHop : current.costHop + 1;
      const nextReferenceDepth = relation === "reference" ? current.referenceDepth + 1 : current.referenceDepth;
      if (nextCostHop > 3 || nextReferenceDepth > 6) continue;
      seenEdges.add(edge.id);
      edges.push({
        id: String(edge.id || ""),
        from: String(edge.from || ""),
        to: String(edge.to || ""),
        relation_type: relation,
      });
      queue.push({ id: edge.from, costHop: nextCostHop, referenceDepth: nextReferenceDepth });
    }
  }
  return {
    target_node_id: node.id,
    runtime_work_mode: runtimeWorkMode,
    nodes,
    edges,
  };
}

function safeContextNode(node) {
  const suppressDraftUploads = node.params?.nodeRole === "asset_card_draft" && !hasFixedVisualAssets(node);
  const draftRefs = assetCardReferenceImageRefs(node);
  return {
    id: String(node.id || ""),
    type: normalizeNodeType(node.type),
    title: String(node.title || "").slice(0, 80),
    prompt: String(node.prompt || node.content || "").replace(/\s+/g, " ").trim().slice(0, 240),
    image_asset_refs: suppressDraftUploads ? draftRefs.slice(0, 4) : nodeContextImageAssetRefs(node).slice(0, 4),
    visual_asset_ids: nodeVisualAssetIds(node).slice(0, 8),
    director_setup_summary: node.params?.directorSetup
      ? directorPromptSummary(normalizeDirectorSetup(node.params.directorSetup)).slice(0, 240)
      : null,
    node_parameters: safeContextParameters(node),
  };
}

function safeContextParameters(node) {
  const params = nodeParameterSnapshot(node);
  return Object.fromEntries(Object.entries(params).filter(([key]) => (
    key !== "asset_reuse" && !/signature|feature|lock|secret|token/i.test(key)
  )));
}

function safeRelation(value) {
  return ["reference", "director", "generation"].includes(value) ? value : "generation";
}

function safeImageAspectRatio(value) {
  const allowed = new Set(["1:1", "16:9", "4:3", "3:2", "2:3", "3:4", "9:16", "21:9"]);
  return allowed.has(value) ? value : "9:16";
}

function linkedDirectorSetup(state, node) {
  if (node.type === "director" && node.params?.directorSetup) return node.params.directorSetup;
  if (node.params?.directorSetup) return node.params.directorSetup;
  const incoming = Object.values(state.edges).filter((edge) => edge.to === node.id).reverse();
  for (const edge of incoming) {
    const upstream = state.nodes[edge.from];
    if (upstream?.type === "director" && upstream.params?.directorSetup) {
      return upstream.params.directorSetup;
    }
  }
  return null;
}

function safeAssetRefs(state, node) {
  const refs = [...assetCardRevisionImageRefs(node)];
  if (node.params?.nodeRole === "asset_card_draft") refs.push(...assetCardNodeUploadImageRefs(node));
  if (node.params?.nodeRole === "keyframe_generation") refs.push(...collectConnectedAssetCardImageAssetRefs(state, node));
  if (!refs.length && shouldCollectConnectedUploads(node)) refs.push(...collectConnectedImageAssetRefs(state, node));
  if (node.params?.firstFrameImageAssetId) refs.push(String(node.params.firstFrameImageAssetId));
  if (node.params?.lastFrameImageAssetId) refs.push(String(node.params.lastFrameImageAssetId));
  for (const att of node.params?.attachments || []) refs.push(String(att.id || att));
  return refs
    .map((v) => String(v).trim())
    .filter(Boolean)
    .filter((v, i, arr) => arr.indexOf(v) === i)
    .filter((v) => !/[\\/]/.test(v))
    .filter((v) => !/(api_key|bearer|signed_url|token)/i.test(v))
    .slice(0, 4);
}

export function collectConnectedImageAssetRefs(state, node) {
  const refs = [...nodeContextImageAssetRefs(node)];
  for (const edge of Object.values(state.edges)) {
    if (edge.to !== node.id) continue;
    const upstream = state.nodes[edge.from];
    refs.push(...nodeContextImageAssetRefs(upstream));
  }
  return refs;
}

export function collectConnectedAssetCardImageAssetRefs(state, node) {
  const refs = [...visualAssetImageRefs(node)];
  for (const edge of Object.values(state.edges || {})) {
    if (edge.to !== node.id) continue;
    const upstream = state.nodes?.[edge.from];
    if (!isAssetCardNode(upstream)) continue;
    refs.push(...visualAssetImageRefs(upstream));
    refs.push(...assetCardGeneratedImageRefs(upstream));
    refs.push(...assetCardNodeUploadImageRefs(upstream));
  }
  return refs;
}

function nodeContextImageAssetRefs(node) {
  return dedupe([...nodeImageAssetRefs(node), ...visualAssetImageRefs(node)]);
}

function nodeImageAssetRefs(node) {
  if (!node?.params?.uploads) return [];
  return node.params.uploads
    .map((item) => String(item?.asset_id || item?.assetId || "").trim())
    .filter(Boolean);
}

function assetCardGeneratedImageRefs(node) {
  if (!node?.params?.uploads) return [];
  return node.params.uploads
    .filter((item) => isAssetCardImageReferenceRole(item?.role || item?.source_kind || item?.sourceKind))
    .map((item) => String(item?.asset_id || item?.assetId || "").trim())
    .filter(Boolean);
}

function visualAssetImageRefs(node) {
  const refs = [];
  for (const asset of Array.isArray(node?.params?.visualAssets) ? node.params.visualAssets : []) {
    const values = Array.isArray(asset?.image_asset_refs)
      ? asset.image_asset_refs
      : Array.isArray(asset?.source_image_asset_refs)
        ? asset.source_image_asset_refs
        : [];
    refs.push(...values);
  }
  return refs.map((value) => String(value || "").trim()).filter(Boolean);
}

function isAssetCardImageReferenceRole(value) {
  const role = String(value || "").toLowerCase();
  return ["character_reference", "scene_reference", "prop_reference", "asset_reference"].includes(role);
}

function isAssetCardNode(node) {
  return Boolean(
    node?.params?.assetCardDraft
    || node?.params?.nodeRole === "asset_card_draft"
    || node?.params?.asset_prep?.source_script_node_id
  );
}

function uploadReferenceSummaries(node) {
  const uploads = Array.isArray(node?.params?.uploads) ? node.params.uploads : [];
  return uploads.map((item) => ({
    asset_id: safeUploadToken(item?.asset_id || item?.assetId, 80),
    filename: safeUploadText(item?.filename || item?.label, 120).replace(/[\\/]/g, ""),
    role: safeUploadToken(item?.role, 60),
    reference_target: safeUploadToken(item?.reference_target, 80),
    user_intent: safeUploadText(item?.user_intent, 240),
    media_kind: safeUploadToken(item?.media_kind, 40),
    mime_type: safeUploadMime(item?.mime_type),
  })).filter((item) => item.asset_id || item.filename).slice(-4);
}

function safeUploadToken(value, limit) {
  const text = String(value || "").trim();
  if (containsUnsafeText(text)) return "";
  return text.replace(/[^0-9A-Za-z_.:-]+/g, "_").replace(/^_+|_+$/g, "").slice(0, limit);
}

function safeUploadText(value, limit) {
  return redactUnsafeText(value, limit);
}

function safeUploadMime(value) {
  const text = String(value || "").toLowerCase();
  return /^[a-z0-9.+-]+\/[a-z0-9.+-]+$/.test(text) ? text.slice(0, 80) : "";
}

function nodeVisualAssetIds(node) {
  const values = [
    ...(Array.isArray(node?.params?.visualAssets) ? node.params.visualAssets : []),
    ...(Array.isArray(node?.params?.visual_asset_ids) ? node.params.visual_asset_ids : []),
  ];
  return values
    .map((item) => String(item?.asset_id || item?.assetId || item || "").trim())
    .filter(Boolean)
    .filter((value, index, arr) => arr.indexOf(value) === index)
    .filter((value) => !/[\\/]/.test(value));
}

function dedupe(values) {
  const result = [];
  for (const value of values) {
    const text = String(value || "").trim();
    if (text && !result.includes(text)) result.push(text);
  }
  return result;
}

function connectedReferenceNodeSummaries(state, node) {
  const summaries = [];
  for (const edge of Object.values(state.edges)) {
    if (edge.to !== node.id) continue;
    const upstream = state.nodes[edge.from];
    if (node.params?.nodeRole === "keyframe_generation" && upstream?.params?.nodeRole === "asset_card_draft" && !hasFixedVisualAssets(upstream)) {
      continue;
    }
    const refs = nodeImageAssetRefs(upstream);
    if (!upstream || (!refs.length && !String(upstream.prompt || "").trim())) continue;
    summaries.push({
      node_id: upstream.id,
      node_type: normalizeNodeType(upstream.type),
      title: String(upstream.title || "").slice(0, 40),
      prompt: String(upstream.prompt || "").trim().slice(0, 180),
      image_asset_refs: refs.slice(0, 4),
    });
  }
  return summaries.slice(0, 6);
}

function shouldCollectConnectedUploads(node) {
  return !["keyframe_generation", "asset_card_draft"].includes(node?.params?.nodeRole);
}

function hasFixedVisualAssets(node) {
  return (Array.isArray(node?.params?.visualAssets) ? node.params.visualAssets : [])
    .some((asset) => ["fixed", "ready"].includes(String(asset?.status || "")));
}

export function normalizeOptimization(result, request) {
  // 只消费用户版字段：中文、分段、无 rule id / trace / 治理文案。
  const userPrompt = String(result?.user_prompt || "").trim();
  const userSections = Array.isArray(result?.user_prompt_sections) ? result.user_prompt_sections : [];
  if (!userPrompt && !userSections.length) throw new Error("运行服务未返回用户版优化结果");
  const sections = userSections.map((s) => ({ name: s.title || s.name, text: s.text }));
  const modelCallContextId = String(result?.model_call_context_id || result?.model_call_context_summary?.context_id || "").trim();
  return {
    source: "runtime",
    original: result?.original_prompt || request.prompt_text,
    optimized: userPrompt || sections.map((s) => `${s.name}：${s.text}`).join("\n"),
    plain: String(result?.user_prompt_plain || "").trim() || sections.map((s) => s.text).filter(Boolean).join("\n"),
    sections,
    optimization_mode: result?.optimization_mode || "not_applicable",
    context_bundle: result?.context_bundle || null,
    model_call_context_id: modelCallContextId,
    model_call_context_summary: normalizeModelCallContextSummary(result?.model_call_context_summary, modelCallContextId),
  };
}

export function normalizeModelCallContextSummary(summary, fallbackContextId = "") {
  const source = safeSummaryObject(summary);
  const contextId = String(source.context_id || fallbackContextId || "").trim();
  if (!contextId) return null;
  const contextSources = safeSummaryObject(source.context_sources);
  const assetContext = safeSummaryObject(source.asset_context);
  const referenceContext = safeSummaryObject(source.reference_context);
  const providerConstraints = safeSummaryObject(source.provider_constraints);
  const traceSummary = safeSummaryObject(source.trace_summary);
  const safetyBoundary = safeSummaryObject(source.safety_boundary);
  return {
    context_id: contextId,
    schema_version: String(source.schema_version || ""),
    operation_intent: String(source.operation_intent || ""),
    generation_target: String(source.generation_target || ""),
    artifact: safeArtifactRef(source.artifact),
    context_sources: {
      context_bundle_present: Boolean(contextSources.context_bundle_present),
      included_asset_count: safeSummaryCount(contextSources.included_asset_count),
      excluded_asset_count: safeSummaryCount(contextSources.excluded_asset_count),
      feedback_context_overlay_count: safeSummaryCount(contextSources.feedback_context_overlay_count),
      upstream_ref_count: safeSummaryCount(contextSources.upstream_ref_count),
    },
    asset_context: {
      context_eligible_asset_count: safeSummaryCount(assetContext.context_eligible_asset_count),
      draft_assets_enter_context: Boolean(assetContext.draft_assets_enter_context),
    },
    reference_context: {
      reference_image_count: safeSummaryCount(referenceContext.reference_image_count),
    },
    provider_constraints: {
      capability: String(providerConstraints.capability || ""),
      provider_gate: String(providerConstraints.provider_gate || ""),
    },
    trace_summary: {
      warning_ids: safeSummaryRefs(traceSummary.warning_ids),
      feedback_context_overlay_ids: safeSummaryRefs(traceSummary.feedback_context_overlay_ids),
    },
    safety_boundary: {
      no_secrets: Boolean(safetyBoundary.no_secrets),
      no_provider_raw: Boolean(safetyBoundary.no_provider_raw),
      no_credentialed_url: Boolean(safetyBoundary.no_credentialed_url),
      no_local_path: Boolean(safetyBoundary.no_local_path),
      no_media_bytes: Boolean(safetyBoundary.no_media_bytes),
      feedback_is_not_memory: Boolean(safetyBoundary.feedback_is_not_memory),
      draft_assets_are_not_context_truth: Boolean(safetyBoundary.draft_assets_are_not_context_truth),
    },
    non_claims: safeSummaryRefs(source.non_claims),
  };
}

function safeArtifactRef(value) {
  const artifact = safeSummaryObject(value);
  if (!artifact.artifact_id && !artifact.filename) return null;
  return {
    artifact_id: String(artifact.artifact_id || ""),
    artifact_type: String(artifact.artifact_type || ""),
    filename: String(artifact.filename || ""),
    role: String(artifact.role || ""),
    media_type: String(artifact.media_type || ""),
  };
}

function safeSummaryObject(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function safeSummaryCount(value) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.max(0, Math.round(number)) : 0;
}

function safeSummaryRefs(value) {
  if (!Array.isArray(value)) return [];
  return value
    .map((item) => String(item || "").trim())
    .filter(Boolean)
    .filter((item, index, arr) => arr.indexOf(item) === index)
    .slice(0, 12);
}
