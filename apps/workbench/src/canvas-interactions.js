const DEFAULT_ZOOM = 1;
const MIN_ZOOM = 0.55;
const MAX_ZOOM = 1.6;
const ZOOM_STEP = 0.1;

let dragState = null;

export function bindCanvasInteractions(root, state, repaint) {
  const stage = root.querySelector("[data-canvas-surface]");
  if (!stage) return;

  stage.addEventListener("pointerdown", (event) => {
    if (event.button !== 0 || isCanvasControl(event.target)) return;
    dragState = { id: event.pointerId, x: event.clientX, y: event.clientY };
    stage.classList.add("is-panning");
    stage.setPointerCapture?.(event.pointerId);
  });
  stage.addEventListener("pointermove", (event) => {
    if (!dragState || dragState.id !== event.pointerId) return;
    const dx = event.clientX - dragState.x;
    const dy = event.clientY - dragState.y;
    dragState = { id: event.pointerId, x: event.clientX, y: event.clientY };
    state.canvasPanX = Math.round(Number(state.canvasPanX || 0) + dx);
    state.canvasPanY = Math.round(Number(state.canvasPanY || 0) + dy);
    updateCanvasTransform(root, state);
  });
  stage.addEventListener("pointerup", (event) => endDrag(stage, event.pointerId));
  stage.addEventListener("pointercancel", (event) => endDrag(stage, event.pointerId));
  stage.addEventListener("wheel", (event) => {
    if (isCanvasControl(event.target)) return;
    event.preventDefault();
    zoomCanvas(state, event.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP);
    repaint();
  }, { passive: false });

  root.querySelectorAll("[data-canvas-action]").forEach((node) => {
    node.addEventListener("click", () => {
      if (node.dataset.canvasAction === "zoom-in") zoomCanvas(state, ZOOM_STEP);
      if (node.dataset.canvasAction === "zoom-out") zoomCanvas(state, -ZOOM_STEP);
      if (node.dataset.canvasAction === "zoom-reset") {
        state.canvasZoom = DEFAULT_ZOOM;
        state.canvasPanX = 0;
        state.canvasPanY = 0;
      }
      repaint();
    });
  });
}

export function canvasTransformStyle(state) {
  const x = Math.round(Number(state?.canvasPanX || 0));
  const y = Math.round(Number(state?.canvasPanY || 0));
  const zoom = normalizedZoom(state);
  return `transform: translate3d(${x}px, ${y}px, 0) scale(${zoom});`;
}

export function zoomPercent(state) {
  return `${Math.round(normalizedZoom(state) * 100)}%`;
}

function updateCanvasTransform(root, state) {
  root.querySelectorAll("[data-canvas-content]").forEach((node) => {
    node.style.transform = canvasTransformStyle(state).replace("transform: ", "").replace(";", "");
  });
}

function zoomCanvas(state, delta) {
  state.canvasZoom = clamp(Math.round((normalizedZoom(state) + delta) * 100) / 100, MIN_ZOOM, MAX_ZOOM);
}

function normalizedZoom(state) {
  return clamp(Number(state?.canvasZoom || DEFAULT_ZOOM), MIN_ZOOM, MAX_ZOOM);
}

function endDrag(stage, pointerId) {
  if (!dragState || dragState.id !== pointerId) return;
  dragState = null;
  stage.classList.remove("is-panning");
}

function isCanvasControl(target) {
  return Boolean(target?.closest?.("button, input, textarea, select, .libtv-node, .libtv-script-flow, .libtv-character-flow, .libtv-image-video-flow, .libtv-audio-video-flow, .libtv-floating, .libtv-side-panel, .libtv-bottom-bar, .libtv-topbar"));
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}
