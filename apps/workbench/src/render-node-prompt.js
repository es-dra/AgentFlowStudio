import { button, el } from "./dom.js";
import { renderPromptOptimizerPanel } from "./render-prompt-optimizer.js";

export function renderNodePrompt(state, options = {}) {
  const placeholder = options.placeholder || "描述你想要生成的内容";
  const rows = String(options.rows || 3);
  const value = options.value ?? state.inspectorPrompt ?? "";
  const surface = options.surface || "node";
  const generation = state.nodeGenerationStatus?.[surface] || {};
  const isGenerating = state.pendingNodeGenerationSurface === surface && state.loading;
  const status = isGenerating ? "generating" : generation.status || "idle";
  const promptReady = Boolean(String(value || "").trim());
  const actionLabel = status === "generating"
    ? "生成中"
    : status === "complete"
      ? "重新预览"
      : options.primaryAction || "生成";
  return el("section", { className: `node-prompt-box is-${status} ${options.className || ""}`.trim() }, [
    el("div", { className: "node-prompt-head" }, [
      el("span", { text: options.label || "提示词" }),
      button("优化", "optimize-current-prompt", "ghost", { promptSurface: surface }),
    ]),
    textArea(options, rows, placeholder, value),
    renderNodeGenerationStatus(status, generation, promptReady),
    renderPromptOptimizerPanel(state),
    el("div", { className: "node-prompt-actions" }, [
      el("button", {
        text: actionLabel,
        dataset: { action: "run-node-generation-preview", nodeGenerateSurface: surface },
        attrs: actionButtonAttrs(status, promptReady),
      }),
      el("small", { text: statusNote(status, generation, options.note) }),
    ]),
  ]);
}

function renderNodeGenerationStatus(status, generation, promptReady) {
  return el("div", { className: "node-prompt-status", attrs: { "data-node-generation-status": status } }, [
    el("span", { className: "node-status-chip", text: statusLabel(status) }),
    el("span", { className: "node-status-copy", text: statusMessage(status, generation, promptReady) }),
    el("span", { className: "node-prompt-progress", attrs: { "aria-hidden": "true" } }),
  ]);
}

function textArea(options, rows, placeholder, value) {
  const node = el("textarea", {
    className: "node-prompt-input",
    attrs: {
      id: options.id || "inspector-prompt",
      rows,
      spellcheck: "false",
      placeholder,
      "data-node-prompt-input": options.surface || "node",
    },
  });
  node.value = value;
  return node;
}

function actionButtonAttrs(status, promptReady) {
  const attrs = { type: "button" };
  if (status === "generating" || !promptReady) attrs.disabled = "disabled";
  return attrs;
}

function statusLabel(status) {
  if (status === "generating") return "生成中";
  if (status === "complete") return "本地预览";
  if (status === "error") return "待补充";
  return "准备就绪";
}

function statusMessage(status, generation, promptReady) {
  if (!promptReady) return "输入提示词后可预览节点输出";
  if (status === "generating") return "正在组织提示词和节点上下文";
  if (generation?.message) return generation.message;
  return "已应用项目风格，可先做本地预览";
}

function statusNote(status, generation, fallback) {
  if (status === "generating") return "正在生成节点预览，不会启动远程模型。";
  if (generation?.message) return generation.message;
  return fallback || "填好提示词后，可先预览节点输出。";
}
