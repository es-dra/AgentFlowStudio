import { MOTION, prefersReducedMotion } from "./motion-tokens.js";

const SAMPLE_LIMIT = 5;

export function createPointerKinematics(event) {
  const samples = [];
  samplePointer(samples, event);
  return {
    sample: (nextEvent) => samplePointer(samples, nextEvent),
    velocity: () => velocityFromSamples(samples),
  };
}

export function animateInertiaPan(store, velocity, options = {}) {
  if (prefersReducedMotion()) return null;
  let vx = Number(velocity?.x || 0);
  let vy = Number(velocity?.y || 0);
  if (Math.hypot(vx, vy) < MOTION.minInertiaSpeed) return null;

  const maxMs = Number(options.maxMs || MOTION.inertiaMaxMs);
  const friction = Number(options.friction || MOTION.inertiaFriction);
  let raf = 0;
  let last = performance.now();
  const started = last;
  let cancelled = false;

  const step = (now) => {
    if (cancelled) return;
    const elapsed = Math.min(34, now - last);
    last = now;
    store.set((state) => {
      state.viewport.x += vx * elapsed;
      state.viewport.y += vy * elapsed;
    }, { history: false, persist: false });
    vx *= friction;
    vy *= friction;
    if (now - started < maxMs && Math.hypot(vx, vy) >= MOTION.minInertiaSpeed) {
      raf = requestAnimationFrame(step);
    }
  };

  raf = requestAnimationFrame(step);
  return () => {
    cancelled = true;
    if (raf) cancelAnimationFrame(raf);
  };
}

function samplePointer(samples, event) {
  samples.push({ x: event.clientX, y: event.clientY, t: performance.now() });
  while (samples.length > SAMPLE_LIMIT) samples.shift();
}

function velocityFromSamples(samples) {
  if (samples.length < 2) return { x: 0, y: 0 };
  const first = samples[0];
  const last = samples[samples.length - 1];
  const dt = Math.max(1, last.t - first.t);
  return {
    x: (last.x - first.x) / dt,
    y: (last.y - first.y) / dt,
  };
}
