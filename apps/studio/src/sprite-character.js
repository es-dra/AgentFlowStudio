export const SPRITE_POSE_ASSETS = {
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
let spritePoseTickerBound = false;
let spriteIdlePoseIndex = 0;
let temporarySpritePose = "";
let temporarySpritePoseTimer = 0;

export function spritePoseImages() {
  return Object.entries(SPRITE_POSE_ASSETS).map(([pose, src]) => (
    `  <img class="sprite-tuantuan-asset" data-pose="${pose}" src="${src}" alt="" draggable="false" />`
  ));
}

export function currentSpritePose(state = {}) {
  if (temporarySpritePose) return temporarySpritePose;
  if (state.sending) return "working";
  if (state.settingsOpen) return "thinking";
  if (state.open) return "curious";
  return IDLE_SPRITE_POSES[spriteIdlePoseIndex] || "idle";
}

export function setSpritePose(button = document.querySelector(".afs-sprite-avatar"), pose = currentSpritePose()) {
  if (!button) return;
  button.dataset.spritePose = SPRITE_POSE_ASSETS[pose] ? pose : "idle";
}

export function applySpritePose(root = document.getElementById("sprite-root"), state = {}) {
  setSpritePose(root?.querySelector(".afs-sprite-avatar"), currentSpritePose(state));
}

export function bindSpritePoseTicker(getState, onTick) {
  if (spritePoseTickerBound || typeof window === "undefined") return;
  spritePoseTickerBound = true;
  window.setInterval(() => {
    const state = getState?.() || {};
    if (state.open || state.settingsOpen || state.sending || temporarySpritePose) return;
    const root = document.getElementById("sprite-root");
    if (root?.classList.contains("is-dragging")) return;
    spriteIdlePoseIndex = (spriteIdlePoseIndex + 1) % IDLE_SPRITE_POSES.length;
    onTick?.();
  }, 7200);
}

export function setTemporarySpritePose(pose, duration = 1500, onExpire) {
  if (!SPRITE_POSE_ASSETS[pose] || typeof window === "undefined") return;
  temporarySpritePose = pose;
  window.clearTimeout(temporarySpritePoseTimer);
  temporarySpritePoseTimer = window.setTimeout(() => {
    temporarySpritePose = "";
    onExpire?.();
  }, duration);
}
