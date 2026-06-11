import { directorPromptContext } from "./director-setup-model.js";
import { selectNodeControl } from "./studio-node-control-state.js";

export function bindStudioExperienceEvents(root, state, repaint) {
  root.querySelectorAll("[data-studio-starter-kind]").forEach((node) => {
    node.addEventListener("click", () => {
      state.studioStarterMode = true;
      state.studioStarterKind = node.dataset.studioStarterKind || "";
      state.studioAddedNodeKind = "";
      state.studioResourceMode = "";
      repaint();
    });
  });
  root.querySelectorAll("[data-studio-sidebar-tab]").forEach((node) => {
    node.addEventListener("click", () => {
      state.studioSidebarTab = node.getAttribute("data-studio-sidebar-tab") || "canvas";
      repaint();
    });
  });
  root.querySelectorAll("[data-toolbox-intent]").forEach((node) => {
    node.addEventListener("click", () => {
      state.studioToolIntent = node.getAttribute("data-toolbox-intent") || "";
      repaint();
    });
  });
  root.querySelectorAll("[data-node-control]").forEach((node) => {
    node.addEventListener("click", () => {
      selectNodeControl(state, node.dataset.nodeControl || "", node.dataset.nodeControlValue || "");
      repaint();
    });
  });
  root.querySelectorAll("[data-visible-asset-type]").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedAssetType = node.dataset.visibleAssetType || "all";
      repaint();
    });
  });
  root.querySelectorAll("[data-visible-asset-id]").forEach((node) => {
    node.addEventListener("click", () => {
      state.selectedVisibleAssetId = node.dataset.visibleAssetId || state.selectedVisibleAssetId;
      repaint();
    });
  });
  root.querySelectorAll("[data-director-element-id]").forEach((node) => {
    node.addEventListener("click", () => {
      state.directorSelectedElementId = node.dataset.directorElementId || "key-light";
      repaint();
    });
  });
  root.querySelectorAll("[data-director-drag-id]").forEach((node) => {
    node.addEventListener("pointerdown", (event) => {
      beginDirectorObjectDrag(event, node, state, repaint);
    });
  });
  root.querySelectorAll("[data-prompt-optimizer]").forEach((node) => {
    node.addEventListener("click", () => {
      state.promptOptimizationOpen = node.dataset.promptOptimizer !== "close";
      repaint();
    });
  });
}

function beginDirectorObjectDrag(event, node, state, repaint) {
  if (event.button !== 0) return;
  const stage = node.closest(".libtv-director-stage");
  if (!stage) return;
  event.preventDefault();
  event.stopPropagation();
  const id = node.dataset.directorDragId || node.dataset.directorElementId || "camera-a";
  state.directorSelectedElementId = id;
  const rect = stage.getBoundingClientRect();
  const update = (clientX, clientY) => {
    const x = clamp(((clientX - rect.left) / rect.width) * 100, 10, 90);
    const y = clamp(((clientY - rect.top) / rect.height) * 100, 8, 92);
    state.directorElementOverrides = {
      ...(state.directorElementOverrides || {}),
      [id]: { ...(state.directorElementOverrides?.[id] || {}), x, y },
    };
    state.directorSaveStatus = "已调整";
    state.directorAppliedShotContext = directorPromptContext(state).slice(0, 96);
    repaint();
  };
  const onMove = (moveEvent) => update(moveEvent.clientX, moveEvent.clientY);
  const onUp = () => {
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
  };
  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onUp, { once: true });
  update(event.clientX, event.clientY);
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}
