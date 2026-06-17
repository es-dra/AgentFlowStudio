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
  return prompt.slice(0, 90) || "生成后的安全摘要会在这里显示。";
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
