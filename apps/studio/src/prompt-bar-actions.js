import { el } from "./overlay.js";

export function updateNode(store, nodeId, mutate) {
  store.set((s) => {
    const node = s.nodes[nodeId];
    if (node) mutate(node);
  });
}

export function flashTooltip(anchor, text) {
  const tip = el("div", "tooltip", text);
  document.getElementById("overlay-root").appendChild(tip);
  const rect = anchor.getBoundingClientRect();
  tip.style.left = `${rect.left}px`;
  tip.style.top = `${rect.top - 30}px`;
  setTimeout(() => tip.remove(), 1400);
}
