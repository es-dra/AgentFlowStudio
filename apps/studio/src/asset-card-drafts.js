export const ASSET_CARD_FIELDS = {
  character: [
    ["identity", "身份定位"],
    ["appearance", "外形辨识"],
    ["wardrobe", "服装/外观"],
    ["palette", "主色调"],
    ["demeanor", "气质状态"],
  ],
  scene: [
    ["location", "地点定位"],
    ["layout", "空间结构"],
    ["props", "关键道具"],
    ["lighting_mood", "光影氛围"],
    ["time_weather", "时间天气"],
  ],
  prop: [
    ["category", "道具类别"],
    ["appearance", "外观细节"],
    ["material", "材质工艺"],
    ["scale", "尺寸比例"],
    ["usage", "使用方式"],
    ["continuity", "连续性约束"],
  ],
};

export function assetCardDraftFromRef(asset, structuredShot, options = {}) {
  const assetType = safeAssetType(asset?.asset_type);
  const label = safeLabel(asset?.label, assetType);
  const shotText = shotDescription(structuredShot);
  const featureCard = defaultFeatureCard(assetType, label, shotText);
  return normalizeAssetCardDraft({
    card_id: `asset_card:${structuredShot?.shot_id || "shot"}:${assetType}:${slug(label)}`,
    asset_type: assetType,
    label,
    status: "draft",
    source: "shot_asset_recognition",
    source_script_node_id: options.sourceScriptNodeId || "",
    source_shot_id: structuredShot?.shot_id || "",
    source_asset_ref: asset || {},
    role_in_shot: roleInShot(assetType, label),
    signature: signatureFor(assetType, label, shotText),
    feature_card: featureCard,
    negative_locks: defaultLocks(assetType, label),
    evidence_text: shotText.slice(0, 500),
    memory_policy: {
      writes_fixed_asset: false,
      included_in_context_before_confirmation: false,
      requires_human_confirmation: true,
    },
    created_at: new Date().toISOString(),
  });
}

export function normalizeAssetCardDraft(draft) {
  const assetType = safeAssetType(draft?.asset_type);
  const label = safeLabel(draft?.label, assetType);
  return {
    ...draft,
    asset_type: assetType,
    label,
    status: draft?.status || "draft",
    signature: String(draft?.signature || signatureFor(assetType, label, draft?.evidence_text || "")).trim(),
    feature_card: compactCard(draft?.feature_card),
    negative_locks: lines(draft?.negative_locks),
    memory_policy: {
      writes_fixed_asset: false,
      included_in_context_before_confirmation: false,
      requires_human_confirmation: true,
      ...(draft?.memory_policy || {}),
    },
  };
}

export function assetCardFieldsForType(assetType) {
  return ASSET_CARD_FIELDS[safeAssetType(assetType)] || ASSET_CARD_FIELDS.character;
}

export function assetCardTypeLabel(assetType) {
  return {
    character: "角色资产",
    scene: "场景资产",
    prop: "道具资产",
  }[safeAssetType(assetType)];
}

export function assetCardText(draft) {
  const card = normalizeAssetCardDraft(draft);
  const fieldLines = assetCardFieldsForType(card.asset_type)
    .map(([key, label]) => `- ${label}：${card.feature_card[key] || "待补充"}`);
  const lockLines = card.negative_locks.length
    ? card.negative_locks.map((item) => `- ${item}`)
    : ["- 确认固定前不进入生成约束"];
  return [
    `资产类型：${assetCardTypeLabel(card.asset_type)}`,
    `资产名称：@${card.label}`,
    "状态：候选草稿，确认固定前不会进入关键帧约束",
    `一句话签名：${card.signature}`,
    "特征卡：",
    ...fieldLines,
    "不可变锁定项：",
    ...lockLines,
    `来源分镜：${card.source_shot_id || "未标记"}`,
  ].join("\n");
}

