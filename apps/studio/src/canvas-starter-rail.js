import { assetsFromNode } from "./asset-reference-summary.js";
import { candidatePreviews } from "./canvas-node-body.js";

export function starterRailState(state) {
  const empty = state.order.length === 0;
  return {
    empty,
    show: empty || shouldShowStarterRail(state),
    mode: empty ? "empty" : "quick-start",
  };
}

function shouldShowStarterRail(state) {
  if (state.order.length === 0) return true;
  if (state.order.length > 1) return false;
  return !hasMeaningfulProductionState(state);
}

function hasMeaningfulProductionState(state) {
  if (Object.keys(state.edges || {}).length) return true;
  if ((state.assets || []).length) return true;
  return (state.order || []).some((id) => {
    const node = state.nodes[id];
    if (!node) return false;
    if (String(node.prompt || node.content || node.result || "").trim()) return true;
    if (node.previewUrl || candidatePreviews(node).length) return true;
    if (assetsFromNode(node).length) return true;
    if (node.params?.lastContextBundle || node.params?.lastSafeManifest || node.params?.lastGenerationManifest) return true;
    return !["", "empty", "idle", "ready"].includes(String(node.status || ""));
  });
}
