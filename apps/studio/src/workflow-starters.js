import { createNode, connect } from "./nodes.js";

export const WORKFLOW_STARTERS = [
  {
    id: "story_to_keyframe",
    icon: "script",
    label: "故事到关键帧",
    summary: "脚本、导演台、关键帧三段式生产链。",
    tag: "短剧起步",
    tone: "story",
  },
  {
    id: "character_asset_card",
    icon: "user",
    label: "角色设定卡",
    summary: "描述角色、上传参考图，确认后保存为角色素材。",
    tag: "角色设定",
    tone: "character",
  },
  {
    id: "scene_asset_card",
    icon: "image",
    label: "场景设定卡",
    summary: "整理场景、道具和参考图，确认后保存为场景素材。",
    tag: "场景设定",
    tone: "scene",
  },
  {
    id: "first_frame_to_video",
    icon: "video",
    label: "首帧到视频",
    summary: "关键帧连接到 I2V 视频节点。",
    tag: "图生视频",
    tone: "video",
  },
  {
    id: "video_asset_revision",
    icon: "frames",
    label: "视频片段复用",
    summary: "整理视频片段、反馈记录和后续修改。",
    tag: "修改迭代",
    tone: "revision",
  },
];

export function createWorkflowStarter(store, starterId, origin = { x: -360, y: -180 }) {
  const x = Math.round(origin.x || 0);
  const y = Math.round(origin.y || 0);
  const gapX = 360;
  const gapY = 260;
  if (starterId === "character_asset_card") return characterAssetFlow(store, x, y, gapX);
  if (starterId === "scene_asset_card") return sceneAssetFlow(store, x, y, gapX);
  if (starterId === "first_frame_to_video") return firstFrameVideoFlow(store, x, y, gapX);
  if (starterId === "video_asset_revision") return videoRevisionFlow(store, x, y, gapX, gapY);
  return storyToKeyframeFlow(store, x, y, gapX);
}

function storyToKeyframeFlow(store, x, y, gapX) {
  const script = createNode(store, "script", x, y);
  const director = createNode(store, "director", x + gapX, y);
  const keyframe = createNode(store, "image", x + gapX * 2, y);
  store.set((s) => {
    Object.assign(s.nodes[script.id], {
      title: "故事脚本",
      prompt: "写出 3 幕短剧脚本，包含角色目标、场景变化和关键情绪转折。",
      content: "从这里输入故事设定，或粘贴已有脚本。确认后继续生成分镜与关键帧。",
      status: "complete",
    });
    Object.assign(s.nodes[director.id], { title: "导演台参数" });
    Object.assign(s.nodes[keyframe.id], {
      title: "关键帧生成",
      prompt: "根据上游故事和导演台参数生成第一张电影感关键帧。",
    });
    s.selection = { nodeIds: [script.id, director.id, keyframe.id], edgeId: null };
  });
  connect(store, script.id, director.id);
  connect(store, director.id, keyframe.id);
  return [script, director, keyframe];
}

function characterAssetFlow(store, x, y, gapX) {
  const brief = createNode(store, "text", x, y);
  const reference = createNode(store, "image", x + gapX, y);
  const card = createNode(store, "script", x + gapX * 2, y);
  store.set((s) => {
    Object.assign(s.nodes[brief.id], {
      title: "角色设定",
      content: "填写角色名称、年龄/阶段、服装或外观、发型或毛发、身份特征、不许漂移的锁定项。",
      status: "complete",
    });
    Object.assign(s.nodes[reference.id], {
      title: "角色参考图",
      prompt: "生成或上传角色参考图，再自动整理角色设定卡草稿。",
    });
    Object.assign(s.nodes[card.id], {
      title: "角色设定卡草稿",
      prompt: "自动识别角色外观、服饰或毛发、可保存特征和待补充信息，确认前不会用于后续生成。",
    });
    s.selection = { nodeIds: [brief.id, reference.id, card.id], edgeId: null };
  });
  connect(store, brief.id, reference.id);
  connect(store, reference.id, card.id);
  return [brief, reference, card];
}

function sceneAssetFlow(store, x, y, gapX) {
  const brief = createNode(store, "text", x, y);
  const reference = createNode(store, "image", x + gapX, y);
  const card = createNode(store, "script", x + gapX * 2, y);
  store.set((s) => {
    Object.assign(s.nodes[brief.id], {
      title: "场景设定",
      content: "填写地点、时代、天气、光线、道具和连续性锚点。",
      status: "complete",
    });
    Object.assign(s.nodes[reference.id], {
      title: "场景参考图",
      prompt: "生成或上传场景参考图，用于自动整理场景设定卡。",
    });
    Object.assign(s.nodes[card.id], {
      title: "场景设定卡草稿",
      prompt: "提取空间结构、主色、可用镜头角度、可能不稳定的细节和待补充信息。",
    });
    s.selection = { nodeIds: [brief.id, reference.id, card.id], edgeId: null };
  });
  connect(store, brief.id, reference.id);
  connect(store, reference.id, card.id);
  return [brief, reference, card];
}

function firstFrameVideoFlow(store, x, y, gapX) {
  const frame = createNode(store, "image", x, y);
  const video = createNode(store, "video", x + gapX, y);
  store.set((s) => {
    Object.assign(s.nodes[frame.id], {
      title: "首帧关键图",
      prompt: "生成视频首帧：主体清晰、构图稳定、动作起势明确。",
    });
    Object.assign(s.nodes[video.id], {
      title: "图生视频",
      prompt: "基于上游首帧生成 5 秒视频，保持角色身份和场景连续。",
    });
    s.selection = { nodeIds: [frame.id, video.id], edgeId: null };
  });
  connect(store, frame.id, video.id);
  return [frame, video];
}

function videoRevisionFlow(store, x, y, gapX, gapY) {
  const base = createNode(store, "video", x, y);
  const card = createNode(store, "script", x + gapX, y - gapY / 2);
  const revision = createNode(store, "video", x + gapX, y + gapY / 2);
  store.set((s) => {
    Object.assign(s.nodes[base.id], {
      title: "原始视频片段",
      prompt: "上传或引用已生成视频，用于整理视频片段卡草稿。",
    });
    Object.assign(s.nodes[card.id], {
      title: "视频片段卡草稿",
      prompt: "识别片段结构、可复用参考画面、动作、镜头运动和可能不稳定的细节。",
    });
    Object.assign(s.nodes[revision.id], {
      title: "局部修订草稿",
      prompt: "描述要保留和要修改的部分，只改目标区域，不改变主体身份。",
    });
    s.selection = { nodeIds: [base.id, card.id, revision.id], edgeId: null };
  });
  connect(store, base.id, card.id);
  connect(store, base.id, revision.id);
  return [base, card, revision];
}
