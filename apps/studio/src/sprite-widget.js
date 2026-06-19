import { icon } from "./icons.js";
import { el } from "./overlay.js";
import {
  applySpritePosition,
  bindSpriteViewportClamp,
  getSpriteScale,
  nudgeSpritePosition,
  rememberSpritePositionFromRoot,
  setSpriteScale,
  startSpriteDrag,
  SPRITE_SCALE_OPTIONS,
} from "./sprite-position.js";

let spriteOpen = false;
let spriteSettingsOpen = false;
let spriteSending = false;
let draftMessage = "";
let lastState = {};
let lastRuntime = {};
let suppressSpriteClick = false;
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
  if (spriteSettingsOpen) shell.appendChild(spriteSettingsPanel());
  return shell;
}

function spriteOrb() {
  const button = el("button", "afs-sprite-orb afs-sprite-avatar");
  button.type = "button";
  button.setAttribute("aria-label", "AFS 小精灵");
  button.setAttribute("aria-pressed", spriteOpen ? "true" : "false");
  button.setAttribute("data-sprite-draggable", "true");
  button.setAttribute("data-sprite-role", "movable-companion");
  button.setAttribute("data-sprite-character", "mascot");
  button.title = spriteOpen ? "拖动或方向键移动，右键设置，点击收起 AFS 小精灵" : "拖动或方向键移动，右键设置，点击打开 AFS 小精灵";
  button.innerHTML = [
    '<span class="sprite-mascot-shell" aria-hidden="true"></span>',
    '<span class="sprite-mascot-ear left" aria-hidden="true"></span>',
    '<span class="sprite-mascot-ear right" aria-hidden="true"></span>',
    '<span class="sprite-mascot-face" aria-hidden="true">',
    '  <span class="sprite-mascot-eye left"></span>',
    '  <span class="sprite-mascot-eye right"></span>',
    '  <span class="sprite-mascot-smile"></span>',
    "</span>",
    '<span class="sprite-mascot-hand left" aria-hidden="true"></span>',
    '<span class="sprite-mascot-hand right" aria-hidden="true"></span>',
    '<span class="sprite-mascot-star" aria-hidden="true"></span>',
    '<span class="sprite-mascot-tag" aria-hidden="true">AFS</span>',
    '<span class="sprite-mascot-shadow" aria-hidden="true"></span>',
    '<span class="sprite-dock-ring"><i></i></span>',
    '<span class="sprite-drag-halo"></span>',
    '<span class="sprite-orbit-dot left" aria-hidden="true"></span>',
    '<span class="sprite-orbit-dot right" aria-hidden="true"></span>',
    '<span class="sprite-navigator-shell" aria-hidden="true"></span>',
    '<span class="sprite-halo-crown" aria-hidden="true"><i></i><i></i><i></i></span>',
    '<span class="sprite-crest" aria-hidden="true"></span>',
    '<span class="sprite-character-shell"></span>',
    '<span class="sprite-hood"></span>',
    '<span class="sprite-helmet-glass"></span>',
    '<span class="sprite-helmet-reflection" aria-hidden="true"></span>',
    '<span class="sprite-move-handle" data-sprite-drag-handle="true" aria-hidden="true"><i></i><i></i><i></i><b></b></span>',
    '<span class="sprite-drag-chip" aria-hidden="true"><i></i><i></i><i></i></span>',
    '<span class="sprite-aura"></span>',
    '<span class="sprite-antenna"></span>',
    '<span class="sprite-ear left"></span>',
    '<span class="sprite-ear right"></span>',
    '<span class="sprite-wing left"></span>',
    '<span class="sprite-wing right"></span>',
    '<span class="sprite-tail-fin"></span>',
    '<span class="sprite-shoulder left"></span>',
    '<span class="sprite-shoulder right"></span>',
    '<span class="sprite-arm left"><span class="sprite-hand left"></span><span class="sprite-mitten left"></span></span>',
    '<span class="sprite-arm right"><span class="sprite-hand right"></span><span class="sprite-mitten right"></span></span>',
    '<span class="sprite-hand-wave" aria-hidden="true"></span>',
    '<span class="sprite-jet-pack" aria-hidden="true"></span>',
    '<span class="sprite-backplate"></span>',
    '<span class="sprite-body">',
    '  <span class="sprite-cockpit"></span>',
    '  <span class="sprite-canopy"></span>',
    '  <span class="sprite-head-shell"></span>',
    '  <span class="sprite-face-window"></span>',
    '  <span class="sprite-face">',
    '    <span class="sprite-brow left"></span>',
    '    <span class="sprite-brow right"></span>',
    '    <span class="sprite-cheek left"></span>',
    '    <span class="sprite-visor"><span class="sprite-eye-glow"></span><i class="sprite-eye left"></i><i class="sprite-eye right"></i><b></b></span>',
    '    <span class="sprite-cheek right"></span>',
    '    <span class="sprite-blush left"></span>',
    '    <span class="sprite-blush right"></span>',
    '    <span class="sprite-mouth"></span>',
    '    <span class="sprite-face-smile"></span>',
    "  </span>",
    '  <span class="sprite-core"></span>',
    '  <span class="sprite-torso-panel"><i></i><i></i></span>',
    '  <span class="sprite-status-light"></span>',
    '  <span class="sprite-badge">AFS</span>',
    "</span>",
    '<span class="sprite-wand" aria-hidden="true"></span>',
    '<span class="sprite-nameplate" aria-hidden="true"><i></i><i></i><b></b></span>',
    '<span class="sprite-personality-tag" aria-hidden="true">星导</span>',
    '<span class="sprite-grab-ribbon" aria-hidden="true">按住移动</span>',
    '<span class="sprite-scarf"></span>',
    '<span class="sprite-foot left"></span>',
    '<span class="sprite-foot right"></span>',
    '<span class="sprite-thruster"></span>',
    '<span class="sprite-glow-trail"></span>',
    '<span class="sprite-hover-pad" aria-hidden="true"></span>',
    '<span class="sprite-shadow"></span>',
    '<span class="sprite-label">AFS 小精灵</span>',
  ].join("");
  button.addEventListener("pointerdown", handleSpriteDrag);
  button.addEventListener("keydown", nudgeSpritePosition);
  button.addEventListener("contextmenu", (event) => {
    event.preventDefault();
    rememberSpritePositionFromRoot();
    spriteSettingsOpen = true;
    spriteOpen = false;
    renderSpriteWidget(lastState, lastRuntime);
  });
  button.addEventListener("click", () => {
    if (suppressSpriteClick) {
      suppressSpriteClick = false;
      return;
    }
    rememberSpritePositionFromRoot();
    spriteSettingsOpen = false;
    spriteOpen = !spriteOpen;
    renderSpriteWidget(lastState, lastRuntime);
  });
  return button;
}

function handleSpriteDrag(event) {
  startSpriteDrag(event, () => {
    suppressSpriteClick = true;
    window.setTimeout(() => {
      suppressSpriteClick = false;
    }, 260);
  });
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
  head.addEventListener("pointerdown", handleSpriteDrag);
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

function spriteSettingsPanel() {
  const panel = el("div", "afs-sprite-settings");
  panel.setAttribute("data-sprite-settings", "true");
  panel.innerHTML = "<h3>小精灵设置</h3><p>调整陪跑角色大小。位置可以直接拖动保存。</p>";
  const grid = el("div", "afs-sprite-size-grid");
  const current = getSpriteScale().id;
  for (const option of SPRITE_SCALE_OPTIONS) {
    const button = el("button", `afs-sprite-size-button${option.id === current ? " active" : ""}`, option.label);
    button.type = "button";
    button.addEventListener("click", () => {
      setSpriteScale(option.id);
      renderSpriteWidget(lastState, lastRuntime);
    });
    grid.appendChild(button);
  }
  panel.appendChild(grid);
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
