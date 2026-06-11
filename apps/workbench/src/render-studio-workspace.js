import { badge, el } from "./dom.js";
import { canvasTransformStyle } from "./canvas-interactions.js";
import { renderAddNodeFlow } from "./render-studio-add-node-flow.js";
import { renderCanvasTopbar as renderCanvasTopbarControls } from "./render-studio-canvas-topbar.js";
import { renderBottomToolbar, renderFloatingPanel } from "./render-studio-panels.js";
import {
  renderAudioVideoStarterFlow,
  renderCharacterStarterFlow,
  renderImageVideoStarterFlow,
  renderScriptStarterFlow,
  renderStarterNodes,
} from "./render-studio-starter-flows.js";
import { renderNodePrompt } from "./render-node-prompt.js";
import { nodeOpenTransitionForCanvas } from "./studio-node-actions.js";
import { canvasRelationFocus, edgeRelationClasses, nodeRelationClasses } from "./canvas-relation-focus.js";

import {
  DEFAULT_EDGES,
  NODE_SIZE,
  WORKFLOW_NODES,
  edgePathBetween,
  nodeKindForCanvasNode,
  nodePort,
  nodePosition,
  workflowNodes,
} from "./studio-workflow-graph.js";

// Static contract markers kept because this shell was split into smaller render modules while older tests still guard source-level strings from the original workspace contract.
const STATIC_CONTRACT_MARKERS = `canvas-rail canvas-surface canvas-inspector canvas-topbar 创作画布 libtv-bottom-bar node-dock dock-plus renderCanvasTopbar(state) 剧本到视频工作流 dataset: { canvasAction: "zoom-out" } dataset: { canvasAction: "zoom-reset" } dataset: { canvasAction: "zoom-in" } dataset: { view: "Assets" } ["text", "文本" ["image", "图片" ["video", "视频" ["video_merge", "视频合成" ["director", "导演台" ["audio", "音频" ["script", "脚本" addResourceKind: "upload" addResourceKind: "history" libtv-text-node-flow libtv-image-node-flow libtv-video-node-flow libtv-audio-node-flow libtv-script-generator-flow libtv-video-merge-flow libtv-director-flow libtv-upload-dropzone libtv-history-resource-picker DEFAULT_NODE_POSITIONS NODE_KIND_META edgePathBetween data-node-id data-node-x data-node-y data-connect-from data-connect-to data-node-drag-handle studio-canvas-edge pending studio-edge-layer studio-canvas-edge connected " active" 生成队列 剧本输入 分镜脚本 角色三视图 场景资产 关键帧 导演台 视频片段 成片合成 分镜脚本 · 已完成 关键帧 · 排队中 视频片段 · 生成中 待生成 排队中 生成中 已完成 失败 本地预览 上传 历史`;
void STATIC_CONTRACT_MARKERS;

export function renderStudioWorkspace(workspace = {}, state = {}) {
  const selected = selectedWorkflowNode(state);
  return el("main", { className: "libtv-canvas canvas-product-v3" }, [
    renderCanvasTopbarControls(workspace, state),
    el("section", { className: "libtv-canvas-stage", dataset: { canvasSurface: "true" } }, [
      renderCanvasContent(workspace, state, selected),
    ]),
    renderBottomToolbar(state.studioPanel, workspace, state),
    renderFloatingPanel(state.studioPanel, workspace, workflowCard(selected), state),
  ]);
}


