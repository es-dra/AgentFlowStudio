import { effectiveHeight } from "./nodes.js";
import { rectsIntersect, screenToWorld } from "./geometry.js";

export function dragSession(store, nodeIds, e, meta = {}) {
  return {
    kind: "drag-node",
    nodeIds,
    primaryId: meta.primaryId || nodeIds[0],
    additive: Boolean(meta.additive),
    startX: e.clientX,
    startY: e.clientY,
    origins: Object.fromEntries(nodeIds.map((id) => {
      const n = store.get().nodes[id];
      return [id, { x: n.x, y: n.y }];
    })),
    moved: false,
  };
}

export function selectInRect(store, rectScreen) {
  const state = store.get();
  const vp = state.viewport;
  const topLeft = screenToWorld(vp, rectScreen.x, rectScreen.y);
  const bottomRight = screenToWorld(vp, rectScreen.x + rectScreen.w, rectScreen.y + rectScreen.h);
  const worldRect = { x: topLeft.x, y: topLeft.y, w: bottomRight.x - topLeft.x, h: bottomRight.y - topLeft.y };
  const hit = Object.values(state.nodes)
    .filter((n) => rectsIntersect(worldRect, { x: n.x, y: n.y, w: n.w, h: effectiveHeight(n) }))
    .map((n) => n.id);
  store.set((s) => { s.selection = { nodeIds: hit, edgeId: null }; }, { history: false, persist: false });
}

export function updatePortHover(e) {
  e.target.closest?.(".node-port")?.closest(".node")?.classList.toggle("port-hovering", e.type === "pointerover");
}

export function isEditable(target) {
  return target && (target.tagName === "TEXTAREA" || target.tagName === "INPUT" || target.isContentEditable);
}
