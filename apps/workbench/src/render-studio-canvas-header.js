import { el } from "./dom.js";
import { displayStatus, displayText } from "./display-labels.js";

const CANVAS_ITEMS = [
  { id: "canvas-1", label: "画布 1", meta: "当前制作画布" },
  { id: "canvas-2", label: "画布 2", meta: "本地草稿位" },
  { id: "canvas-review", label: "审片画布", meta: "候选对比视图" },
];

export function renderCanvasTopbar(workspace, state) {
  const project = workspace.active_project || {};
  const command = workspace.primary_command || {};
  return el("header", { className: "libtv-topbar" }, [
    el("div", { className: "libtv-project-pill libtv-canvas-header" }, [
      el("span", { className: "libtv-mark", text: "AFS" }),
      renderProjectTitleInput(project, state),
      renderCanvasSwitcher(state),
    ]),
    state.studioCanvasIntent ? renderCanvasIntentStatus(state) : null,
    el("div", { className: "libtv-top-actions" }, [
      (state.studioStarterMode || state.studioAddedNodeKind) ? el("button", {
        className: "btn secondary",
        text: "实际画布",
        dataset: { studioStarter: "close" },
        attrs: { type: "button" },
      }) : null,
      command.enabled && command.view ? el("button", { className: "btn primary", text: displayText(command.label || "继续"), dataset: { view: command.view }, attrs: { type: "button" } }) : null,
      toolButton("gate", `生成能力 ${displayStatus(workspace.provider_status || "ready_not_run")}`, "⚡", false),
    ]),
  ]);
}

function renderProjectTitleInput(project, state) {
  const title = state.studioProjectTitle || displayText(project.title || "未命名项目");
  return el("input", {
    className: "libtv-canvas-title-input",
    attrs: {
      "aria-label": "项目名称",
      "data-studio-title-input": "true",
      autocomplete: "off",
      spellcheck: "false",
      title: displayText(project.goal || "本地画布项目"),
      value: title,
    },
  });
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
      el("small", { text: "仅登记本地画布意图" }),
    ]),
  ]);
}

function renderCanvasIntentStatus(state) {
  return el("div", { className: "libtv-canvas-intent-status" }, [
    el("strong", { text: "本地画布意图已登记" }),
    el("span", { text: canvasIntentLabel(state.studioCanvasIntent) }),
    el("small", { text: "未创建真实画布 · 未启动 provider" }),
  ]);
}

function canvasIntentLabel(intent) {
  const labels = {
    "canvas-1": "切换到画布 1",
    "canvas-2": "切换到画布 2",
    "canvas-review": "切换到审片画布",
    new_canvas: "准备新建画布",
  };
  return labels[intent] || "更新画布工作区";
}

function toolButton(panel, label, icon, active) {
  return el("button", {
    className: `libtv-tool${active ? " active" : ""}`,
    dataset: { studioTool: panel },
    attrs: { type: "button", title: label, "aria-label": label },
  }, [
    el("span", { text: icon }),
    el("small", { text: label }),
  ]);
}
