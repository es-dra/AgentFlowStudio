const EDGE_THRESHOLD = 74;
const MAX_STEP = 16;

export function applyEdgeAutoPan(store, rootEl, event, options = {}) {
  const delta = edgeAutoPanDelta(rootEl, event, options);
  if (!delta.active) return delta;
  store.set((state) => {
    state.viewport.x += delta.x;
    state.viewport.y += delta.y;
  }, { history: false, persist: false });
  return delta;
}

export function edgeAutoPanDelta(rootEl, event, options = {}) {
  const rect = rootEl.getBoundingClientRect();
  const threshold = Number(options.threshold || EDGE_THRESHOLD);
  const maxStep = Number(options.maxStep || MAX_STEP);
  const left = event.clientX - rect.left;
  const right = rect.right - event.clientX;
  const top = event.clientY - rect.top;
  const bottom = rect.bottom - event.clientY;
  const x = edgeStep(left, right, threshold, maxStep);
  const y = edgeStep(top, bottom, threshold, maxStep);
  return { x, y, active: Boolean(x || y) };
}

function edgeStep(nearStart, nearEnd, threshold, maxStep) {
  if (nearStart < threshold) return strength(nearStart, threshold, maxStep);
  if (nearEnd < threshold) return -strength(nearEnd, threshold, maxStep);
  return 0;
}

function strength(distance, threshold, maxStep) {
  const ratio = Math.max(0, Math.min(1, (threshold - distance) / threshold));
  return Math.round((3 + ratio * maxStep) * 10) / 10;
}