export function assetImagePrompt(draft) {
  const card = normalizeAssetCardDraft(draft);
  const fields = assetCardFieldsForType(card.asset_type)
    .map(([key, label]) => `${label}：${card.feature_card[key] || "待补充"}`)
    .join("\n");
  return [
    `生成可复用${assetCardTypeLabel(card.asset_type)}参考图：@${card.label}`,
    "用途：资产定稿参考图，不直接生成关键帧或视频。",
    `签名：${card.signature}`,
    fields,
    "要求：主体清晰、便于后续固定为资产；不要添加文字、水印、UI、边框。",
  ].filter(Boolean).join("\n");
}

function defaultFeatureCard(assetType, label, shotText) {
  if (assetType === "scene") {
    return {
      location: label,
      layout: "根据分镜画面确定空间结构和主体位置关系",
      props: "保留分镜中出现的关键道具与环境元素",
      lighting_mood: phraseFromShot(shotText, "自然光影，氛围服务剧情"),
      time_weather: "按分镜语境确定",
    };
  }
  if (assetType === "prop") {
    return {
      category: label,
      appearance: "根据分镜描述确定外观轮廓和辨识细节",
      material: "材质待人工确认",
      scale: "与角色/场景比例一致",
      usage: "按分镜动作使用",
      continuity: "后续镜头保持同一造型和损耗状态",
    };
  }
  return {
    identity: label,
    appearance: "根据分镜描述确定脸部/体态/轮廓辨识点",
    wardrobe: "服装或外观待人工确认",
    palette: "主色调待人工确认",
    demeanor: phraseFromShot(shotText, "神态服务当前剧情"),
  };
}

function signatureFor(assetType, label, shotText) {
  const suffix = {
    character: "可复用角色，身份与外观待确认",
    scene: "可复用场景，空间与光影待确认",
    prop: "可复用道具，外观与使用方式待确认",
  }[assetType] || "可复用资产";
  const hint = phraseFromShot(shotText, suffix);
  return `${label}：${hint}`.slice(0, 120);
}

function defaultLocks(assetType, label) {
  if (assetType === "scene") return [`保持${label}空间结构`, "保持光影氛围", "保持关键环境元素"];
  if (assetType === "prop") return [`保持${label}外观`, "保持材质和尺寸比例", "保持使用状态连续"];
  return [`保持${label}身份`, "保持外观辨识点", "保持体态比例"];
}

function roleInShot(assetType, label) {
  if (assetType === "scene") return `${label}作为当前分镜空间承载`;
  if (assetType === "prop") return `${label}作为剧情动作道具`;
  return `${label}作为当前分镜角色主体`;
}

function phraseFromShot(text, fallback) {
  const clean = String(text || "").replace(/\s+/g, " ").trim();
  if (!clean) return fallback;
  return clean.split(/[。；.!?！？]/u)[0].slice(0, 80) || fallback;
}

function shotDescription(structuredShot) {
  return String(structuredShot?.description || structuredShot?.source_text || "").trim();
}

function safeAssetType(value) {
  return ["character", "scene", "prop"].includes(String(value || "")) ? String(value) : "character";
}

function safeLabel(value, assetType) {
  const fallback = assetType === "scene" ? "主要场景" : assetType === "prop" ? "关键道具" : "主角";
  return String(value || fallback).replace(/^@+/, "").trim().slice(0, 40) || fallback;
}

function compactCard(card) {
  const result = {};
  for (const [key, value] of Object.entries(card || {})) {
    const text = String(value || "").trim();
    if (key && text) result[key] = text.slice(0, 260);
  }
  return result;
}

function lines(value) {
  const source = Array.isArray(value) ? value : String(value || "").split(/\r?\n/);
  return source.map((item) => String(item || "").trim()).filter(Boolean).slice(0, 16);
}

function slug(value) {
  return encodeURIComponent(value).replace(/%/g, "").slice(0, 40).toLowerCase() || "asset";
}
