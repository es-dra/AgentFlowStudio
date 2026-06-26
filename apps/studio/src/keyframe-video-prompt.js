export const DEFAULT_KEYFRAME_VIDEO_MOTION = "轻微推进，保留对峙张力和呼吸感镜头。";

export function buildKeyframeVideoPrompt(source, videoAssetPlan, options = {}) {
  const duration = String(options.duration || source?.params?.spec?.duration || "5s").trim();
  const motion = String(options.motion || DEFAULT_KEYFRAME_VIDEO_MOTION).trim();
  const assetLines = videoAssetLines(videoAssetPlan);
  const sourceSummary = videoSafeSourceSummary(source);
  return [
    `${duration} 图生视频时间轴：以上游关键帧作为 0.0s 首帧视觉锚点。`,
    "首帧锁定：0.0s 必须贴合上游关键帧的角色身份、服装、道具几何、场景布局、镜头构图、光影和色彩关系。",
    "资产连续性锁定：",
    ...assetLines,
    "时间轴动作设计：",
    "0.0s：完全承接首帧姿态和构图，不跳切，不改脸，不换装，不改场景。",
    "0.0-1.0s：保留对峙关系，只加入呼吸、衣料、发丝、尘土或环境光的轻微运动。",
    "1.0-2.5s：主体沿首帧动作方向做小幅蓄势或重心转移，道具保持形状、尺度和握持关系。",
    "2.5-4.0s：动作继续推进但不改变镜头主体关系；冲突张力增强，构图仍稳定。",
    "4.0-5.0s：动作自然收束到可作为下一镜头衔接的姿态，保留首帧身份和空间关系。",
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
