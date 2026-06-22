import { assetCardTypeLabel, assetImagePrompt } from "./asset-card-drafts.js";

export function assetCardPromptText(node) {
  const draft = node.params?.assetCardDraft;
  if (!draft || node.params?.nodeRole !== "asset_card_draft") return "";
  const generated = assetImagePrompt(draft);
  const content = String(node.content || "").trim();
  const typeLabel = assetCardTypeLabel(draft.asset_type);
  const guard = [
    `${typeLabel}生成模式：只生成 @${String(draft.label || "").replace(/^@+/, "") || "资产"} 的资产参考图，不生成完整分镜关键帧。`,
    draft.asset_type === "scene" ? "场景资产不得加入角色主体，除非资产卡明确要求角色作为空间比例参考。" : "",
    draft.asset_type === "character" ? "角色资产以主体身份、结构、材质、比例和关键辨识点为主，背景保持简洁。" : "",
    draft.asset_type === "prop" ? "道具资产以单体外观、材质、比例和使用状态为主，背景保持简洁。" : "",
  ].filter(Boolean).join("\n");
  return [generated, content, guard].filter(Boolean).join("\n");
}

export function safeAssetCardSnapshot(draft) {
  return {
    asset_type: String(draft.asset_type || "").slice(0, 40),
    label: String(draft.label || "").replace(/^@+/, "").slice(0, 80),
    status: String(draft.status || "").slice(0, 40),
    signature: String(draft.signature || "").slice(0, 180),
  };
}
