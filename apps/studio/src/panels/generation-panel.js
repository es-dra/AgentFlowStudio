import { icon } from "../icons.js";
import { el, showModal } from "../overlay.js";

export function openGenerationPanel({ store, node, onRun }) {
  const current = store.get().nodes[node?.id] || node;
  if (!current) return null;

  const modal = el("div", "modal compact generation-panel");
  const head = el("div", "modal-head generation-panel-head");
  head.appendChild(el("strong", "", "生成设置"));
  head.appendChild(el("small", "", typeLabel(current)));
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
  const ratio = field("画幅", "select", ["9:16", "16:9", "1:1", "4:3", "3:4"]);
  ratio.input.value = current.params?.spec?.ratio || current.params?.previewAspectRatio || "9:16";
  const candidates = field("张数", "number");
  candidates.input.min = "1";
  candidates.input.max = "4";
  candidates.input.step = "1";
  candidates.input.value = String(current.params?.candidateCount || 1);
  const motion = field("镜头", "input");
  motion.input.value = current.params?.motion || "";
  settings.append(ratio.wrap, candidates.wrap, motion.wrap);

  body.append(promptField.wrap, settings, safeNote(current));

  const actions = el("div", "modal-actions generation-panel-actions");
  const cancel = el("button", "ghost-btn", "取消");
  const confirm = el("button", "primary-btn", "开始生成");
  confirm.innerHTML = `${icon("play", 13)}<span>开始生成</span>`;
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
      target.prompt = promptField.input.value.trim();
      target.params.spec = { ...(target.params.spec || {}), ratio: ratio.input.value };
      target.params.candidateCount = clamp(Number(candidates.input.value || 1), 1, 4);
      target.params.motion = motion.input.value.trim();
      target.params.generationPanelTouchedAt = new Date().toISOString();
      s.selection = { nodeIds: [target.id], edgeId: null };
    });
    close();
    const fresh = store.get().nodes[current.id];
    onRun?.(fresh);
  });
  setTimeout(() => promptField.input.focus(), 20);
  return close;
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

function safeNote(node) {
  const note = el("div", "generation-safe-note");
  const parts = [
    "点击开始后才会进入真实生成流程。",
    node.type === "video" ? "视频任务可能产生费用，请确认首帧和运动描述。" : "候选数量越多，等待时间和费用可能越高。",
  ];
  note.textContent = parts.join(" ");
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

function typeLabel(node) {
  if (node.type === "video") return "视频生成";
  if (node.type === "image") return "图片生成";
  if (node.type === "script") return "脚本生成";
  return "创作节点";
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
