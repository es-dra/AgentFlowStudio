import {
  assetCardFieldsForType,
  assetCardTypeLabel,
  normalizeAssetCardDraft,
} from "./asset-card-drafts.js";

export function assetImagePrompt(draft) {
  const card = normalizeAssetCardDraft(draft);
  return [
    assetImageLead(card),
    assetImageModeInstruction(card.asset_type, card.label),
    "Use professional concept art rendering with clear forms, readable materials, stable proportions, and production reference quality.",
    `Asset signature: ${card.signature}`,
    "Asset facts:",
    assetFieldLines(card),
    "Keep the result as a visual reference image only. Do not turn it into a storyboard keyframe or a complete narrative scene.",
    "Forbidden: software dashboard, app interface, data chart, infographic, UI panel, typography, captions, labels, watermarks, logos, borders, decorative card layout.",
  ].filter(Boolean).join("\n");
}

export function assetImageRatio(assetType) {
  return safeAssetType(assetType) === "prop" ? "1:1" : "16:9";
}

export function assetPromptSupplementFromNode(node) {
  const manual = String(node?.params?.assetCardDraft?.user_edited_text || "").trim();
  if (manual && !looksLikeGeneratedAssetCardText(manual)) return `User asset-card adjustment:\n${manual}`;
  return "";
}

function assetImageLead(card) {
  return `Visual target: reusable ${assetCardTypeLabel(card.asset_type)} reference image for asset named ${cleanAssetName(card.label)}.`;
}

function assetImageModeInstruction(assetType, label) {
  const assetName = cleanAssetName(label);
  if (assetType === "scene") {
    return [
      `Environment reference for asset named ${assetName}: show the same environment/location from multiple clear camera angles in one image.`,
      "Required views: wide establishing view, reverse angle, overhead/spatial layout view, and lighting/material detail view.",
      "Keep the same architecture, skyline, horizon, props, lighting direction, time of day, and spatial relationship across all views.",
      "No main character or robot unless a tiny scale reference is explicitly needed.",
    ].join(" ");
  }
  if (assetType === "prop") {
    return [
      `Object reference for asset named ${assetName}: show one prop/object with orthographic front, side, top, and close-up material/detail views.`,
      "Keep the object centered, isolated, readable, and consistent across all views.",
      "Do not let a character or environment become the main subject.",
    ].join(" ");
  }
  return [
    `Character turnaround for asset named ${assetName}: show the same character in front full-body, side full-body, back full-body, and head/chest material detail views.`,
    "Keep one consistent identity, head shape, body proportions, limb structure, silhouette, palette, material, and expression across every view.",
    "Use a plain neutral studio background with minimal ground shadow; do not include the rooftop scene as the main background.",
  ].join(" ");
}

function cleanAssetName(value) {
  return String(value || "asset").replace(/^@+/, "").replace(/[<>]/g, "").trim() || "asset";
}

function assetFieldLines(card) {
  return assetCardFieldsForType(card.asset_type)
    .map(([key, label]) => `${providerFieldLabel(card.asset_type, key, label)}: ${card.feature_card[key] || "to be confirmed"}`)
    .join("\n");
}

function providerFieldLabel(assetType, key, fallback) {
  const labels = {
    character: {
      identity: "Identity",
      appearance: "Recognizable structure",
      wardrobe: "Outer shell / clothing",
      palette: "Color palette",
      demeanor: "Mood / expression",
      reference_views: "Required reference views",
    },
    scene: {
      location: "Location",
      layout: "Spatial layout",
      props: "Environment elements",
      lighting_mood: "Lighting mood",
      time_weather: "Time and weather",
      view_set: "Required camera angles",
    },
    prop: {
      category: "Object category",
      appearance: "Recognizable details",
      material: "Materials and craft",
      scale: "Scale relationship",
      usage: "Usage state",
      continuity: "Continuity constraint",
      reference_views: "Required reference views",
    },
  };
  return labels[safeAssetType(assetType)]?.[key] || fallback;
}

function looksLikeGeneratedAssetCardText(value) {
  return /^资产类型：/u.test(value)
    || /状态：候选草稿/u.test(value)
    || /特征卡：/u.test(value)
    || /不可变锁定项：/u.test(value);
}

function safeAssetType(value) {
  return ["character", "scene", "prop"].includes(value) ? value : "character";
}
