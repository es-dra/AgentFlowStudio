import { propDefaults } from "./visual-asset-prop-defaults.js";

export function visualAssetDefaults(node, imageAsset, assetType) {
  const text = [
    node?.title,
    node?.prompt,
    node?.result,
    imageAsset?.filename,
    imageAsset?.label,
  ].filter(Boolean).join(" ");
  if (assetType === "scene") return sceneDefaults(node, text);
  if (assetType === "prop") return propDefaults(node, text);
  return characterDefaults(node, text);
}

function characterDefaults(node, text) {
  if (isAnimalSubject(text)) return animalSubjectDefaults(node, text);
  const label = defaultLabel(node, "角色资产");
  const personSection = sectionText(text, ["角色/主体", "人物/主体", "人物", "主体"]);
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
    hair: hair || "保持参考图角色发型发色",
    face: face || "保持参考图角色脸部五官与辨识度",
    build: build || "保持参考图角色体型比例",
    wardrobe: wardrobe || "保持参考图角色服装",
    palette: palette || "保持参考图角色主色调",
    demeanor: demeanor || "保持参考图角色气质和神态",
  };
  return {
    label: named || label,
    signature: compact(uniqueTextParts([named || identity, hair, wardrobe, palette]).join("，")) || "参考图角色",
    card,
    locks: [
      "保持参考图角色身份和脸部辨识度",
      hair ? `保持${hair}` : "",
      wardrobe ? `保持${wardrobe}` : "",
      palette ? `保持${palette}` : "",
    ].filter(Boolean).join("\n"),
  };
}

function animalSubjectDefaults(node, text) {
  const label = animalLabel(node, text);
  const personSection = sectionText(text, ["角色/主体", "人物/主体", "人物", "主体"]);
  const identity = inferAnimalIdentity(personSection, label);
  const fur = inferFur(text);
  const palette = inferAnimalPalette(text) || inferPalette(text);
  const card = {
    identity,
    hair: fur || "保持参考图动物主体的毛色、毛发纹理和斑纹",
    face: "保持参考图动物主体的脸部斑纹、眼睛、耳朵和胡须辨识点",
    build: "保持参考图动物主体的体型比例、四肢和尾巴形态",
    wardrobe: "默认保持自然动物外观；服装、饰品或拟人化只在用户明确要求时添加",
    palette: palette || "保持参考图动物主体的毛色主色调",
    demeanor: "保持参考图动物主体的自然神态和姿态",
  };
  return {
    label,
    signature: compact(uniqueTextParts([label, fur, palette]).join("，")) || "参考图动物主体",
    card,
    locks: [
      "保持参考图中同一只动物的毛色、斑纹、眼睛、耳朵、尾巴和体型比例",
      "默认保持自然动物主体身份；拟人化或服装需由用户明确指定",
      fur ? `保持${fur}` : "",
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

function inferFur(text) {
  const parts = [];
  if (includesAny(text, ["黑色狸花猫"])) return "黑色狸花猫毛色与虎斑纹";
  if (includesAny(text, ["狸花猫", "tabby"])) parts.push("狸花猫虎斑纹");
  if (includesAny(text, ["黑猫", "黑色的猫", "黑色猫"])) parts.push("黑色短毛");
  if (includesAny(text, ["棕灰黑", "棕灰", "灰黑"])) parts.push("棕灰黑相间毛色");
  if (includesAny(text, ["M 字纹", "M字纹", "额头 M"])) parts.push("额头 M 字纹");
  return parts.join("，") || "";
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

function inferAnimalPalette(text) {
  if (includesAny(text, ["棕灰黑", "狸花猫", "tabby"])) return "棕灰黑虎斑毛色";
  if (includesAny(text, ["黑猫", "黑色的猫", "黑色猫"])) return "黑色毛色";
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
  "意图", "角色/主体", "人物/主体", "人物", "主体",
  "场景/美术", "场景", "美术", "道具", "关键道具", "物件", "资产",
  "动作/情节", "动作", "镜头/构图", "镜头", "构图", "灯光",
  "运动/时间推进", "运动", "连续性", "负面约束",
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
    return detail ? `${named}，${detail}` : `${named}，参考图中的角色主体`;
  }
  return firstClauses(personSection, 3) || "参考图中的角色主体";
}

function inferAnimalIdentity(personSection, label) {
  const identity = firstClauses(personSection, 3);
  if (identity && !includesAny(identity, ["人物", "人像", "服装", "头发"])) return identity;
  if (label.includes("狸花猫")) return "参考图中的同一只狸花猫";
  if (label.includes("猫")) return "参考图中的同一只猫";
  if (label.includes("狗")) return "参考图中的同一只狗";
  return "参考图中的同一只动物主体";
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

function isAnimalSubject(text) {
  const source = String(text || "");
  const animalTerms = ["狸花猫", "黑猫", "白猫", "橘猫", "猫", "小狗", "狗", "犬", "宠物", "动物", "tabby", "cat", "kitten", "feline", "dog", "puppy", "animal", "pet"];
  const humanTerms = ["人像", "真人", "人类", "女孩", "男孩", "女人", "男人", "女性", "男性", "头发", "发型", "校服", "服装", "person", "human", "girl", "boy", "woman", "man", "hair", "wardrobe", "uniform"];
  return includesAny(source, animalTerms) && !includesAny(source.replaceAll("角色/主体", "").replaceAll("人物/主体", ""), humanTerms);
}

function animalLabel(node, text) {
  const title = defaultLabel(node, "");
  if (title && !includesAny(title, ["图片 / 关键帧", "图片", "关键帧"])) return title;
  if (includesAny(text, ["黑色狸花猫"])) return "黑色狸花猫";
  if (includesAny(text, ["狸花猫", "tabby"])) return "狸花猫";
  if (includesAny(text, ["猫", "cat", "kitten", "feline"])) return "猫主体资产";
  if (includesAny(text, ["狗", "犬", "dog", "puppy"])) return "狗主体资产";
  return "动物主体资产";
}

function compact(value) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, 80);
}

function compactLong(value, length) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, length);
}