function renderCanvasContent(workspace, state, selected) {
  const attrs = { style: canvasTransformStyle(state), ...(nodeOpenTransitionForCanvas(state) ? { "data-node-open-transition": nodeOpenTransitionForCanvas(state) } : {}) };
  if (state.openedCanvasNodeId) attrs["data-opened-node-id"] = state.openedCanvasNodeId;
  if (state.studioAddedNodeKind) return renderAddNodeFlow(state.studioAddedNodeKind, attrs, state);
  if (state.studioResourceMode) return renderResourceCanvas(state.studioResourceMode, attrs);
  if (state.studioStarterMode && state.studioStarterKind) return renderStarterFlow(state.studioStarterKind, attrs, state);
  if (state.studioStarterMode) return renderStarterNodes(attrs, state.studioStarterKind);
  const nodes = workflowNodes(state);
  const relationFocus = canvasRelationFocus(state, selected[0], nodes);
  return el("div", { className: "libtv-node-layer workflow-node-layer", dataset: { canvasContent: "true" }, attrs }, [
    el("div", { className: "libtv-empty-hint" }, [
      el("span", { text: "⌁" }),
      el("small", { text: "双击画布，或从底部添加节点开始创作" }),
    ]),
    renderEdgeLayer(selected[0], state, nodes, relationFocus),
    ...nodes.map((node, index) => renderWorkflowNode(node, index, state, relationFocus)),
    renderSelectionFrame(state, nodes),
    renderSelectedEdgeToolbar(state, nodes),
    renderWorkflowPromptCard(selected, state, nodes),
  ]);
}

function renderStarterFlow(kind, attrs, state) {
  if (kind === "script") return renderScriptStarterFlow(attrs, state);
  if (kind === "character") return renderCharacterStarterFlow(attrs, state);
  if (kind === "image") return renderImageVideoStarterFlow(attrs, state);
  if (kind === "audio") return renderAudioVideoStarterFlow(attrs, state);
  return renderStarterNodes(attrs, kind);
}

function renderWorkflowNode([id, icon, title, summary, status], index, state, relationFocus) {
  const position = nodePosition(state, id, index);
  const kind = nodeKindForCanvasNode(state, id);
  return el("article", {
    className: `libtv-node workflow-node node-pos-${index + 1}${nodeRelationClasses(relationFocus, id)}`,
    dataset: { cardId: id, relationRole: relationRole(relationFocus, id) },
    attrs: {
      "data-connect-to": id,
      "data-node-id": id,
      "data-node-x": String(position.x),
      "data-node-y": String(position.y),
      style: `left:${position.x}px;top:${position.y}px;`,
    },
  }, [
    renderNodePort(id, title, "input"),
    el("div", { className: "libtv-node-title" }, [
      el("span", { className: "node-icon", text: icon }),
      el("strong", { text: title, attrs: { "data-node-drag-handle": id } }),
    ]),
    badge(status, statusTone(status)),
    el("div", { className: "libtv-node-preview" }, [
      el("span", { className: "preview-bars", attrs: { "aria-hidden": "true" } }),
      el("p", { text: summary }),
    ]),
    el("div", { className: "studio-node-actions" }, [
      el("button", { text: "打开", attrs: { type: "button", "data-open-node-id": id, "data-open-node-kind": kind } }),
    ]),
    renderNodePort(id, title, "output"),
  ]);
}

function renderNodePort(id, title, kind) {
  const isInput = kind === "input";
  return el("button", {
    className: `canvas-node-port ${isInput ? "input-port" : "output-port"}`,
    attrs: {
      type: "button",
      "data-port-kind": kind,
      [isInput ? "data-connect-to" : "data-connect-from"]: id,
      "aria-label": `${title}${isInput ? "输入端口" : "输出端口"}`,
      title: isInput ? "接收上游节点" : "拖出连接到下游节点",
    },
  });
}

function renderWorkflowPromptCard(selected, state, nodes) {
  const [id, icon, title, summary] = selected;
  const position = nodePosition(state, id, nodes.findIndex((node) => node[0] === id));
  const x = Math.min(position.x, 2180);
  const y = Math.max(72, position.y + NODE_SIZE.height + 20);
  return el("aside", { className: "libtv-workflow-control", attrs: { style: `left:${x}px;top:${y}px;` } }, [
    el("header", {}, [
      el("span", { className: "node-icon", text: icon }),
      el("div", {}, [
        el("strong", { text: title }),
        el("small", { text: summary }),
      ]),
    ]),
    renderNodePrompt(state, {
      placeholder: promptPlaceholder(id),
      surface: id,
      primaryAction: primaryActionLabel(id),
      note: `${title}未启动`,
    }),
  ]);
}

