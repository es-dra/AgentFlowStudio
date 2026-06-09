import { badge, el, sectionTitle } from "./dom.js";
import { displayStatus, displayText } from "./display-labels.js";

function renderCounts(counts) {
  const value = counts || {};
  return el("div", { className: "memory-facts" }, [
    badge(`${value.total || 0} 个素材`, value.total ? "ready" : "quiet"),
    badge(`${value.brief || 0} 个需求`, value.brief ? "good" : "quiet"),
    badge(`${value.reference || 0} 个参考`, value.reference ? "ready" : "quiet"),
    badge(`${value.script || 0} 个脚本`, value.script ? "active" : "quiet"),
  ]);
}

function renderAsset(item) {
  return el("article", { className: "reference-card" }, [
    el("div", { className: "card-head" }, [el("h3", { text: item.label }), badge(assetTypeLabel(item.asset_type), "ready")]),
    el("p", { className: "card-summary", text: item.summary }),
    el("div", { className: "chips" }, [badge(displayText(item.usage), "quiet"), badge(displayText(item.safety), "quiet")]),
    el("code", { text: item.asset_id }),
  ]);
}

function assetTypeLabel(type) {
  return {
    brief: "需求",
    reference: "参考",
    script: "脚本",
  }[type] || "素材";
}

function groupedAssets(items) {
  const groups = [
    ["brief", "内容需求"],
    ["reference", "视觉参考"],
    ["script", "脚本提纲"],
    ["other", "其他素材"],
  ];
  return groups.map(([type, label]) => ({
    type,
    label,
    items: items.filter((item) => (type === "other" ? !["brief", "reference", "script"].includes(item.asset_type) : item.asset_type === type)),
  }));
}

function renderNextActions(actions) {
  const items = Array.isArray(actions) && actions.length ? actions : ["添加安全参考摘要后继续。"];
  return el("ul", { className: "memory-list" }, items.map((item) => el("li", { text: displayText(item) })));
}

export function renderAssetLibrary(assetLibrary) {
  const value = assetLibrary || { counts: {}, items: [], next_actions: [] };
  const items = Array.isArray(value.items) ? value.items : [];
  return el("section", { className: "reference-library" }, [
    el("div", { className: "asset-library-head" }, [
      sectionTitle("素材库", displayStatus(value.status || "needs_assets")),
      el("p", { className: "card-summary", text: displayText(value.summary, "先添加安全摘要，再进入制作检查。") }),
    ]),
    renderCounts(value.counts),
    items.length ? el("div", { className: "asset-groups" }, groupedAssets(items).map(renderAssetGroup)) : renderEmptyLibrary(),
    el("div", { className: "asset-next-actions" }, [
      sectionTitle("下一步", displayText("safe summary only")),
      renderNextActions(value.next_actions),
    ]),
  ]);
}

function renderAssetGroup(group) {
  return el("section", { className: "asset-group" }, [
    sectionTitle(group.label, `${group.items.length}`),
    group.items.length ? el("div", { className: "reference-grid" }, group.items.map(renderAsset)) : el("p", { className: "muted", text: "暂无内容。" }),
  ]);
}

function renderEmptyLibrary() {
  return el("div", { className: "asset-empty-state" }, [
    el("strong", { text: "还没有素材摘要" }),
    el("p", { text: "请从左侧操作区添加内容需求、视觉参考或脚本提纲。这里只接收 safe summary，不接收本地素材路径或媒体字节。" }),
  ]);
}
