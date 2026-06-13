import { imageSpecLabel, videoSpecLabel } from "./presets/specs.js";
import { cameraSummary } from "./presets/cameras.js";
import { directorPromptSummary, normalizeDirectorSetup, safeDirectorSetup } from "./director-data.js";
import { providerServiceForImageModel } from "./presets/models.js";

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
  const nodeParameters = nodeParameterSnapshot(node);
  const assetRefs = safeAssetRefs(state, node);
  const contextSubgraph = buildContextSubgraph(state, node, "prompt_optimize");
  const referenceCount = collectConnectedImageAssetRefs(state, node).length;
  const connectedReferences = connectedReferenceNodeSummaries(state, node);
  if (directorSetup) nodeParameters.director_summary = directorPromptSummary(normalizeDirectorSetup(directorSetup));
  if (referenceCount) nodeParameters.reference_image_count = referenceCount;
  if (connectedReferences.length) nodeParameters.connected_reference_nodes = connectedReferences;
  return {
    node_id: node.id,
    node_type: normalizeNodeType(node.type),
    prompt_text: String(node.prompt || "").trim() || "请根据当前节点生成专业创作提示词。",
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
function nodeParameterSnapshot(node) {
  const p = node.params || {};
  const snapshot = {
    model: p.model || null,
    llm_provider: "minimax_m3",
    llm_model: "minimax-m3-enhance",
    remote_optimizer_required: true,
  };
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
  if (p.styleRef) snapshot.style_ref = p.styleRef;
  if (p.directorSetup) snapshot.director_summary = directorPromptSummary(normalizeDirectorSetup(p.directorSetup));
  if (p.directorRef) snapshot.director_ref = String(p.directorRef);
  const uploadedImages = uploadReferenceSummaries(node);
  if (uploadedImages.length) snapshot.uploaded_images = uploadedImages;
  return snapshot;
}

export function buildKeyframeGenerationRequest(state, node) {
  const optimizationRequest = buildOptimizationRequest(state, node);
  const spec = node.params?.spec || {};
  const plainOptimizedPrompt = String(node.params?.lastOptimizedPromptPlain || "").trim();
  return {
    node_id: node.id,
    prompt_text: optimizationRequest.prompt_text,
    optimized_prompt: plainOptimizedPrompt || optimizationRequest.prompt_text,
    target_platform: optimizationRequest.target_platform,
    style: optimizationRequest.style,
    aspect_ratio: safeImageAspectRatio(spec.ratio),
    candidate_count: Math.max(1, Math.min(Number(spec.count || 1), 4)),
    provider_service_id: providerServiceForImageModel(node.params?.model),
    asset_refs: optimizationRequest.asset_refs,
    director_setup: optimizationRequest.director_setup,
    node_parameters: optimizationRequest.node_parameters,
    context_subgraph: buildContextSubgraph(state, node, "context_generate"),
    temporary_lock_overrides: node.params?.temporaryLockOverrides || [],
    seed: node.params?.seed ?? null,
    generated_at: new Date().toISOString(),
  };
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
  return {
    id: String(node.id || ""),
    type: normalizeNodeType(node.type),
    title: String(node.title || "").slice(0, 80),
    prompt: String(node.prompt || node.content || "").replace(/\s+/g, " ").trim().slice(0, 240),
    image_asset_refs: nodeImageAssetRefs(node).slice(0, 4),
    visual_asset_ids: nodeVisualAssetIds(node).slice(0, 8),
    director_setup_summary: node.params?.directorSetup
      ? directorPromptSummary(normalizeDirectorSetup(node.params.directorSetup)).slice(0, 240)
      : null,
    node_parameters: safeContextParameters(node),
  };
}

function safeContextParameters(node) {
  const params = nodeParameterSnapshot(node);
  return Object.fromEntries(Object.entries(params).filter(([key]) => !/signature|feature|lock|secret|token/i.test(key)));
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
  const refs = collectConnectedImageAssetRefs(state, node);
  for (const att of node.params?.attachments || []) refs.push(String(att.id || att));
  return refs
    .map((v) => String(v).trim())
    .filter(Boolean)
    .filter((v, i, arr) => arr.indexOf(v) === i)
    .filter((v) => !/[\\/]/.test(v))
    .filter((v) => !/(api_key|bearer|signed_url|token)/i.test(v))
    .slice(0, 3);
}

export function collectConnectedImageAssetRefs(state, node) {
  const refs = [...nodeImageAssetRefs(node)];
  for (const edge of Object.values(state.edges)) {
    if (edge.to !== node.id) continue;
    const upstream = state.nodes[edge.from];
    refs.push(...nodeImageAssetRefs(upstream));
  }
  return refs;
}

function nodeImageAssetRefs(node) {
  if (!node?.params?.uploads) return [];
  return node.params.uploads
    .map((item) => String(item?.asset_id || item?.assetId || "").trim())
    .filter(Boolean);
}

function uploadReferenceSummaries(node) {
  const uploads = Array.isArray(node?.params?.uploads) ? node.params.uploads : [];
  return uploads.map((item) => ({
    asset_id: String(item?.asset_id || item?.assetId || "").trim().slice(0, 80),
    filename: String(item?.filename || item?.label || "").replace(/[\\/]/g, "").slice(0, 120),
    role: String(item?.role || "").slice(0, 60),
  })).filter((item) => item.asset_id || item.filename).slice(-4);
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

function connectedReferenceNodeSummaries(state, node) {
  const summaries = [];
  for (const edge of Object.values(state.edges)) {
    if (edge.to !== node.id) continue;
    const upstream = state.nodes[edge.from];
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

export function normalizeOptimization(result, request) {
  // 只消费用户版字段：中文、分段、无 rule id / trace / 治理文案。
  const userPrompt = String(result?.user_prompt || "").trim();
  const userSections = Array.isArray(result?.user_prompt_sections) ? result.user_prompt_sections : [];
  if (!userPrompt && !userSections.length) throw new Error("运行服务未返回用户版优化结果");
  const sections = userSections.map((s) => ({ name: s.title || s.name, text: s.text }));
  return {
    source: "runtime",
    original: result?.original_prompt || request.prompt_text,
    optimized: userPrompt || sections.map((s) => `${s.name}：${s.text}`).join("\n"),
    plain: String(result?.user_prompt_plain || "").trim() || sections.map((s) => s.text).filter(Boolean).join("\n"),
    sections,
    optimization_mode: result?.optimization_mode || "not_applicable",
    context_bundle: result?.context_bundle || null,
  };
}
