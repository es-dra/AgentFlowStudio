import { createNode, connect } from "./nodes.js";
import { buildOptimizationRequest, normalizeOptimization } from "./optimizer-contract.js";
import { structuredShotFromSegment, structuredShotText } from "./structured-shot.js";

const SHOT_MARKER_RE = /^\s*(第?\s*\d+\s*[镜幕场]|镜头\s*\d+|分镜\s*\d+|场景\s*\d+|scene\s*\d+|shot\s*\d+)/i;

export function importScriptFileIntoTextNode(store, node, textarea = null) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = ".txt,.md,.markdown,text/plain,text/markdown";
  input.addEventListener("change", async () => {
    const file = input.files?.[0];
    if (!file) return;
    const text = await file.text();
    updateTextNode(store, node.id, text, {
      title: trimFileTitle(file.name),
      scriptInputMode: "full_script_upload",
    });
    if (textarea) textarea.value = text;
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
    const request = buildOptimizationRequest(store.get(), { ...fresh, type: "script", prompt: idea });
    request.node_type = "script";
    request.generation_target = "script";
    const response = runtime?.optimizePrompt ? await runtime.optimizePrompt(request) : null;
    const outcome = response ? normalizeOptimization(response, request) : null;
    const script = outcome?.plain || outcome?.optimized || draftScriptFromIdea(idea);
    updateTextNode(store, fresh.id, script, {
      scriptInputMode: "idea_expanded_script",
      scriptExpansionState: { status: "complete", completed_at: new Date().toISOString() },
    });
    if (textarea) textarea.value = script;
  } catch {
    const script = draftScriptFromIdea(idea);
    updateTextNode(store, fresh.id, script, {
      scriptInputMode: "idea_expanded_script_fallback",
      scriptExpansionState: { status: "fallback", completed_at: new Date().toISOString() },
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
    const structuredShot = normalizeStoryboardShot(shot, index + 1);
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
    sourceNode.params.storyboardBreakdownState = { status: "complete", completed_at: new Date().toISOString() };
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
  const chunks = [];
  for (let index = 0; index < sentences.length; index += 3) {
    chunks.push(sentences.slice(index, index + 3).join(""));
  }
  return chunks;
}

function draftScriptFromIdea(idea) {
  const clean = cleanSegment(idea);
  return [
    `分镜 01：建立画面。${clean}`,
    `分镜 02：推进主体。围绕核心角色或物体补足动作、情绪和画面重点。`,
    `分镜 03：展示变化。突出冲突、转折或最有传播力的视觉瞬间。`,
    `分镜 04：收束结果。给出清晰结尾，并保留下一步生成关键帧所需的信息。`,
  ].join("\n\n");
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
    node.params.scriptExpansionState = { status, started_at: new Date().toISOString() };
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
    node.params.storyboardBreakdownState = { status, message, updated_at: new Date().toISOString() };
    if (status === "running") node.status = "generating";
  }, { history: false, persist: false });
}

function safeBreakdownError(error) {
  const message = error instanceof Error ? error.message : String(error || "");
  return message.replace(/Bearer\s+\S+/gi, "Bearer <redacted>").slice(0, 120);
}

function cleanSegment(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function trimFileTitle(name) {
  const value = String(name || "").replace(/\.(txt|md|markdown)$/i, "").trim();
  return value ? `剧本：${value.slice(0, 24)}` : "剧本文本";
}
