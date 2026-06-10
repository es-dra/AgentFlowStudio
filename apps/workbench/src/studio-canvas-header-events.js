export function bindCanvasHeaderEvents(root, state, paint) {
  root.querySelectorAll("[data-studio-title-input]").forEach((node) => {
    node.addEventListener("input", () => {
      state.studioProjectTitle = node.value;
    });
  });
  root.querySelectorAll("[data-studio-canvas-menu]").forEach((node) => {
    node.addEventListener("click", () => {
      state.studioCanvasMenuOpen = !state.studioCanvasMenuOpen;
      paint();
    });
  });
  root.querySelectorAll("[data-studio-canvas-id]").forEach((node) => {
    node.addEventListener("click", () => {
      state.studioActiveCanvasId = node.dataset.studioCanvasId || state.studioActiveCanvasId;
      state.studioCanvasIntent = node.dataset.studioCanvasId || "";
      state.studioCanvasMenuOpen = false;
      paint();
    });
  });
  root.querySelectorAll("[data-studio-canvas-action]").forEach((node) => {
    node.addEventListener("click", () => {
      state.studioCanvasIntent = node.dataset.studioCanvasAction || "";
      state.studioCanvasMenuOpen = false;
      paint();
    });
  });
}
