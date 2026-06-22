export function visualAssetDefaultsFromAssetCardDraft(draft, assetType) {
  if (!draft || draft.asset_type !== assetType) return null;
  const card = draft.feature_card && typeof draft.feature_card === "object" ? draft.feature_card : {};
  const label = String(draft.label || "").replace(/^@+/, "").trim();
  const base = {
    label: label || fallbackLabel(assetType),
    signature: String(draft.signature || "").trim(),
    locks: Array.isArray(draft.negative_locks) ? draft.negative_locks.join("\n") : "",
  };
  if (assetType === "scene") {
    return {
      ...base,
      card: {
        location: card.location || label || "待确认场景空间",
        layout: card.layout || "保持资产卡中的空间结构",
        props: card.props || "保持资产卡中的关键环境元素",
        lighting_mood: card.lighting_mood || "保持资产卡中的光影氛围",
        palette: card.palette || "保持资产卡中的场景主色调",
        time_weather: card.time_weather || "",
        view_set: card.view_set || "同一场景的俯瞰全景、正向广角、入口/边缘视角、光影或材质细节视角",
      },
    };
  }
  if (assetType === "prop") {
    return {
      ...base,
      card: {
        category: card.category || label || "待确认道具",
        appearance: card.appearance || "保持资产卡中的道具外观",
        material: card.material || "保持资产卡中的材质工艺",
        scale: card.scale || "保持与角色/场景的比例关系",
        usage: card.usage || "按分镜动作使用",
        continuity: card.continuity || "后续镜头保持同一造型、材质和使用状态",
        reference_views: card.reference_views || "正面、侧面、俯视、局部结构/材质特写",
      },
    };
  }
  return {
    ...base,
    card: {
      identity: card.identity || label || "待确认角色主体",
      hair: card.appearance || "保持资产卡中的外形、材质和颜色辨识点",
      face: card.head_details || card.appearance || "保持头部/面部或关键识别结构",
      build: card.body_shape || "保持体态比例和结构关系",
      wardrobe: card.wardrobe || "保持服装、外壳或外观层",
      palette: card.palette || "保持角色主色调",
      demeanor: card.demeanor || "保持角色气质和神态",
      reference_views: card.reference_views || "正面全身、侧面全身、背面全身、头部/胸口或关键材质细节近景",
    },
  };
}

function fallbackLabel(assetType) {
  if (assetType === "scene") return "场景资产";
  if (assetType === "prop") return "道具资产";
  return "角色资产";
}
