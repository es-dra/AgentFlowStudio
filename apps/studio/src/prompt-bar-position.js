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
  const contextToolbarSafeGap = 54;
  const placement = chooseNonOverlappingY({
    belowY: bottom.y + contextToolbarSafeGap,
    aboveY: top.y - height - 40,
    height,
    topY: top.y,
    bottomY: bottom.y,
    dockSafe,
  });
  let y = placement.y;
  if (placement.above) {
    bar.classList.add("above");
  } else {
    bar.classList.remove("above");
  }
  y = Math.max(8, Math.min(y, window.innerHeight - height - 8));
  const x = Math.max(8, Math.min(bottom.x - width / 2, window.innerWidth - width - 8));
  bar.style.left = `${Math.round(x)}px`;
  bar.style.top = `${Math.round(y)}px`;
}

export function bindBarResizePositioning(bar, store, nodeId) {
  if (!window.ResizeObserver) return;
  const observer = new ResizeObserver(() => {
    if (!bar.isConnected) {
      observer.disconnect();
      return;
    }
    const state = store.get();
    const fresh = state.nodes[nodeId];
    if (fresh) positionBar(bar, state, fresh);
  });
  observer.observe(bar);
}

export function chooseNonOverlappingY({ belowY, aboveY, height, topY, bottomY, dockSafe }) {
  const minY = 8;
  const maxY = Math.max(minY, window.innerHeight - height - minY);
  const viewportBottom = window.innerHeight - dockSafe;
  const candidates = [
    { y: clampY(belowY, minY, maxY), above: false, priority: belowY + height <= viewportBottom ? 0 : 2 },
    { y: clampY(aboveY, minY, maxY), above: true, priority: aboveY >= minY ? 1 : 3 },
    { y: clampY(bottomY + 16, minY, maxY), above: false, priority: 4 },
    { y: clampY(topY - height - 16, minY, maxY), above: true, priority: 5 },
  ];
  const clear = candidates
    .filter((candidate) => !overlapWithNode(candidate.y, height, topY, bottomY))
    .sort((a, b) => a.priority - b.priority)[0];
  if (clear) return { y: clear.y, above: clear.above };
  const leastOverlap = candidates
    .map((candidate) => ({
      ...candidate,
      overlap: overlapAmount(candidate.y, height, topY, bottomY),
    }))
    .sort((a, b) => a.overlap - b.overlap || a.priority - b.priority)[0];
  return { y: leastOverlap.y, above: leastOverlap.above };
}

function clampY(y, minY, maxY) {
  return Math.max(minY, Math.min(y, maxY));
}

function overlapAmount(y, height, topY, bottomY, gap = 16) {
  const top = Math.max(y, topY - gap);
  const bottom = Math.min(y + height, bottomY + gap);
  return Math.max(0, bottom - top);
}

export function overlapWithNode(y, height, topY, bottomY, gap = 16) {
  return overlapAmount(y, height, topY, bottomY, gap) > 0;
}
