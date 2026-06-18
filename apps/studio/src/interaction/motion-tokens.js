export const MOTION = Object.freeze({
  dragStartMs: 110,
  dragLandMs: 180,
  guideMs: 120,
  inertiaMaxMs: 420,
  inertiaFriction: 0.88,
  minInertiaSpeed: 0.025,
});

export function prefersReducedMotion() {
  return Boolean(
    typeof window !== "undefined"
      && window.matchMedia
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
}
