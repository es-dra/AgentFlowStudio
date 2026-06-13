import { defaultModel } from "./presets/models.js";
import { defaultImageSpec, defaultVideoSpec } from "./presets/specs.js";

// Node registry: AFS creation-flow types, visible labels, empty-state intent, and port compatibility.
// icon 字段为 icons.js 中的图标名。
export const NODE_TYPES = {
  text: {
    label: "文本",
    icon: "text",
    intents: [
      { icon: "pencil", label: "自己编写内容" },
      { icon: "video", label: "文生视频" },
      { icon: "image", label: "图片反推提示词" },
      { icon: "music", label: "文字生音乐" },
    ],
    downstream: ["text", "image", "video", "director", "script", "ref"],
    size: { w: 280, h: 280 },
  },
  image: {
    label: "图片",
    icon: "image",
    upload: true,
    intents: [
      { icon: "upload", label: "图生图" },
      { icon: "hd", label: "图片高清" },
    ],
    downstream: ["text", "image", "video", "director", "script", "ref"],
    size: { w: 280, h: 280 },
  },
  video: {
    label: "视频",
    icon: "video",
    upload: true,
    intents: [
      { icon: "frames", label: "首尾帧生成视频" },
      { icon: "sparkle1", label: "首帧生成视频" },
    ],
    downstream: ["text", "video", "video_merge", "audio", "script", "ref"],
    size: { w: 280, h: 280 },
  },
  video_merge: {
    label: "视频合成",
    tag: "Beta",
    icon: "scissors",
    intents: [{ icon: "video", label: "多段视频拼接合成" }],
    downstream: ["video", "audio", "ref"],
    size: { w: 280, h: 250 },
  },
  director: {
    label: "导演台",
    tag: "NEW",
    icon: "layers",
    intents: [],
    downstream: ["image", "video", "ref"],
    size: { w: 280, h: 280 },
  },
  audio: {
    label: "音频",
    icon: "audio",
    intents: [
      { icon: "music", label: "文字生音乐" },
      { icon: "mic", label: "文字转语音" },
    ],
    downstream: ["video", "video_merge", "ref"],
    size: { w: 280, h: 250 },
  },
  script: {
    label: "脚本",
    tag: "Beta",
    icon: "script",
    intents: [
      { icon: "text", label: "剧本生成分镜脚本" },
      { icon: "video", label: "视频参考生成分镜脚本" },
      { icon: "user", label: "角色生成分镜脚本" },
    ],
    downstream: ["text", "image", "video", "director", "ref"],
    size: { w: 280, h: 280 },
  },
  library: {
    label: "素材库",
    tag: "NEW",
    icon: "library",
    intents: [],
    downstream: ["ref"],
    size: { w: 280, h: 250 },
  },
};

export const RESOURCE_ENTRIES = [
  { id: "upload", icon: "upload", label: "上传" },
  { id: "from_history", icon: "clock", label: "从生成历史选择" },
];

export const NODE_MENU_ORDER = ["text", "image", "video", "video_merge", "director", "audio", "script", "library"];

export const COLLAPSED_HEIGHT = 48;

export function effectiveHeight(node) {
  return node.collapsed ? COLLAPSED_HEIGHT : node.h;
}

export function createNode(store, type, wx, wy) {
  const def = NODE_TYPES[type] || NODE_TYPES.text;
  const id = store.nextId("node");
  let seq = 0;
  store.set((s) => {
    seq = s.order.length + 1;
  });
  const node = {
    id,
    type,
    title: `${def.label}节点 ${seq}`,
    x: Math.round(wx),
    y: Math.round(wy),
    w: def.size.w,
    h: def.size.h,
    prompt: "",
    params: defaultParams(type),
    content: "",
    status: "empty",
    result: null,
    groupId: null,
    collapsed: false,
  };
  store.set((s) => {
    s.nodes[id] = node;
    s.order.push(id);
    s.selection = { nodeIds: [id], edgeId: null };
  });
  return node;
}

