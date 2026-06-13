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
  const personSection = sectionText(text, ["人物/主体", "人物", "主体"]);
  const hair = inferHair(text);
  const wardrobe = inferWardrobe(text);
  const palette = inferPalette(text);
  const named = includesAny(text, ["周彤"]) ? "周彤" : "";
  const identity = inferIdentity(personSection, named);
  const face = inferFace(personSection);
  const build = inferBuild(personSection);
  const demeanor = inferDemeanor(personSection);
  const card = {
    identity,
    hair: hair || "保持参考图人物发型发色",
    face: face || "保持参考图人物脸部五官与辨识度",
    build: build || "保持参考图人物体型比例",
    wardrobe: wardrobe || "保持参考图人物服装",
    palette: palette || "保持参考图人物主色调",
    demeanor: demeanor || "保持参考图人物气质和神态",
  };
  return {
    label: named || label,
    signature: compact(uniqueTextParts([named || identity, hair, wardrobe, palette]).join("，")) || "参考图人物",
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
  const sceneSection = sectionText(text, ["场景/美术", "场景", "美术"]);
  const lightingSection = sectionText(text, ["灯光"]);
  const palette = inferPalette(text);
  const card = {
    location: firstClauses(sceneSection, 2) || "参考图中的场景空间",
    layout: inferLayout(sceneSection) || "保持参考图空间结构和主体位置关系",
    props: inferProps(sceneSection) || "保持参考图关键道具与环境元素",
    lighting_mood: firstClauses(lightingSection, 2) || inferLighting(text) || "保持参考图光线基调",
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
  if (includesAny(text, ["深色风衣"])) return "深色风衣";
  if (includesAny(text, ["黑色风衣"])) return "黑色风衣";
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

const SECTION_LABELS = [
  "意图",
  "人物/主体",
  "人物",
  "主体",
  "场景/美术",
  "场景",
  "美术",
  "动作/情节",
  "动作",
  "镜头/构图",
  "镜头",
  "构图",
  "灯光",
  "运动/时间推进",
  "运动",
  "连续性",
  "负面约束",
];

function sectionText(text, labels) {
  const source = String(text || "");
  let start = -1;
  let markerLength = 0;
  for (const label of labels) {
    for (const marker of [`【${label}】`, `${label}：`, `${label}:`]) {
      const index = source.indexOf(marker);
      if (index >= 0 && (start < 0 || index < start)) {
        start = index;
        markerLength = marker.length;
      }
    }
  }
  if (start < 0) return "";
  const bodyStart = start + markerLength;
  let end = source.length;
  for (const label of SECTION_LABELS) {
    for (const marker of [`【${label}】`, `${label}：`, `${label}:`]) {
      const index = source.indexOf(marker, bodyStart + 1);
      if (index >= 0 && index < end) end = index;
    }
  }
  return compactLong(source.slice(bodyStart, end), 260);
}

function inferIdentity(personSection, named) {
  if (named) {
    const detail = firstClauses(personSection, 2);
    return detail ? `${named}，${detail}` : `${named}，参考图中的人物角色`;
  }
  return firstClauses(personSection, 3) || "参考图中的人物角色";
}

function inferFace(personSection) {
  return matchPhrases(personSection, [/面容[^，。；]+/u, /目光[^，。；]+/u, /脸[^，。；]+/u, /五官[^，。；]+/u], 2);
}

function inferBuild(personSection) {
  return matchPhrases(personSection, [/身形[^，。；]+/u, /身材[^，。；]+/u, /体型[^，。；]+/u, /身体[^，。；]+/u], 1);
}

function inferDemeanor(personSection) {
  return matchPhrases(personSection, [/情绪[^，。；]+/u, /神情[^，。；]+/u, /气质[^，。；]+/u, /目光[^，。；]+/u], 2);
}

function inferLayout(sceneSection) {
  return matchPhrases(sceneSection, [/小巷[^，。；]+/u, /街角[^，。；]+/u, /路面[^，。；]+/u, /背景[^，。；]+/u], 2);
}

function inferProps(sceneSection) {
  return matchPhrases(sceneSection, [/霓虹[^，。；]+/u, /砖墙[^，。；]+/u, /路灯[^，。；]+/u, /薄雾[^，。；]+/u, /雨滴[^，。；]+/u], 3);
}

function firstClauses(text, count) {
  return compactLong(String(text || "").split(/[。；\n]/u)[0]?.split(/[，,]/u).slice(0, count).join("，"), 160);
}

function matchPhrases(text, patterns, limit) {
  const source = String(text || "");
  const matches = [];
  for (const pattern of patterns) {
    const match = source.match(pattern);
    if (match?.[0]) pushUniqueText(matches, match[0]);
    if (matches.length >= limit) break;
  }
  return compactLong(matches.join("，"), 160);
}

function uniqueTextParts(values) {
  const parts = [];
  for (const value of values) pushUniqueText(parts, value);
  return parts;
}

function pushUniqueText(parts, value) {
  const text = String(value || "").trim();
  if (!text) return;
  if (parts.some((part) => part.includes(text) || text.includes(part))) return;
  parts.push(text);
}

function includesAny(text, values) {
  return values.some((value) => String(text || "").includes(value));
}

function compact(value) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, 80);
}

function compactLong(value, length) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, length);
}
