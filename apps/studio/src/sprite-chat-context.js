export function selectedNodeId(state) {
  return String(state?.selection?.nodeIds?.[0] || "");
}

export function canvasSummary(state) {
  const nodeId = selectedNodeId(state);
  const node = nodeId ? state.nodes?.[nodeId] : null;
  return {
    nodes: Array.isArray(state?.order) ? state.order.length : 0,
    assets: Array.isArray(state?.assets) ? state.assets.length : 0,
    edges: Object.keys(state?.edges || {}).length,
    selected_node_type: node?.type || "",
    selected_node_status: node?.status || "",
  };
}

export function safeReply(value) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.slice(0, 220) || "我先观察当前画布，再给出一个不打断创作的建议。";
}
