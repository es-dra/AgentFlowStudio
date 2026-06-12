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
  const snapshot = { model: p.model || null };
  if (p.model === "minimax-m3-enhance") snapshot.llm_provider = "minimax_m3";
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
  return snapshot;
}

export function buildKeyframeGenerationRequest(state, node) {
  const optimizationRequest = buildOptimizationRequest(state, node);
  const spec = node.params?.spec || {};
  return {
    node_id: node.id,
    prompt_text: optimizationRequest.prompt_text,
    optimized_prompt: optimizationRequest.prompt_text,
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
  const queue = [{ id: node.id, hop: 0 }];
  while (queue.length && nodes.length < 24) {
    const current = queue.shift();
    const item = state.nodes[current.id];
    if (!item || seenNodes.has(item.id) || current.hop > 3) continue;
    seenNodes.add(item.id);
    nodes.push(safeContextNode(item));
    if (current.hop >= 3) continue;
    for (const edge of Object.values(state.edges)) {
      if (edge.to !== item.id || seenEdges.has(edge.id) || edges.length >= 32) continue;
      seenEdges.add(edge.id);
      edges.push({
        id: String(edge.id || ""),
        from: String(edge.from || ""),
        to: String(edge.to || ""),
        relation_type: safeRelation(edge.relation_type || edge.relationType),
      });
      queue.push({ id: edge.from, hop: current.hop + 1 });
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
    sections,
    context_bundle: result?.context_bundle || null,
  };
}

// Local fallback optimizer: outputs the same six user-facing sections as the backend.
export function buildLocalOptimization(request) {
  const text = request.prompt_text;
  const p = request.node_parameters || {};
  const directorText = request.director_setup
    ? directorPromptSummary(normalizeDirectorSetup(request.director_setup))
    : "";
  const isStill = request.generation_target === "image" || request.generation_target === "keyframe";
  const cameraBits = [
    p.camera ? `摄影参数：${p.camera}` : "",
    p.spec ? `画面规格：${p.spec}` : "",
    p.panorama ? "720° 全景画面，画幅 2:1" : "",
  ].filter(Boolean).join("，");
  const sections = [
    { name: "人物", text: "以原始描述中的主体为核心，保持人物身份、服装与神态在多镜头间一致，避免一次性动作改变人物设定。" },
    {
      name: "场景",
      text: `依据原始描述补全场景：交代地点、时间与氛围${p.style_ref ? `，整体风格为「${p.style_ref}」` : ""}，保留可复用的空间结构与关键道具${directorText ? `；已参考导演台布置：${directorText}` : ""}。`,
    },
    {
      name: "镜头",
      text: `${directorText || cameraBits || (isStill ? "中景为主，主体置于视觉优先位" : "先交代环境再聚焦主体")}，构图清晰，单一镜头只表达一个主要意图。`,
    },
    {
      name: "灯光",
      text: `${directorText ? `参考导演台灯光关系：${directorText}。` : ""}光源有明确动机：主光方向清晰，明暗对比柔和，色温与情绪一致，避免无来源的平光。`,
    },
    {
      name: "运动",
      text: isStill
        ? "静态画面：通过姿态、视线与景深暗示动势，强调材质与细节质感。"
        : `${p.motion ? `运镜采用「${p.motion}」，` : "一个主导镜头运动贯穿始终，"}速度与情绪节奏一致，关键帧之间保持光线与服装连续。`,
    },
    {
      name: "负面约束",
      text: `避免人物畸形、五官扭曲、多余肢体、文字乱码与水印；避免镜头语言互相冲突。${directorText ? "避免光源冲突、机位冲突和空间关系错乱。" : ""}${request.generation_target === "video" ? "避免画面闪烁、场景跳变与身份漂移。" : ""}`,
    },
  ];
  return {
    source: "local",
    original: text,
    optimized: sections.map((s) => `${s.name}：${s.text}`).join("\n"),
    sections,
  };
}
