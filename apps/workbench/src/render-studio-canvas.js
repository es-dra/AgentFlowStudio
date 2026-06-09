import { badge, button, el, sectionTitle } from "./dom.js";
import { displayStatus, displayText } from "./display-labels.js";
import { statusTone } from "./workbench-state.js";

export function selectedStudioCardId(cards, workspace, state) {
  const stateCardId = state && state.selectedCardId;
  if (cards.some((card) => card.card_id === stateCardId)) return stateCardId;
  return workspace.canvas?.selected_card_id || cards[0]?.card_id || "";
}

export function selectedStudioInspector(cards, selectedCardId, fallback) {
  const card = cards.find((item) => item.card_id === selectedCardId);
  if (!card) return fallback;
  return {
    card_id: card.card_id,
    mode: card.kind === "scene_card" ? "scene" : "setup",
    title: card.title || "未选择卡片",
    status: card.status || "not_started",
    summary: card.summary || "",
    primary_artifact_id: card.primary_artifact_id || "",
    fields: card.inspector || {},
    refs: card.refs || [],
    blockers: card.blockers || [],
    actions: card.actions || [],
  };
}

export function renderStudioCanvas(workspace, selectedCardId) {
  const cards = Array.isArray(workspace.canvas?.cards) ? workspace.canvas.cards : [];
  return el("div", { className: "studio-canvas" }, [
    renderCanvasToolbar(workspace, cards),
    renderStageHeader(cards),
    cards.length
      ? el("div", { className: "studio-node-flow" }, cards.map((card, index) => renderNode(card, selectedCardId, index, cards.length)))
      : renderEmptyCanvas(),
  ]);
}

export function renderStudioFilmstrip(items) {
  return el("div", { className: "studio-filmstrip" }, [
    sectionTitle("分镜条", `${items.length} 个镜头`),
    items.length ? el("div", { className: "studio-filmstrip-row" }, items.map(renderFilmstripItem)) : el("p", { className: "muted", text: "生成或添加分镜卡后会出现镜头序列。" }),
  ]);
}

function renderCanvasToolbar(workspace, cards) {
  const refCount = cards.reduce((total, card) => total + (Array.isArray(card.refs) ? card.refs.length : 0), 0);
  const blockerCount = cards.reduce((total, card) => total + (Array.isArray(card.blockers) ? card.blockers.length : 0), 0);
  return el("div", { className: "studio-canvas-toolbar" }, [
    el("div", {}, [
      sectionTitle("创作画布", displayStatus(workspace.status || "not_started")),
      el("p", { className: "card-summary", text: "把需求、素材、分镜、候选和项目记忆放在同一张制作画布上推进。" }),
    ]),
    el("div", { className: "studio-canvas-tools" }, [
      badge(`${cards.length} 个节点`, cards.length ? "ready" : "quiet"),
      badge(`${refCount} 个引用`, refCount ? "active" : "quiet"),
      badge(`${blockerCount} 个阻塞`, blockerCount ? "blocked" : "quiet"),
      button("生成画布草稿", "draft-canvas", "secondary"),
      button("添加分镜卡", "register-content-card", "ghost"),
    ]),
  ]);
}

function renderStageHeader(cards) {
  const labels = ["需求", "素材", "分镜", "候选", "审片", "记忆"];
  return el("div", { className: "studio-stage" }, labels.map((label, index) =>
    el("span", { className: index < Math.max(cards.length, 1) ? "active" : "", text: label }),
  ));
}

function renderNode(card, selectedCardId, index, total) {
  const tone = statusTone(card.status);
  return el("div", { className: "studio-node-wrap" }, [
    el("article", { className: `studio-node ${tone}${card.card_id === selectedCardId ? " selected" : ""}`, dataset: { cardId: card.card_id } }, [
      renderMediaFrame(card, index),
      el("div", { className: "studio-node-top" }, [
        badge(nodeLabel(card, index), tone),
        badge(displayStatus(card.status || "not_started"), tone),
      ]),
      el("h3", { text: displayText(card.title || "未命名节点") }),
      card.summary ? el("p", { className: "card-summary", text: displayText(card.summary) }) : null,
      renderNodeMeta(card),
      card.blockers?.length ? el("div", { className: "chips" }, card.blockers.map((item) => badge(displayText(item.message || item.blocker_id), "blocked"))) : null,
    ]),
    index < total - 1 ? el("span", { className: "studio-node-connector", text: "→" }) : null,
  ]);
}

function renderMediaFrame(card, index) {
  return el("div", { className: `studio-media-frame ${mediaFrameTone(card, index)}` }, [
    el("span", { text: mediaFrameLabel(card, index) }),
    el("strong", { text: String(index + 1).padStart(2, "0") }),
    el("small", { text: displayText(card.kind || "canvas node") }),
  ]);
}

function renderNodeMeta(card) {
  const refs = Array.isArray(card.refs) ? card.refs.length : 0;
  return el("div", { className: "studio-node-meta" }, [
    badge(`${refs} 引用`, refs ? "ready" : "quiet"),
    card.primary_artifact_id ? button("打开产物", "open-artifact-ref", "ghost", { artifactId: card.primary_artifact_id }) : null,
  ]);
}

function renderEmptyCanvas() {
  const starters = ["需求", "素材", "分镜", "审片", "记忆"];
  return el("div", { className: "studio-empty-flow" }, starters.map((item, index) =>
    el("div", { className: "studio-empty-node" }, [
      el("div", { className: "studio-node-preview" }, [el("span", { text: String(index + 1).padStart(2, "0") })]),
      el("strong", { text: item }),
    ]),
  ));
}

function renderFilmstripItem(item, index) {
  return el("button", { className: "studio-filmstrip-item", dataset: { cardId: item.card_id } }, [
    el("span", { className: "studio-filmstrip-preview", text: String(index + 1).padStart(2, "0") }),
    el("span", { text: String(index + 1).padStart(2, "0") }),
    el("strong", { text: displayText(item.title) }),
    el("small", { text: displayText(item.summary || item.status) }),
  ]);
}

function nodeLabel(card, index) {
  if (card.kind === "scene_card") return "镜头";
  if (card.kind === "source") return "素材";
  if (card.kind === "review") return "审片";
  if (card.kind === "memory") return "记忆";
  return ["需求", "素材", "分镜", "镜头", "审片", "记忆"][index] || "节点";
}

function mediaFrameLabel(card, index) {
  if (card.primary_artifact_id) return "产物";
  if (card.kind === "scene_card") return "镜头";
  if (card.kind === "source") return "素材";
  if (card.kind === "review") return "候选";
  if (card.kind === "memory") return "记忆";
  return ["需求", "素材", "画布", "镜头", "审片", "记忆"][index] || "节点";
}

function mediaFrameTone(card, index) {
  if (card.status === "blocked") return "blocked";
  if (card.primary_artifact_id) return "artifact";
  return ["brief", "asset", "board", "shot", "review", "memory"][index] || "node";
}
