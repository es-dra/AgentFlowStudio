import { icon } from "./icons.js";
import { el } from "./overlay.js";

let spriteOpen = false;
let spriteSending = false;
let draftMessage = "";
let lastState = {};
let lastRuntime = {};
let spritePosition = null;
let suppressSpriteClick = false;
let spriteResizeBound = false;
const SPRITE_POSITION_KEY = "afs_studio_sprite_position";
const SPRITE_MARGIN = 18;
const SPRITE_SIZE = 156;
const SPRITE_HEIGHT = 176;
const spriteMessages = [
  { role: "sprite", text: "我在这里看着画布。可以问我下一步、素材确认或节点连线。" },
];

export function renderSpriteWidget(state, runtime) {
  const root = document.getElementById("sprite-root");
  if (!root) return;
  lastState = state || {};
  lastRuntime = runtime || {};
  bindSpriteViewportClamp();
  rememberSpritePositionFromRoot(root);
  applySpritePosition(root);
  root.replaceChildren(spriteShell(state, runtime));
}

function spriteShell(state, runtime) {
  const shell = el("section", `afs-sprite${spriteOpen ? " open" : ""}`);
  shell.setAttribute("aria-label", "AFS 小精灵");
  shell.appendChild(spriteOrb());
  if (spriteOpen) shell.appendChild(spritePanel(state, runtime));
  return shell;
}

function spriteOrb() {
  const button = el("button", "afs-sprite-orb afs-sprite-avatar");
  button.type = "button";
  button.setAttribute("aria-label", "AFS 小精灵");
  button.setAttribute("aria-pressed", spriteOpen ? "true" : "false");
  button.setAttribute("data-sprite-draggable", "true");
  button.title = spriteOpen ? "拖动移动，点击收起 AFS 小精灵" : "拖动移动，点击打开 AFS 小精灵";
  button.innerHTML = [
    '<span class="sprite-dock-ring"><i></i></span>',
    '<span class="sprite-drag-halo"></span>',
    '<span class="sprite-drag-chip" aria-hidden="true"><i></i><i></i><i></i></span>',
    '<span class="sprite-aura"></span>',
    '<span class="sprite-antenna"></span>',
    '<span class="sprite-wing left"></span>',
    '<span class="sprite-wing right"></span>',
    '<span class="sprite-tail-fin"></span>',
    '<span class="sprite-shoulder left"></span>',
    '<span class="sprite-shoulder right"></span>',
    '<span class="sprite-arm left"><span class="sprite-hand left"></span><span class="sprite-mitten left"></span></span>',
    '<span class="sprite-arm right"><span class="sprite-hand right"></span><span class="sprite-mitten right"></span></span>',
    '<span class="sprite-backplate"></span>',
    '<span class="sprite-body">',
    '  <span class="sprite-cockpit"></span>',
    '  <span class="sprite-canopy"></span>',
    '  <span class="sprite-head-shell"></span>',
    '  <span class="sprite-face">',
    '    <span class="sprite-cheek left"></span>',
    '    <span class="sprite-visor"><span class="sprite-eye-glow"></span><i></i><i></i><b></b></span>',
    '    <span class="sprite-cheek right"></span>',
    '    <span class="sprite-mouth"></span>',
    "  </span>",
    '  <span class="sprite-core"></span>',
    '  <span class="sprite-status-light"></span>',
    '  <span class="sprite-badge">AFS</span>',
    "</span>",
    '<span class="sprite-foot left"></span>',
    '<span class="sprite-foot right"></span>',
    '<span class="sprite-thruster"></span>',
    '<span class="sprite-glow-trail"></span>',
    '<span class="sprite-shadow"></span>',
    '<span class="sprite-label">AFS 小精灵</span>',
  ].join("");
  button.addEventListener("pointerdown", startSpriteDrag);
  button.addEventListener("click", () => {
    if (suppressSpriteClick) {
      suppressSpriteClick = false;
      return;
    }
    rememberSpritePositionFromRoot();
    spriteOpen = !spriteOpen;
    renderSpriteWidget(lastState, lastRuntime);
  });
  return button;
}

