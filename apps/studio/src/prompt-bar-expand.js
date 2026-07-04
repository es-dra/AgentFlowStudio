import { promptPlaceholder } from "./nodes.js";
import { showModal, el } from "./overlay.js";
import { openOptimizer } from "./optimizer.js";
import { icon } from "./icons.js";
import { flashTooltip, updateNode } from "./prompt-bar-actions.js";
import { assetCardPromptPlaceholder, assetCardUserAdjustmentText } from "./asset-card-image-prompts.js";
import { buildUserAssetCardRevisionState } from "./asset-revision-references.js";

export function openExpandEditor(store, runtime, node) {
  const wrap = el("div", "prompt-expand");
  const textarea = document.createElement("textarea");
  const fresh = store.get().nodes[node.id] || node;
  textarea.value = expandedPromptValue(fresh);
  textarea.placeholder = expandedPromptPlaceholder(fresh);
  textarea.addEventListener("input", () => updateNode(store, node.id, (n) => {
    applyExpandedPromptValue(n, textarea.value);
  }, { history: false }));

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

function expandedPromptValue(node) {
  if (node?.params?.assetCardDraft) return assetCardUserAdjustmentText(node);
  return node?.prompt || node?.content || "";
}

function expandedPromptPlaceholder(node) {
  if (node?.params?.assetCardDraft) {
    return assetCardPromptPlaceholder(node.params.assetCardDraft.asset_type);
  }
  return promptPlaceholder(node?.type, node?.params?.spec?.mode);
}

function applyExpandedPromptValue(node, value) {
  node.prompt = value;
  if (node.params?.assetCardDraft) {
    node.params.assetCardDraft.user_edited_text = value;
    node.params.assetCardDraft.updated_by_user = Boolean(value.trim());
    if (value.trim()) {
      node.params.assetCardRevision = buildUserAssetCardRevisionState(node, node.params.assetCardDraft, value);
    } else if (usesPromptBarAssetCardRevision(node.params.assetCardRevision)) {
      delete node.params.assetCardRevision;
    }
  } else if (node.type === "text" || node.type === "script") {
    node.content = value;
  }
  if (node.params) delete node.params.lastOptimizedPromptPlain;
}

function usesPromptBarAssetCardRevision(revision) {
  return Array.isArray(revision?.changed_fields)
    && revision.changed_fields.some((item) => item?.field === "user_instruction");
}
