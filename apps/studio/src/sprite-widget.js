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
import {
  applySpritePose,
  bindSpritePoseTicker,
  currentSpritePose,
  setSpritePose,
  setTemporarySpritePose,
  spriteStoryLayers,
} from "./sprite-character.js";
import {
  bindSpriteMotion,
  pulseSpriteMotion,
  setSpriteMotionMode,
} from "./sprite-motion.js";

let spriteOpen = false;
let spriteSettingsOpen = false;
let spriteSending = false;
let draftMessage = "";
let lastState = {};
let lastRuntime = {};
let suppressSpriteClick = false;
const spriteMessages = [
  { role: "sprite", text: "我先观察画布。需要时，我会给出下一步建议。" },
];

export function renderSpriteWidget(state, runtime) {
  const root = document.getElementById("sprite-root");
  if (!root) return;
  lastState = state || {};
  lastRuntime = runtime || {};
  bindSpritePoseTicker(spriteState, () => applySpritePose(document.getElementById("sprite-root"), spriteState()));
  bindSpriteMotion(root);
  bindSpriteViewportClamp();
  rememberSpritePositionFromRoot(root);
  applySpritePosition(root);
  root.replaceChildren(spriteShell(state, runtime));
  applySpritePose(root, spriteState());
  setSpriteMotionMode(spriteMotionMode(), root);
}

function spriteShell(state, runtime) {
  const shell = el("section", `afs-sprite${spriteOpen ? " open" : ""}`);
  shell.setAttribute("aria-label", "团团画布 Agent");
  shell.appendChild(spriteOrb());
  if (spriteOpen) shell.appendChild(spritePanel(state, runtime));
  if (spriteSettingsOpen) shell.appendChild(spriteSettingsPanel());
  return shell;
}

function spriteOrb() {
  const button = el("button", "afs-sprite-orb afs-sprite-avatar");
  button.type = "button";
  button.setAttribute("aria-label", "团团，AFS 画布 Agent");
  button.setAttribute("aria-pressed", spriteOpen ? "true" : "false");
  button.setAttribute("data-sprite-draggable", "true");
  button.setAttribute("data-sprite-role", "embodied-agent");
  button.setAttribute("data-sprite-character", "story-cat");
  button.setAttribute("data-sprite-state", currentSpritePose(spriteState()));
  button.title = spriteOpen ? "拖动或方向键移动，右键设置，点击收起团团" : "拖动或方向键移动，右键设置，点击查看团团的观察";
  button.innerHTML = [
    '<span class="sprite-tuantuan-stage" aria-hidden="true">',
    ...spriteStoryLayers(),
    "</span>",
    '<span class="sprite-drag-halo"></span>',
    '<span class="sprite-move-handle" data-sprite-drag-handle="true" aria-hidden="true"><i></i><i></i><i></i><b></b></span>',
    '<span class="sprite-agent-sequence" aria-hidden="true">观察 · 提案 · 执行</span>',
    '<span class="sprite-label">团团</span>',
  ].join("");
  button.addEventListener("pointerdown", handleSpriteDrag);
  button.addEventListener("pointerenter", () => {
    if (!spriteOpen && !spriteSettingsOpen && !spriteSending) {
      setSpritePose(button, "think");
      setSpriteMotionMode("hover");
    }
  });
  button.addEventListener("pointerleave", () => {
    if (!spriteOpen && !spriteSettingsOpen && !spriteSending) {
      setSpritePose(button, currentSpritePose(spriteState()));
      setSpriteMotionMode(spriteMotionMode());
    }
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

function handleSpriteDrag(event) {
  setSpritePose(event.currentTarget, "observe");
  setSpriteMotionMode("drag");
  startSpriteDrag(event, () => {
    suppressSpriteClick = true;
    window.setTimeout(() => {
      suppressSpriteClick = false;
    }, 260);
  }, () => {
    applySpritePose(document.getElementById("sprite-root"), spriteState());
    setSpriteMotionMode(spriteMotionMode());
  });
}

function spriteState() {
  return {
    open: spriteOpen,
    settingsOpen: spriteSettingsOpen,
    sending: spriteSending,
  };
}

function spriteMotionMode() {
  if (spriteSending) return "think";
  if (spriteSettingsOpen) return "think";
  if (spriteOpen) return "suggest";
  return "observe";
}

function spritePanel(state, runtime) {
  const panel = el("div", "afs-sprite-panel");
  const head = el("div", "afs-sprite-head");
  head.title = "拖动移动团团";
  head.setAttribute("data-sprite-drag-handle", "true");
  head.innerHTML = [
    icon("sparkles", 14),
    "<span>",
    "<strong>团团</strong>",
    "<small>观察 · 提案 · 执行</small>",
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
  panel.innerHTML = "<h3>团团设置</h3><p>调整画布 Agent 的尺寸。团团会保持低干扰，位置可以直接拖动保存。</p>";
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
  input.placeholder = "把想法放这里，团团先观察上下文...";
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
    pulseSpriteMotion("success");
    setTemporarySpritePose("suggest", 1500, () => renderSpriteWidget(lastState, lastRuntime));
  } catch {
    spriteMessages.push({ role: "sprite", text: "我暂时连不上工作台服务。可以先继续整理画布，我会保持观察。" });
    pulseSpriteMotion("error");
    setTemporarySpritePose("observe", 1800, () => renderSpriteWidget(lastState, lastRuntime));
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
  return text.slice(0, 220) || "我先观察当前画布，再给出一个不打断创作的建议。";
}
