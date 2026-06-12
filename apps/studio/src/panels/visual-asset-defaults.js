export function visualAssetDefaults(node, imageAsset, assetType) {
  const text = [
    node?.title,
    node?.prompt,
    node?.result,
    imageAsset?.filename,
    imageAsset?.label,
  ].filter(Boolean).join(" ");
  return assetType === "scene" ? sceneDefaults(node, text) : characterDefaults(node, text);
}

function characterDefaults(node, text) {
  const label = defaultLabel(node, "人物资产");
  const hair = inferHair(text);
  const wardrobe = inferWardrobe(text);
  const palette = inferPalette(text);
  const named = includesAny(text, ["周彤"]) ? "周彤" : "";
  const identity = named ? `${named}，参考图中的人物角色` : "参考图中的人物角色";
  const card = {
    identity,
    hair: hair || "保持参考图人物发型发色",
    face: "保持参考图人物脸部五官与辨识度",
    build: "保持参考图人物体型比例",
    wardrobe: wardrobe || "保持参考图人物服装",
    palette: palette || "保持参考图人物主色调",
    demeanor: "保持参考图人物气质和神态",
  };
  return {
    label: named || label,
    signature: compact([named || "参考图人物", hair, wardrobe, palette].filter(Boolean).join("，")) || "参考图人物",
    card,
    locks: [
      "保持参考图人物身份和脸部辨识度",
      hair ? `保持${hair}` : "",
      wardrobe ? `保持${wardrobe}` : "",
      palette ? `保持${palette}` : "",
    ].filter(Boolean).join("\n"),
  };
}

function sceneDefaults(node, text) {
  const label = defaultLabel(node, "场景资产");
  const palette = inferPalette(text);
  const card = {
    location: "参考图中的场景空间",
    layout: "保持参考图空间结构和主体位置关系",
    props: "保持参考图关键道具与环境元素",
    lighting_mood: inferLighting(text) || "保持参考图光线基调",
    palette: palette || "保持参考图场景主色调",
    time_weather: inferTimeWeather(text) || "",
  };
  return {
    label,
    signature: compact([label, card.lighting_mood, palette].filter(Boolean).join("，")) || "参考图场景",
    card,
    locks: [
      "保持参考图空间结构",
      "保持参考图关键道具与环境元素",
      card.lighting_mood ? `保持${card.lighting_mood}` : "",
    ].filter(Boolean).join("\n"),
  };
}

function defaultLabel(node, fallback) {
  const title = String(node?.title || "").trim();
  if (title && !/^图片节点\s*\d*$/u.test(title)) return title.slice(0, 32);
  return fallback;
}

function inferHair(text) {
  const parts = [];
  if (includesAny(text, ["短发", "短髮"])) parts.push("短发");
  else if (includesAny(text, ["长发", "長髮"])) parts.push("长发");
  if (includesAny(text, ["黑发", "黑色头发", "黑色长发", "黑色短发"])) parts.unshift("黑色");
  if (includesAny(text, ["刘海", "额发"])) parts.push("带刘海");
  return parts.join("") || "";
}

function inferWardrobe(text) {
  if (includesAny(text, ["校服", "蓝白校服"])) return "蓝白校服";
  if (includesAny(text, ["运动服", "蓝白运动服", "蓝白色运动服"])) return "蓝白运动服";
  if (includesAny(text, ["红色卫衣", "红卫衣"])) return "红色卫衣";
  if (includesAny(text, ["风衣"])) return "风衣";
  return "";
}

function inferPalette(text) {
  if (includesAny(text, ["蓝白", "蓝色和白色"])) return "蓝白配色";
  if (includesAny(text, ["红黑", "红色和黑色"])) return "红黑配色";
  if (includesAny(text, ["黑白"])) return "黑白配色";
  return "";
}

function inferLighting(text) {
  if (includesAny(text, ["夜晚", "暗光", "低照度"])) return "低照度夜景光线";
  if (includesAny(text, ["日光", "阳光", "白天"])) return "自然日光";
  return "";
}

function inferTimeWeather(text) {
  if (includesAny(text, ["雨", "雨夜"])) return "雨天或雨夜";
  if (includesAny(text, ["夜晚", "深夜"])) return "夜晚";
  return "";
}

function includesAny(text, values) {
  return values.some((value) => String(text || "").includes(value));
}

function compact(value) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, 80);
}
