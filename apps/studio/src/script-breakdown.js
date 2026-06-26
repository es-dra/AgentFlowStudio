import { createNode, connect } from "./nodes.js";
import { buildOptimizationRequest, normalizeOptimization } from "./optimizer-contract.js";
import { SCRIPT_UPLOAD_ACCEPT, readScriptFileText, safeFileName, scriptFileExtension } from "./script-file-import.js";
import { refineStructuredShotAssets, structuredShotFromSegment, structuredShotText } from "./structured-shot.js";

const SHOT_MARKER_RE = /^\s*(第?\s*\d+\s*[镜幕场]|镜头\s*\d+|分镜\s*\d+|场景\s*\d+|scene\s*\d+|shot\s*\d+)/i;
const STORYBOARD_PLACEHOLDER_RE = /(推进主体|展示变化|收束结果|保留下一步生成关键帧所需的信息)/;

export function importScriptFileIntoTextNode(store, node, textarea = null) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = SCRIPT_UPLOAD_ACCEPT;
  input.addEventListener("change", async () => {
    const file = input.files?.[0];
    if (!file) return;
    try {
      const text = await readScriptFileText(file);
      updateTextNode(store, node.id, text, {
        title: trimFileTitle(file.name),
        scriptInputMode: "full_script_upload",
        scriptImportState: {
          status: "complete",
          file_name: safeFileName(file.name),
          file_type: scriptFileExtension(file.name),
          completed_at: new Date().toISOString(),
        },
      });
      if (textarea) textarea.value = text;
    } catch (error) {
      setScriptImportError(store, node.id, safeScriptImportError(error));
    }
  }, { once: true });
  input.click();
}

export async function expandTextIdeaToScript(store, runtime, node, textarea = null) {
  const fresh = store.get().nodes[node.id] || node;
  const idea = String(fresh.prompt || fresh.content || "").trim();
  if (!idea) return;
  setScriptExpansionState(store, fresh.id, "running", idea);
  textarea?.classList?.add("prompt-shimmer");
  try {
    const request = buildOptimizationRequest(store.get(), {
      ...fresh,
      type: "script",
      prompt: formalScriptExpansionPrompt(idea),
    });
    request.node_type = "script";
    request.generation_target = "script";
    request.node_parameters = {
      ...(request.node_parameters || {}),
      script_expansion_contract: "formal_script_before_storyboard_breakdown",
      source_idea: idea.slice(0, 600),
      forbidden_output: "storyboard_placeholder_outline",
    };
    const response = runtime?.optimizePrompt ? await runtime.optimizePrompt(request) : null;
    const outcome = response ? normalizeOptimization(response, request) : null;
    const script = normalizeExpandedScript(outcome?.plain || outcome?.optimized, idea);
    updateTextNode(store, fresh.id, script, {
      scriptInputMode: "idea_expanded_script",
      scriptExpansionState: { status: "complete", percent: 100, completed_at: new Date().toISOString() },
    });
    if (textarea) textarea.value = script;
  } catch {
    const script = draftScriptFromIdea(idea);
    updateTextNode(store, fresh.id, script, {
      scriptInputMode: "idea_expanded_script_fallback",
      scriptExpansionState: { status: "fallback", percent: 100, completed_at: new Date().toISOString() },
    });
    if (textarea) textarea.value = script;
  } finally {
    textarea?.classList?.remove("prompt-shimmer");
  }
}

export async function splitTextNodeToStoryboardNodes(store, node, runtime = null) {
  const fresh = store.get().nodes[node.id] || node;
  const source = String(fresh.content || fresh.prompt || "").trim();
  if (!source) return [];
  setStoryboardBreakdownState(store, fresh.id, "running");
  const breakdown = await loadStoryboardBreakdown(store, runtime, fresh, source);
  const shots = breakdown.shots;
  if (!shots.length) return [];
  const createdIds = [];
  const x = fresh.x + fresh.w + 180;
  for (const [index, shot] of shots.entries()) {
    const structuredShot = refineStructuredShotAssets(normalizeStoryboardShot(shot, index + 1), source);
    const shotText = structuredShotText(structuredShot);
    const shotNode = createNode(store, "script", x, fresh.y + index * 230);
    store.set((s) => {
      const target = s.nodes[shotNode.id];
      if (!target) return;
      target.title = `分镜 ${String(index + 1).padStart(2, "0")}`;
      target.prompt = shotText;
      target.content = shotText;
      target.status = "complete";
      target.h = Math.max(280, Math.min(520, 160 + Math.ceil(shotText.length / 26) * 18));
      target.params.sourceTextNodeId = fresh.id;
      target.params.scriptSegmentIndex = index + 1;
      target.params.structuredShot = structuredShot;
      target.params.shotAssetRefs = structuredShot.asset_refs;
      target.params.assetPrepState = {
        status: "pending_user_review",
        downstream_node_ids: [],
        updated_at: new Date().toISOString(),
      };
    });
    connect(store, fresh.id, shotNode.id);
    createdIds.push(shotNode.id);
  }
  store.set((s) => {
    const sourceNode = s.nodes[fresh.id];
    if (!sourceNode) return;
    sourceNode.params.storyboardBreakdown = {
      status: "shots_ready_for_review",
      mode: breakdown.mode,
      shot_count: createdIds.length,
      downstream_node_ids: createdIds,
      asset_node_ids: [],
      asset_nodes_created: false,
      provider_calls_started: Boolean(breakdown.provider_calls_started),
      updated_at: new Date().toISOString(),
    };
    sourceNode.params.storyboardBreakdownState = { status: "complete", percent: 100, completed_at: new Date().toISOString() };
    sourceNode.status = "complete";
  });
  return createdIds;
}

