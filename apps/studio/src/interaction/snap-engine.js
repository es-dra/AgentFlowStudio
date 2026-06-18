import { snap } from "../geometry.js";
import { effectiveHeight } from "../nodes.js";

const ALIGN_THRESHOLD = 10;

export function resolveDragSnap(state, session, pointer) {
  const primaryId = session.primaryId || session.nodeIds[0];
  const primary = state.nodes[primaryId];
  const primaryOrigin = session.origins[primaryId];
  if (!primary || !primaryOrigin) return { positions: {}, guides: [], kind: "none" };

  const delta = axisLockedDelta(pointer);
  const base = {
    x: snap(primaryOrigin.x + delta.dx),
    y: snap(primaryOrigin.y + delta.dy),
  };
  const align = pointer.ctrlKey || pointer.metaKey
    ? { x: null, y: null, dx: 0, dy: 0 }
    : resolveAlignment(state, session, primary, base);
  const positions = {};

  for (const id of session.nodeIds) {
    const origin = session.origins[id];
    if (!origin) continue;
    positions[id] = {
      x: snap(origin.x + delta.dx) + align.dx,
      y: snap(origin.y + delta.dy) + align.dy,
    };
  }

  return {
    positions,
    guides: [align.x, align.y].filter(Boolean),
    kind: align.x || align.y ? "align" : "grid",
    primaryPosition: positions[primaryId] || base,
  };
}

function axisLockedDelta(pointer) {
  const dx = Number(pointer.dx || 0);
  const dy = Number(pointer.dy || 0);
  if (!pointer.shiftKey) return { dx, dy };
  return Math.abs(dx) >= Math.abs(dy) ? { dx, dy: 0 } : { dx: 0, dy };
}

function resolveAlignment(state, session, primary, base) {
  const selected = new Set(session.nodeIds);
  const primaryAnchors = anchorsFor(primary, base);
  const otherAnchors = Object.values(state.nodes)
    .filter((node) => node && !selected.has(node.id))
    .flatMap((node) => anchorsFor(node, { x: node.x, y: node.y }));
  const x = nearestGuide(primaryAnchors.filter((item) => item.axis === "x"), otherAnchors, "x");
  const y = nearestGuide(primaryAnchors.filter((item) => item.axis === "y"), otherAnchors, "y");
  return {
    x: x ? { axis: "x", value: x.value, label: x.label } : null,
    y: y ? { axis: "y", value: y.value, label: y.label } : null,
    dx: x ? x.value - x.fromValue : 0,
    dy: y ? y.value - y.fromValue : 0,
  };
}

function nearestGuide(fromAnchors, otherAnchors, axis) {
  let best = null;
  for (const from of fromAnchors) {
    for (const target of otherAnchors) {
      if (target.axis !== axis) continue;
      const distance = Math.abs(target.value - from.value);
      if (distance > ALIGN_THRESHOLD) continue;
      if (!best || distance < best.distance) {
        best = { value: target.value, fromValue: from.value, distance, label: target.kind };
      }
    }
  }
  return best;
}

function anchorsFor(node, position) {
  const w = Number(node.w || 280);
  const h = Number(effectiveHeight(node) || node.h || 250);
  return [
    { axis: "x", kind: "left", value: position.x },
    { axis: "x", kind: "center", value: position.x + w / 2 },
    { axis: "x", kind: "right", value: position.x + w },
    { axis: "y", kind: "top", value: position.y },
    { axis: "y", kind: "middle", value: position.y + h / 2 },
    { axis: "y", kind: "bottom", value: position.y + h },
  ];
}
