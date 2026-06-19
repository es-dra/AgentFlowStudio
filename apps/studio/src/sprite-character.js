export const SPRITE_AGENT_STATES = {
  observe: "观察",
  think: "思考",
  suggest: "提案",
  preview: "预览",
  execute: "执行",
  complete: "完成",
  sleep: "休息",
};

// TuanTuan visualizes the AFS Agent sequence: Observe → Suggest → Execute.
const IDLE_AGENT_STATES = ["observe", "observe", "think", "observe", "sleep"];
let spriteTickerBound = false;
let idleStateIndex = 0;
let temporaryState = "";
let temporaryStateTimer = 0;

export function spriteStoryLayers() {
  return [
    '<span class="sprite-story-orbit" aria-hidden="true">',
    '  <i data-orbit-node="observe"></i>',
    '  <i data-orbit-node="suggest"></i>',
    '  <i data-orbit-node="preview"></i>',
    '  <i data-orbit-node="execute"></i>',
    '  <i data-orbit-node="complete"></i>',
    "</span>",
    '<span class="sprite-preview-ghost" aria-hidden="true"></span>',
    '<span class="sprite-suggestion-bubble" aria-hidden="true"><i></i><b></b><i></i></span>',
    '<span class="sprite-complete-sparks" aria-hidden="true"><i></i><i></i><i></i></span>',
    '<span class="sprite-sleep-mark" aria-hidden="true">zZ</span>',
    '<span class="sprite-tuantuan-cat" aria-hidden="true">',
    '  <span class="sprite-cat-tail"><i class="sprite-tail-panel one"></i><i class="sprite-tail-panel two"></i><i class="sprite-tail-panel three"></i></span>',
    '  <span class="sprite-cat-body"><i></i><i></i><i></i><span class="sprite-cat-story-panel"><i></i><b></b></span></span>',
    '  <span class="sprite-cat-head">',
    '    <span class="sprite-cat-ear left"><span class="sprite-cat-inner-ear"></span></span>',
    '    <span class="sprite-cat-ear right"><span class="sprite-cat-inner-ear"></span></span>',
    '    <span class="sprite-cat-sprout"><i></i><i></i></span>',
    '    <span class="sprite-cat-face-mark forehead"></span>',
    '    <span class="sprite-cat-face-mark cheek left"></span>',
    '    <span class="sprite-cat-face-mark cheek right"></span>',
    '    <span class="sprite-cat-eye left"></span>',
    '    <span class="sprite-cat-eye right"></span>',
    '    <span class="sprite-cat-nose"></span>',
    '    <span class="sprite-cat-muzzle"></span>',
    '    <span class="sprite-cat-mouth"></span>',
    '    <span class="sprite-cat-whiskers left"><i></i><i></i></span>',
    '    <span class="sprite-cat-whiskers right"><i></i><i></i></span>',
    "  </span>",
    '  <span class="sprite-cat-paw left"></span>',
    '  <span class="sprite-cat-paw right"></span>',
    "</span>",
    '<span class="sprite-tuantuan-shadow" aria-hidden="true"></span>',
  ];
}

export function currentSpritePose(state = {}) {
  return currentSpriteState(state);
}

export function currentSpriteState(state = {}) {
  if (temporaryState) return temporaryState;
  if (state.sending) return "think";
  if (state.settingsOpen) return "think";
  if (state.open) return "suggest";
  return IDLE_AGENT_STATES[idleStateIndex] || "observe";
}

export function setSpritePose(button = document.querySelector(".afs-sprite-avatar"), state = currentSpriteState()) {
  if (!button) return;
  const nextState = SPRITE_AGENT_STATES[state] ? state : "observe";
  button.dataset.spriteState = nextState;
  button.dataset.spritePose = nextState;
}

export function applySpritePose(root = document.getElementById("sprite-root"), state = {}) {
  setSpritePose(root?.querySelector(".afs-sprite-avatar"), currentSpriteState(state));
}

export function bindSpritePoseTicker(getState, onTick) {
  if (spriteTickerBound || typeof window === "undefined") return;
  spriteTickerBound = true;
  window.setInterval(() => {
    const state = getState?.() || {};
    if (state.open || state.settingsOpen || state.sending || temporaryState) return;
    const root = document.getElementById("sprite-root");
    if (root?.classList.contains("is-dragging")) return;
    idleStateIndex = (idleStateIndex + 1) % IDLE_AGENT_STATES.length;
    onTick?.();
  }, 9000);
}

export function setTemporarySpritePose(state, duration = 1500, onExpire) {
  if (!SPRITE_AGENT_STATES[state] || typeof window === "undefined") return;
  temporaryState = state;
  window.clearTimeout(temporaryStateTimer);
  temporaryStateTimer = window.setTimeout(() => {
    temporaryState = "";
    onExpire?.();
  }, duration);
}
