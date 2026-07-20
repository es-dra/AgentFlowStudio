import { icon } from "./icons.js";
import { el } from "./overlay.js";
import {
  cancelAgentCommand,
  executePendingAgentCommand,
  executePendingAgentCommandWithRuntime,
  recordAgentCommandError,
  submitAgentChatMessage,
  undoAgentReceipt,
  undoAgentReceiptWithRuntime,
} from "./agent-chat-lifecycle.js";
import { bindStableTextInputLifecycle } from "./stable-text-input.js";

export function buildAgentChatPanel({
  session,
  context,
  store,
  runtime = null,
  collapsed = false,
  mobileOpen = false,
  onToggleCollapse,
  onResizeStart,
  onOpen,
  onRender,
} = {}) {
  const aside = el("aside", `studio-agent-chat${collapsed ? " collapsed" : ""}${mobileOpen ? " mobile-open" : ""}`);
  aside.dataset.contextKey = context?.context_key || "";
  aside.setAttribute("aria-label", "Agent Chat");
  if (!collapsed) aside.appendChild(resizeHandle(onResizeStart));
  aside.appendChild(panelHeader({ context, collapsed, onToggleCollapse }));
  if (collapsed) return aside;

  const body = el("div", "agent-chat-body");
  body.appendChild(contextStrip(context));
  body.appendChild(messageLog(session));
  if (session?.pendingCommand) body.appendChild(commandPreview({ session, store, runtime, onRender }));
  body.appendChild(receiptList({ session, store, runtime, onRender }));
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
    ["版本", context?.script_revision_id ? "已绑定剧本版本" : "未创建剧本版本"],
    ["节点", context?.selected_node_title || "未选择"],
  ]) {
    strip.append(el("dt", "", label), el("dd", "", value));
  }
  const counts = context?.counts || {};
  strip.append(el("dt", "", "画布"), el("dd", "", `${Number(counts.nodes || 0)} 节点 · ${Number(counts.scenes || 0)} 场景 · ${Number(counts.shots || 0)} 镜头`));
  if (context?.production_graph_version) {
    strip.append(el("dt", "", "制作序列"), el("dd", "", `版本 ${Number(context.production_graph_version)} · ${Number(counts.graph_tasks || 0)} 项任务 · ${Number(counts.graph_pending_reviews || 0)} 项待审`));
  } else {
    strip.append(el("dt", "", "计划"), el("dd", "", planStateLabel(context?.production_plan_state)));
  }
  strip.appendChild(evidenceDetails("上下文证据", [
    ["project_id", context?.project_id],
    ["script_revision_id", context?.script_revision_id],
    ["source_digest", context?.script_source_digest],
    ["production_plan_id", context?.production_plan_id],
    ["production_plan_digest", context?.production_plan_digest],
    ["production_graph_version", context?.production_graph_version],
    ["production_graph_digest", context?.production_graph_digest],
    ["selected_node_id", context?.selected_node_id],
  ]));
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

