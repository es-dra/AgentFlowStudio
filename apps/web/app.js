import { normalizeWorkspace, parseFiles } from "./artifact-workspace.js?v=m4-memory-canvas-tools";
import { applyStaticCopy, collectAppElements } from "./app-elements.js";
import { mountAppShell } from "./app-shell-template.js";
import { renderWorkspace } from "./app-workspace-render.js";
import { attachFeedbackHandlers } from "./feedback-wiring.js";
import { getCopy } from "./ui-copy.js";
import { initializeProductionMode, productionState, recordRunFeedbackCaptured, recordSupervisionIntent, renderProductionState } from "./production-mode.js";
import { revokeCurrentVideoUrl } from "./video-preview.js";
import { attachMemoryWorkbenchHandlers, buildMemoryWorkbenchView, memorySourceForArtifacts } from "./memory-workbench-controller.js";
import { renderMemoryWorkbench } from "./memory-workbench-render.js";

mountAppShell();

const state = {
  language: "zh",
  mode: initialMode(),
  workspace: normalizeWorkspace([]),
  memorySource: "fixture",
};

const elements = collectAppElements();

elements.fileInput.addEventListener("change", async (event) => {
  const files = Array.from(event.target.files || []);
  const artifacts = await parseFiles(files);
  state.workspace = normalizeWorkspace(artifacts);
  state.memorySource = memorySourceForArtifacts(artifacts);
  render();
});

elements.languageToggle.addEventListener("click", () => {
  state.language = state.language === "zh" ? "en" : "zh";
  render();
});

elements.modeReview.addEventListener("click", () => setMode("review"));
elements.modeProduction.addEventListener("click", () => setMode("production"));
elements.modeMemory.addEventListener("click", () => setMode("memory"));
attachMemoryWorkbenchHandlers(elements, {
  onWorkspaceLoaded: (workspace, source) => {
    state.workspace = workspace;
    state.memorySource = source;
  },
  setMode,
});
elements.supervisionActions.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-supervision]");
  if (!button) return;
  recordSupervisionIntent(button.dataset.supervision, elements, getCopy(state.language));
});

attachFeedbackHandlers(elements, {
  getCopyForLanguage: () => getCopy(state.language),
  productionState,
  onRunFeedbackCaptured: () => recordRunFeedbackCaptured(elements, getCopy(state.language)),
});

window.addEventListener("beforeunload", revokeCurrentVideoUrl);

initializeProductionMode(elements, getCopy(state.language));
render();

function setMode(mode) {
  state.mode = mode;
  render();
}

function initialMode() {
  const mode = window.location?.hash?.replace("#", "") || "";
  return ["review", "production", "memory"].includes(mode) ? mode : "review";
}

function render() {
  const copy = getCopy(state.language);
  document.documentElement.lang = state.language === "zh" ? "zh-CN" : "en";
  applyStaticCopy(copy, elements);
  renderMode();
  renderWorkspace(elements, state.workspace, copy);
  renderMemoryWorkbench(elements, buildMemoryWorkbenchView(state.workspace, state.memorySource), copy);
  renderProductionState(elements, copy, state.workspace);
}

function renderMode() {
  const review = state.mode === "review";
  const production = state.mode === "production";
  const memory = state.mode === "memory";
  elements.reviewWorkbench.hidden = !review;
  elements.productionWorkbench.hidden = !production;
  elements.memoryWorkbench.hidden = !memory;
  elements.modeReview.classList.toggle("active", review);
  elements.modeProduction.classList.toggle("active", production);
  elements.modeMemory.classList.toggle("active", memory);
}
