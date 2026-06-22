export function propDefaults(node, text) {
  const label = defaultLabel(node, "道具资产");
  const propSection = sectionText(text, ["道具", "关键道具", "物件", "资产"]);
  const card = {
    category: label,
    appearance: firstClauses(propSection || text, 2) || "参考图中的道具外观",
    material: inferMaterial(text) || "保持参考图材质",
    scale: "保持参考图与角色/场景的比例关系",
    usage: inferUsage(text) || "按分镜动作使用",
    continuity: "保持同一造型、磨损状态和摆放/持握方式",
    reference_views: "正面、侧面、俯视、局部结构/材质特写保持一致",
  };
  return {
    label,
    signature: compact([label, card.appearance, card.material].filter(Boolean).join("，")) || "参考图道具",
    card,
    locks: [
      "保持参考图道具外观",
      card.material ? `保持${card.material}` : "",
      "保持尺寸比例和使用状态",
    ].filter(Boolean).join("\n"),
  };
}

function defaultLabel(node, fallback) {
  const title = String(node?.title || "").trim();
  if (title && !/^图片节点\s*\d*$/u.test(title)) return title.slice(0, 32);
  return fallback;
}

function sectionText(text, labels) {
  const source = String(text || "");
  const markers = labels.flatMap((label) => [`【${label}】`, `${label}：`, `${label}:`]);
  const found = markers.map((marker) => [source.indexOf(marker), marker.length]).filter(([index]) => index >= 0);
  if (!found.length) return "";
  const [start, markerLength] = found.sort((a, b) => a[0] - b[0])[0];
  const bodyStart = start + markerLength;
  const end = source.slice(bodyStart + 1).search(/【[^】]+】|[\u4e00-\u9fa5/]+[：:]/u);
  return compactLong(source.slice(bodyStart, end >= 0 ? bodyStart + 1 + end : source.length), 260);
}

function firstClauses(text, count) {
  return compactLong(String(text || "").split(/[。；\n]/u)[0]?.split(/[，,]/u).slice(0, count).join("，"), 160);
}

function inferMaterial(text) {
  if (includesAny(text, ["黄铜", "铜"])) return "黄铜材质";
  if (includesAny(text, ["玻璃"])) return "玻璃材质";
  if (includesAny(text, ["金属"])) return "金属材质";
  if (includesAny(text, ["木质", "木头"])) return "木质材质";
  return "";
}

function inferUsage(text) {
  if (includesAny(text, ["手持", "拿着", "握住"])) return "角色手持使用";
  if (includesAny(text, ["佩戴", "挂在"])) return "角色佩戴或随身携带";
  if (includesAny(text, ["桌上", "摆放"])) return "作为场景内摆放道具";
  return "";
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
