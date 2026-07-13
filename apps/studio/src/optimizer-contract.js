import { imageSpecLabel, videoSpecLabel } from "./presets/specs.js";
import { cameraSummary } from "./presets/cameras.js";
import { directorPromptSummary, normalizeDirectorSetup, safeDirectorSetup } from "./director-data.js";
import { providerServiceForImageModel } from "./presets/models.js";
import { assetCardPromptText, safeAssetCardSnapshot } from "./asset-card-generation-prompt.js";
import {
  ASSET_REUSE_CONTRACT_VERSION,
  ASSET_REUSE_STATES,
  assetReuseSummariesForNode,
} from "./asset-reuse-contract.js";
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

const SCRIPT_SURFACE_MARKERS = [
  "片名",
  "镜号",
  "画面描述",
  "分镜",
  "镜头",
  "时长",
  "景别",
  "光影氛围",
  "运镜",
  "对白",
  "旁白",
  "音效",
  "资产",
];

const RUNTIME_FORBIDDEN_REQUEST_FRAGMENTS = [
  "D:\\",
  "C:\\",
  "data/processed/runs",
  "data/raw/",
  ".mp4",
  ".mov",
  "api_key",
  "access_token",
  "refresh_token",
  "secret_key",
  "client_secret",
  "authorization:",
  "bearer ",
  "cookie=",
  "signed_url",
];

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
    generation_target: inferredGenerationTarget(node),
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

function inferredGenerationTarget(node) {
  if (looksLikeScriptSurfaceNode(node)) return "script";
  return GENERATION_TARGET[node.type] || "prompt";
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
  if (p.scriptInputMode) snapshot.scriptInputMode = String(p.scriptInputMode).slice(0, 80);
  if (p.sourceTextNodeId) snapshot.sourceTextNodeId = String(p.sourceTextNodeId).slice(0, 120);
  if (p.scriptSegmentIndex !== undefined && p.scriptSegmentIndex !== null) {
    const index = Number(p.scriptSegmentIndex);
    if (Number.isFinite(index)) snapshot.scriptSegmentIndex = index;
  }
  if (p.structuredShot && typeof p.structuredShot === "object") {
    snapshot.structuredShot = safeStructuredShotSnapshot(p.structuredShot);
  }
  if (p.storyboardBreakdown && typeof p.storyboardBreakdown === "object") {
    snapshot.storyboardBreakdown = safeStoryboardBreakdownSnapshot(p.storyboardBreakdown);
  }
  if (looksLikeScriptSurfaceNode(node)) {
    snapshot.script_surface_intent = "preserve_script_shape";
    if (!snapshot.scriptInputMode) snapshot.scriptInputMode = "inferred_script_surface";
  }
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
  const assetReuse = assetReusePromptOptimizerSnapshot(state || { nodes: { [node.id]: node }, edges: {}, assets: [] }, node);
  if (assetReuse.items.length) snapshot.asset_reuse = assetReuse;
  return snapshot;
}

function looksLikeScriptSurfaceNode(node) {
  if (!node) return false;
  if (node.type === "script") return true;
  const p = node.params || {};
  if (p.scriptInputMode || p.sourceTextNodeId || p.scriptSegmentIndex !== undefined || p.structuredShot || p.storyboardBreakdown) return true;
  if (node.type !== "text") return false;
  const text = `${node.content || ""}\n${node.prompt || ""}`.trim();
  if (!text) return false;
  const markerCount = SCRIPT_SURFACE_MARKERS.reduce((count, marker) => count + (text.includes(marker) ? 1 : 0), 0);
  if (markerCount >= 2) return true;
  return text.length >= 120 && /(?:角色|人物|场景|动作|转折|结尾|冲突|对白|旁白)/.test(text) && /(?:。|！|\n)/.test(text);
}

function safeStructuredShotSnapshot(shot) {
  const refs = Array.isArray(shot.asset_refs) ? shot.asset_refs : [];
  return {
    shot_id: String(shot.shot_id || "").slice(0, 80),
    index: Number.isFinite(Number(shot.index)) ? Number(shot.index) : null,
    duration: String(shot.duration || "").slice(0, 40),
    description: String(shot.description || "").slice(0, 900),
    shot_size: String(shot.shot_size || "").slice(0, 80),
    light_atmosphere: String(shot.light_atmosphere || "").slice(0, 180),
    camera_motion: String(shot.camera_motion || "").slice(0, 180),
    asset_refs: refs.slice(0, 8).map((asset) => ({
      label: String(asset?.label || asset?.display_name || "").slice(0, 80),
      asset_type: String(asset?.asset_type || "").slice(0, 40),
      status: String(asset?.status || "").slice(0, 40),
    })),
  };
}