export function splitScriptIntoShots(source) {
  const text = String(source || "").trim();
  if (!text) return [];
  const lines = text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const marked = splitByMarkedLines(lines);
  if (marked.length > 1) return marked;
  const paragraphs = text.split(/\n\s*\n/).map(cleanSegment).filter(Boolean);
  if (paragraphs.length > 1) return paragraphs.slice(0, 24);
  return sentenceChunks(text).slice(0, 24);
}

function splitByMarkedLines(lines) {
  const chunks = [];
  let current = [];
  for (const line of lines) {
    if (SHOT_MARKER_RE.test(line) && current.length) {
      chunks.push(cleanSegment(current.join("\n")));
      current = [];
    }
    current.push(line);
  }
  if (current.length) chunks.push(cleanSegment(current.join("\n")));
  return chunks.filter(Boolean);
}

function sentenceChunks(text) {
  const sentences = text
    .split(/(?<=[。！？!?；;])\s*/)
    .map(cleanSegment)
    .filter(Boolean);
  if (!sentences.length) return [text];
  const targetCount = Math.max(1, Math.min(Math.max(Math.ceil(sentences.length / 2), Math.ceil(text.length / 180)), sentences.length, 12));
  return balancedSentenceChunks(sentences, targetCount);
}

function balancedSentenceChunks(sentences, targetCount) {
  const chunks = [];
  for (let index = 0; index < targetCount; index += 1) {
    const start = Math.round(index * sentences.length / targetCount);
    const end = Math.round((index + 1) * sentences.length / targetCount);
    const chunk = sentences.slice(start, end).join("");
    if (chunk) chunks.push(chunk);
  }
  return chunks;
}

function normalizeExpandedScript(value, idea) {
  const text = String(value || "").trim();
  if (!text || looksLikeStoryboardPlaceholder(text)) return draftScriptFromIdea(idea);
  return text;
}

function looksLikeStoryboardPlaceholder(text) {
  const lines = String(text || "").split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
  const markerCount = lines.filter((line) => SHOT_MARKER_RE.test(line)).length;
  return markerCount >= 3 && STORYBOARD_PLACEHOLDER_RE.test(text);
}

function draftScriptFromIdea(idea) {
  const clean = cleanSegment(idea);
  const title = fallbackScriptTitle(clean);
  return [
    `片名：《${title}》`,
    "",
    `故事从一个清晰的核心画面展开：${clean}。开场先交代主要人物或核心物体所处的环境，让观众立刻理解它为什么出现在这里，以及这个瞬间带来的情绪基调。`,
    "",
    "随着时间推进，主角或核心物体开始产生细微动作和情绪变化。周围的光线、声音、空间细节共同推动气氛，让画面从静态设定进入一个可被感知的故事时刻，而不是只停留在概念展示。",
    "",
    "结尾给出一个明确但不过度解释的动作或结果：主角完成一次选择、凝视、触碰、离开或停留。这个收束要保留下一步拆分分镜所需的人物、场景、动作、情绪和视觉重点。",
  ].join("\n");
}

function fallbackScriptTitle(clean) {
  const compact = clean.replace(/[，。！？；、,.!?;:：\s]+/g, "");
  return (compact || "短片").slice(0, 12);
}

function formalScriptExpansionPrompt(idea) {
  return [
    "请把下面的一句话扩写成正式短视频剧本正文，而不是分镜列表。",
    "输出要求：",
    "- 先给片名，再给连续叙事正文。",
    "- 明确角色、场景、情绪、动作变化和结尾。",
    "- 不要输出“分镜 01/02/03/04”，不要写占位句，不要写“推进主体/展示变化/收束结果”。",
    "- 文字要能在下一步再拆分成分镜。",
    "",
    `原始想法：${cleanSegment(idea)}`,
  ].join("\n");
}

