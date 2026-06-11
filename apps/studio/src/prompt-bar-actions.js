import { el } from "./overlay.js";

export function updateNode(store, nodeId, mutate, options) {
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (node) mutate(node);
  }, options);
}

export function flashTooltip(anchor, text) {
  const tip = el("div", "tooltip", text);
  document.getElementById("overlay-root").appendChild(tip);
  const rect = anchor.getBoundingClientRect();
  tip.style.left = `${rect.left}px`;
  tip.style.top = `${rect.top - 30}px`;
  setTimeout(() => tip.remove(), 1400);
}
