export function selectedNodeId(state) {
  return String(state?.selection?.nodeIds?.[0] || "");
}

const SPRITE_REPLY_FALLBACK = "我先观察当前画布，再给出一个不打断创作的建议。";
const SPRITE_PROMPT_LEAK_FRAGMENTS = [
  "你是团团",
  "第一人称",
  "系统设定",
  "user message:",
  "canvas summary:",
  "project id:",
];

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
  const lowered = text.toLowerCase();
  if (SPRITE_PROMPT_LEAK_FRAGMENTS.some((fragment) => lowered.includes(fragment))) return SPRITE_REPLY_FALLBACK;
  return text.slice(0, 220) || SPRITE_REPLY_FALLBACK;
}
