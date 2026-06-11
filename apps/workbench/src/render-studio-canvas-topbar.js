import { el } from "./dom.js";
import { displayText } from "./display-labels.js";

const CANVAS_ITEMS = [
  { id: "canvas-1", label: "画布 1", meta: "当前创作画布" },
  { id: "canvas-2", label: "画布 2", meta: "本地草稿画布" },
  { id: "canvas-review", label: "审看片段", meta: "候选片段对比" },
];

export function renderCanvasTopbar(workspace = {}, state = {}) {
  const project = workspace.active_project || {};
  const title = state.studioProjectTitle || displayText(project.title || "未命名项目");
  return el("header", { className: "canvas-topbar" }, [
    el("div", { className: "canvas-title libtv-canvas-header" }, [
      el("span", { className: "libtv-mark", text: "AFS" }),
      el("input", {
        className: "libtv-canvas-title-input",
        attrs: {
          "aria-label": "项目名称",
          "data-studio-title-input": "true",
          autocomplete: "off",
          spellcheck: "false",
          title: displayText(project.goal || "本地画布项目"),
          value: title,
        },
      }),
      renderCanvasSwitcher(state),
      state.studioCanvasIntent ? renderCanvasIntentStatus(state) : null,
    ]),
    el("div", { className: "canvas-top-actions" }, [
      (state.studioStarterMode || state.studioAddedNodeKind || state.studioResourceMode) ? el("button", {
        className: "btn secondary",
        text: "返回画布",
        dataset: { view: "Create", studioStarter: "close" },
        attrs: { type: "button" },
      }) : null,
      topButton("-", "缩小画布", { canvasAction: "zoom-out" }),
      topButton(`${Math.round((state.canvasZoom || 1) * 100)}%`, "重置画布", { canvasAction: "zoom-reset" }),
      topButton("+", "放大画布", { canvasAction: "zoom-in" }),
      el("button", { className: "btn secondary", text: "资产库", dataset: { view: "Assets" }, attrs: { type: "button" } }),
    ]),
  ]);
}

function renderCanvasSwitcher(state) {
  const activeCanvas = CANVAS_ITEMS.find((item) => item.id === state.studioActiveCanvasId) || CANVAS_ITEMS[0];
  return el("div", { className: "libtv-canvas-switcher" }, [
    el("button", {
      className: "libtv-canvas-select",
      text: activeCanvas.label,
      attrs: { type: "button", "aria-label": "画布选择", "data-studio-canvas-menu": "toggle" },
    }),
    state.studioCanvasMenuOpen ? renderCanvasMenu(activeCanvas) : null,
  ]);
}

function renderCanvasMenu(activeCanvas) {
  return el("div", { className: "libtv-canvas-menu" }, [
    ...CANVAS_ITEMS.map((item) => el("button", {
      className: item.id === activeCanvas.id ? "active" : "",
      attrs: { type: "button", "data-studio-canvas-id": item.id },
    }, [
      el("strong", { text: item.label }),
      el("small", { text: item.meta }),
    ])),
    el("button", {
      className: "libtv-canvas-new",
      attrs: { type: "button", "data-studio-canvas-action": "new_canvas" },
    }, [
      el("strong", { text: "新建画布" }),
      el("small", { text: "创建新的创作空间" }),
    ]),
  ]);
}

function renderCanvasIntentStatus(state) {
  return el("div", { className: "libtv-canvas-intent-status" }, [
    el("strong", { text: "画布已更新" }),
    el("span", { text: canvasIntentLabel(state.studioCanvasIntent) }),
  ]);
}

function canvasIntentLabel(intent) {
  const labels = {
    "canvas-1": "切换到画布 1",
    "canvas-2": "切换到画布 2",
    "canvas-review": "切换到审看片段",
    new_canvas: "准备新建画布",
  };
  return labels[intent] || "更新画布工作区";
}

function topButton(text, title, dataset) {
  return el("button", {
    className: "zoom-chip",
    text,
    dataset,
    attrs: { type: "button", title, "aria-label": title },
  });
}
