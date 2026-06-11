import { worldToScreen } from "./geometry.js";
import { effectiveHeight } from "./nodes.js";

export function barSignature(state, node) {
  return [
    node.id, node.type, node.x, node.y, node.status,
    state.viewport.x, state.viewport.y, state.viewport.scale,
    structureSignature(node),
  ].join("|");
}

export function structureSignature(node) {
  const p = node.params || {};
  return [
    node.id, node.type, p.model,
    p.spec ? JSON.stringify(p.spec) : "",
    p.camera ? "cam" : "", p.motion || "", p.styleRef || "", p.effect || "",
    (p.attachments || []).length,
  ].join("~");
}

export function positionBar(bar, state, node) {
  const h = effectiveHeight(node);
  const bottom = worldToScreen(state.viewport, node.x + node.w / 2, node.y + h);
  const top = worldToScreen(state.viewport, node.x + node.w / 2, node.y);
  const width = bar.offsetWidth || 540;
  const height = bar.offsetHeight || 150;
  const dockSafe = 84;
  let y = bottom.y + 14;
  if (y + height > window.innerHeight - dockSafe) {
    y = top.y - height - 40;
    bar.classList.add("above");
  } else {
    bar.classList.remove("above");
  }
  y = Math.max(8, Math.min(y, window.innerHeight - height - 8));
  const x = Math.max(8, Math.min(bottom.x - width / 2, window.innerWidth - width - 8));
  bar.style.left = `${Math.round(x)}px`;
  bar.style.top = `${Math.round(y)}px`;
}
