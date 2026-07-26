export const DEFAULT_KEYFRAME_VIDEO_MOTION = "延续已确认镜头动作与机位，不新增剧情事实。";

export function buildKeyframeVideoPrompt(source, videoAssetPlan, options = {}) {
  const duration = String(options.duration || source?.params?.spec?.duration || "5s").trim();
  const motion = String(options.motion || DEFAULT_KEYFRAME_VIDEO_MOTION).trim();
  const assetLines = videoAssetLines(videoAssetPlan);
  const sourceSummary = videoSafeSourceSummary(source);
  const shot = source?.params?.structuredShot || {};
  const action = String(shot.action || shot.description || source?.prompt || "").trim();
  const composition = String(shot.composition || "").trim();
  const camera = String(shot.camera_angle || "").trim();
  const emotion = String(shot.emotion || "").trim();
  const continuity = safeArray(shot.continuity_cues).map((item) => String(item || "").trim()).filter(Boolean);
  return [
    `${duration} 图生视频时间轴：以上游关键帧作为 0.0s 首帧视觉锚点。`,
    "首帧锁定：0.0s 必须贴合上游关键帧的角色身份、服装、道具几何、场景布局、镜头构图、光影和色彩关系。",
    "资产连续性锁定：",
    ...assetLines,
    action ? `镜头动作：${action}` : "",
    composition ? `构图：${composition}` : "",
    camera ? `机位：${camera}` : "",
    emotion ? `情绪：${emotion}` : "",
    continuity.length ? `连续性：${continuity.join("；")}` : "",
    "时间轴：从已批准首帧开始，只推进已明确的镜头动作，结尾保持可读且不增加新事件。",
    `镜头运动：${motion} 保持中低幅度镜头变化，避免大幅推拉、旋转、换景或突然剪辑。`,
    "负向约束：不新增角色、不新增额外道具、不出现文字、水印、UI、边框；不改变人物身份、脸型、发型轮廓、服装、道具结构或场景位置关系。",
    sourceSummary ? `上游关键帧摘要（仅作为首帧和连续性依据）：${sourceSummary}` : "",
  ].filter(Boolean).join("\n");
}

function videoAssetLines(videoAssetPlan) {
  const assets = safeArray(videoAssetPlan?.assets);
  if (!assets.length) {
    return ["- 未识别到独立资产卡：以首帧中已经出现的角色、道具、场景为唯一连续性依据。"];
  }
  return assets.map((asset) => {
    const status = assetStatusLabel(asset.status);
    const policy = asset.reference_policy === "reference_images_available"
      ? "有参考图时按参考图稳定身份与外观"
      : "无参考图时仅按首帧和文字摘要约束";
    const lock = continuityLockForType(asset.asset_type);
    const signature = String(asset.signature || "").trim();
    const suffix = signature ? `；视觉摘要：${compactText(signature, 120)}` : "";
    return `- @${asset.label}（${videoAssetTypeLabel(asset.asset_type)} / ${status}）：${lock}；${policy}${suffix}`;
  });
}

function continuityLockForType(type) {
  if (type === "character") return "锁定身份、脸型轮廓、体态比例、服装和首帧站位";
  if (type === "scene") return "锁定地形结构、空间层次、光影方向、天气和镜头落点";
  if (type === "prop") return "锁定道具形状、尺度、材质、握持或摆放关系";
  return "锁定首帧中的外观、功能和与其他资产的空间关系";
}

function videoAssetTypeLabel(type) {
  if (type === "character") return "角色";
  if (type === "scene") return "场景";
  if (type === "prop") return "道具";
  return "资产";
}

function assetStatusLabel(status) {
  const value = String(status || "").trim().toLowerCase();
  if (["fixed", "ready", "accepted"].includes(value)) return "已固定";
  if (["rejected", "retired"].includes(value)) return "不使用";
  return "候选";
}

function videoSafeSourceSummary(source) {
  const text = String(source?.prompt || source?.result || "").trim();
  if (!text) return "";
  const lines = text
    .split(/\r?\n/u)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.replace(/^根据分镜生成关键帧[:：]\s*/u, "分镜意图："))
    .filter((line) => !/(画面要求|单张关键帧|候选资产卡|未固定不阻断|不作为参考图注入|已固定资产|必须保持)/u.test(line));
  return compactText(lines.join(" "), 520);
}

function compactText(value, limit) {
  const text = String(value || "").replace(/\s+/gu, " ").trim();
  return text.length > limit ? `${text.slice(0, Math.max(0, limit - 3))}...` : text;
}

function safeArray(value) {
  return Array.isArray(value) ? value : [];
}
