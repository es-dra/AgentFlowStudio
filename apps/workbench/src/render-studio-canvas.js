import { button, el, sectionTitle } from "./dom.js";
import { displayText } from "./display-labels.js";
import { statusTone } from "./workbench-state.js";
import { STUDIO_MODES, studioModeById, studioModeCards } from "./studio-mode.js";

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

export function renderStudioCanvas(workspace, selectedCardId, mode = "produce") {
  const cards = Array.isArray(workspace.canvas?.cards) ? workspace.canvas.cards : [];
  const visibleCards = studioModeCards(cards, mode);
  return el("div", { className: "studio-canvas" }, [
    renderCanvasToolbar(workspace, cards, mode),
    renderStudioModeSwitch(mode),
    visibleCards.length
      ? el("div", { className: "studio-node-flow" }, visibleCards.map((card, index) => renderNode(card, selectedCardId, index, visibleCards.length)))
      : renderModeEmpty(mode),
  ]);
}

export function renderStudioFilmstrip(items) {
  return el("div", { className: "studio-filmstrip" }, [
    sectionTitle("分镜条", `${items.length} 个镜头`),
    items.length ? el("div", { className: "studio-filmstrip-row" }, items.map(renderFilmstripItem)) : el("p", { className: "muted", text: "生成或添加分镜卡后会出现镜头序列。" }),
  ]);
}

function renderCanvasToolbar(workspace, cards, mode) {
  const modeInfo = studioModeById(mode);
  const visibleCount = studioModeCards(cards, mode).length;
  return el("div", { className: "studio-canvas-toolbar" }, [
    el("div", { className: "studio-canvas-title" }, [
      el("h2", { text: "创作画布" }),
      el("small", { text: `${modeInfo.label} · ${visibleCount || "暂无"} 个对象` }),
    ]),
    el("div", { className: "studio-canvas-tools" }, [
      button("生成画布草稿", "draft-canvas", "secondary"),
      button("添加分镜卡", "register-content-card", "ghost"),
    ]),
  ]);
}

function renderStudioModeSwitch(mode) {
  return el("div", { className: "studio-mode-switch", attrs: { "aria-label": "创作模式" } }, STUDIO_MODES.map((item) =>
    el("button", {
      className: `studio-mode-segment${item.id === mode ? " active" : ""}`,
      text: item.label,
      attrs: { "data-studio-mode": item.id, "aria-pressed": item.id === mode ? "true" : "false", title: item.meta },
    }),
  ));
}

function renderModeEmpty(mode) {
  const modeInfo = studioModeById(mode);
  return el("div", { className: "studio-mode-empty" }, [
    el("div", {}, [
      el("strong", { text: `${modeInfo.label}模式暂无内容` }),
      el("p", { text: modeInfo.empty }),
    ]),
  ]);
}

function renderNode(card, selectedCardId, index, total) {
  const tone = statusTone(card.status);
  return el("div", { className: "studio-node-wrap" }, [
    el("article", { className: `studio-node ${tone}${card.card_id === selectedCardId ? " selected" : ""}`, dataset: { cardId: card.card_id } }, [
      renderMediaFrame(card, index),
      el("div", { className: "studio-node-caption" }, [
        el("span", { className: `studio-node-status ${tone}`, attrs: { title: displayText(card.status || "not_started") } }),
        el("h3", { text: displayText(card.title || "未命名节点") }),
      ]),
      card.blockers?.length ? el("small", { className: "studio-node-warning", text: "需要处理" }) : null,
    ]),
    index < total - 1 ? el("span", { className: "studio-node-connector", attrs: { "aria-hidden": "true" } }) : null,
  ]);
}

function renderMediaFrame(card, index) {
  return el("div", { className: `studio-media-frame ${mediaFrameTone(card, index)}` }, [
    el("span", { text: mediaFrameLabel(card, index) }),
    el("strong", { text: String(index + 1).padStart(2, "0") }),
  ]);
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
