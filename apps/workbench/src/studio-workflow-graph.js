export const WORKFLOW_NODES = [
  ["script-input", "▤", "剧本输入", "粘贴剧本或输入创作目标。", "待生成"],
  ["storyboard", "▥", "分镜脚本", "拆成镜头编号、画面、台词、运动和时长。", "本地预览"],
  ["character", "◉", "角色三视图", "确定人物正面、侧面、背面和服装版本。", "待生成"],
  ["scene", "▧", "场景资产", "整理空间、道具、时代、材质和参考图。", "已完成"],
  ["keyframe", "▩", "关键帧", "生成每个镜头可复用的首帧。", "排队中"],
  ["director", "◫", "导演台", "布置机位、人物、灯光和遮光器材。", "已完成"],
  ["clip", "▶", "视频片段", "默认 5s，从关键帧生成视频片段。", "生成中"],
  ["compose", "✂", "成片合成", "连接视频节点后整理为可审看的序列。", "待连接"],
];

export const DEFAULT_NODE_POSITIONS = {
  "script-input": { x: 90, y: 110 },
  storyboard: { x: 480, y: 110 },
  character: { x: 870, y: 70 },
  scene: { x: 870, y: 360 },
  keyframe: { x: 1260, y: 120 },
  director: { x: 1260, y: 400 },
  clip: { x: 1650, y: 160 },
  compose: { x: 2040, y: 240 },
};

export const NODE_KIND_META = {
  text: ["text", "TXT", "文本", "输入剧本、广告词、旁白或提示词。", "待生成"],
  image: ["image", "IMG", "图片", "上传参考图、图生图或生成关键帧。", "待生成"],
  video: ["video", "VID", "视频", "文生视频、首尾帧或图片参考生成片段。", "待生成"],
  video_merge: ["video_merge", "CUT", "视频合成", "连接视频节点后合成为序列。", "待连接"],
  director: ["director", "DIR", "导演台", "布置机位、人物、灯光和场景对象。", "本地预览"],
  audio: ["audio", "AUD", "音频", "旁白、音乐、音效和音频驱动视频。", "待生成"],
  script: ["script", "SCR", "脚本", "从剧本或视频参考生成分镜脚本。", "待生成"],
  source: ["source", "SRC", "素材", "上传或选择历史素材作为当前节点参考。", "本地预览"],
};

export const WORKFLOW_NODE_KIND = {
  "script-input": "text",
  storyboard: "script",
  character: "image",
  scene: "image",
  keyframe: "image",
  director: "director",
  clip: "video",
  compose: "video_merge",
};

export const DEFAULT_EDGES = [
  ["script-input", "storyboard"], ["storyboard", "character"], ["storyboard", "scene"],
  ["character", "keyframe"], ["scene", "director"], ["director", "keyframe"],
  ["keyframe", "clip"], ["clip", "compose"],
];

export const NODE_SIZE = { width: 330, height: 224 };

export function workflowNodes(state) {
  const customNodes = Array.isArray(state.canvasCustomNodes) ? state.canvasCustomNodes : [];
  return [
    ...WORKFLOW_NODES,
    ...customNodes.map((node) => {
      const meta = NODE_KIND_META[node.kind] || NODE_KIND_META.text;
      return [node.id, meta[1], node.title || meta[2], node.summary || meta[3], node.status || meta[4]];
    }),
  ];
}

export function nodeKindForCanvasNode(state, id) {
  const custom = Array.isArray(state?.canvasCustomNodes) ? state.canvasCustomNodes.find((node) => node.id === id) : null;
  return custom?.kind || WORKFLOW_NODE_KIND[id] || "text";
}

export function nodePosition(state, id, index = 0) {
  const saved = state.canvasNodePositions?.[id];
  if (saved) return { x: Number(saved.x || 0), y: Number(saved.y || 0) };
  if (DEFAULT_NODE_POSITIONS[id]) return DEFAULT_NODE_POSITIONS[id];
  return { x: 160 + Math.max(0, index) * 72, y: 720 + Math.max(0, index) * 44 };
}

export function nodeCenter(state, id, nodes) {
  const index = nodes.findIndex((node) => node[0] === id);
  const position = nodePosition(state, id, index);
  return { x: position.x + NODE_SIZE.width / 2, y: position.y + NODE_SIZE.height / 2 };
}

export function nodePort(state, id, nodes, side = "output") {
  const index = nodes.findIndex((node) => node[0] === id);
  const position = nodePosition(state, id, index);
  const x = side === "input" ? position.x : position.x + NODE_SIZE.width;
  return { x, y: position.y + NODE_SIZE.height / 2 };
}

export function allEdges(state) {
  return [...DEFAULT_EDGES.map(([from, to]) => ({ from, to })), ...(Array.isArray(state.canvasEdges) ? state.canvasEdges : [])];
}

export function edgePathBetween(from, to) {
  const dx = Math.max(120, Math.abs(to.x - from.x) * 0.46);
  const c1x = from.x + dx;
  const c2x = to.x - dx;
  return `M ${from.x} ${from.y} C ${c1x} ${from.y} ${c2x} ${to.y} ${to.x} ${to.y}`;
}

