import { NODE_TYPES, createNode } from "./nodes.js";

export const ACTION_GROUPS = [
  {
    id: "basic_nodes",
    label: "基础素材",
    actions: [
      { id: "node_text", type: "text", label: "文本", icon: "text" },
      { id: "node_ref", type: "ref", label: "参考集", icon: "link" },
      { id: "node_image", type: "image", label: "图片 / 关键帧", icon: "image" },
      { id: "node_video", type: "video", label: "视频", icon: "video" },
    ],
  },
  {
    id: "production_nodes",
    label: "创作流程",
    actions: [
      { id: "node_script", type: "script", label: "脚本 / 分镜", icon: "script", tag: "可编辑" },
      { id: "node_sequence", type: "sequence", label: "叙事段落", icon: "layers" },
      { id: "node_scene", type: "scene", label: "场景", icon: "script" },
      { id: "node_shot", type: "shot", label: "镜头", icon: "camera" },
      { id: "node_director", type: "director", label: "导演台", icon: "layers", tag: "常用" },
      { id: "node_video_merge", type: "video_merge", label: "视频合成", icon: "scissors", tag: "剪辑" },
    ],
  },
  {
    id: "asset_nodes",
    label: "角色与场景",
    actions: [
      { id: "asset_character", type: "character", label: "角色设定卡", icon: "user", tag: "草稿" },
      { id: "asset_scene", type: "location", label: "场景设定卡", icon: "image", tag: "草稿" },
      { id: "asset_prop", type: "prop", label: "道具设定卡", icon: "bookmark", tag: "草稿" },
      { id: "asset_video", type: "video", label: "视频片段卡", icon: "frames", tag: "草稿" },
    ],
  },
  {
    id: "resource_actions",
    label: "资源",
    actions: [
      { id: "resource_upload", type: "ref", label: "上传参考", icon: "upload" },
      { id: "resource_history", type: "library", label: "从生成历史选择", icon: "clock" },
      { id: "resource_library", type: "library", label: "素材库", icon: "library", tag: "常用" },
    ],
  },
  {
    id: "gated_actions",
    label: "真实生成",
    actions: [
      { id: "gate_image", type: "image", label: "生成图片", icon: "bolt", tag: "需确认", requires_gate: "AFS_ALLOW_REMOTE_IMAGE" },
      { id: "gate_video", type: "video", label: "生成视频", icon: "lock", tag: "需确认", requires_gate: "task authorization" },
    ],
  },
];

export function actionById(actionId) {
  for (const group of ACTION_GROUPS) {
    const action = group.actions.find((item) => item.id === actionId);
    if (action) return action;
  }
  return null;
}

export function createActionNode(store, actionId, wx, wy) {
  const action = typeof actionId === "object" ? actionId : actionById(actionId);
  const nodeType = action?.type === "library" ? "text" : action?.type || "text";
  const node = createNode(store, nodeType, wx, wy);
  store.set((s) => {
    const current = s.nodes[node.id];
    if (!current) return;
    applyActionDefaults(current, action || { id: "node_text", label: NODE_TYPES[nodeType]?.label || "节点" });
  });
  return node;
}

function applyActionDefaults(node, action) {
  node.params.actionId = action.id;
  node.params.actionLabel = action.label;
  node.params.requiresGate = action.requires_gate || "";
  if (action.id === "asset_character") {
    node.title = "角色设定卡草稿";
    node.prompt = "上传或生成一张角色参考图，然后自动整理角色特征、可固定细节和待补充信息。";
    node.params.assetCardDraft = { asset_type: "character", updated_by_user: false };
    return;
  }
  if (action.id === "asset_scene") {
    node.title = "场景设定卡草稿";
    node.prompt = "上传或生成场景参考图，然后整理空间结构、光线、道具、连续细节和待补充信息。";
    node.params.assetCardDraft = { asset_type: "scene", updated_by_user: false };
    return;
  }
  if (action.id === "asset_prop") {
    node.title = "道具设定卡草稿";
    node.prompt = "上传或生成道具参考图，然后整理外观、材质、比例、使用方式和连续性约束。";
    node.params.assetCardDraft = { asset_type: "prop", updated_by_user: false };
    return;
  }
  if (action.id === "asset_video") {
    node.title = "视频片段卡草稿";
    node.prompt = "引用一段视频，整理片段、动作、可用参考画面和后续修改范围。";
    return;
  }
  if (action.id === "resource_upload") {
    node.title = "上传参考图";
    node.prompt = "上传参考素材，并选择是否固定为角色或场景资产。";
    node.params.referenceIntent = "canvas_upload";
    return;
  }
  if (action.id === "resource_history" || action.id === "resource_library") {
    node.title = action.label;
    node.content = `${action.label}：选择项目内已有输出或素材后，连接到目标生成节点。`;
    node.status = "complete";
    return;
  }
  if (action.requires_gate) {
    node.title = action.label;
    node.prompt = `${action.label} 需要先确认授权。当前只准备本地草稿，不会自动开始真实生成。`;
    return;
  }
  node.title = action.label || node.title;
}
