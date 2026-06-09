import { el, sectionTitle } from "./dom.js";
import { displayStatus, displayText } from "./display-labels.js";

export function renderStudioSideRail(sideRail, counts) {
  const assets = Array.isArray(sideRail.assets) ? sideRail.assets : [];
  const candidates = Array.isArray(sideRail.review_candidates) ? sideRail.review_candidates : [];
  const styleProfile = sideRail.style_profile || {};
  return el("aside", { className: "studio-side-rail" }, [
    renderSideSection("assets", [
      sectionTitle("参考素材", `${counts.assets || 0}`),
      assets.length ? el("div", { className: "studio-asset-list" }, assets.map(renderAsset)) : el("p", { className: "muted", text: "先添加安全素材摘要。" }),
    ]),
    renderSideSection("memory", [
      sectionTitle("项目记忆", displayStatus(styleProfile.status || "not_started")),
      styleProfile.summary ? el("p", { className: "card-summary", text: displayText(styleProfile.summary) }) : el("p", { className: "muted", text: "审片决定会影响下一轮复用。" }),
      renderPreferences(styleProfile.reusable_preferences || []),
    ]),
    renderSideSection("review", [
      sectionTitle("审片队列", `${candidates.length}`),
      candidates.length ? el("div", { className: "studio-review-list" }, candidates.map(renderCandidate)) : el("p", { className: "muted", text: "还没有审片候选。" }),
    ]),
  ]);
}

function renderSideSection(kind, children) {
  return el("div", { className: `studio-side-section studio-side-${kind}` }, children);
}

function renderAsset(asset) {
  return el("article", { className: "studio-asset-card" }, [
    el("span", { className: "studio-side-thumb", text: assetThumb(asset) }),
    el("span", { text: displayText(asset.asset_type || "reference") }),
    el("strong", { text: displayText(asset.label || "素材") }),
    el("small", { text: displayText(asset.summary || "安全摘要") }),
  ]);
}

function renderCandidate(candidate) {
  return el("button", { className: "studio-review-card", dataset: { variantId: candidate.candidate_id, artifactId: candidate.artifact_id } }, [
    el("span", { className: "studio-side-thumb", text: "CUT" }),
    el("strong", { text: displayText(candidate.title || "审片候选") }),
    el("small", { text: displayText(candidate.summary || candidate.stage || candidate.status) }),
  ]);
}

function assetThumb(asset) {
  const type = String(asset.asset_type || "reference").toLowerCase();
  if (type.includes("visual") || type.includes("image")) return "IMG";
  if (type.includes("script")) return "TXT";
  if (type.includes("brief") || type.includes("requirement")) return "BRF";
  return "REF";
}

function renderPreferences(items) {
  if (!items.length) return el("p", { className: "muted", text: "还没有可复用偏好。" });
  return el("ul", { className: "studio-memory-list" }, items.slice(0, 4).map((item) => el("li", { text: displayText(item) })));
}
