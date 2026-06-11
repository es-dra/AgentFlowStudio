import { buildPromptOptimization } from "./prompt-optimizer-knowledge.js";

const NODE_TYPE_BY_KIND = {
  node_text: "text",
  text: "text",
  node_image: "image",
  image: "image",
  node_video: "video",
  video: "video",
  node_audio: "audio",
  audio: "audio",
  node_script: "script",
  script: "script",
  node_director: "director",
  director: "director",
  node_video_merge: "video_merge",
  video_merge: "video_merge",
};

const GENERATION_TARGET_BY_NODE_TYPE = {
  text: "prompt",
  image: "image",
  video: "video",
  audio: "audio",
  script: "script",
  director: "prompt",
  video_merge: "video",
};

export function buildRuntimePromptOptimizationRequest(state, card) {
  const nodeType = runtimeNodeType(state, card);
  const promptText = runtimePromptText(state, nodeType, card);
  return {
    node_id: runtimeNodeId(state, card),
    node_type: nodeType,
    prompt_text: promptText || "请根据当前节点生成专业创作提示词。",
    generation_target: GENERATION_TARGET_BY_NODE_TYPE[nodeType] || "prompt",
    target_platform: "short_video",
    style: state.inspectorStyleDirection || state.scriptDraftTone || "cinematic",
    asset_refs: safeArtifactRefs(state, card),
    generated_at: new Date().toISOString(),
  };
}

export function normalizeRuntimePromptOptimization(result, request) {
  const display = buildPromptOptimization(result?.original_prompt || request.prompt_text, { style: request.style });
  return {
    artifact_type: "prompt_optimization_result",
    ui_surface: result?.ui_surface || "node_prompt_optimizer",
    optimization_source: "runtime_service",
    source_prompt: result?.original_prompt || request.prompt_text,
    original_prompt: result?.original_prompt || request.prompt_text,
    optimized_prompt: display.optimized_prompt,
    prompt_sections: display.prompt_sections,
    applied_rules: result?.safe_manifest?.knowledge_rules || [],
    artifacts: result?.artifacts || {},
    safe_manifest: result?.safe_manifest || {},
    warnings: result?.non_claims || [],
  };
}

export function buildFallbackPromptOptimization(request, error) {
  const fallback = buildPromptOptimization(request.prompt_text, { style: request.style });
  return {
    ...fallback,
    ui_surface: "node_prompt_optimizer",
    optimization_source: "local_rule_fallback",
    original_prompt: request.prompt_text,
    source_prompt: request.prompt_text,
    fallback_reason: error instanceof Error ? error.message : String(error),
    warnings: [...(fallback.warnings || []), "已用本地优化"],
  };
}

function runtimePromptText(state, nodeType, card) {
  const scriptPrompt = state.studioStarterKind === "script" || nodeType === "script"
    ? state.scriptDraftGoal
    : "";
  return String(scriptPrompt || state.inspectorPrompt || state.scriptDraftGoal || card?.summary || "").trim();
}

function runtimeNodeType(state, card) {
  const rawKind = String(state.studioAddedNodeKind || state.studioStarterKind || card?.kind || "text");
  if (NODE_TYPE_BY_KIND[rawKind]) return NODE_TYPE_BY_KIND[rawKind];
  if (rawKind.includes("script")) return "script";
  if (rawKind.includes("image")) return "image";
  if (rawKind.includes("video")) return "video";
  if (rawKind.includes("audio")) return "audio";
  if (rawKind.includes("director")) return "director";
  return "text";
}

function runtimeNodeId(state, card) {
  const addedKind = state.studioAddedNodeKind || state.studioStarterKind;
  if (addedKind) return `node_${addedKind}`;
  return card?.id || card?.card_id || state.selectedCardId || "script-input";
}

function safeArtifactRefs(state, card) {
  return [state.selectedArtifactId, card?.primary_artifact_id, state.scriptDraftPreviousArtifactId]
    .filter(Boolean)
    .map((value) => String(value).trim())
    .filter((value, index, values) => values.indexOf(value) === index)
    .filter((value) => !/[\\/]/.test(value))
    .filter((value) => !/(api_key|bearer|signed_url)/i.test(value))
    .slice(0, 3);
}
