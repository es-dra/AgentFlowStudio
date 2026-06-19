let spritePosition = null;
let spriteResizeBound = false;

export const SPRITE_POSITION_KEY = "afs_studio_sprite_position";
export const SPRITE_SIZE = 156;
const SPRITE_MARGIN = 18;
const SPRITE_HEIGHT = 176;

export function startSpriteDrag(event, onMoved) {
  if (event.button !== undefined && event.button !== 0) return;
  const root = document.getElementById("sprite-root");
  if (!root) return;
  const startPoint = { x: event.clientX, y: event.clientY };
  const startPosition = spritePosition || readSpritePosition() || defaultSpritePosition();
  let moved = false;
  event.preventDefault();
  captureSpritePointer(event);
  root.classList.add("is-dragging");
  const onMove = (moveEvent) => {
    const dx = moveEvent.clientX - startPoint.x;
    const dy = moveEvent.clientY - startPoint.y;
    if (Math.abs(dx) + Math.abs(dy) > 4) moved = true;
    setSpritePosition({ x: startPosition.x + dx, y: startPosition.y + dy });
  };
  const onEnd = () => {
    root.classList.remove("is-dragging");
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onEnd);
    window.removeEventListener("pointercancel", onEnd);
    if (moved) {
      onMoved?.();
      storeSpritePosition(spritePosition);
    }
  };
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onEnd, { once: true });
  window.addEventListener("pointercancel", onEnd, { once: true });
}

function captureSpritePointer(event) {
  try {
    event.currentTarget?.setPointerCapture?.(event.pointerId);
  } catch {
    // Synthetic pointer events in browser automation may not own the pointer.
  }
}

export function nudgeSpritePosition(event) {
  const directions = {
    ArrowLeft: { x: -1, y: 0 },
    ArrowRight: { x: 1, y: 0 },
    ArrowUp: { x: 0, y: -1 },
    ArrowDown: { x: 0, y: 1 },
  };
  const direction = directions[event.key];
  if (!direction) return;
  const step = event.shiftKey ? 42 : 18;
  const current = spritePosition || readSpritePosition() || defaultSpritePosition();
  event.preventDefault();
  setSpritePosition({
    x: current.x + direction.x * step,
    y: current.y + direction.y * step,
  });
  storeSpritePosition(spritePosition);
}

export function bindSpriteViewportClamp() {
  if (spriteResizeBound) return;
  spriteResizeBound = true;
  window.addEventListener("resize", () => {
    if (!spritePosition) return;
    setSpritePosition(spritePosition);
    storeSpritePosition(spritePosition);
  });
}

export function applySpritePosition(root) {
  setSpritePosition(spritePosition || readSpritePosition() || defaultSpritePosition(), root);
}

export function rememberSpritePositionFromRoot(root = document.getElementById("sprite-root")) {
  if (!root?.firstElementChild) return;
  const rect = root.getBoundingClientRect();
  if (!Number.isFinite(rect?.left) || !Number.isFinite(rect?.top)) return;
  spritePosition = clampSpritePosition({ x: rect.left, y: rect.top });
}

function setSpritePosition(position, root = document.getElementById("sprite-root")) {
  if (!root) return;
  spritePosition = clampSpritePosition(position);
  root.style.setProperty("--sprite-x", `${spritePosition.x}px`);
  root.style.setProperty("--sprite-y", `${spritePosition.y}px`);
  root.dataset.dock = spritePosition.x < window.innerWidth / 2 ? "left" : "right";
  root.dataset.vertical = spritePosition.y < window.innerHeight / 2 ? "top" : "bottom";
}

function readSpritePosition() {
  try {
    const value = JSON.parse(window.localStorage?.getItem(SPRITE_POSITION_KEY) || "null");
    if (Number.isFinite(value?.x) && Number.isFinite(value?.y)) return value;
  } catch {
    return null;
  }
  return null;
}

export function storeSpritePosition(position) {
  if (!position) return;
  try {
    window.localStorage?.setItem(SPRITE_POSITION_KEY, JSON.stringify(clampSpritePosition(position)));
  } catch {
    // Storage can be blocked; the current session position still remains live.
  }
}

function defaultSpritePosition() {
  return {
    x: Math.max(SPRITE_MARGIN, window.innerWidth - SPRITE_SIZE - 24),
    y: Math.max(76, window.innerHeight - SPRITE_HEIGHT - 48),
  };
}

export function clampSpritePosition(position) {
  const maxX = Math.max(SPRITE_MARGIN, window.innerWidth - SPRITE_SIZE - 10);
  const maxY = Math.max(76, window.innerHeight - SPRITE_HEIGHT - 10);
  const rawX = Number(position?.x);
  const rawY = Number(position?.y);
  const nextX = Number.isFinite(rawX) ? rawX : maxX;
  const nextY = Number.isFinite(rawY) ? rawY : maxY;
  return {
    x: Math.max(SPRITE_MARGIN, Math.min(maxX, Math.round(nextX))),
    y: Math.max(76, Math.min(maxY, Math.round(nextY))),
  };
}
