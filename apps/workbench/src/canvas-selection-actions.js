import { centerCanvasOnSelection } from "./canvas-viewport-actions.js";
import { nodeKindForCanvasNode, nodePosition, workflowNodes } from "./studio-workflow-graph.js";

export function applyCanvasSelectionAction(state, action) {
  if (action === "duplicate") duplicateSelectedNodes(state);
  if (action === "align-row") alignSelectedNodes(state, "row");
  if (action === "align-column") alignSelectedNodes(state, "column");
  if (action === "delete") deleteCustomSelectedNodes(state);
  if (action === "clear") clearCanvasSelection(state);
}

export function applyCanvasEdgeAction(state, action) {
  if (action === "center-edge") centerCanvasOnSelectedEdge(state);
  if (action === "disconnect-edge") disconnectSelectedCustomEdge(state);
}

export function duplicateSelectedNodes(state) {
  const selected = selectedIds(state);
  if (!selected.length) return;
  const nodes = workflowNodes(state);
  const customNodes = Array.isArray(state.canvasCustomNodes) ? state.canvasCustomNodes : [];
  const nextNodes = [];
  const nextPositions = {};
  selected.forEach((id, index) => {
    const source = nodes.find((node) => node[0] === id);
    if (!source) return;
    const nextId = `${nodeKindForCanvasNode(state, id)}-${Date.now()}-${index + 1}`;
    const position = nodePosition(state, id, nodes.findIndex((node) => node[0] === id));
    nextNodes.push({
      id: nextId,
      kind: nodeKindForCanvasNode(state, id),
      title: `${source[2]} 副本`,
      summary: source[3],
      status: "本地预览",
    });
    nextPositions[nextId] = { x: position.x + 48, y: position.y + 48 };
  });
  state.canvasCustomNodes = [...customNodes, ...nextNodes];
  state.canvasNodePositions = { ...(state.canvasNodePositions || {}), ...nextPositions };
  state.selectedEdgeKey = "";
  state.selectedNodeIds = nextNodes.map((node) => node.id);
  state.selectedCardId = state.selectedNodeIds[0] || state.selectedCardId;
  state.lastResult = { status: "canvas_selection_duplicated", message: `已复制 ${nextNodes.length} 个节点` };
}

export function alignSelectedNodes(state, direction = "row") {
  const selected = selectedIds(state);
  if (selected.length < 2) return;
  const nodes = workflowNodes(state);
  const positions = selected.map((id) => [id, nodePosition(state, id, nodes.findIndex((node) => node[0] === id))]);
  const anchor = positions[0]?.[1] || { x: 0, y: 0 };
  const aligned = Object.fromEntries(positions.map(([id, position], index) => [
    id,
    direction === "column"
      ? { x: anchor.x, y: anchor.y + index * 264 }
      : { x: anchor.x + index * 390, y: anchor.y },
  ]));
  state.canvasNodePositions = { ...(state.canvasNodePositions || {}), ...aligned };
  state.lastResult = {
    status: "canvas_selection_aligned",
    message: direction === "column" ? "已纵向对齐选中节点" : "已横向对齐选中节点",
  };
}

export function deleteCustomSelectedNodes(state) {
  const selected = new Set(selectedIds(state));
  if (!selected.size) return;
  const customNodes = Array.isArray(state.canvasCustomNodes) ? state.canvasCustomNodes : [];
  const deletedIds = new Set(customNodes.filter((node) => selected.has(node.id)).map((node) => node.id));
  state.canvasCustomNodes = customNodes.filter((node) => !deletedIds.has(node.id));
  state.canvasEdges = (Array.isArray(state.canvasEdges) ? state.canvasEdges : [])
    .filter((edge) => !deletedIds.has(edge.from) && !deletedIds.has(edge.to));
  state.canvasNodePositions = Object.fromEntries(Object.entries(state.canvasNodePositions || {})
    .filter(([id]) => !deletedIds.has(id)));
  state.selectedEdgeKey = "";
  state.selectedNodeIds = [...selected].filter((id) => !deletedIds.has(id));
  state.selectedCardId = state.selectedNodeIds[0] || "script-input";
  state.lastResult = {
    status: "canvas_selection_deleted",
    message: deletedIds.size ? `已删除 ${deletedIds.size} 个自建节点` : "默认流程节点已保留，仅清除选择",
  };
  if (!state.selectedNodeIds.length) clearCanvasSelection(state);
}

export function clearCanvasSelection(state) {
  state.selectedNodeIds = [];
  state.selectedEdgeKey = "";
  state.lastResult = { status: "canvas_selection_cleared", message: "已清除画布选择" };
}

function centerCanvasOnSelectedEdge(state) {
  const endpoints = edgeEndpoints(state.selectedEdgeKey);
  if (!endpoints) return;
  state.selectedNodeIds = endpoints;
  state.selectedCardId = endpoints[1];
  centerCanvasOnSelection(state);
  state.lastResult = { status: "canvas_edge_centered", message: "已定位连接两端节点" };
}

function disconnectSelectedCustomEdge(state) {
  const endpoints = edgeEndpoints(state.selectedEdgeKey);
  if (!endpoints) return;
  const [from, to] = endpoints;
  const before = Array.isArray(state.canvasEdges) ? state.canvasEdges : [];
  state.canvasEdges = before.filter((edge) => !(edge.from === from && edge.to === to));
  state.selectedEdgeKey = "";
  state.selectedNodeIds = [from, to];
  state.selectedCardId = to;
  state.lastResult = {
    status: before.length === state.canvasEdges.length ? "canvas_default_edge_kept" : "canvas_edge_disconnected",
    message: before.length === state.canvasEdges.length ? "默认流程连接已保留" : "已断开自定义连接",
  };
}

function edgeEndpoints(edgeKey) {
  const [from, to] = String(edgeKey || "").split(":");
  return from && to ? [from, to] : null;
}

function selectedIds(state) {
  return Array.isArray(state.selectedNodeIds) ? state.selectedNodeIds.filter(Boolean) : [];
}
