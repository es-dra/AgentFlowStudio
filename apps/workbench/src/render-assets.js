import { badge, el, sectionTitle } from "./dom.js";

function renderCounts(counts) {
  const value = counts || {};
  return el("div", { className: "memory-facts" }, [
    badge(`${value.total || 0} total`, value.total ? "ready" : "quiet"),
    badge(`${value.brief || 0} briefs`, value.brief ? "good" : "quiet"),
    badge(`${value.reference || 0} refs`, value.reference ? "ready" : "quiet"),
    badge(`${value.script || 0} scripts`, value.script ? "active" : "quiet"),
  ]);
}

function renderAsset(item) {
  return el("article", { className: "reference-card" }, [
    el("div", { className: "card-head" }, [el("h3", { text: item.label }), badge(item.asset_type, "ready")]),
    el("p", { className: "card-summary", text: item.summary }),
    el("div", { className: "chips" }, [badge(item.usage, "quiet"), badge(item.safety, "quiet")]),
    el("code", { text: item.asset_id }),
  ]);
}

function renderNextActions(actions) {
  const items = Array.isArray(actions) && actions.length ? actions : ["Add safe reference summaries to continue."];
  return el("ul", { className: "memory-list" }, items.map((item) => el("li", { text: item })));
}

export function renderAssetLibrary(assetLibrary) {
  const value = assetLibrary || { counts: {}, items: [], next_actions: [] };
  const items = Array.isArray(value.items) ? value.items : [];
  return el("section", { className: "reference-library" }, [
    sectionTitle("Reference Library", value.status || "needs_assets"),
    el("p", { className: "card-summary", text: value.summary || "Add safe summaries before production checks." }),
    renderCounts(value.counts),
    items.length
      ? el("div", { className: "reference-grid" }, items.map(renderAsset))
      : el("p", { className: "muted", text: "Use Asset Library controls to add a brief, script, or approved reference summary." }),
    renderNextActions(value.next_actions),
  ]);
}
