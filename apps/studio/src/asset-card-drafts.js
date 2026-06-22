export const ASSET_CARD_FIELDS = {
  character: [
    ["identity", "身份定位"],
    ["appearance", "外形辨识"],
    ["wardrobe", "服装/外观"],
    ["palette", "主色调"],
    ["demeanor", "气质状态"],
    ["reference_views", "设定板视图组"],
  ],
  scene: [
    ["location", "地点定位"],
    ["layout", "空间结构"],
    ["props", "关键道具"],
    ["lighting_mood", "光影氛围"],
    ["time_weather", "时间天气"],
    ["view_set", "多视角视图组"],
  ],
  prop: [
    ["category", "道具类别"],
    ["appearance", "外观细节"],
    ["material", "材质工艺"],
    ["scale", "尺寸比例"],
    ["usage", "使用方式"],
    ["continuity", "连续性约束"],
    ["reference_views", "道具视图组"],
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
  const evidenceText = String(draft?.evidence_text || "");
  return {
    ...draft,
    asset_type: assetType,
    label,
    status: draft?.status || "draft",
    signature: normalizedSignature(assetType, label, evidenceText, draft?.signature),
    feature_card: normalizedFeatureCard(assetType, label, evidenceText, draft?.feature_card),
    negative_locks: lines(draft?.negative_locks),
    memory_policy: {
      writes_fixed_asset: false,
      included_in_context_before_confirmation: false,
      requires_human_confirmation: true,
      ...(draft?.memory_policy || {}),
    },
  };
}

export function assetCardFieldsForType(assetType) { return ASSET_CARD_FIELDS[safeAssetType(assetType)] || ASSET_CARD_FIELDS.character; }

export function assetCardTypeLabel(assetType) {
  return { character: "角色资产", scene: "场景资产", prop: "道具资产" }[safeAssetType(assetType)];
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

function defaultFeatureCard(assetType, label, shotText) {
  if (assetType === "scene") {
    return {
      location: sceneLocation(label, shotText),
      layout: sceneLayout(shotText),
      props: sceneProps(shotText),
      lighting_mood: sceneLightingMood(shotText),
      time_weather: sceneTimeWeather(shotText),
      view_set: "同一场景的俯瞰全景、正向广角、入口/边缘视角、光影或材质细节视角，空间关系保持一致",
    };
  }
  if (assetType === "prop") {
    return {
      category: label,
      appearance: propAppearance(label, shotText),
      material: propMaterial(label, shotText),
      scale: "与角色/场景比例一致",
      usage: propUsage(label, shotText),
      continuity: "后续镜头保持同一造型、材质和使用状态",
      reference_views: "正面、侧面、俯视、局部结构/材质特写，比例与材质保持一致",
    };
  }
  return {
    identity: characterIdentity(label, shotText),
    appearance: characterAppearance(label, shotText),
    wardrobe: characterWardrobe(shotText),
    palette: characterPalette(shotText),
    demeanor: characterDemeanor(shotText),
    reference_views: "正面全身、侧面全身、背面全身、头部/胸口或关键材质细节近景，比例与外观保持一致",
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
  if (assetType === "scene") return [`保持${label}空间结构`, "保持多视角空间关系一致", "保持时间/光影氛围", "保持关键环境元素"];
  if (assetType === "prop") return [`保持${label}外观`, "保持多视图结构一致", "保持材质和尺寸比例", "保持使用状态连续"];
  return [`保持${label}身份`, "保持正侧背视图一致", "保持外观辨识点", "保持体态比例", "保持主色调"];
}

function roleInShot(assetType, label) {
  if (assetType === "scene") return `${label}作为当前分镜空间承载`;
  if (assetType === "prop") return `${label}作为剧情动作道具`;
  return `${label}作为当前分镜角色主体`;
}

function phraseFromShot(text, fallback) {
  const clean = stripAssetTags(String(text || "")).replace(/\s+/g, " ").trim();
  if (!clean) return fallback;
  return clean.split(/[。；.!?！？]/u)[0].slice(0, 80) || fallback;
}

function normalizedSignature(assetType, label, evidenceText, value) {
  const clean = cleanDraftField(value);
  if (!signatureHasMeaning(clean, label)) return signatureFor(assetType, label, evidenceText);
  if (clean.includes("：") || clean.includes(":")) return clean.slice(0, 120);
  return `${label}：${clean}`.slice(0, 120);
}

function normalizedFeatureCard(assetType, label, evidenceText, card) {
  const fallback = defaultFeatureCard(assetType, label, evidenceText);
  const source = card && typeof card === "object" ? card : {};
  const result = {};
  for (const [key] of assetCardFieldsForType(assetType)) {
    const clean = cleanDraftField(source[key]);
    const text = clean && signatureHasMeaning(clean, label) ? clean : fallback[key];
    if (text) result[key] = String(text).slice(0, 260);
  }
  return result;
}

function signatureHasMeaning(value, label) {
  const clean = stripAssetTags(String(value || ""))
    .replace(new RegExp(`^${escapeRegExp(label)}\\s*[：:]?\\s*`, "u"), "")
    .replace(/[：:\s]+$/u, "")
    .trim();
  return clean.length > 0;
}

function cleanDraftField(value) {
  return stripAssetTags(String(value || ""))
    .replace(/\s+/g, " ")
    .replace(/^[\s，。、；：:]+/u, "")
    .trim();
}

function shotDescription(structuredShot) { return String(structuredShot?.description || structuredShot?.source_text || "").trim(); }

function stripAssetTags(text) {
  return String(text || "").replace(/@[^\s，。、；：:]+(?:（[^）]*）)?/gu, "").replace(/^[\s，。、；：:]+/u, "").trim();
}

function characterIdentity(label, text) {
  if (/机器人|机械|金属机身/.test(text)) return label === "主角" ? "来自未来的机器人主角" : `${label}，未来科幻机器人角色`;
  return label;
}

function characterAppearance(label, text) {
  if (/机器人|机械|金属机身/.test(text)) {
    return "金属机身，精密发光纹路，清晰头部轮廓、躯干比例和四肢结构";
  }
  if (/脸|眼神|表情|体态|轮廓/.test(text)) return "根据分镜保留脸部、体态和轮廓辨识点";
  return "根据分镜描述确定可复用外观辨识点";
}

function characterWardrobe(text) {
  if (/机器人|机械|金属机身/.test(text)) return "无传统服装，机械外壳与发光部件作为外观层";
  return "服装或外观按分镜语境确定，后续可人工补充";
}

function characterPalette(text) {
  if (/冷蓝|星光|星空|月光|青蓝|蓝/.test(text)) return "冷灰金属与青蓝发光纹路，低饱和城市反射";
  if (/霓虹/.test(text)) return "低饱和霓虹反射与主体主色调保持一致";
  return "主色调按分镜语境确定，后续可人工补充";
}

function characterDemeanor(text) {
  if (/安静|专注|孤独|沉静|忧伤/.test(text)) return "安静专注，孤独沉静，略带诗意的科幻疏离感";
  return phraseFromShot(text, "神态服务当前剧情");
}

function sceneLocation(label, text) {
  if (/屋顶|楼顶|天台/.test(text)) return "夜晚城市屋顶/楼顶平台";
  if (/城市|天际线/.test(text)) return "城市外景与天际线环境";
  return label;
}

function sceneLayout(text) {
  if (/星空|天际线|屋顶|楼顶|天台/.test(text)) {
    return "屋顶边缘与平台前景，远处城市天际线，广阔星空占据主要空间";
  }
  return "根据分镜画面确定空间结构、主体位置和远近层次";
}

function sceneProps(text) {
  if (/灯火|霓虹|高楼|天际线/.test(text)) return "城市灯火、远处高楼、低饱和霓虹反射作为环境元素";
  return "保留分镜中出现的关键环境元素，不额外新增无关道具";
}

function sceneLightingMood(text) {
  if (/冷蓝|月光|星光|星空|霓虹|低饱和/.test(text)) return "冷蓝月光与星光主导，城市霓虹提供低饱和反射";
  if (/低照度|夜晚|深夜/.test(text)) return "低照度夜景光线，暗部压低，主体轮廓清晰";
  return phraseFromShot(text, "自然光影，氛围服务剧情");
}

function sceneTimeWeather(text) {
  if (/夜|星空|月光/.test(text)) return "晴朗夜晚，冷蓝月光与星光主导";
  if (/雨|雾|风/.test(text)) return "按分镜天气与空气状态确定";
  return "按分镜语境确定";
}

function propAppearance(label, text) {
  if (/灯|路灯|灯具|灯柱/.test(label)) return "独立灯具/光源结构，外轮廓清楚，发光区域和支撑结构可辨认";
  return "根据分镜描述确定外观轮廓和辨识细节";
}

function propMaterial(label, text) {
  if (/灯|路灯|灯具|灯柱/.test(label) && /科幻|未来|金属/.test(text)) return "金属与半透明发光材料，冷色反射";
  return "材质待人工确认";
}

function propUsage(label, text) {
  if (/灯|路灯|灯具|灯柱/.test(label)) return "作为环境光源或局部照明使用";
  return "按分镜动作使用";
}

function safeAssetType(value) { return ["character", "scene", "prop"].includes(String(value || "")) ? String(value) : "character"; }

function safeLabel(value, assetType) {
  const fallback = assetType === "scene" ? "主要场景" : assetType === "prop" ? "关键道具" : "主角";
  return String(value || fallback).replace(/^@+/, "").trim().slice(0, 40) || fallback;
}

function lines(value) {
  const source = Array.isArray(value) ? value : String(value || "").split(/\r?\n/);
  return source.map((item) => String(item || "").trim()).filter(Boolean).slice(0, 16);
}

function slug(value) { return encodeURIComponent(value).replace(/%/g, "").slice(0, 40).toLowerCase() || "asset"; }

function escapeRegExp(value) {
  return String(value || "").replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
