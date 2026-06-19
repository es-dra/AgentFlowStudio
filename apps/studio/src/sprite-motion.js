let motionBound = false;
let pointer = null;
let mode = "observe";
const motion = {
  lookX: 0,
  lookY: 0,
  lift: 0,
  tilt: 0,
  bob: 0,
  squashX: 1,
  squashY: 1,
};

export function bindSpriteMotion(root = document.getElementById("sprite-root")) {
  if (motionBound || typeof window === "undefined") return;
  motionBound = true;
  seedMotionVars(root);
  window.addEventListener("pointermove", (event) => {
    pointer = { x: event.clientX, y: event.clientY, at: performance.now() };
  }, { passive: true });
  window.addEventListener("pointerleave", () => {
    pointer = null;
  });
  window.requestAnimationFrame(tickSpriteMotion);
}

export function setSpriteMotionMode(nextMode = "observe", root = document.getElementById("sprite-root")) {
  mode = nextMode || "observe";
  if (root) root.dataset.spriteMotion = mode;
}

export function pulseSpriteMotion(kind = "success") {
  mode = kind === "error" ? "error" : "success";
  const root = document.getElementById("sprite-root");
  if (root) root.dataset.spriteMotion = mode;
  window.setTimeout(() => {
    const current = document.getElementById("sprite-root");
    if (mode === "success" || mode === "error") setSpriteMotionMode("observe", current);
  }, 1300);
}

function tickSpriteMotion(now) {
  const root = document.getElementById("sprite-root");
  if (root) {
    const target = targetMotion(root, now);
    motion.lookX = spring(motion.lookX, target.lookX, 0.11);
    motion.lookY = spring(motion.lookY, target.lookY, 0.11);
    motion.lift = spring(motion.lift, target.lift, 0.1);
    motion.tilt = spring(motion.tilt, target.tilt, 0.1);
    motion.bob = spring(motion.bob, target.bob, 0.08);
    motion.squashX = spring(motion.squashX, target.squashX, 0.12);
    motion.squashY = spring(motion.squashY, target.squashY, 0.12);
    writeMotionVars(root);
  }
  window.requestAnimationFrame(tickSpriteMotion);
}

function targetMotion(root, now) {
  if (prefersReducedMotion()) {
    return {
      lookX: 0,
      lookY: 0,
      lift: mode === "drag" ? 5 : 0,
      tilt: 0,
      bob: 0,
      squashX: 1,
      squashY: 1,
    };
  }
  const rect = root.getBoundingClientRect();
  const center = {
    x: rect.left + rect.width / 2,
    y: rect.top + rect.height / 2,
  };
  const age = pointer ? now - pointer.at : Infinity;
  const activePointer = pointer && age < 1800;
  const dx = activePointer ? pointer.x - center.x : 0;
  const dy = activePointer ? pointer.y - center.y : 0;
  const distance = Math.hypot(dx, dy);
  const attention = activePointer ? clamp(1 - distance / 620, 0, 1) : 0;
  const lookX = activePointer ? clamp(dx / 360, -1, 1) * (0.38 + attention * 0.62) : 0;
  const lookY = activePointer ? clamp(dy / 320, -1, 1) * (0.28 + attention * 0.5) : 0;
  const idleBob = Math.sin(now / 880) * 1.8;
  const drag = root.classList.contains("is-dragging") || mode === "drag";
  const thinking = mode === "think" || mode === "suggest";
  const executing = mode === "execute";
  const success = mode === "success";
  const error = mode === "error";
  return {
    lookX,
    lookY,
    lift: (attention * 4.5) + (drag ? 9 : 0) + (thinking ? 3 : 0) + (executing ? 6 : 0) + (success ? 7 : 0),
    tilt: (lookX * (drag ? 9 : 4.5)) + (error ? Math.sin(now / 80) * 2.8 : 0),
    bob: idleBob + (thinking ? Math.sin(now / 230) * 1.5 : 0) + (executing ? Math.sin(now / 170) * 2.4 : 0) + (success ? Math.sin(now / 110) * 4 : 0),
    squashX: drag ? 1.035 : success ? 1.02 : 1,
    squashY: drag ? 0.975 : success ? 1.01 : 1,
  };
}

function writeMotionVars(root) {
  const target = motionTarget(root);
  if (!target) return;
  target.style.setProperty("--sprite-look-x", motion.lookX.toFixed(4));
  target.style.setProperty("--sprite-look-y", motion.lookY.toFixed(4));
  target.style.setProperty("--sprite-lift", motion.lift.toFixed(3));
  target.style.setProperty("--sprite-tilt", motion.tilt.toFixed(3));
  target.style.setProperty("--sprite-bob", motion.bob.toFixed(3));
  target.style.setProperty("--sprite-squash-x", motion.squashX.toFixed(4));
  target.style.setProperty("--sprite-squash-y", motion.squashY.toFixed(4));
  target.style.setProperty("--sprite-shift-x", `${(motion.lookX * 7).toFixed(2)}px`);
  target.style.setProperty("--sprite-shift-y", `${((motion.lookY * 5) + motion.bob - motion.lift).toFixed(2)}px`);
  target.style.setProperty("--sprite-tilt-deg", `${motion.tilt.toFixed(2)}deg`);
  target.style.setProperty("--sprite-shadow-x", `${(motion.lookX * 6).toFixed(2)}px`);
  target.style.setProperty("--sprite-shadow-scale", clamp(1 - (motion.lift * 0.024), 0.72, 1.08).toFixed(4));
  target.style.setProperty("--sprite-shadow-opacity", clamp(0.72 - (motion.lift * 0.022), 0.44, 0.78).toFixed(4));
}

function seedMotionVars(root) {
  const target = motionTarget(root);
  if (!root || !target) return;
  target.style.setProperty("--sprite-look-x", "0");
  target.style.setProperty("--sprite-look-y", "0");
  target.style.setProperty("--sprite-lift", "0");
  target.style.setProperty("--sprite-tilt", "0");
  target.style.setProperty("--sprite-bob", "0");
  target.style.setProperty("--sprite-squash-x", "1");
  target.style.setProperty("--sprite-squash-y", "1");
  target.style.setProperty("--sprite-shift-x", "0px");
  target.style.setProperty("--sprite-shift-y", "0px");
  target.style.setProperty("--sprite-tilt-deg", "0deg");
  target.style.setProperty("--sprite-shadow-x", "0px");
  target.style.setProperty("--sprite-shadow-scale", "1");
  target.style.setProperty("--sprite-shadow-opacity", "0.72");
  root.dataset.spriteMotion = mode;
}

function spring(current, target, factor) {
  return current + (target - current) * factor;
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function prefersReducedMotion() {
  return window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches === true;
}

function motionTarget(root) {
  return root?.querySelector?.(".afs-sprite-avatar") || root;
}
