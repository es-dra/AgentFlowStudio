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
let spritePoseTickerBound = false;
let spriteIdlePoseIndex = 0;
let temporarySpritePose = "";
let temporarySpritePoseTimer = 0;
const SPRITE_POSE_ASSETS = {
  idle: "./assets/tuantuan-idle.png",
  happy: "./assets/tuantuan-happy.png",
  curious: "./assets/tuantuan-curious.png",
  thinking: "./assets/tuantuan-thinking.png",
  surprised: "./assets/tuantuan-surprised.png",
  sleepy: "./assets/tuantuan-sleepy.png",
  working: "./assets/tuantuan-working.png",
  celebrate: "./assets/tuantuan-celebrate.png",
};
const IDLE_SPRITE_POSES = ["idle", "curious", "happy", "sleepy"];
const spriteMessages = [
  { role: "sprite", text: "我在这里看着画布。可以问我下一步、素材确认或节点连线。" },
];

export function renderSpriteWidget(state, runtime) {
  const root = document.getElementById("sprite-root");
  if (!root) return;
  lastState = state || {};
  lastRuntime = runtime || {};
  bindSpritePoseTicker();
  bindSpriteViewportClamp();
  rememberSpritePositionFromRoot(root);
  applySpritePosition(root);
  root.replaceChildren(spriteShell(state, runtime));
  applySpritePose(root);
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
  button.setAttribute("data-sprite-pose", currentSpritePose());
  button.title = spriteOpen ? "拖动或方向键移动，右键设置，点击收起 AFS 小精灵" : "拖动或方向键移动，右键设置，点击打开 AFS 小精灵";
  button.innerHTML = [
    '<span class="sprite-tuantuan-stage" aria-hidden="true">',
    ...spritePoseImages(),
    "</span>",
    '<span class="sprite-mascot-shadow" aria-hidden="true"></span>',
    '<span class="sprite-drag-halo"></span>',
    '<span class="sprite-move-handle" data-sprite-drag-handle="true" aria-hidden="true"><i></i><i></i><i></i><b></b></span>',
    '<span class="sprite-grab-ribbon" aria-hidden="true">按住移动</span>',
    '<span class="sprite-mascot-tag" aria-hidden="true">团团</span>',
    '<span class="sprite-label">AFS 小精灵</span>',
  ].join("");
  button.addEventListener("pointerdown", handleSpriteDrag);
  button.addEventListener("pointerenter", () => {
    if (!spriteOpen && !spriteSettingsOpen && !spriteSending) setSpritePose(button, "happy");
  });
  button.addEventListener("pointerleave", () => {
    if (!spriteOpen && !spriteSettingsOpen && !spriteSending) setSpritePose(button);
  });
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

function spritePoseImages() {
  return Object.entries(SPRITE_POSE_ASSETS).map(([pose, src]) => (
    `  <img class="sprite-tuantuan-asset" data-pose="${pose}" src="${src}" alt="" draggable="false" />`
  ));
}

function handleSpriteDrag(event) {
  setSpritePose(event.currentTarget, "happy");
  startSpriteDrag(event, () => {
    suppressSpriteClick = true;
    window.setTimeout(() => {
      suppressSpriteClick = false;
    }, 260);
  }, () => {
    applySpritePose();
  });
}

function currentSpritePose() {
  if (temporarySpritePose) return temporarySpritePose;
  if (spriteSending) return "working";
  if (spriteSettingsOpen) return "thinking";
  if (spriteOpen) return "curious";
  return IDLE_SPRITE_POSES[spriteIdlePoseIndex] || "idle";
}

function setSpritePose(button = document.querySelector(".afs-sprite-avatar"), pose = currentSpritePose()) {
  if (!button) return;
  button.dataset.spritePose = SPRITE_POSE_ASSETS[pose] ? pose : "idle";
}

function applySpritePose(root = document.getElementById("sprite-root")) {
  setSpritePose(root?.querySelector(".afs-sprite-avatar"));
}

function bindSpritePoseTicker() {
  if (spritePoseTickerBound || typeof window === "undefined") return;
  spritePoseTickerBound = true;
  window.setInterval(() => {
    if (spriteOpen || spriteSettingsOpen || spriteSending || temporarySpritePose) return;
    const root = document.getElementById("sprite-root");
    if (root?.classList.contains("is-dragging")) return;
    spriteIdlePoseIndex = (spriteIdlePoseIndex + 1) % IDLE_SPRITE_POSES.length;
    applySpritePose(root);
  }, 7200);
}

function setTemporarySpritePose(pose, duration = 1500) {
  if (!SPRITE_POSE_ASSETS[pose] || typeof window === "undefined") return;
  temporarySpritePose = pose;
  window.clearTimeout(temporarySpritePoseTimer);
  temporarySpritePoseTimer = window.setTimeout(() => {
    temporarySpritePose = "";
    renderSpriteWidget(lastState, lastRuntime);
  }, duration);
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
    setTemporarySpritePose("celebrate");
  } catch {
    spriteMessages.push({ role: "sprite", text: "我暂时连不上工作台服务。你仍可以先检查当前节点的参考图和已确认素材。" });
    setTemporarySpritePose("surprised", 1800);
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