function commandPreview({ session, store, runtime, onRender }) {
  const command = session.pendingCommand;
  const preview = el("section", `agent-command-preview ${command.status}`);
  preview.dataset.commandType = command.command_type;
  preview.append(
    el("span", "eyebrow", command.status === "blocked" ? "无法执行" : "命令预览"),
    el("strong", "", command.title || "待确认命令"),
    el("p", "", command.error_message || command.summary || "确认前不会改变画布。"),
  );
  const details = el("dl", "agent-command-details");
  if (command.node_id || command.target_asset_id || command.target_shot_id || command.target_chunk_id) details.append(el("dt", "", "目标"), el("dd", "", humanCommandTarget(command)));
  if (command.impact?.node_ids?.length) details.append(el("dt", "", "影响"), el("dd", "", `${command.impact.node_ids.length} 个画布节点`));
  details.append(el("dt", "", "故事板"), el("dd", "", command.impact?.storyboard_write ? "需要确认写入" : "不写入"));
  preview.appendChild(details);
  if (command.preview_diff) preview.appendChild(diffPreview(command.preview_diff));
  preview.appendChild(evidenceDetails("查看证据/开发详情", [
    ["command_id", command.command_id],
    ["command_type", command.command_type],
    ["raw_command_text", command.raw_command_text],
    ["schema_version", command.schema_version],
    ["node_id", command.node_id],
    ["revision_id", command.revision_id || command.script_revision_id],
    ["source_digest", command.source_digest],
    ["plan_digest", command.plan_digest],
    ["graph_version", command.graph_version],
    ["graph_digest", command.graph_digest],
  ]));
  const actions = el("div", "agent-command-actions");
  if (command.status !== "blocked") {
    const confirm = el("button", "studio-primary-button", command.status === "executing" ? "执行中" : "确认执行");
    confirm.type = "button";
    confirm.disabled = command.status === "executing";
    confirm.addEventListener("click", () => {
      command.status = "executing";
      onRender?.();
      const run = command.execution_mode === "runtime"
        ? executePendingAgentCommandWithRuntime(session, store, runtime)
        : Promise.resolve().then(() => {
          store.set((state) => executePendingAgentCommand(session, state));
        });
      run.catch((error) => {
        command.status = "preview";
        recordAgentCommandError(session, error);
      }).finally(() => onRender?.());
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

function receiptList({ session, store, runtime, onRender }) {
  const receipts = (session?.receipts || []).slice(-3).reverse();
  const wrap = el("section", "agent-receipts");
  if (!receipts.length) {
    return wrap;
  }
  wrap.appendChild(el("span", "eyebrow", "执行回执"));
  for (const receipt of receipts) {
    const item = el("article", `agent-receipt ${receipt.status}`);
    item.append(el("strong", "", receipt.status === "undone" ? "已撤销" : "已执行"));
    item.append(el("p", "", receipt.summary));
    if (receipt.recovery_available && !receipt.undo_available) {
      item.appendChild(el("small", "agent-recovery-hint", "如遇版本冲突，刷新制作图后可安全重试；原记录不会被覆盖。"));
    }
    if (receipt.undo_available) {
      const undo = el("button", "studio-text-button");
      undo.type = "button";
      undo.innerHTML = `${icon("retry", 13)}撤销`;
      undo.addEventListener("click", () => {
        undo.disabled = true;
        const run = receipt.execution_mode === "runtime"
          ? undoAgentReceiptWithRuntime(session, receipt, store, runtime)
          : Promise.resolve().then(() => {
            store.set((state) => undoAgentReceipt(session, receipt, state));
          });
        run.catch((error) => {
          undo.disabled = false;
          recordAgentCommandError(session, error);
        }).finally(() => onRender?.());
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
  input.maxLength = 12000;
  input.placeholder = context?.selected_node_id
    ? "描述你想怎么调整当前节点或镜头"
    : "输入想法、剧本要求或下一步计划";
  input.setAttribute("aria-label", "向 Agent Chat 发送消息或命令");
  bindStableTextInputLifecycle(input, () => {}, {
    onKeyDown: (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
        event.preventDefault();
        form.requestSubmit();
      }
    },
  });
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

function resizeHandle(onResizeStart) {
  const handle = el("div", "agent-resize-handle");
  handle.setAttribute("role", "separator");
  handle.setAttribute("aria-label", "调整 Agent Chat 宽度");
  handle.setAttribute("aria-orientation", "vertical");
  handle.addEventListener("pointerdown", (event) => onResizeStart?.(event));
  return handle;
}

function planStateLabel(value) {
  const state = String(value || "").trim();
  if (!state || state === "planning_required") return "待规划";
  if (state === "pending_capability") return "等待能力确认";
  if (state === "planned") return "已规划";
  if (state === "blocked") return "有阻断";
  return state.replace(/_/g, " ");
}

function humanCommandTarget(command) {
  if (command.target_chunk_id) return "当前分段";
  if (command.target_shot_id) return "当前镜头";
  if (command.target_asset_id) return "当前资产";
  if (command.node_id) return "当前节点";
  return "当前上下文";
}

function diffPreview(diff) {
  const wrap = el("section", "agent-diff-preview");
  wrap.appendChild(el("strong", "", "修订预览"));
  const before = el("p", "", `原文 ${Number(diff.before_chars || 0)} 字：${diff.before_excerpt || "空"}`);
  const after = el("p", "", `修订 ${Number(diff.after_chars || 0)} 字：${diff.after_excerpt || "空"}`);
  wrap.append(before, after);
  return wrap;
}

function evidenceDetails(title, entries) {
  const details = el("details", "agent-evidence-details");
  details.appendChild(el("summary", "", title));
  const list = el("dl", "");
  for (const [label, value] of entries) {
    if (!value) continue;
    list.append(el("dt", "", label), el("dd", "", String(value)));
  }
  if (!list.children.length) list.appendChild(el("p", "", "暂无开发详情。"));
  details.appendChild(list);
  return details;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}
