import { promptPlaceholder } from "./nodes.js";
import { showModal, el } from "./overlay.js";
import { openOptimizer } from "./optimizer.js";
import { icon } from "./icons.js";
import { flashTooltip, updateNode } from "./prompt-bar-actions.js";

export function openExpandEditor(store, runtime, node) {
  const wrap = el("div", "prompt-expand");
  const textarea = document.createElement("textarea");
  textarea.value = store.get().nodes[node.id]?.prompt || "";
  textarea.placeholder = promptPlaceholder(node.type, node.params.spec?.mode);
  textarea.addEventListener("input", () => updateNode(store, node.id, (n) => { n.prompt = textarea.value; }));

  const row = el("div", "bar-row");
  const optimizeBtn = el("button", "bar-tool optimize-btn");
  optimizeBtn.innerHTML = `${icon("sparkles", 14)}<span>优化</span>`;
  optimizeBtn.addEventListener("click", () => {
    if (!textarea.value.trim()) { flashTooltip(optimizeBtn, "先输入提示词"); return; }
    openOptimizer(store, runtime, node.id, optimizeBtn, textarea);
  });

  const closeBtn = el("button", "bar-tool");
  closeBtn.innerHTML = `${icon("shrink", 14)}<span>收起</span>`;
  row.appendChild(optimizeBtn);
  row.appendChild(el("span", "row-spacer"));
  row.appendChild(closeBtn);
  wrap.appendChild(textarea);
  wrap.appendChild(row);

  const close = showModal(wrap);
  closeBtn.addEventListener("click", close);
  textarea.focus();
}