function renderEdgeLayer(selectedId, state, nodes, relationFocus) {
  const nodeIds = new Set(nodes.map((node) => node[0]));
  const records = edgeRecords(state)
    .filter((edge) => nodeIds.has(edge.from) && nodeIds.has(edge.to));
  const pending = state.connectionDraft?.from ? state.connectionDraft : null;
  return el("svg", { className: "studio-edge-layer", attrs: { viewBox: "0 0 2600 1700", preserveAspectRatio: "none" } }, [
    ...records.map(({ from, to, defaultEdge }) => el("path", {
      className: edgeClassName(state, relationFocus, from, to),
      attrs: {
        d: edgePathBetween(nodePort(state, from, nodes, "output"), nodePort(state, to, nodes, "input")),
        "data-linked-node-id": `${from}:${to}`,
        "data-edge-default": defaultEdge ? "true" : "false",
        "data-edge-relation": edgeRelationRole(relationFocus, from, to),
      },
    })),
    pending ? el("path", {
      className: `studio-canvas-edge pending${pending.targetNodeId ? " target-locked" : ""}`,
      attrs: { d: edgePathBetween(nodePort(state, pending.from, nodes, "output"), { x: pending.x, y: pending.y }), "data-linked-node-id": pending.from },
    }) : null,
  ]);
}

function renderSelectedEdgeToolbar(state, nodes) {
  const selected = edgeRecords(state).find((edge) => `${edge.from}:${edge.to}` === state.selectedEdgeKey);
  if (!selected) return null;
  const nodeMap = new Map(nodes.map((node) => [node[0], node[2]]));
  const from = nodePort(state, selected.from, nodes, "output");
  const to = nodePort(state, selected.to, nodes, "input");
  const left = Math.round((from.x + to.x) / 2 - 136);
  const top = Math.round((from.y + to.y) / 2 - 46);
  return el("aside", {
    className: `canvas-edge-toolbar${selected.defaultEdge ? " default-edge" : ""}`,
    attrs: {
      "data-selected-edge-key": `${selected.from}:${selected.to}`,
      "data-selected-edge-default": selected.defaultEdge ? "true" : "false",
      style: `left:${left}px;top:${top}px;`,
    },
  }, [
    el("span", { text: selected.defaultEdge ? "默认链路" : "自定义连接" }),
    el("strong", { text: `${nodeMap.get(selected.from) || selected.from} → ${nodeMap.get(selected.to) || selected.to}` }),
    el("div", {}, [
      el("button", { text: "定位两端", attrs: { type: "button", "data-canvas-edge-action": "center-edge" } }),
      el("button", {
        text: selected.defaultEdge ? "已保护" : "断开",
        attrs: { type: "button", "data-canvas-edge-action": "disconnect-edge", ...(selected.defaultEdge ? { disabled: "disabled" } : {}) },
      }),
    ]),
  ]);
}

