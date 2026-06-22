import { assetCardTypeLabel, assetImagePrompt } from "./asset-card-drafts.js";

export function assetCardPromptText(node) {
  const draft = node.params?.assetCardDraft;
  if (!draft || node.params?.nodeRole !== "asset_card_draft") return "";
  const generated = assetImagePrompt(draft);
  const content = String(node.content || "").trim();
  const typeLabel = assetCardTypeLabel(draft.asset_type);
  const guard = [
    `${typeLabel}生成模式：只生成 @${String(draft.label || "").replace(/^@+/, "") || "资产"} 的资产设定板，不生成完整分镜关键帧。`,
    "不得把上游分镜直接画成单张剧情插画；必须输出可复用、可审查、可固定的设定参考。",
    draft.asset_type === "scene" ? "场景资产必须是同一空间的多视角场景设定图，四宫格或清晰分区展示俯瞰、广角、入口/边缘和细节视角；不得加入角色主体，除非资产卡明确要求比例参考。" : "",
    draft.asset_type === "character" ? "角色资产必须是多视图角色设定表，展示正面全身、侧面全身、背面全身和头部/关键材质特写；以主体身份、结构、材质、比例和关键辨识点为主，背景保持简洁。" : "",
    draft.asset_type === "prop" ? "道具资产必须是多视图道具设定表，展示正面、侧面、俯视和局部结构/材质特写；以单体外观、材质、比例和使用状态为主，背景保持简洁。" : "",
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
