const ASSET_RE = /@([A-Za-z0-9_\-\u4e00-\u9fff·]+)/g;
const SCENE_HINTS = ["办公室", "房间", "街道", "屋顶", "城市", "森林", "海边", "山谷", "餐厅", "车内", "走廊", "宫殿", "庭院", "广场", "屏幕"];
const CHARACTER_HINTS = ["主角", "角色", "人物", "女孩", "男孩", "女人", "男人", "老人", "孩子", "机器人", "队长", "老师", "学生"];
const PROP_HINTS = ["手机", "电脑", "键盘", "刀", "剑", "车", "信", "照片", "灯", "书", "门"];

export function structuredShotFromSegment(segment, index) {
  const source = cleanText(segment);
  const assetRefs = extractShotAssetRefs(source);
  return {
    shot_id: `shot_${String(index).padStart(2, "0")}`,
    index,
    duration: inferDuration(source),
    description: descriptionWithAssets(source, assetRefs),
    shot_size: inferShotSize(source),
    light_atmosphere: inferLighting(source),
    camera_motion: inferCameraMotion(source),
    dialogue: inferDialogue(source),
    sound: inferSound(source),
    asset_refs: assetRefs,
    source_text: source,
  };
}

export function structuredShotText(shot) {
  const assetLine = shot.asset_refs.length
    ? shot.asset_refs.map(assetRefToken).join("、")
    : "@主角、@主要场景";
  return [
    `镜号：${String(shot.index).padStart(2, "0")}`,
    `时长：${shot.duration}`,
    `画面描述：${shot.description}`,
    `景别：${shot.shot_size}`,
    `光影氛围：${shot.light_atmosphere}`,
    `运镜：${shot.camera_motion}`,
    `对白/旁白：${shot.dialogue}`,
    `音效：${shot.sound}`,
    `资产：${assetLine}`,
  ].join("\n");
}

export function extractShotAssetRefs(text) {
  const refs = [];
  for (const match of String(text || "").matchAll(ASSET_RE)) {
    pushAssetRef(refs, match[1], classifyAsset(match[1], text), "explicit");
  }
  addImplicitRefs(refs, text);
  return refs;
}

export function assetRefToken(asset) {
  return `@${asset.label}`;
}

export function assetTypeLabel(asset) {
  return {
    character: "角色资产",
    scene: "场景资产",
    prop: "道具资产",
  }[asset.asset_type] || "资产";
}

function addImplicitRefs(refs, text) {
  const hasCharacter = refs.some((asset) => asset.asset_type === "character");
  const hasScene = refs.some((asset) => asset.asset_type === "scene");
  const hasProp = refs.some((asset) => asset.asset_type === "prop");
  if (!hasCharacter && CHARACTER_HINTS.some((hint) => text.includes(hint))) {
    pushAssetRef(refs, "主角", "character", "candidate");
  }
  if (!hasScene && SCENE_HINTS.some((hint) => text.includes(hint))) {
    pushAssetRef(refs, "主要场景", "scene", "candidate");
  }
  if (!hasProp) {
    const prop = PROP_HINTS.find((hint) => text.includes(hint));
    if (prop) pushAssetRef(refs, prop, "prop", "candidate");
  }
  if (!refs.length) {
    pushAssetRef(refs, "主角", "character", "candidate");
    pushAssetRef(refs, "主要场景", "scene", "candidate");
  }
}

function pushAssetRef(refs, label, assetType, source) {
  const clean = cleanAssetLabel(label);
  if (!clean || refs.some((asset) => asset.label === clean)) return;
  refs.push({
    label: clean,
    asset_id: `candidate:${assetType}:${slug(clean)}`,
    asset_type: assetType,
    status: source === "explicit" ? "mentioned" : "candidate",
    source,
  });
}

function descriptionWithAssets(source, assetRefs) {
  const missing = assetRefs.filter((asset) => !source.includes(assetRefToken(asset)));
  const prefix = missing.length ? `${missing.map(assetRefToken).join(" ")}。` : "";
  return `${prefix}${source}`;
}

function inferDuration(text) {
  const match = text.match(/(\d{1,2})\s*(?:s|秒)/i);
  if (match) return `${match[1]}s`;
  if (text.length > 130) return "8s";
  if (text.length > 70) return "6s";
  return "5s";
}

function inferShotSize(text) {
  if (/大远景|远景|全貌|城市|山谷|天空/.test(text)) return "远景";
  if (/全景|全身|环境/.test(text)) return "全景";
  if (/近景|脸|眼神|表情/.test(text)) return "近景";
  if (/特写|手指|瞳孔|细节|屏幕/.test(text)) return "特写";
  if (/半身|肩/.test(text)) return "半身景";
  return "中景";
}

function inferLighting(text) {
  if (/夜|霓虹|暗|阴影/.test(text)) return "低照度，冷色阴影压低环境";
  if (/晨|清晨|阳光|明亮/.test(text)) return "自然主光，明亮通透";
  if (/雨|雾|烟|尘/.test(text)) return "柔散光，空气颗粒增强层次";
  if (/紧张|压迫|冲突/.test(text)) return "高反差侧光，氛围紧张";
  return "自然光影，氛围服务情绪推进";
}

function inferCameraMotion(text) {
  if (/推近|逼近|靠近/.test(text)) return "缓慢推近";
  if (/拉远|退后/.test(text)) return "缓慢拉远";
  if (/跟随|追|奔跑/.test(text)) return "跟拍移动";
  if (/摇|环绕/.test(text)) return "轻微摇移";
  if (/切|闪回|突然/.test(text)) return "快速切入";
  return "固定机位，轻微呼吸感";
}

function inferDialogue(text) {
  const quote = text.match(/[“"](.*?)[”"]/);
  if (quote?.[1]) return quote[1].slice(0, 80);
  const line = text.match(/(?:对白|旁白|台词)\s*[:：]\s*(.+)$/);
  return line?.[1]?.slice(0, 80) || "无明确对白";
}

function inferSound(text) {
  if (/键盘|电脑|屏幕/.test(text)) return "键盘声与设备低频环境音";
  if (/雨|海|风/.test(text)) return "环境自然声持续铺底";
  if (/冲突|奔跑|撞|爆/.test(text)) return "急促动作音与低频冲击";
  return "环境底噪，动作音随画面同步";
}

function classifyAsset(label, context) {
  if (SCENE_HINTS.some((hint) => label.includes(hint) || context.includes(`${label}里`))) return "scene";
  if (PROP_HINTS.some((hint) => label.includes(hint))) return "prop";
  return "character";
}

function cleanText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function cleanAssetLabel(value) {
  return String(value || "").replace(/[，。；:：,.!?！？]+$/g, "").trim().slice(0, 24);
}

function slug(value) {
  return encodeURIComponent(value).replace(/%/g, "").slice(0, 32).toLowerCase() || "asset";
}