function safeStoryboardBreakdownSnapshot(value) {
  const shots = Array.isArray(value.shots) ? value.shots : [];
  return {
    status: String(value.status || value.safe_manifest?.status || "").slice(0, 80),
    mode: String(value.planning_mode || value.mode || "").slice(0, 80),
    shot_count: shots.length || Number(value.shot_count || 0) || 0,
  };
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
    filename: safeUploadFilename(item?.filename || item?.label, 120),
    role: safeUploadToken(item?.role, 60),
    reference_target: safeUploadToken(item?.reference_target, 80),
    user_intent: safeUploadText(item?.user_intent, 240),
    media_kind: safeUploadToken(item?.media_kind, 40),
    mime_type: safeUploadMime(item?.mime_type),
  })).filter((item) => item.asset_id || item.filename).slice(-4);
}

function assetReusePromptOptimizerSnapshot(state, node) {
  const items = assetReuseSummariesForNode(state, node)
    .map(assetReusePromptOptimizerItem)
    .filter(Boolean)
    .slice(0, 16);
  return {
    artifact_type: "studio_asset_reuse_prompt_optimizer_summary",
    contract_version: ASSET_REUSE_CONTRACT_VERSION,
    node_id: safeUploadToken(node?.id, 120),
    states: [...ASSET_REUSE_STATES],
    summary: assetReusePromptOptimizerSummary(items),
    items,
    non_claims: [
      "not provider smoke",
      "not generated media QA",
      "not human acceptance",
      "not fixed asset promotion",
      "not durable memory promotion",
      "not business validation",
      "not legal readiness",
    ],
  };
}

function assetReusePromptOptimizerSummary(items) {
  return {
    item_count: items.length,
    recognized_count: items.filter((item) => item.state === "recognized").length,
    reused_count: items.filter((item) => item.state === "reused").length,
    graph_bound_count: items.filter((item) => item.state === "graph-bound").length,
    blocked_count: items.filter((item) => item.state === "blocked").length,
    conflicted_count: items.filter((item) => item.state === "conflicted").length,
    reversed_unbound_count: items.filter((item) => item.state === "reversed/unbound").length,
  };
}

function assetReusePromptOptimizerItem(item) {
  if (!item || typeof item !== "object") return null;
  return {
    reuse_id: safeUploadToken(item.reuse_id, 140),
    state: safeUploadText(item.state, 40),
    studio_entity_id: safeUploadToken(item.studio_entity_id, 80),
    selected_state: safeUploadToken(item.selected_state, 80),
    target_ref: safeUploadToken(item.target_ref, 120),
    target: {
      node_id: safeUploadToken(item.target?.node_id, 120),
      slot: safeUploadToken(item.target?.slot, 120),
    },
    asset: {
      asset_id: safeUploadToken(item.asset?.asset_id, 120),
      visual_asset_id: safeUploadToken(item.asset?.visual_asset_id, 120),
      label: safeUploadText(item.asset?.label, 80),
      asset_type: safeUploadToken(item.asset?.asset_type, 40),
      media_kind: safeUploadToken(item.asset?.media_kind, 40),
      mime_type: safeUploadMime(item.asset?.mime_type),
      role: safeUploadToken(item.asset?.role, 60),
      reference_target: safeUploadToken(item.asset?.reference_target, 80),
    },
    source_evidence: {
      source_mode: safeUploadToken(item.source_evidence?.source_mode, 80),
      source_asset_id: safeUploadToken(item.source_evidence?.source_asset_id, 120),
      source_node_id: safeUploadToken(item.source_evidence?.source_node_id, 120),
      artifact_id: safeUploadToken(item.source_evidence?.artifact_id, 120),
      source_contract: safeUploadToken(item.source_evidence?.source_contract, 120),
      source_stage: safeUploadToken(item.source_evidence?.source_stage, 80),
      source_algorithm_id: safeUploadToken(item.source_evidence?.source_algorithm_id, 120),
      source_relationship_type: safeUploadToken(item.source_evidence?.source_relationship_type, 120),
      source_asset_card_candidate_id: safeUploadToken(item.source_evidence?.source_asset_card_candidate_id, 120),
      source_human_gate_id: safeUploadToken(item.source_evidence?.source_human_gate_id, 120),
      user_intent: safeUploadText(item.source_evidence?.user_intent, 180),
    },
    confidence: Number.isFinite(Number(item.confidence)) ? Math.max(0, Math.min(Number(item.confidence), 1)) : null,
    lock_state: safeUploadToken(item.lock_state, 80),
    review_state: safeUploadToken(item.review_state, 80),
    block_reasons: (Array.isArray(item.block_reasons) ? item.block_reasons : [])
      .map((reason) => safeUploadToken(reason, 80))
      .filter(Boolean)
      .slice(0, 8),
    next_action: safeUploadToken(item.next_action, 80),
    draft_candidate: Boolean(item.draft_candidate),
    confirmed_fixed_asset: Boolean(item.confirmed_fixed_asset),
  };
}

