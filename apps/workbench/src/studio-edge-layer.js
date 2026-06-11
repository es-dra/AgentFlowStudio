import { el } from "./dom.js";

export function renderStudioEdgeLayer(cards, selectedCardId, state) {
  const edges = cards.slice(0, -1).map((card, index) => [card.card_id, cards[index + 1]?.card_id, index]);
  return el("svg", { className: "studio-edge-layer", attrs: { viewBox: "0 0 1200 680", "aria-hidden": "true" } }, [
    ...edges.map(([from, to, index]) => el("path", {
      className: edgeClass(from, to, selectedCardId),
      attrs: { d: edgePath(index), "data-linked-node-id": `${from}:${to}` },
    })),
    state.connectingFromNodeId ? el("path", {
      className: "studio-canvas-edge pending",
      attrs: { d: "M 480 300 C 570 240 660 360 760 300", "data-linked-node-id": state.connectingFromNodeId },
    }) : null,
  ]);
}

export function linkedNodeClass(card, cards, selectedCardId) {
  if (!selectedCardId || card.card_id === selectedCardId) return "";
  const selectedIndex = cards.findIndex((item) => item.card_id === selectedCardId);
  const index = cards.findIndex((item) => item.card_id === card.card_id);
  if (Math.abs(index - selectedIndex) === 1) return " is-linked";
  return selectedIndex >= 0 ? " is-dimmed" : "";
}

function edgeClass(from, to, selectedCardId) {
  const active = from === selectedCardId || to === selectedCardId;
  return `studio-canvas-edge connected${active ? " selected" : ""}`;
}

function edgePath(index) {
  const y = 160 + (index % 3) * 140;
  const startX = 190 + index * 120;
  return `M ${startX} ${y} C ${startX + 80} ${y - 70} ${startX + 180} ${y + 70} ${startX + 260} ${y}`;
}
