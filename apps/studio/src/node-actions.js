import { createNode, connect } from "./nodes.js";
import { SAMPLE_SCRIPT, SAMPLE_SCRIPT_TITLE } from "./presets/starters.js";

// Empty-state intent: script starter lays out a safe local upstream example flow.
export function handleNodeIntent(store, node, intent) {
  if (node.type === "script" && intent === "剧本生成分镜脚本") {
    spawnSampleScriptFlow(store, node);
    return;
  }
  store.set((s) => {
    const target = s.nodes[node.id];
    if (target) target.params.intent = intent;
    s.selection = { nodeIds: [node.id], edgeId: null };
  });
}

export function spawnSampleScriptFlow(store, scriptNode) {
  const textNode = createNode(store, "text", scriptNode.x - 420, scriptNode.y + 140);
  const groupId = store.nextId("group");
  store.set((s) => {
    const t = s.nodes[textNode.id];
    t.title = "文本";
    t.content = SAMPLE_SCRIPT;
    t.h = 320;
    t.status = "complete";
    const sc = s.nodes[scriptNode.id];
    sc.params.attachments = [{ id: textNode.id, label: SAMPLE_SCRIPT_TITLE }];
    s.groups[groupId] = {
      id: groupId,
      title: `预设 - ${SAMPLE_SCRIPT_TITLE}`,
      nodeIds: [scriptNode.id, textNode.id],
    };
    t.groupId = groupId;
    sc.groupId = groupId;
    s.selection = { nodeIds: [scriptNode.id], edgeId: null };
  });
  connect(store, textNode.id, scriptNode.id);
}

// 发送（Ctrl+Enter / 发送按钮）：本地安全预览，不触发 provider。
export function startLocalPreview(store, node, resultText) {
  store.set((s) => {
    const n = s.nodes[node.id];
    if (!n) return;
    n.status = "generating";
  });
  setTimeout(() => {
    store.set((s) => {
      const n = s.nodes[node.id];
      if (!n) return;
      n.status = "complete";
      n.result = resultText || buildPreviewResult(n);
      const asset = visibleAssetForNode(store, n);
      s.assets.unshift({
        ...asset,
        created_at: new Date().toISOString(),
      });
    });
  }, 1200);
}

export function visibleAssetForNode(store, node) {
  const kind = assetKind(node.type);
  return {
    id: store.nextId("asset"),
    kind,
    title: assetTitle(node),
    safe_summary: assetSummary(node),
    thumbnail_ref: thumbnailForKind(kind),
    source_node_id: node.id,
    status: "ready",
  };
}

function buildPreviewResult(node) {
  const prompt = (node.prompt || "").trim();
  const head = {
    text: "文本结果（本地预览）",
    image: "图片结果占位（本地预览）",
    video: "视频结果占位（本地预览）",
    audio: "音频结果占位（本地预览）",
    script: "分镜脚本占位（本地预览）",
    video_merge: "合成结果占位（本地预览）",
  }[node.type] || "结果占位（本地预览）";
  return `${head}\n${prompt ? `提示词：${prompt}` : "（未输入提示词）"}`;
}

function assetKind(type) {
  return {
    text: "text_brief",
    image: "keyframe",
    video: "video_clip",
    audio: "audio_clip",
    script: "storyboard",
    director: "director_setup",
    video_merge: "video_comp",
  }[type] || "reference";
}

function assetTitle(node) {
  const fallback = {
    text: "文本创作摘要",
    image: "关键帧预览",
    video: "5s 视频片段预览",
    audio: "音频预览",
    script: "分镜脚本预览",
    director: "导演台布置",
    video_merge: "合成预览",
  }[node.type] || "显性资产";
  return node.title || fallback;
}

function assetSummary(node) {
  if (node.type === "director" && node.params?.directorSummary) return node.params.directorSummary;
  const prompt = (node.prompt || node.result || node.content || "").replace(/\s+/g, " ").trim();
  return prompt.slice(0, 90) || "本地预览生成的安全摘要，可作为后续节点参考。";
}

function thumbnailForKind(kind) {
  return {
    text_brief: "text",
    keyframe: "keyframe",
    video_clip: "video",
    audio_clip: "audio",
    storyboard: "storyboard",
    director_setup: "director-board",
    video_comp: "video",
  }[kind] || "reference";
}
