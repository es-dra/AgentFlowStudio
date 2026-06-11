import { imageSpecLabel, videoSpecLabel } from "./presets/specs.js";
import { cameraSummary } from "./presets/cameras.js";
import { directorPromptSummary, normalizeDirectorSetup, safeDirectorSetup } from "./director-data.js";

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
  if (directorSetup) nodeParameters.director_summary = directorPromptSummary(normalizeDirectorSetup(directorSetup));
  return {
    node_id: node.id,
    node_type: normalizeNodeType(node.type),
    prompt_text: String(node.prompt || "").trim() || "请根据当前节点生成专业创作提示词。",
    generation_target: GENERATION_TARGET[node.type] || "prompt",
    target_platform: "short_video",
    style: node.params?.styleRef || "cinematic",
    asset_refs: safeAssetRefs(state, node),
    director_setup: directorSetup ? safeDirectorSetup(directorSetup) : null,
    node_parameters: nodeParameters,
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
  const refs = [];
  for (const edge of Object.values(state.edges)) {
    if (edge.to === node.id) refs.push(edge.from);
  }
  for (const att of node.params?.attachments || []) refs.push(String(att.id || att));
  return refs
    .map((v) => String(v).trim())
    .filter(Boolean)
    .filter((v, i, arr) => arr.indexOf(v) === i)
    .filter((v) => !/[\\/]/.test(v))
    .filter((v) => !/(api_key|bearer|signed_url|token)/i.test(v))
    .slice(0, 3);
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