function safeUploadToken(value, limit) {
  const text = safeUploadText(value, Math.max(limit, 160));
  if (!text || containsUnsafeText(text) || containsRuntimeForbiddenRequestText(text)) return "";
  return text.replace(/[^0-9A-Za-z_.:-]+/g, "_").replace(/^_+|_+$/g, "").slice(0, limit);
}

function safeUploadText(value, limit) {
  const original = String(value || "");
  return runtimeSafeRequestText(redactUnsafeText(original, Math.max(limit, original.length + 128)), limit);
}

function safeUploadFilename(value, limit) {
  return safeUploadText(value, limit)
    .replace(/[\\/]/g, "")
    .replace(/\.(?:mp4|mov)\b/gi, "_media")
    .slice(0, limit);
}

function safeUploadMime(value) {
  const text = String(value || "").toLowerCase();
  return /^[a-z0-9.+-]+\/[a-z0-9.+-]+$/.test(text) ? text.slice(0, 80) : "";
}

function runtimeSafeRequestText(value, limit) {
  const text = String(value || "")
    .replace(/\.(?:mp4|mov)\b/gi, "_media")
    .replace(/data\/processed\/runs/gi, "runtime-runs")
    .replace(/data\/raw\//gi, "runtime-raw/")
    .replace(/authorization:/gi, "authorization ")
    .replace(/\bbearer\s+/gi, "credential ")
    .replace(/cookie=/gi, "cookie ")
    .replace(/signed_url/gi, "signed-url")
    .replace(/api_key|access_token|refresh_token|secret_key|client_secret/gi, "credential")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, limit);
  return containsRuntimeForbiddenRequestText(text) ? "" : text;
}

function containsRuntimeForbiddenRequestText(value) {
  const text = String(value || "").toLowerCase();
  return RUNTIME_FORBIDDEN_REQUEST_FRAGMENTS.some((fragment) => text.includes(fragment.toLowerCase()));
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
  const creativeRuntimeContractId = String(
    result?.creative_runtime_contract_id || result?.creative_runtime_contract_summary?.contract_id || "",
  ).trim();
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
    creative_runtime_contract_id: creativeRuntimeContractId,
    creative_runtime_contract_summary: normalizeCreativeRuntimeContractSummary(
      result?.creative_runtime_contract_summary,
      creativeRuntimeContractId,
    ),
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

export function normalizeCreativeRuntimeContractSummary(summary, fallbackContractId = "") {
  const source = safeSummaryObject(summary);
  const contractId = String(source.contract_id || fallbackContractId || "").trim();
  if (!contractId) return null;
  const memoryContext = safeSummaryObject(source.memory_context);
  const knowledgeContext = safeSummaryObject(source.knowledge_context);
  const assetContext = safeSummaryObject(source.asset_context);
  const modelCallContext = safeSummaryObject(source.model_call_context);
  const providerContext = safeSummaryObject(source.provider_context);
  const evidenceContext = safeSummaryObject(source.evidence_context);
  return {
    contract_id: contractId,
    schema_version: String(source.schema_version || ""),
    operation: String(source.operation || ""),
    generation_target: String(source.generation_target || ""),
    artifact: safeArtifactRef(source.artifact),
    memory_context: {
      project_memory_count: safeSummaryCount(memoryContext.project_memory_count),
      user_preference_count: safeSummaryCount(memoryContext.user_preference_count),
      promotion_candidates_only: Boolean(memoryContext.promotion_candidates_only),
    },
    knowledge_context: {
      rule_count: safeSummaryCount(knowledgeContext.rule_count),
      director_scenario_count: safeSummaryCount(knowledgeContext.director_scenario_count),
      registry_hash: String(knowledgeContext.registry_hash || ""),
    },
    asset_context: {
      fixed_asset_count: safeSummaryCount(assetContext.fixed_asset_count),
      draft_asset_count: safeSummaryCount(assetContext.draft_asset_count),
      unresolved_asset_count: safeSummaryCount(assetContext.unresolved_asset_count),
    },
    model_call_context: {
      context_id: String(modelCallContext.context_id || ""),
      schema_version: String(modelCallContext.schema_version || ""),
    },
    provider_context: {
      capability: String(providerContext.capability || ""),
      required_gate: String(providerContext.required_gate || ""),
      gate_status: String(providerContext.gate_status || ""),
      provider_calls_started: Boolean(providerContext.provider_calls_started),
    },
    evidence_context: {
      model_call_context_id: String(evidenceContext.model_call_context_id || ""),
      safe_manifest_ref: String(evidenceContext.safe_manifest_ref || ""),
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