export function defaultParams(type) {
  const base = { model: defaultModel(type)?.id || null, attachments: [], styleRef: null, isReference: false };
  if (type === "image") return { ...base, spec: defaultImageSpec(), camera: null };
  if (type === "video" || type === "video_merge") return { ...base, spec: defaultVideoSpec(), motion: null, effect: null };
  return base;
}

export function duplicateNode(store, nodeId) {
  const source = store.get().nodes[nodeId];
  if (!source) return null;
  const id = store.nextId("node");
  const clone = JSON.parse(JSON.stringify(source));
  clone.id = id;
  clone.x = source.x + 32;
  clone.y = source.y + 32;
  clone.title = `${source.title} 副本`;
  clone.groupId = null;
  store.set((s) => {
    s.nodes[id] = clone;
    s.order.push(id);
    s.selection = { nodeIds: [id], edgeId: null };
  });
  return clone;
}

export function deleteNodes(store, nodeIds) {
  const removal = new Set(nodeIds);
  store.set((s) => {
    for (const id of removal) delete s.nodes[id];
    s.order = s.order.filter((id) => !removal.has(id));
    for (const [eid, edge] of Object.entries(s.edges)) {
      if (removal.has(edge.from) || removal.has(edge.to)) delete s.edges[eid];
    }
    for (const group of Object.values(s.groups)) {
      group.nodeIds = group.nodeIds.filter((id) => !removal.has(id));
    }
    for (const gid of Object.keys(s.groups)) {
      if (!s.groups[gid].nodeIds.length) delete s.groups[gid];
    }
    s.selection = { nodeIds: [], edgeId: null };
  });
}

export function connect(store, fromId, toId) {
  let created = null;
  store.set((s) => {
    const exists = Object.values(s.edges).some((e) => e.from === fromId && e.to === toId);
    if (exists || fromId === toId) return;
    const id = `edge_${fromId}__${toId}`;
    s.edges[id] = { id, from: fromId, to: toId, relation_type: relationTypeFor(s, fromId, toId) };
    created = id;
    s.ui.lastConnectedEdgeId = id;
  });
  if (created) {
    setTimeout(() => {
      store.set((s) => {
        if (s.ui.lastConnectedEdgeId === created) s.ui.lastConnectedEdgeId = null;
      });
    }, 1100);
  }
  return created;
}

function relationTypeFor(state, fromId, toId) {
  const from = state.nodes[fromId];
  const to = state.nodes[toId];
  if (from?.type === "director") return "director";
  if (from?.params?.isReference || to?.params?.isReference) return "reference";
  return "generation";
}

export function downstreamTypesFor(type) {
  return (NODE_TYPES[type] || NODE_TYPES.text).downstream;
}

export function relationSets(state) {
  const focus = state.selection.nodeIds.length === 1 ? state.selection.nodeIds[0] : null;
  if (!focus) return null;
  const upstream = new Set();
  const downstream = new Set();
  walk(focus, upstream, (id) => Object.values(state.edges).filter((e) => e.to === id).map((e) => e.from));
  walk(focus, downstream, (id) => Object.values(state.edges).filter((e) => e.from === id).map((e) => e.to));
  if (!upstream.size && !downstream.size) return null;
  return { focus, upstream, downstream };

  function walk(start, bag, next) {
    const queue = [start];
    while (queue.length) {
      const current = queue.shift();
      for (const id of next(current)) {
        if (id !== start && !bag.has(id)) {
          bag.add(id);
          queue.push(id);
        }
      }
    }
  }
}

export function promptPlaceholder(type, mode) {
  if (type === "text") return "写下你想讲的故事、场景或角色设定。例如：一个来自未来的机器人，在城市屋顶看星星…";
  if (type === "image") return "可直接文字生图，或上传图片输入文字指令对图片进行编辑，如：将背景改为雪夜";
  if (type === "video") return mode === "文生视频" ? "描述你想要生成的画面内容，@引用素材" : `已选 ${mode || "参考"} 模式，描述画面内容，@引用素材`;
  if (type === "script") return "描述剧情或添加角色参考、视频参考等，为你生成分镜脚本";
  if (type === "audio") return "描述你想要的音乐、音效或台词内容";
  if (type === "video_merge") return "描述合成顺序与转场要求，@引用上游视频";
  return "输入提示词…";
}