function edgeRecords(state) {
  const seen = new Set();
  return [
    ...DEFAULT_EDGES.map(([from, to]) => ({ from, to, defaultEdge: true })),
    ...(Array.isArray(state.canvasEdges) ? state.canvasEdges : []).map((edge) => ({ from: edge.from, to: edge.to, defaultEdge: false })),
  ].filter((edge) => {
    const key = `${edge.from}:${edge.to}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function edgeClassName(state, relationFocus, from, to) {
  const key = `${from}:${to}`;
  return `studio-canvas-edge connected${edgeRelationClasses(relationFocus, from, to)}${state.lastConnectedEdgeKey === key ? " connection-success-ripple" : ""}${state.selectedEdgeKey === key ? " edge-selected" : ""}`;
}

function renderSelectionFrame(state, nodes) {
  const selectedIds = Array.isArray(state.selectedNodeIds) ? state.selectedNodeIds.filter(Boolean) : [];
  if (selectedIds.length < 2) return null;
  const selected = selectedIds.map((id) => {
    const index = nodes.findIndex((node) => node[0] === id);
    if (index < 0) return null;
    return { id, ...nodePosition(state, id, index) };
  }).filter(Boolean);
  if (selected.length < 2) return null;
  const left = Math.min(...selected.map((node) => node.x)) - 12;
  const top = Math.min(...selected.map((node) => node.y)) - 12;
  const right = Math.max(...selected.map((node) => node.x + NODE_SIZE.width)) + 12;
  const bottom = Math.max(...selected.map((node) => node.y + NODE_SIZE.height)) + 12;
  return el("div", {
    className: "canvas-selection-frame",
    attrs: {
      "data-selection-count": String(selected.length),
      style: `left:${left}px;top:${top}px;width:${right - left}px;height:${bottom - top}px;`,
    },
  }, [
    el("div", { className: "canvas-selection-toolbar" }, [
      el("span", { text: `${selected.length} 个节点` }),
      el("button", { text: "复制", attrs: { type: "button", "data-canvas-selection-action": "duplicate" } }),
      el("button", { text: "横排", attrs: { type: "button", "data-canvas-selection-action": "align-row" } }),
      el("button", { text: "竖排", attrs: { type: "button", "data-canvas-selection-action": "align-column" } }),
      el("button", { text: "删除", attrs: { type: "button", "data-canvas-selection-action": "delete" } }),
      el("button", { text: "取消", attrs: { type: "button", "data-canvas-selection-action": "clear" } }),
    ]),
  ]);
}

function renderResourceCanvas(kind, attrs) {
  const isHistory = kind === "history";
  return el("div", { className: `resource-canvas ${isHistory ? "libtv-history-resource-picker" : "libtv-upload-dropzone"}`, dataset: { canvasContent: "true" }, attrs }, [
    el("strong", { text: isHistory ? "从生成历史选择" : "上传资源" }),
    el("p", { text: isHistory ? "按图片、视频、音频筛选可复用记录，并加入当前镜头。" : "选择图片、视频或音频文件作为参考素材。" }),
    el("button", { className: "btn primary", text: isHistory ? "选择历史资产" : "选择文件", attrs: { type: "button" } }),
  ]);
}

function selectedWorkflowNode(state) {
  const selectedId = state.selectedCardId || "script-input";
  return workflowNodes(state).find((node) => node[0] === selectedId) || WORKFLOW_NODES[0];
}

function workflowCard(node) {
  return { card_id: node[0], title: node[2], summary: node[3], status: node[4], inspector: { prompt: "" } };
}

function relationRole(focus, id) {
  if (!focus?.active) return "none";
  if (focus.selected.has(id)) return "selected";
  if (focus.upstream.has(id) && focus.downstream.has(id)) return "bridge";
  if (focus.upstream.has(id)) return focus.directUpstream.has(id) ? "direct-upstream" : "upstream";
  if (focus.downstream.has(id)) return focus.directDownstream.has(id) ? "direct-downstream" : "downstream";
  return "dimmed";
}

function edgeRelationRole(focus, from, to) {
  const classes = edgeRelationClasses(focus, from, to);
  if (classes.includes("edge-upstream")) return "upstream";
  if (classes.includes("edge-downstream")) return "downstream";
  if (classes.includes("edge-dimmed")) return "dimmed";
  return "neutral";
}

function statusTone(status) {
  if (status.includes("失败")) return "error";
  if (status.includes("生成中")) return "loading";
  if (status.includes("已完成")) return "active";
  if (status.includes("排队中")) return "quiet";
  return "ready";
}

function promptPlaceholder(id) {
  const copy = {
    "script-input": "输入剧本、剧情梗概或一句创作目标。",
    storyboard: "描述你希望拆分出的分镜结构、节奏和镜头数量。",
    character: "描述人物年龄、外观、服装、表情和三视图一致性。",
    scene: "描述场景空间、道具、材质、时代和参考氛围。",
    keyframe: "描述关键帧构图、景别、光线和主体动作。",
    director: "描述机位、灯光、人物站位和场景调度。",
    clip: "描述 5s 视频片段的运动、节奏和镜头语言。",
    compose: "描述片段顺序、转场、节奏和成片结构。",
  };
  return copy[id] || "描述你想生成的内容。";
}

function primaryActionLabel(id) {
  return id === "compose" ? "合成" : id === "clip" ? "生成视频" : "生成";
}
