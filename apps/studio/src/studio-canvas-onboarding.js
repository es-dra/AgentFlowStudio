import { visibleCanvasCenter } from "./canvas-safe-area.js";
import { createNode } from "./nodes.js";
import { importScriptFileIntoTextNode } from "./script-breakdown.js";

export function bindCanvasEmptyOnboarding(store) {
  const form = document.querySelector(".canvas-empty-onboarding");
  if (!form || form.dataset.bound) return;
  form.dataset.bound = "1";
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const input = form.querySelector('[data-empty-action="idea-text"]');
    const text = String(input?.value || "").trim();
    if (!text) {
      input?.focus();
      return;
    }
    window.dispatchEvent(new CustomEvent("afs:agent-chat-submit", { detail: { message: `/idea ${text}` } }));
  });
  form.querySelector('[data-empty-action="import-script"]')?.addEventListener("click", () => {
    const node = createEmptyTextNode(store, "剧本文本");
    importScriptFileIntoTextNode(store, node);
  });
  form.querySelector('[data-empty-action="blank-node"]')?.addEventListener("click", () => {
    createEmptyTextNode(store, "故事文本");
  });
}

function createEmptyTextNode(store, title) {
  const point = canvasCenterWorldPoint(store);
  const node = createNode(store, "text", point.x - 150, point.y - 120);
  store.set((state) => {
    const target = state.nodes[node.id];
    if (!target) return;
    target.title = title;
    target.status = "empty";
    target.content = "";
    target.prompt = "";
    state.selection = { nodeIds: [node.id], edgeId: null };
  });
  return store.get().nodes[node.id] || node;
}

function canvasCenterWorldPoint(store) {
  const viewport = store.get().viewport || { x: 0, y: 0, scale: 1 };
  const center = visibleCanvasCenter();
  const scale = Number(viewport.scale || 1) || 1;
  return {
    x: Math.round(((center.x || 450) - Number(viewport.x || 0)) / scale),
    y: Math.round(((center.y || 310) - Number(viewport.y || 0)) / scale),
  };
}
