import { button, el } from "./dom.js";
import { displayText } from "./display-labels.js";
import { canvasTransformStyle } from "./canvas-interactions.js";
import { renderAddNodeFlow, selectedAddNode } from "./render-studio-add-node-flow.js";
import { renderCanvasTopbar } from "./render-studio-canvas-header.js";
import { renderExecutionScaffold } from "./render-studio-execution-scaffold.js";
import { renderBottomToolbar, renderFloatingPanel } from "./render-studio-panels.js";
import {
  nodeIcon,
  renderAudioVideoStarterFlow,
  renderCharacterStarterFlow,
  renderImageVideoStarterFlow,
  renderScriptStarterFlow,
  renderStarterNodes,
  selectedStarterNode,
} from "./render-studio-starter-flows.js";

export function renderStudioWorkspace(workspace, state) {
  const value = workspace || { canvas: { cards: [] }, counts: {}, side_rail: {}, operations_summary: {} };
  const cards = Array.isArray(value.canvas?.cards) ? value.canvas.cards : [];
  const selectedCardId = selectedStudioCardId(cards, value, state);
  const selected = state.studioAddedNodeKind
    ? selectedAddNode(state.studioAddedNodeKind)
    : state.studioStarterMode ? selectedStarterNode(state.studioStarterKind) : selectedStudioCard(cards, selectedCardId);
  const panel = (state.studioAddedNodeKind || (state.studioStarterMode && ["script", "character", "image", "audio"].includes(state.studioStarterKind))) ? "" : studioPanel(state);
  return el("section", { className: `studio-workspace canvas-v2 libtv-canvas studio-panel-${panel || "none"}` }, [
    renderCanvasTopbar(value, state),
    el("div", { className: "libtv-canvas-stage", dataset: { canvasSurface: "true" } }, [
      renderCanvasHint(cards, state),
      renderNodeLayer(cards, selectedCardId, state),
      renderFloatingPanel(panel, value, selected, state),
    ]),
    renderBottomToolbar(panel, value, state),
  ]);
}

export function selectedStudioCardId(cards, workspace, state) {
  const stateCardId = state && state.selectedCardId;
  if (cards.some((card) => card.card_id === stateCardId)) return stateCardId;
  return workspace.canvas?.selected_card_id || cards[0]?.card_id || "";
}

function selectedStudioCard(cards, selectedCardId) {
  return cards.find((item) => item.card_id === selectedCardId) || cards[0] || {};
}

function studioPanel(state) {
  const allowed = ["add", "assets", "resource", "toolbox", "history", "shortcuts", "help", "inspector", "gate"];
  return allowed.includes(state?.studioPanel) ? state.studioPanel : "";
}

function renderCanvasHint(cards, state) {
  if (state.studioAddedNodeKind) return null;
  if (state.studioStarterMode && ["script", "character", "image", "audio"].includes(state.studioStarterKind)) return null;
  if (cards.length && !state.studioStarterMode) return null;
  return el("div", { className: "libtv-empty-hint" }, [
    el("span", { text: "⌁" }),
    el("strong", { text: "双击画布，自由添加生产节点" }),
  ]);
}

function renderNodeLayer(cards, selectedCardId, state) {
  const attrs = { style: canvasTransformStyle(state) };
  if (state.studioAddedNodeKind) return renderAddNodeFlow(state.studioAddedNodeKind, attrs);
  if (state.studioStarterMode && state.studioStarterKind === "script") return renderScriptStarterFlow(attrs);
  if (state.studioStarterMode && state.studioStarterKind === "character") return renderCharacterStarterFlow(attrs);
  if (state.studioStarterMode && state.studioStarterKind === "image") return renderImageVideoStarterFlow(attrs);
  if (state.studioStarterMode && state.studioStarterKind === "audio") return renderAudioVideoStarterFlow(attrs);
  if (state.studioStarterMode || !cards.length) return renderStarterNodes(attrs, state.studioStarterKind);
  return el("div", { className: "libtv-node-layer libtv-node-layer-execution", dataset: { canvasContent: "true" }, attrs }, [
    ...cards.map((card, index) => renderCanvasNode(card, selectedCardId, index)),
    renderExecutionScaffold(cards, selectedCardId, state),
  ]);
}

