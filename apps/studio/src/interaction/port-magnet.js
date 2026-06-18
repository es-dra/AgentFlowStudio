const MAGNET_RANGE = 44;
const EDGE_INSET = 18;
const PORT_Y_RANGE = 42;
const PORT_FOLLOW_Y = 16;

let activeNode = null;

export function updatePortMagnet(event) {
  const target = nearestMagnetTarget(event);
  if (!target) {
    clearPortMagnet();
    return null;
  }
  applyMagnetTarget(target);
  return { nodeId: target.nodeEl.dataset.nodeId, side: target.side };
}

export function outputPortFromMagnet(event) {
  const target = nearestMagnetTarget(event);
  if (!target || target.side !== "right") return null;
  applyMagnetTarget(target);
  return target.nodeEl.querySelector(".node-port.out");
}

export function clearPortMagnet() {
  if (!activeNode) return;
  activeNode.classList.remove("port-magnet-left", "port-magnet-right");
  activeNode.style.removeProperty("--port-magnet-y");
  activeNode = null;
}

function applyMagnetTarget(target) {
  if (activeNode && activeNode !== target.nodeEl) clearPortMagnet();
  activeNode = target.nodeEl;
  activeNode.classList.toggle("port-magnet-left", target.side === "left");
  activeNode.classList.toggle("port-magnet-right", target.side === "right");
  activeNode.style.setProperty("--port-magnet-y", `${Math.round(target.offsetY)}px`);
}

function nearestMagnetTarget(event) {
  let best = null;
  for (const nodeEl of document.querySelectorAll(".node")) {
    const rect = nodeEl.getBoundingClientRect();
    const side = magnetSide(event.clientX, event.clientY, rect);
    if (!side) continue;
    const sideX = side === "left" ? rect.left : rect.right;
    const sideY = portCenterY(rect);
    const distanceX = Math.abs(event.clientX - sideX);
    const distanceY = Math.abs(event.clientY - sideY);
    const distance = distanceX + distanceY * 0.45;
    if (best && distance >= best.distance) continue;
    best = {
      nodeEl,
      side,
      distance,
      offsetY: clamp(event.clientY - sideY, -PORT_FOLLOW_Y, PORT_FOLLOW_Y),
    };
  }
  return best;
}

function magnetSide(x, y, rect) {
  const withinPortBand = Math.abs(y - portCenterY(rect)) <= PORT_Y_RANGE;
  if (!withinPortBand) return null;
  const nearLeft = x >= rect.left - MAGNET_RANGE && x <= rect.left + EDGE_INSET;
  const nearRight = x <= rect.right + MAGNET_RANGE && x >= rect.right - EDGE_INSET;
  if (nearLeft && nearRight) {
    return Math.abs(x - rect.left) <= Math.abs(x - rect.right) ? "left" : "right";
  }
  if (nearLeft) return "left";
  if (nearRight) return "right";
  return null;
}

function portCenterY(rect) {
  return rect.top + rect.height / 2;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}
