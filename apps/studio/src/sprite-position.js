let spritePosition = null;
let spriteResizeBound = false;

export const SPRITE_POSITION_KEY = "afs_studio_sprite_position";
export const SPRITE_POSITION_VERSION = "2026-06-tuantuan-raster-v1";
export const SPRITE_SCALE_KEY = "afs_studio_sprite_scale";
export const SPRITE_SCALE_OPTIONS = [
  { id: "small", label: "小", value: 0.82 },
  { id: "normal", label: "中", value: 1 },
  { id: "large", label: "大", value: 1.18 },
];
export const SPRITE_SIZE = 190;
const SPRITE_MARGIN = 18;
const SPRITE_HEIGHT = 238;

export function startSpriteDrag(event, onMoved, onEnded) {
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
    onEnded?.();
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
  applySpriteScale(root);
  setSpritePosition(spritePosition || readSpritePosition() || defaultSpritePosition(), root);
}

export function getSpriteScale() {
  try {
    const value = window.localStorage?.getItem(SPRITE_SCALE_KEY);
    return SPRITE_SCALE_OPTIONS.find((item) => item.id === value) || SPRITE_SCALE_OPTIONS[1];
  } catch {
    return SPRITE_SCALE_OPTIONS[1];
  }
}

export function setSpriteScale(scaleId, root = document.getElementById("sprite-root")) {
  const option = SPRITE_SCALE_OPTIONS.find((item) => item.id === scaleId) || SPRITE_SCALE_OPTIONS[1];
  try {
    window.localStorage?.setItem(SPRITE_SCALE_KEY, option.id);
  } catch {
    // Local UI preference only; blocked storage should not break the companion.
  }
  applySpriteScale(root);
  setSpritePosition(spritePosition || readSpritePosition() || defaultSpritePosition(), root);
  storeSpritePosition(spritePosition);
  return option;
}

function applySpriteScale(root = document.getElementById("sprite-root")) {
  if (!root) return;
  root.style.setProperty("--sprite-scale", String(getSpriteScale().value));
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
    if (value?.version === SPRITE_POSITION_VERSION && Number.isFinite(value?.x) && Number.isFinite(value?.y)) return value;
  } catch {
    return null;
  }
  return null;
}

export function storeSpritePosition(position) {
  if (!position) return;
  try {
    window.localStorage?.setItem(SPRITE_POSITION_KEY, JSON.stringify({
      version: SPRITE_POSITION_VERSION,
      ...clampSpritePosition(position),
    }));
  } catch {
    // Storage can be blocked; the current session position still remains live.
  }
}

function defaultSpritePosition() {
  return safeDefaultSpritePosition();
}

export function safeDefaultSpritePosition() {
  const inspectorRect = visibleOverlayRect("inspector");
  const dockRect = visibleOverlayRect("dock");
  const rightSafeX = inspectorRect
    ? inspectorRect.left - scaledSpriteWidth() - 24
    : window.innerWidth - scaledSpriteWidth() - 24;
  const bottomSafeY = dockRect
    ? dockRect.top - scaledSpriteHeight() - 22
    : window.innerHeight - scaledSpriteHeight() - 48;
  return {
    x: Math.max(SPRITE_MARGIN, Math.round(rightSafeX)),
    y: Math.max(76, Math.round(bottomSafeY)),
  };
}

function visibleOverlayRect(id) {
  const element = document.getElementById(id);
  if (!element) return null;
  const rect = element.getBoundingClientRect();
  if (rect.width < 80 || rect.height < 32) return null;
  const isVisible = rect.right > 0
    && rect.bottom > 0
    && rect.left < window.innerWidth
    && rect.top < window.innerHeight;
  return isVisible ? rect : null;
}

export function clampSpritePosition(position) {
  const maxX = Math.max(SPRITE_MARGIN, window.innerWidth - scaledSpriteWidth() - 10);
  const maxY = Math.max(76, window.innerHeight - scaledSpriteHeight() - 10);
  const rawX = Number(position?.x);
  const rawY = Number(position?.y);
  const nextX = Number.isFinite(rawX) ? rawX : maxX;
  const nextY = Number.isFinite(rawY) ? rawY : maxY;
  return {
    x: Math.max(SPRITE_MARGIN, Math.min(maxX, Math.round(nextX))),
    y: Math.max(76, Math.min(maxY, Math.round(nextY))),
  };
}

function scaledSpriteWidth() {
  return SPRITE_SIZE * getSpriteScale().value;
}

function scaledSpriteHeight() {
  return SPRITE_HEIGHT * getSpriteScale().value;
}
