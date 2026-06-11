import { badge, button, el, textareaField } from "./dom.js";
import { buildPromptOptimization } from "./prompt-optimizer-knowledge.js";

export function renderPromptOptimizerPanel(state) {
  if (!state.promptOptimizationOpen) return null;
  const result = state.promptOptimizationResult || buildPromptOptimization(state.inspectorPrompt, {
    style: state.inspectorStyleDirection,
  });
  const localFallback = result.optimization_source === "local_rule_fallback";
  return el("section", { className: "prompt-optimizer-panel prompt-optimizer-popover" }, [
    el("header", {}, [
      el("div", {}, [
        el("strong", { text: "提示词优化" }),
        el("span", { text: "已按影视结构优化" }),
      ]),
      el("button", { text: "×", dataset: { promptOptimizer: "close" }, attrs: { type: "button", title: "关闭" } }),
    ]),
    el("div", { className: "prompt-status-row" }, [
      localFallback ? badge("已用本地优化", "quiet") : badge("已完成优化", "active"),
      badge("已结合当前项目风格", "active"),
      badge("已参考角色/场景设定", "quiet"),
    ]),
    textareaField("原始描述", "prompt-optimizer-source", result.source_prompt, { rows: "3", readonly: "readonly" }),
    textareaField("专业提示词", "prompt-optimizer-result", result.optimized_prompt, { rows: "6", readonly: "readonly" }),
    el("div", { className: "prompt-section-grid" }, (result.prompt_sections || []).map(renderPromptSection)),
    el("div", { className: "prompt-action-row" }, [
      button("替换当前输入", "replace-current-prompt", "secondary"),
      button("追加到当前输入", "append-current-prompt", "secondary"),
      button("复制", "copy-optimized-prompt", "secondary"),
      button("应用到节点", "apply-optimized-to-node", "primary"),
    ]),
  ]);
}

function renderPromptSection(section) {
  return el("article", { className: "prompt-section-card" }, [
    el("strong", { text: section.title }),
    el("p", { text: section.text }),
  ]);
}