function spritePanel(state, runtime) {
  const panel = el("div", "afs-sprite-panel");
  const head = el("div", "afs-sprite-head");
  head.title = "拖动移动 AFS 小精灵";
  head.setAttribute("data-sprite-drag-handle", "true");
  head.innerHTML = [
    icon("sparkles", 14),
    "<span>",
    "<strong>AFS 小精灵</strong>",
    "<small>陪跑中</small>",
    "</span>",
    '<span class="afs-sprite-grip" aria-hidden="true"><i></i><i></i><i></i></span>',
  ].join("");
  head.addEventListener("pointerdown", startSpriteDrag);
  panel.appendChild(head);
  const log = el("div", "afs-sprite-log");
  for (const message of spriteMessages.slice(-5)) {
    const item = el("p", `afs-sprite-msg ${message.role}`, message.text);
    log.appendChild(item);
  }
  panel.appendChild(log);
  panel.appendChild(spriteForm(state, runtime));
  return panel;
}

function spriteForm(state, runtime) {
  const form = el("form", "afs-sprite-form");
  const input = document.createElement("input");
  input.type = "text";
  input.value = draftMessage;
  input.placeholder = "问问下一步怎么做...";
  input.maxLength = 180;
  input.addEventListener("input", () => {
    draftMessage = input.value;
  });
  const send = el("button", "afs-sprite-send");
  send.type = "submit";
  send.disabled = spriteSending;
  send.innerHTML = spriteSending ? "..." : icon("arrowUp", 13);
  form.append(input, send);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    submitSpriteMessage(state, runtime, input.value);
  });
  return form;
}

async function submitSpriteMessage(state, runtime, rawText) {
  const message = String(rawText || "").trim();
  if (!message || spriteSending) return;
  draftMessage = "";
  spriteMessages.push({ role: "user", text: message });
  spriteSending = true;
  renderSpriteWidget(state, runtime);
  try {
    const response = await runtime.spriteChat({
      message,
      node_id: selectedNodeId(state),
      canvas_summary: canvasSummary(state),
      generated_at: new Date().toISOString(),
    });
    spriteMessages.push({ role: "sprite", text: safeReply(response?.reply) });
  } catch {
    spriteMessages.push({ role: "sprite", text: "我暂时连不上工作台服务。你仍可以先检查当前节点的参考图和已确认素材。" });
  } finally {
    spriteSending = false;
    renderSpriteWidget(state, runtime);
  }
}

function selectedNodeId(state) {
  return String(state?.selection?.nodeIds?.[0] || "");
}

function canvasSummary(state) {
  const nodeId = selectedNodeId(state);
  const node = nodeId ? state.nodes?.[nodeId] : null;
  return {
    nodes: Array.isArray(state?.order) ? state.order.length : 0,
    assets: Array.isArray(state?.assets) ? state.assets.length : 0,
    edges: Object.keys(state?.edges || {}).length,
    selected_node_type: node?.type || "",
    selected_node_status: node?.status || "",
  };
}

function safeReply(value) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.slice(0, 220) || "我先在这里陪跑。可以从当前节点的下一步动作开始。";
}

function startSpriteDrag(event) {
  if (event.button !== undefined && event.button !== 0) return;
  const root = document.getElementById("sprite-root");
  if (!root) return;
  const startPoint = { x: event.clientX, y: event.clientY };
  const startPosition = spritePosition || readSpritePosition() || defaultSpritePosition();
  let moved = false;
  event.preventDefault();
  event.currentTarget.setPointerCapture?.(event.pointerId);
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
      suppressSpriteClick = true;
      window.setTimeout(() => {
        suppressSpriteClick = false;
      }, 260);
      storeSpritePosition(spritePosition);
    }
  };
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onEnd, { once: true });
  window.addEventListener("pointercancel", onEnd, { once: true });
}

function bindSpriteViewportClamp() {
  if (spriteResizeBound) return;
  spriteResizeBound = true;
  window.addEventListener("resize", () => {
    if (!spritePosition) return;
    setSpritePosition(spritePosition);
    storeSpritePosition(spritePosition);
  });
}

function applySpritePosition(root) {
  setSpritePosition(spritePosition || readSpritePosition() || defaultSpritePosition(), root);
}

function rememberSpritePositionFromRoot(root = document.getElementById("sprite-root")) {
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

function storeSpritePosition(position) {
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

function clampSpritePosition(position) {
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
