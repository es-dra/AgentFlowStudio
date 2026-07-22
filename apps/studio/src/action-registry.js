import { NODE_TYPES, createNode } from "./nodes.js";

export const ACTION_GROUPS = [
  {
    id: "basic_nodes",
    label: "常用入口",
    actions: [
      { id: "node_text", type: "text", label: "想法/文本", icon: "text" },
      { id: "node_script", type: "script", label: "剧本/导入", icon: "script" },
      { id: "node_sequence", type: "sequence", label: "场景与镜头", icon: "layers" },
      { id: "asset_character", type: "character", label: "角色与资产", icon: "user" },
      { id: "node_image", type: "image", label: "参考图/图片", icon: "image" },
      { id: "node_video", type: "video", label: "视频", icon: "video" },
    ],
  },
  {
    id: "production_nodes",
    label: "故事结构",
    actions: [
      { id: "node_scene", type: "scene", label: "场景故事单元", icon: "script" },
      { id: "node_shot", type: "shot", label: "镜头设计", icon: "camera" },
      { id: "node_director", type: "director", label: "镜头调度板", icon: "layers" },
    ],
  },
  {
    id: "asset_nodes",
    label: "资产设定",
    actions: [
      { id: "asset_scene", type: "location", label: "空间设定", icon: "image" },
      { id: "asset_prop", type: "prop", label: "道具设定", icon: "bookmark" },
      { id: "node_ref", type: "ref", label: "参考资料集", icon: "link" },
    ],
  },
  {
    id: "resource_actions",
    label: "资源",
    actions: [
      { id: "resource_upload", type: "ref", label: "上传参考图", icon: "upload" },
      { id: "resource_history", type: "library", label: "从生成历史选择", icon: "clock" },
      { id: "resource_library", type: "library", label: "项目素材", icon: "library" },
    ],
  },
  {
    id: "gated_actions",
    label: "生成准备",
    actions: [
      { id: "gate_image", type: "image", label: "预览图片生成", icon: "bolt", requires_gate: "AFS_ALLOW_REMOTE_IMAGE" },
      { id: "gate_video", type: "video", label: "预览视频生成", icon: "lock", requires_gate: "task authorization" },
      { id: "node_video_merge", type: "video_merge", label: "剪辑合成草稿", icon: "scissors" },
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
