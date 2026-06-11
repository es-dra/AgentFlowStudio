const CANVAS_NODE_META = {
  text: ["文本", "输入剧本、旁白、广告词或提示词。"],
  image: ["图片", "上传参考图、图生图或生成关键帧。"],
  video: ["视频", "文生视频、首尾帧或图片参考生成片段。"],
  video_merge: ["视频合成", "连接视频节点后合成为序列。"],
  director: ["导演台", "布置机位、人物、灯光和场景对象。"],
  audio: ["音频", "旁白、音乐、音效和音频驱动视频。"],
  script: ["脚本", "从剧本或视频参考生成分镜脚本。"],
  source: ["素材", "上传或选择历史素材作为当前节点参考。"],
};

export function createCanvasNode(state, kind = "text") {
  const cleanKind = kind || "text";
  const [title, summary] = CANVAS_NODE_META[cleanKind] || CANVAS_NODE_META.text;
  const nodes = Array.isArray(state.canvasCustomNodes) ? state.canvasCustomNodes : [];
  const index = nodes.filter((item) => item.kind === cleanKind).length + 1;
  const id = `${cleanKind}-${Date.now()}-${index}`;
  const position = state.pendingNodePosition || { x: 360 + index * 36, y: 360 + index * 24 };
  state.canvasCustomNodes = [...nodes, { id, kind: cleanKind, title: `${title} ${index}`, summary, status: "待生成" }];
  state.canvasNodePositions = { ...(state.canvasNodePositions || {}), [id]: position };
  state.selectedCardId = id;
  state.selectedNodeIds = [id];
  clearCanvasModes(state);
}

export function openCanvasNode(state, nodeId, kind = "text") {
  const cleanKind = kind || "text";
  state.nodeOpenTransition = state.openedCanvasNodeId && state.openedCanvasNodeId !== nodeId ? "chain" : "enter";
  state.selectedCardId = nodeId || state.selectedCardId;
  state.selectedNodeIds = nodeId ? [nodeId] : state.selectedNodeIds;
  state.openedCanvasNodeId = nodeId || "";
  state.studioAddedNodeKind = cleanKind;
  state.studioStarterKind = "";
  state.studioStarterMode = false;
  state.studioResourceMode = "";
  state.studioPanel = "";
  state.pendingNodePosition = null;
  state.canvasAddMenuScreenX = 0;
  state.canvasAddMenuScreenY = 0;
}

export function nodeOpenTransitionForCanvas(state) {
  if (!state.studioAddedNodeKind) return state.nodeOpenTransition || "";
  return state.nodeOpenTransition === "chain" ? "chain" : "enter";
}

function clearCanvasModes(state) {
  state.pendingNodePosition = null;
  state.canvasAddMenuScreenX = 0;
  state.canvasAddMenuScreenY = 0;
  state.studioPanel = "";
  state.studioStarterKind = "";
  state.studioAddedNodeKind = "";
  state.studioResourceMode = "";
  state.openedCanvasNodeId = "";
  state.nodeOpenTransition = "";
}