async function loadStoryboardBreakdown(store, runtime, node, source) {
  if (runtime?.breakdownStoryboard) {
    try {
      const payload = await runtime.breakdownStoryboard({
        node_id: node.id,
        script_text: source,
        target_platform: "short_video",
        style: "cinematic",
        node_parameters: {
          llm_provider: node.params?.llm_provider || node.params?.llmProvider || "prompt_optimizer",
        },
        generated_at: new Date().toISOString(),
      });
      const shots = normalizeStoryboardShotList(payload?.shots);
      if (shots.length) {
        return {
          shots,
          mode: payload?.safe_manifest?.status || "runtime_storyboard_breakdown",
          provider_calls_started: Boolean(payload?.provider_calls_started),
        };
      }
    } catch (error) {
      setStoryboardBreakdownState(store, node.id, "fallback", safeBreakdownError(error));
    }
  }
  return {
    shots: splitScriptIntoShots(source).map((segment, index) => structuredShotFromSegment(segment, index + 1)),
    mode: "local_fallback",
    provider_calls_started: false,
  };
}

function normalizeStoryboardShotList(value) {
  if (!Array.isArray(value)) return [];
  return value.map((shot, index) => normalizeStoryboardShot(shot, index + 1));
}

function normalizeStoryboardShot(shot, fallbackIndex) {
  if (typeof shot === "string") return structuredShotFromSegment(shot, fallbackIndex);
  const source = String(shot?.source_text || shot?.description || "").trim();
  const fallback = structuredShotFromSegment(source, fallbackIndex);
  const assetRefs = Array.isArray(shot?.asset_refs) && shot.asset_refs.length
    ? shot.asset_refs.map((asset, index) => normalizeAssetRef(asset, index)).filter(Boolean)
    : fallback.asset_refs;
  return {
    ...fallback,
    shot_id: String(shot?.shot_id || fallback.shot_id),
    index: Number(shot?.index || fallbackIndex),
    duration: String(shot?.duration || fallback.duration),
    description: String(shot?.description || fallback.description),
    shot_size: String(shot?.shot_size || fallback.shot_size),
    light_atmosphere: String(shot?.light_atmosphere || fallback.light_atmosphere),
    camera_motion: String(shot?.camera_motion || fallback.camera_motion),
    dialogue: String(shot?.dialogue || fallback.dialogue),
    sound: String(shot?.sound || fallback.sound),
    asset_refs: assetRefs,
    source_text: source || fallback.source_text,
  };
}

function normalizeAssetRef(asset, index) {
  if (!asset || typeof asset !== "object") return null;
  const label = String(asset.label || asset.name || "").trim().slice(0, 24);
  if (!label) return null;
  const type = ["character", "scene", "prop"].includes(asset.asset_type) ? asset.asset_type : "character";
  return {
    label,
    asset_id: String(asset.asset_id || `candidate:${type}:${index + 1}`),
    asset_type: type,
    status: String(asset.status || "candidate"),
    source: String(asset.source || "llm"),
  };
}

function updateTextNode(store, nodeId, prompt, params = {}) {
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    node.prompt = prompt;
    node.content = prompt;
    node.status = "complete";
    Object.assign(node.params, params);
    if (params.title) node.title = params.title;
  });
}

function setScriptExpansionState(store, nodeId, status, visibleText = "") {
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    node.params.scriptExpansionState = {
      status,
      percent: status === "running" ? 18 : 100,
      label: "剧本扩写",
      started_at: new Date().toISOString(),
    };
    if (status === "running" && visibleText) {
      node.content = node.content || visibleText;
      node.prompt = visibleText;
      node.status = "generating";
    }
  }, { history: false, persist: false });
}

function setStoryboardBreakdownState(store, nodeId, status, message = "") {
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    node.params.storyboardBreakdownState = {
      status,
      message,
      percent: status === "running" ? 22 : 100,
      label: "分镜拆解",
      updated_at: new Date().toISOString(),
    };
    if (status === "running") node.status = "generating";
  }, { history: false, persist: false });
}

function setScriptImportError(store, nodeId, message) {
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (!node) return;
    node.status = "error";
    node.result = `剧本导入失败：${message}`;
    node.params.scriptImportState = {
      status: "error",
      message,
      completed_at: new Date().toISOString(),
    };
  }, { history: false });
}

function safeBreakdownError(error) {
  const message = error instanceof Error ? error.message : String(error || "");
  return message.replace(/Bearer\s+\S+/gi, "Bearer <redacted>").slice(0, 120);
}

function cleanSegment(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function trimFileTitle(name) {
  const value = String(name || "").replace(/\.(txt|md|markdown|docx?|pptx?)$/i, "").trim();
  return value ? `剧本：${value.slice(0, 24)}` : "剧本文本";
}

function safeScriptImportError(error) {
  const message = error instanceof Error ? error.message : String(error || "无法读取文件");
  return message.replace(/Bearer\s+\S+/gi, "Bearer <redacted>").slice(0, 160);
}
