import { icon } from "./icons.js";
import { el } from "./overlay.js";
import {
  cancelAgentCommand,
  executePendingAgentCommand,
  recordAgentCommandError,
  submitAgentChatMessage,
  undoAgentReceipt,
} from "./agent-chat-lifecycle.js";

export function buildAgentChatPanel({
  session,
  context,
  store,
  collapsed = false,
  mobileOpen = false,
  onToggleCollapse,
  onOpen,
  onRender,
} = {}) {
  const aside = el("aside", `studio-agent-chat${collapsed ? " collapsed" : ""}${mobileOpen ? " mobile-open" : ""}`);
  aside.dataset.contextKey = context?.context_key || "";
  aside.setAttribute("aria-label", "Agent Chat");
  aside.appendChild(panelHeader({ context, collapsed, onToggleCollapse }));
  if (collapsed) return aside;

  const body = el("div", "agent-chat-body");
  body.appendChild(contextStrip(context));
  body.appendChild(messageLog(session));
  if (session?.pendingCommand) body.appendChild(commandPreview({ session, store, onRender }));
  body.appendChild(receiptList({ session, store, onRender }));
  body.appendChild(composer({ session, context, onOpen, onRender }));
  aside.appendChild(body);
  return aside;
}

function panelHeader({ context, collapsed, onToggleCollapse }) {
  const head = el("header", "agent-chat-head");
  const title = el("div", "agent-chat-title");
  title.innerHTML = [
    '<span class="agent-mark">AI</span>',
    "<span>",
    "<strong>Agent Chat</strong>",
    `<small>${escapeHtml(contextLabel(context))}</small>`,
    "</span>",
  ].join("");
  const collapse = el("button", "studio-icon-button");
  collapse.type = "button";
  collapse.setAttribute("aria-label", collapsed ? "展开 Agent Chat" : "收起 Agent Chat");
  collapse.setAttribute("aria-expanded", String(!collapsed));
  collapse.innerHTML = icon(collapsed ? "panel" : "chevronDown", 15);
  collapse.addEventListener("click", () => onToggleCollapse?.());
  head.append(title, collapse);
  return head;
}

function contextStrip(context) {
  const strip = el("dl", "agent-context-strip");
  for (const [label, value] of [
    ["项目", context?.project_name || "未命名项目"],
    ["版本", context?.revision_id || "未保存"],
    ["节点", context?.selected_node_title || context?.selected_node_id || "未选择"],
  ]) {
    strip.append(el("dt", "", label), el("dd", "", value));
  }
  const counts = context?.counts || {};
  strip.append(el("dt", "", "画布"), el("dd", "", `${Number(counts.nodes || 0)} 节点 · ${Number(counts.scenes || 0)} 场景 · ${Number(counts.shots || 0)} 镜头`));
  return strip;
}

function messageLog(session) {
  const log = el("div", "agent-chat-log");
  log.setAttribute("aria-live", "polite");
  for (const message of (session?.messages || []).slice(-8)) {
    const item = el("article", `agent-message ${message.role}${message.tone ? ` ${message.tone}` : ""}`);
    item.append(el("span", "agent-message-role", message.role === "user" ? "我" : "AI"));
    item.append(el("p", "", message.text));
    log.appendChild(item);
  }
  return log;
}

function commandPreview({ session, store, onRender }) {
  const command = session.pendingCommand;
  const preview = el("section", `agent-command-preview ${command.status}`);
  preview.dataset.commandType = command.command_type;
  preview.append(
    el("span", "eyebrow", command.status === "blocked" ? "无法执行" : "命令预览"),
    el("strong", "", command.title || "待确认命令"),
    el("p", "", command.error_message || command.summary || "确认前不会改变画布。"),
  );
  const details = el("dl", "agent-command-details");
  if (command.node_id) details.append(el("dt", "", "目标"), el("dd", "", command.node_id));
  if (command.impact?.node_ids?.length) details.append(el("dt", "", "影响"), el("dd", "", `${command.impact.node_ids.length} 个画布节点`));
  details.append(el("dt", "", "故事板"), el("dd", "", command.impact?.storyboard_write ? "需要确认写入" : "不写入"));
  preview.appendChild(details);
  const actions = el("div", "agent-command-actions");
  if (command.status !== "blocked") {
    const confirm = el("button", "studio-primary-button", "确认执行");
    confirm.type = "button";
    confirm.addEventListener("click", () => {
      try {
        store.set((state) => executePendingAgentCommand(session, state));
      } catch (error) {
        recordAgentCommandError(session, error);
      }
      onRender?.();
    });
    actions.appendChild(confirm);
  }
  const cancel = el("button", "studio-secondary-button", "取消");
  cancel.type = "button";
  cancel.addEventListener("click", () => {
    cancelAgentCommand(session);
    onRender?.();
  });
  actions.appendChild(cancel);
  preview.appendChild(actions);
  return preview;
}

function receiptList({ session, store, onRender }) {
  const receipts = (session?.receipts || []).slice(-3).reverse();
  const wrap = el("section", "agent-receipts");
  wrap.appendChild(el("span", "eyebrow", "执行回执"));
  if (!receipts.length) {
    wrap.appendChild(el("p", "agent-empty-copy", "还没有已确认的命令。"));
    return wrap;
  }
  for (const receipt of receipts) {
    const item = el("article", `agent-receipt ${receipt.status}`);
    item.append(el("strong", "", receipt.status === "undone" ? "已撤销" : "已执行"));
    item.append(el("p", "", receipt.summary));
    if (receipt.undo_available) {
      const undo = el("button", "studio-text-button");
      undo.type = "button";
      undo.innerHTML = `${icon("retry", 13)}撤销`;
      undo.addEventListener("click", () => {
        try {
          store.set((state) => undoAgentReceipt(session, receipt, state));
        } catch (error) {
          recordAgentCommandError(session, error);
        }
        onRender?.();
      });
      item.appendChild(undo);
    }
    wrap.appendChild(item);
  }
  return wrap;
}

function composer({ session, context, onOpen, onRender }) {
  const form = el("form", "agent-chat-composer");
  const input = document.createElement("textarea");
  input.rows = 3;
  input.maxLength = 900;
  input.placeholder = context?.selected_node_id
    ? "发送上下文，或输入 /rename-selected 新名称"
    : "发送上下文，或先在画布选择节点再发命令";
  input.setAttribute("aria-label", "向 Agent Chat 发送消息或命令");
  const send = el("button", "studio-icon-button");
  send.type = "submit";
  send.setAttribute("aria-label", "发送到 Agent Chat");
  send.innerHTML = icon("arrowUp", 16);
  form.append(input, send);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const result = submitAgentChatMessage(session, input.value, context);
    if (result.status !== "empty") input.value = "";
    onOpen?.();
    onRender?.();
  });
  return form;
}

function contextLabel(context) {
  if (context?.selected_node_title) return context.selected_node_title;
  if (context?.section === "storyboard_read_only") return "故事板只读投影";
  return "画布上下文";
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}