function renderCanvasNode(card, selectedCardId, index) {
  const kind = nodeKind(card, index);
  const selected = card.card_id === selectedCardId;
  return el("article", {
    className: `libtv-node libtv-node-${kind} node-pos-${(index % 8) + 1}${selected ? " selected" : ""}`,
    dataset: { cardId: card.card_id },
  }, [
    el("div", { className: "libtv-node-title" }, [
      el("span", { className: "node-icon", text: nodeIcon(kind) }),
      el("strong", { text: displayText(card.title || nodeTitle(kind)) }),
    ]),
    el("div", { className: "libtv-node-preview" }, [
      el("span", { className: "preview-bars", attrs: { "aria-hidden": "true" } }),
      el("p", { text: displayText(card.summary || nodeSummary(kind)) }),
    ]),
    renderNodeTries(kind, card),
    renderNodeFooter(kind, card),
  ]);
}

function renderNodeTries(kind, card) {
  const tries = nodeTries(kind, card).slice(0, 2);
  return el("div", { className: "libtv-node-tries" }, [
    el("span", { text: "尝试：" }),
    ...tries.map((item) => el("button", { text: item, attrs: { type: "button" } })),
  ]);
}

function renderNodeFooter(kind, card) {
  return el("div", { className: "libtv-node-footer" }, [
    el("span", { text: modelLabel(kind) }),
    card.primary_artifact_id ? button("查看证据", "open-artifact-ref", "ghost", { artifactId: card.primary_artifact_id }) : null,
  ]);
}

function nodeKind(card, index) {
  const kind = String(card.kind || "").toLowerCase();
  if (kind.includes("source") || kind.includes("brief")) return "source";
  if (kind.includes("scene")) return "scene";
  if (kind.includes("review") || kind.includes("candidate")) return "review";
  if (kind.includes("memory") || kind.includes("next")) return "memory";
  if (kind.includes("generation") || kind.includes("check")) return "gate";
  return ["brief", "source", "script", "scene", "review", "memory", "gate"][index] || "node";
}

function nodeTitle(kind) {
  const labels = { brief: "项目目标", source: "素材引用", script: "脚本生成器", scene: "分镜节点", review: "审片节点", memory: "项目记忆", gate: "生成能力门" };
  return labels[kind] || "画布节点";
}

function nodeSummary(kind) {
  const labels = {
    brief: "写下内容目标、受众和安全边界。",
    source: "上传或登记素材摘要，前端只接触安全引用。",
    script: "基于剧情、角色和视频参考生成分镜脚本。",
    scene: "组织镜头、提示词、参考和首轮检查。",
    review: "查看候选，记录保留、修改或拒绝。",
    memory: "把已审片偏好作为下一轮候选记忆。",
    gate: "真实生成前检查能力门和阻塞项。",
  };
  return labels[kind] || "继续生产链路。";
}

function nodeTries(kind) {
  const labels = {
    brief: ["自己编写目标", "套用项目模板", "补充平台"],
    source: ["添加素材摘要", "上传参考", "整理素材"],
    script: ["剧本生成分镜脚本", "素材参考生成分镜", "角色生成分镜"],
    scene: ["生成画布草稿", "运行首轮检查", "打开分镜台"],
    review: ["保留方向", "标记修改", "拒绝候选"],
    memory: ["复用风格偏好", "进入下一轮", "查看证据"],
    gate: ["运行预检", "查看阻塞", "等待授权"],
  };
  return labels[kind] || ["继续"];
}

function modelLabel(kind) {
  if (kind === "gate") return "Provider Gate";
  if (kind === "memory") return "Project Memory";
  if (kind === "review") return "Review Room";
  if (kind === "source") return "Safe refs";
  return "AFS Runtime";
}
