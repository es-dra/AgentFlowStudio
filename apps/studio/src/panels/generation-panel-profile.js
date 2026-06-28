import { IMAGE_COUNTS, VIDEO_DURATIONS, VIDEO_RATIOS, VIDEO_RESOLUTIONS } from "../presets/specs.js";

const IMAGE_RATIOS = ["9:16", "16:9", "1:1", "4:3", "3:4"];
const VIDEO_MOTIONS = [
  "固定机位",
  "缓慢推进",
  "轻微拉远",
  "镜头缓慢上升",
  "从左向右平移",
  "轻微环绕主体",
  "轻微跟随主体",
  "保持首帧构图，加入轻微呼吸感",
];

export function generationProfile(node) {
  if (node.type === "video_merge") {
    return {
      kind: "informational",
      label: "视频片段复用",
      runsGeneration: false,
      note: "当前视频片段复用还没有接入真实生成设置；请在节点内容中描述复用需求。",
      fields: [],
    };
  }
  if (node.type === "video") {
    return {
      kind: "video",
      label: "图生视频",
      runsGeneration: true,
      note: "画幅、时长、分辨率和运镜会随视频请求提交，首帧必须有效。",
      fields: [
        { key: "firstFrame", label: "首帧来源", kind: "input", readonly: true, readonlyReason: "首帧请在节点菜单中上传或设置" },
        { key: "duration", label: "视频时长", kind: "select", options: VIDEO_DURATIONS, defaultValue: "5s" },
        { key: "resolution", label: "分辨率", kind: "select", options: VIDEO_RESOLUTIONS, defaultValue: "720P" },
        { key: "ratio", label: "比例", kind: "select", options: VIDEO_RATIOS, defaultValue: "9:16" },
        { key: "motion", label: "镜头运动 / 运镜", kind: "select", options: VIDEO_MOTIONS, defaultValue: "固定机位" },
      ],
    };
  }
  if (node.type === "image") {
    const assetLabel = node.params?.assetCardDraft ? "设定图生成" : "首帧 / 关键帧生成";
    return {
      kind: "image",
      label: assetLabel,
      runsGeneration: true,
      note: node.params?.assetCardDraft
        ? "资产卡生成会输出可复用设定图；画幅和张数会进入图片生成请求。"
        : "关键帧生成会使用画幅和张数。",
      fields: [
        { key: "ratio", label: "画幅", kind: "select", options: IMAGE_RATIOS, defaultValue: "9:16" },
        { key: "imageCount", label: "张数", kind: "select", options: IMAGE_COUNTS, defaultValue: 1 },
      ],
    };
  }
  if (node.type === "script" || node.type === "text") {
    return {
      kind: "informational",
      label: node.type === "script" ? "故事脚本 / 分镜规划" : "文本创意规划",
      runsGeneration: false,
      note: "文本规划节点当前不直接使用生成设置；请在节点正文或底部提示词中编辑内容。",
      fields: [],
    };
  }
  if (node.type === "director") {
    return {
      kind: "informational",
      label: "导演台参数",
      runsGeneration: false,
      note: "导演台请使用专门的导演台面板编辑；这里不展示未接入真实流程的设置。",
      fields: [],
    };
  }
  return {
    kind: "generic",
    label: "创作节点",
    runsGeneration: false,
    note: "当前节点没有专用生成参数；只会保存提示词，不展示画幅、张数等媒体参数。",
    fields: [],
  };
}

export function valueForGenerationField(node, item) {
  const spec = node.params?.spec || {};
  const params = node.params || {};
  if (item.key === "ratio") return spec.ratio || node.params?.previewAspectRatio || item.defaultValue || "9:16";
  if (item.key === "imageCount") return spec.count || params.candidateCount || item.defaultValue || 1;
  if (item.key === "duration") return spec.duration || item.defaultValue || "5s";
  if (item.key === "resolution") return spec.resolution || item.defaultValue || "720P";
  if (item.key === "motion") return params.motion || item.defaultValue || "固定机位";
  if (item.key === "firstFrame") return params.firstFrameImageAssetId || params.sourceKeyframeAssetId || "未设置首帧";
  return item.defaultValue || "";
}

export function applyGenerationProfileSettings(target, profile, controls) {
  if (profile.kind === "image") {
    const count = clamp(Number(controls.imageCount?.value || 1), 1, 4);
    target.params.spec = { ...(target.params.spec || {}), ratio: controls.ratio?.value || "9:16", count };
    target.params.candidateCount = count;
    return;
  }
  if (profile.kind === "video") {
    target.params.spec = {
      ...(target.params.spec || {}),
      ratio: controls.ratio?.value || "9:16",
      resolution: controls.resolution?.value || "720P",
      duration: controls.duration?.value || "5s",
    };
    target.params.motion = controls.motion?.value || "固定机位";
    return;
  }
}

function clamp(value, min, max) {
  if (!Number.isFinite(value)) return min;
  return Math.max(min, Math.min(max, value));
}
