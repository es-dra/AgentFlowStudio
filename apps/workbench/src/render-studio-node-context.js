import { el } from "./dom.js";
import { allEdges, nodeKindForCanvasNode, workflowNodes } from "./studio-workflow-graph.js";

const KIND_LABELS = {
  text: "文本",
  image: "图片",
  video: "视频",
  video_merge: "视频合成",
  director: "导演台",
  audio: "音频",
  script: "脚本",
  source: "素材",
};

export function renderNodeOpenContext(state = {}, fallbackKind = "text") {
  const nodeId = state.openedCanvasNodeId || state.selectedCardId || "";
  const nodes = workflowNodes(state);
  const node = nodes.find((item) => item[0] === nodeId);
  const kind = nodeKindForCanvasNode(state, nodeId) || fallbackKind;
  const title = node?.[2] || KIND_LABELS[kind] || "节点";
  const upstream = linkedNodes(state, nodes, nodeId, "upstream");
  const downstream = linkedNodes(state, nodes, nodeId, "downstream");
  return el("nav", {
    className: "node-open-context-bar",
    attrs: { "data-node-open-context": nodeId, "data-node-open-kind": kind },
  }, [
    el("div", { className: "node-open-origin" }, [
      el("span", { text: "画布节点" }),
      el("strong", { text: title }),
      el("small", { text: KIND_LABELS[kind] || kind }),
    ]),
    renderContextChain("context-upstream", "上游", upstream),
    renderContextChain("context-current", "当前", [{ id: nodeId, title, kind }]),
    renderContextChain("context-downstream", "下游", downstream),
    el("button", {
      className: "node-context-return",
      text: "返回画布",
      dataset: { view: "Create", studioStarter: "close" },
      attrs: { type: "button" },
    }),
  ]);
}

function renderContextChain(className, label, items) {
  const visibleItems = items.length ? items : [{ id: "empty", title: "暂无连接", empty: true }];
  return el("div", { className: `context-chain ${className}` }, [
    el("span", { text: label }),
    ...visibleItems.slice(0, 3).map((item) => renderContextChip(item, className)),
  ]);
}

function renderContextChip(item, className) {
  if (item.empty) {
    return el("em", {
      className: "context-node-chip empty",
      text: item.title || item.id,
      attrs: { title: item.title || item.id },
    });
  }
  return el("button", {
    className: `context-node-chip${className === "context-current" ? " current" : ""}`,
    text: item.title || item.id,
    attrs: {
      type: "button",
      title: item.title || item.id,
      "data-context-nav-node": item.id,
      "data-open-node-id": item.id,
      "data-open-node-kind": item.kind || "text",
    },
  });
}

function linkedNodes(state, nodes, nodeId, direction) {
  if (!nodeId) return [];
  const nodeMap = new Map(nodes.map((node) => [node[0], node[2]]));
  return allEdges(state)
    .filter((edge) => direction === "upstream" ? edge.to === nodeId : edge.from === nodeId)
    .map((edge) => direction === "upstream" ? edge.from : edge.to)
    .filter((id) => nodeMap.has(id))
    .map((id) => ({ id, title: nodeMap.get(id), kind: nodeKindForCanvasNode(state, id) }));
}
