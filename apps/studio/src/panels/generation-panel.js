import { icon } from "../icons.js";
import { el, showModal } from "../overlay.js";
import {
  applyGenerationProfileSettings,
  generationProfile,
  valueForGenerationField,
} from "./generation-panel-profile.js";

export function openGenerationPanel({ store, node, onRun }) {
  const current = store.get().nodes[node?.id] || node;
  if (!current) return null;
  const profile = generationProfile(current);

  const modal = el("div", "modal compact generation-panel");
  const head = el("div", "modal-head generation-panel-head");
  head.appendChild(el("strong", "", "生成设置"));
  head.appendChild(el("small", "", profile.label));
  const closeBtn = el("button", "modal-close");
  closeBtn.innerHTML = icon("x", 15);
  head.appendChild(el("span", "head-spacer"));
  head.appendChild(closeBtn);

  const body = el("div", "modal-body generation-panel-body");
  body.appendChild(nodeSummary(current));
  const promptField = field("提示词", "textarea");
  promptField.input.value = current.prompt || current.content || "";
  promptField.input.rows = 5;

  const settings = el("div", "generation-setting-grid");
  settings.classList.add(`generation-setting-${profile.kind}`);
  settings.classList.add(`generation-setting-count-${profile.fields.length}`);
  const controls = renderProfileSettings(settings, current, profile);

  body.append(promptField.wrap, settings, safeNote(profile));

  const actions = el("div", "modal-actions generation-panel-actions");
  const cancel = el("button", "ghost-btn", "取消");
  const confirm = el("button", "primary-btn", profile.runsGeneration === false ? "保存设置" : "开始生成");
  confirm.innerHTML = profile.runsGeneration === false
    ? `${icon("check", 13)}<span>保存设置</span>`
    : `${icon("play", 13)}<span>开始生成</span>`;
  actions.append(cancel, confirm);
  modal.append(head, body, actions);

  const close = showModal(modal);
  modal.closest(".modal-backdrop")?.classList.add("generation-panel-backdrop");
  positionGenerationPanel(modal, current.id);
  closeBtn.addEventListener("click", close);
  cancel.addEventListener("click", close);
  confirm.addEventListener("click", () => {
    store.set((s) => {
      const target = s.nodes[current.id];
      if (!target) return;
      target.params = target.params || {};
      target.prompt = promptField.input.value.trim();
      applyGenerationProfileSettings(target, profile, controls);
      target.params.generationPanelTouchedAt = new Date().toISOString();
      s.selection = { nodeIds: [target.id], edgeId: null };
    });
    close();
    const fresh = store.get().nodes[current.id];
    if (profile.runsGeneration !== false) onRun?.(fresh);
  });
  setTimeout(() => promptField.input.focus(), 20);
  return close;
}

function renderProfileSettings(settings, node, profile) {
  const controls = {};
  for (const item of profile.fields) {
    if (item.kind === "note") {
      settings.appendChild(inlineNote(item.text));
      continue;
    }
    const control = field(item.label, item.kind, item.options || []);
    if (item.kind === "number") {
      control.input.min = String(item.min ?? 1);
      control.input.max = String(item.max ?? 999);
      control.input.step = String(item.step ?? 1);
    }
    if (item.readonly) {
      control.input.disabled = true;
      control.input.title = item.readonlyReason || "";
    }
    control.input.value = String(valueForGenerationField(node, item));
    settings.appendChild(control.wrap);
    controls[item.key] = control.input;
  }
  return controls;
}

function positionGenerationPanel(modal, nodeId) {
  const nodeEl = document.querySelector(`[data-node-id="${cssEscape(nodeId)}"]`);
  if (!nodeEl) return;
  const nodeRect = nodeEl.getBoundingClientRect();
  const drawerRect = document.getElementById("drawer")?.getBoundingClientRect();
  const inspectorRect = document.getElementById("inspector")?.getBoundingClientRect();
  const margin = 14;
  const width = Math.min(340, Math.max(300, window.innerWidth - 80));
  modal.style.width = `${width}px`;
  modal.style.position = "fixed";
  const leftLimit = drawerRect && drawerRect.width > 80 ? drawerRect.right + margin : margin;
  const rightLimit = inspectorRect && inspectorRect.width > 80 ? inspectorRect.left - margin : window.innerWidth - margin;
  let left = nodeRect.right + margin;
  if (left + width > rightLimit) left = nodeRect.left - width - margin;
  if (left < leftLimit) left = Math.min(Math.max(nodeRect.right + margin, leftLimit), window.innerWidth - width - margin);
  const height = modal.offsetHeight || 420;
  const top = Math.max(70, Math.min(nodeRect.top, window.innerHeight - height - 70));
  modal.style.left = `${Math.round(left)}px`;
  modal.style.top = `${Math.round(top)}px`;
}

function nodeSummary(node) {
  const box = el("section", "generation-node-summary");
  box.innerHTML = [
    `<span class="generation-node-icon">${icon(node.type === "video" ? "video" : node.type === "image" ? "image" : "text", 16)}</span>`,
    `<span><strong>${escapeHtml(node.title || "未命名节点")}</strong><small>${escapeHtml(summaryText(node))}</small></span>`,
  ].join("");
  return box;
}

function safeNote(profile) {
  const note = el("div", "generation-safe-note");
  const parts = [
    profile.runsGeneration === false ? "保存设置不会直接触发真实生成流程。" : "点击开始后才会进入真实生成流程。",
    profile.note,
  ];
  note.textContent = parts.join(" ");
  return note;
}

function inlineNote(text) {
  const note = el("div", "generation-safe-note");
  note.textContent = text;
  return note;
}

function field(label, kind, options = []) {
  const wrap = el("label", "generation-field");
  wrap.appendChild(el("span", "", label));
  let input;
  if (kind === "textarea") input = document.createElement("textarea");
  else if (kind === "select") {
    input = document.createElement("select");
    for (const optionValue of options) {
      const option = document.createElement("option");
      option.value = optionValue;
      option.textContent = optionValue;
      input.appendChild(option);
    }
  } else {
    input = document.createElement("input");
    input.type = kind;
  }
  wrap.appendChild(input);
  return { wrap, input };
}

function summaryText(node) {
  if (node.previewUrl) return "已有预览，可继续生成或复用";
  if (node.result) return String(node.result).replace(/\s+/g, " ").slice(0, 70);
  return "填写提示词后开始生成";
}

function clamp(value, min, max) {
  if (!Number.isFinite(value)) return min;
  return Math.max(min, Math.min(max, value));
}

function cssEscape(value) {
  if (window.CSS?.escape) return window.CSS.escape(String(value));
  return String(value).replace(/["\\]/g, "\\$&");
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}
