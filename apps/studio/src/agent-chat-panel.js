import { icon } from "./icons.js";
import { el } from "./overlay.js";
import {
  cancelAgentCommand,
  executePendingAgentCommand,
  executePendingAgentCommandWithRuntime,
  recordAgentCommandError,
  submitAgentChatMessageWithRuntime,
  undoAgentReceipt,
  undoAgentReceiptWithRuntime,
} from "./agent-chat-lifecycle.js";
import { bindStableTextInputLifecycle } from "./stable-text-input.js";
import {
  applyEmbeddedCreativeAction,
  cancelEmbeddedCreativeAction,
  clearEmbeddedCreativeAction,
  editEmbeddedCreativePreview,
  startEmbeddedCreativeAction,
} from "./embedded-creative-actions.js";
import {
  screenplayCandidateSummary,
  shotPlanSummary,
  taskPhaseLabel,
  taskStateLabel,
} from "./creative-task-contract.js";

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
  aside.setAttribute("aria-label", "AI 创作搭档");
  if (!collapsed) aside.appendChild(resizeHandle(onResizeStart));
  aside.appendChild(panelHeader({ context, collapsed, onToggleCollapse }));
  if (collapsed) return aside;

  const body = el("div", "agent-chat-body");
  body.appendChild(contextStrip(context));
  const taskReview = currentTaskReview({ store, runtime, onRender });
  if (taskReview) body.appendChild(taskReview);
  body.appendChild(messageLog(session));
  if (session?.conversationRequest) body.appendChild(conversationStatus({ session, context, runtime, onRender }));
  if (session?.pendingCommand) body.appendChild(commandPreview({ session, store, runtime, onRender }));
  body.appendChild(receiptList({ session, store, runtime, onRender }));
  body.appendChild(composer({ session, context, runtime, onOpen, onRender }));
  aside.appendChild(body);
  return aside;
}

function panelHeader({ context, collapsed, onToggleCollapse }) {
  const head = el("header", "agent-chat-head");
  const title = el("div", "agent-chat-title");
  title.innerHTML = [
    '<span class="agent-mark">AI</span>',
    "<span>",
    "<strong>AI 创作搭档</strong>",
    `<small>${escapeHtml(contextLabel(context))}</small>`,
    "</span>",
  ].join("");
  const collapse = el("button", "studio-icon-button");
  collapse.type = "button";
  collapse.setAttribute("aria-label", collapsed ? "展开 AI 创作搭档" : "收起 AI 创作搭档");
  collapse.setAttribute("aria-expanded", String(!collapsed));
  collapse.innerHTML = icon(collapsed ? "panel" : "chevronDown", 15);
  collapse.addEventListener("click", () => onToggleCollapse?.());
  head.append(title, collapse);
  return head;
}

function contextStrip(context) {
  const strip = el("section", "agent-context-strip");
  strip.appendChild(el("span", "agent-context-chip", context?.selected_node_title ? `当前：${context.selected_node_title}` : "当前：画布"));
  strip.appendChild(el("span", "agent-context-chip", context?.script_revision_id ? "剧本可追溯" : "可从任意节点开始"));
  if (context?.selected_edge_id) {
    strip.appendChild(
      el("span", "agent-context-chip", `连线：${context.selected_edge_from_title || "上游"} → ${context.selected_edge_to_title || "下游"}`),
    );
  }
  const counts = context?.counts || {};
  if (context?.media_operations) {
    const media = context.media_operations;
    strip.appendChild(el("span", "agent-context-chip", "媒体制作"));
    strip.appendChild(el("span", "agent-context-chip", `${Number(media.ready_shot_count || 0)}/${Number(media.shot_count || 0)} 镜头可审`));
    strip.appendChild(el("span", "agent-context-chip", `估算 $${Number(media.estimated_cost_usd || 0).toFixed(2)}`));
  } else {
    strip.appendChild(el("span", "agent-context-chip", `${Number(counts.nodes || 0)} 节点 · ${Number(counts.scenes || 0)} 场景 · ${Number(counts.shots || 0)} 镜头`));
  }
  strip.appendChild(contextDetails(context));
  return strip;
}

function contextDetails(context) {
  const details = el("details", "agent-context-details");
  details.appendChild(el("summary", "", "上下文范围"));
  const list = el("dl", "");
  for (const [label, value] of [
    ["项目", context?.project_name || "未命名项目"],
    ["节点", context?.selected_node_title || "未选择"],
    ["画布", `${Number(context?.counts?.nodes || 0)} 节点 · ${Number(context?.counts?.scenes || 0)} 场景 · ${Number(context?.counts?.shots || 0)} 镜头`],
  ]) {
    list.append(el("dt", "", label), el("dd", "", value));
  }
  if (context?.media_operations) {
    list.append(el("dt", "", "计划"), el("dd", "", "从已确认脚本、分镜和资产 Bible 只读投影"));
  } else if (context?.production_graph_version) {
    list.append(el("dt", "", "制作序列"), el("dd", "", `版本 ${Number(context.production_graph_version)} · ${Number(context?.counts?.graph_tasks || 0)} 项任务 · ${Number(context?.counts?.graph_pending_reviews || 0)} 项待审`));
  } else {
    list.append(el("dt", "", "计划"), el("dd", "", planStateLabel(context?.production_plan_state)));
  }
  details.appendChild(list);
  details.appendChild(evidenceDetails("开发证据", [
    ["project_id", context?.project_id],
    ["script_revision_id", context?.script_revision_id],
    ["source_digest", context?.script_source_digest],
    ["production_plan_id", context?.production_plan_id],
    ["production_plan_digest", context?.production_plan_digest],
    ["production_graph_version", context?.production_graph_version],
    ["production_graph_digest", context?.production_graph_digest],
    ["selected_node_id", context?.selected_node_id],
  ]));
  return details;
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
  if (command.edge_id || command.node_id || command.target_asset_id || command.target_shot_id || command.target_chunk_id) details.append(el("dt", "", "目标"), el("dd", "", humanCommandTarget(command)));
  if (command.impact?.node_ids?.length) details.append(el("dt", "", "影响"), el("dd", "", `${command.impact.node_ids.length} 个画布节点`));
  if (command.tool_label) details.append(el("dt", "", "工具"), el("dd", "", command.tool_label));
  if (command.provider_label) details.append(el("dt", "", "能力"), el("dd", "", command.provider_label));
  if (command.cost_label) details.append(el("dt", "", "费用"), el("dd", "", command.cost_label));
  details.append(el("dt", "", "故事板"), el("dd", "", command.impact?.storyboard_write ? "确认后同步" : "不写入"));
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
    ["edge_id", command.edge_id],
  ]));
  const actions = el("div", "agent-command-actions");
  if (command.status !== "blocked") {
    const confirm = el("button", "studio-primary-button", command.status === "executing" ? "执行中" : "确认执行");
    confirm.type = "button";
    confirm.disabled = command.status === "executing";
    confirm.addEventListener("click", () => {
      command.status = "executing";
      onRender?.();
      const run = command.command_type === "start_embedded_creative_action"
        ? executeEmbeddedCreativeCommand({ session, store, runtime, command })
        : command.execution_mode === "runtime"
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

async function executeEmbeddedCreativeCommand({ session, store, runtime, command }) {
  const node = store?.get?.()?.nodes?.[command.node_id];
  if (!node) throw new Error("selected node no longer exists");
  session.pendingCommand = null;
  pushAssistantMessage(session, `已在「${node.title || "当前节点"}」打开${command.action_type === "shot_breakdown" ? "分镜拆解" : "剧本化修订"}任务；结果会在当前任务区审阅，确认前不改动画布。`);
  await startEmbeddedCreativeAction(store, runtime, node, command.action_type, { mode: command.mode });
  return null;
}

function currentTaskReview({ store, runtime, onRender }) {
  const state = store?.get?.() || {};
  const node = selectedCanvasNode(state);
  const action = node?.params?.embeddedCreativeAction;
  if (!node || !action || action.status === "cancelled") return null;
  const task = action.creative_task || {};
  const wrap = el("section", `agent-current-task-review ${action.status || "idle"}`);
  wrap.dataset.nodeId = node.id;
  wrap.dataset.creativeAction = action.action_type || "script_revision";
  const header = el("header", "agent-current-task-head");
  header.append(
    el("span", "eyebrow", "当前任务"),
    el("strong", "", currentTaskTitle(action)),
    el("small", "", taskStatePhaseSummary(task, action)),
  );
  wrap.appendChild(header);
  wrap.appendChild(taskPhaseList(task, action));
  if (action.status === "running") {
    wrap.appendChild(el("p", "agent-current-task-copy", action.message || "正在生成可审查预览；确认前不会写入画布。"));
  } else if (action.status === "preview") {
    wrap.appendChild(action.action_type === "shot_breakdown" ? shotPlanReview(action.preview?.shot_plan) : screenplayReview(action, store, node));
  } else if (action.status === "unavailable") {
    wrap.appendChild(el("p", "agent-current-task-error", action.message || action.error || "任务失败；当前节点没有改变。"));
  } else if (action.status === "applied") {
    wrap.appendChild(el("p", "agent-current-task-copy", action.message || "结果已应用；可以使用画布撤销恢复。"));
    if (action.applied_subgraph) wrap.appendChild(appliedSubgraphSummary(action.applied_subgraph));
  }
  wrap.appendChild(currentTaskActions({ store, runtime, node, action, onRender }));
  const evidence = currentTaskEvidence(action);
  if (evidence) wrap.appendChild(evidence);
  return wrap;
}

function currentTaskActions({ store, runtime, node, action, onRender }) {
  const row = el("div", "agent-current-task-actions");
  if (action.status === "preview") {
    row.appendChild(taskButton("应用", "studio-primary-button", () => {
      applyEmbeddedCreativeAction(store, node.id);
      onRender?.();
    }));
    row.appendChild(taskButton("取消", "studio-secondary-button", () => {
      cancelEmbeddedCreativeAction(store, node.id);
      onRender?.();
    }));
  }
  if (["preview", "unavailable"].includes(action.status)) {
    row.appendChild(taskButton("重新生成", "studio-secondary-button", () => {
      void startEmbeddedCreativeAction(store, runtime, store.get().nodes[node.id], action.action_type, { mode: action.mode })
        .finally(() => onRender?.());
      onRender?.();
    }));
  }
  if (["running"].includes(action.status)) {
    row.appendChild(taskButton("取消任务", "studio-secondary-button", () => {
      cancelEmbeddedCreativeAction(store, node.id);
      onRender?.();
    }));
  }
  if (["unavailable", "applied"].includes(action.status)) {
    row.appendChild(taskButton("收起", "studio-text-button", () => {
      clearEmbeddedCreativeAction(store, node.id);
      onRender?.();
    }));
  }
  return row;
}

function screenplayReview(action, store, node) {
  const preview = action.preview || {};
  const wrap = el("div", "agent-screenplay-review");
  const summary = screenplayCandidateSummary(preview.screenplay_candidate);
  wrap.appendChild(el("p", "agent-current-task-copy", `${summary.title} · ${summary.scene_count} 场 · ${summary.character_count} 名角色 · ${summary.dialogue_blocks} 段对白。`));
  const diff = el("div", "agent-current-diff");
  const before = el("section", "");
  before.append(el("strong", "", "原文"), el("p", "", excerpt(action.source_text, 360)));
  diff.appendChild(before);
  const after = el("section", "");
  after.appendChild(el("strong", "", "可编辑预览"));
  const editor = document.createElement("textarea");
  editor.className = "agent-current-task-editor";
  editor.value = preview.revised_text || "";
  editor.maxLength = 40000;
  editor.rows = 10;
  editor.setAttribute("aria-label", "编辑剧本化预览文本");
  editor.addEventListener("input", () => editEmbeddedCreativePreview(store, node.id, editor.value));
  after.appendChild(editor);
  diff.appendChild(after);
  wrap.appendChild(diff);
  if (preview.screenplay_candidate) wrap.appendChild(screenplayCandidateView(preview.screenplay_candidate));
  if (Array.isArray(preview.change_summary) && preview.change_summary.length) wrap.appendChild(simpleList("改动摘要", preview.change_summary));
  if (preview.rationale) wrap.appendChild(el("p", "agent-current-task-copy", preview.rationale));
  return wrap;
}

function screenplayCandidateView(candidate) {
  const details = el("details", "agent-screenplay-candidate");
  details.open = true;
  details.appendChild(el("summary", "", "专业剧本结构"));
  const meta = el("dl", "agent-current-task-kv");
  for (const [label, value] of [
    ["标题", candidate?.title],
    ["版本", candidate?.version_label],
    ["梗概", candidate?.logline],
  ]) {
    if (value) meta.append(el("dt", "", label), el("dd", "", value));
  }
  details.appendChild(meta);
  const characters = Array.isArray(candidate?.characters) ? candidate.characters : [];
  if (characters.length) {
    details.appendChild(simpleList("角色目标/冲突/变化", characters.slice(0, 6).map((item) => `${item.name || "角色"}：目标 ${item.goal || "待定"}；冲突 ${item.conflict || "待定"}；变化 ${item.change || "待定"}`)));
  }
  const sceneWrap = el("div", "agent-screenplay-scenes");
  (candidate?.scenes || []).slice(0, 5).forEach((scene, index) => {
    const section = el("section", "");
    section.appendChild(el("strong", "", `${index + 1}. ${scene.heading || scene.title || "场景"}`));
    section.appendChild(el("p", "", `${scene.location || "地点待定"} · ${scene.time_of_day || "时间待定"} · ${scene.purpose || "场景目的待定"}`));
    const blocks = el("ol", "");
    (scene.blocks || []).slice(0, 8).forEach((block) => {
      blocks.appendChild(el("li", "", `${screenplayBlockLabel(block.type)}${block.character ? ` / ${block.character}` : ""}：${block.text || ""}`));
    });
    section.appendChild(blocks);
    sceneWrap.appendChild(section);
  });
  details.appendChild(sceneWrap);
  return details;
}

function shotPlanReview(plan) {
  const summary = shotPlanSummary(plan);
  const wrap = el("div", "agent-shot-plan-review");
  wrap.appendChild(el("p", "agent-current-task-copy", `${summary.scene_count} 场 · ${summary.shot_count} 镜头 · 约 ${Math.round(summary.estimated_duration_sec)} 秒。应用后会创建可见候选分镜子图，确认前不写成最终制作事实。`));
  const details = el("details", "agent-shot-plan-candidate");
  details.open = true;
  details.appendChild(el("summary", "", "分镜候选结构"));
  (plan?.scenes || []).slice(0, 5).forEach((scene, sceneIndex) => {
    const section = el("section", "");
    section.appendChild(el("strong", "", `${sceneIndex + 1}. ${scene.title || "场景"}`));
    section.appendChild(el("p", "", scene.purpose || "叙事目的待定"));
    const list = el("ol", "");
    (scene.shots || []).slice(0, 10).forEach((shot) => {
      list.appendChild(el("li", "", `${shot.title || "镜头"} · ${Number(shot.duration_sec || 0)} 秒 · ${shot.shot_size || "景别"} · ${shot.camera_angle || "机位"} · ${shot.movement || "运动"} · ${shot.sound || "声音"} · ${shot.transition || "转场"} · ${shot.narrative_purpose || "目的"}`));
    });
    section.appendChild(list);
    details.appendChild(section);
  });
  wrap.appendChild(details);
  return wrap;
}

function appliedSubgraphSummary(subgraph) {
  return simpleList("已创建候选子图", [
    `${Number(subgraph.scene_count || 0)} 场 · ${Number(subgraph.shot_count || 0)} 镜头`,
    `新增节点 ${Number(subgraph.created_node_ids?.length || 0)} 个，连线 ${Number(subgraph.created_edge_ids?.length || 0)} 条`,
  ]);
}

function taskPhaseList(task, action) {
  const phases = Array.isArray(task?.completed_phases) ? task.completed_phases : [];
  const current = task?.phase || action?.status || "";
  const line = el("ol", "agent-task-phases");
  const ordered = [];
  for (const phase of [...phases, current].filter(Boolean)) {
    if (!ordered.includes(phase)) ordered.push(phase);
  }
  for (const phase of ordered.slice(-5)) {
    const item = el("li", phase === current ? "current" : "", taskPhaseLabel(phase));
    line.appendChild(item);
  }
  return line;
}

function taskStatePhaseSummary(task, action) {
  const stateLabel = taskStateLabel(task);
  const phaseLabel = taskPhaseLabel(task?.phase || action?.status || "queued");
  return stateLabel === phaseLabel ? stateLabel : `${stateLabel} · ${phaseLabel}`;
}

function currentTaskEvidence(action) {
  const lineage = action.provider_lineage || {};
  if (!lineage.provider_calls_started && !action.latency_ms && !action.creative_task?.task_id) return null;
  return evidenceDetails("高级证据", [
    ["task_id", action.creative_task?.task_id],
    ["node_version", action.creative_task?.node_version],
    ["request_id", lineage.request_id],
    ["model_surface", lineage.model_surface],
    ["schema_digest", lineage.structured_output_schema_digest],
    ["latency_ms", action.latency_ms ? Math.round(Number(action.latency_ms)) : ""],
    ["cost_usd", `$${Number(action.cost_usd || 0).toFixed(4)}`],
  ]);
}

function selectedCanvasNode(state) {
  const nodeId = state?.selection?.nodeIds?.[0];
  return nodeId ? state.nodes?.[nodeId] || null : null;
}

function currentTaskTitle(action) {
  if (action.action_type === "shot_breakdown") return "动态分镜候选审阅";
  return action.mode === "professional_screenplay" ? "剧本化扩写审阅" : "节点修订审阅";
}

function taskButton(label, className, onClick) {
  const button = el("button", className, label);
  button.type = "button";
  button.addEventListener("click", onClick);
  return button;
}

function simpleList(title, items) {
  const wrap = el("section", "agent-current-list");
  wrap.appendChild(el("strong", "", title));
  const list = el("ul", "");
  for (const item of (items || []).filter(Boolean)) list.appendChild(el("li", "", item));
  wrap.appendChild(list);
  return wrap;
}

function screenplayBlockLabel(type) {
  return {
    action: "动作",
    character: "人物",
    dialogue: "对白",
    parenthetical: "括注",
    transition: "转场",
  }[String(type || "")] || "文本";
}

function excerpt(value, limit) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.length > limit ? `${text.slice(0, limit - 1)}…` : text || "空";
}

function pushAssistantMessage(session, text) {
  const messages = Array.isArray(session.messages) ? session.messages : [];
  messages.push({ role: "assistant", text });
  session.messages = messages.slice(-28);
}

function receiptList({ session, store, runtime, onRender }) {
  const receipts = (session?.receipts || []).slice(-3).reverse();
  const wrap = el("details", "agent-receipts");
  if (!receipts.length) {
    return wrap;
  }
  wrap.appendChild(el("summary", "", `活动记录 · ${receipts.length} 条执行回执`));
  for (const receipt of receipts) {
    const item = el("article", `agent-receipt ${receipt.status}`);
    if (receipt.command_type) item.dataset.commandType = String(receipt.command_type);
    if (receipt.receipt_id) item.dataset.receiptId = String(receipt.receipt_id);
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

function conversationStatus({ session, context, runtime, onRender }) {
  const state = session.conversationRequest || {};
  const wrap = el("section", `agent-conversation-status ${state.status || ""}`);
  const label = state.status === "loading" ? "正在回答" : state.status === "failed" ? "模型不可用" : "对话状态";
  wrap.append(el("span", "eyebrow", label), el("p", "", state.message || "AI 创作搭档会通过运行服务回答，不会改动画布。"));
  const actions = el("div", "agent-command-actions");
  if (state.status === "loading" && typeof state.cancel === "function") {
    const cancel = el("button", "studio-secondary-button", "取消回答");
    cancel.type = "button";
    cancel.addEventListener("click", () => {
      state.cancel();
      state.status = "cancelled";
      state.message = "已取消这次回答；如果服务端已经开始处理，结果不会写入画布。";
      onRender?.();
    });
    actions.appendChild(cancel);
  }
  if (["failed", "unavailable", "cancelled"].includes(state.status) && state.lastMessage) {
    const retry = el("button", "studio-secondary-button", "重试");
    retry.type = "button";
    retry.addEventListener("click", () => {
      submitAgentChatMessageWithRuntime(session, state.lastMessage, context, runtime)
        .finally(() => onRender?.());
      onRender?.();
    });
    actions.appendChild(retry);
  }
  if (actions.childNodes.length) wrap.appendChild(actions);
  return wrap;
}

function composer({ session, context, runtime, onOpen, onRender }) {
  const form = el("form", "agent-chat-composer");
  const input = document.createElement("textarea");
  input.rows = 3;
  input.maxLength = 12000;
  input.placeholder = context?.selected_node_id
    ? "可以提问，也可以预览修改当前节点、连线或媒体动作"
    : "打招呼、提问，或从想法、剧本、参考图、图片、视频开始";
  input.setAttribute("aria-label", "向 AI 创作搭档发送消息或命令");
  input.value = session?.draftMessage || "";
  input.addEventListener("input", () => {
    session.draftMessage = input.value;
  });
  bindStableTextInputLifecycle(input, () => {}, {
    onKeyDown: (event) => {
      if (event.key !== "Enter" || event.isComposing) return;
      if (event.shiftKey) return;
      if (!event.ctrlKey && !event.metaKey) {
        event.preventDefault();
        form.requestSubmit();
        return;
      }
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    },
  });
  const send = el("button", "studio-icon-button");
  send.type = "submit";
  send.setAttribute("aria-label", "发送到 AI 创作搭档");
  send.innerHTML = icon("arrowUp", 16);
  const syncDraft = () => {
    session.draftMessage = input.value || session.draftMessage || "";
  };
  send.addEventListener("pointerdown", syncDraft);
  send.addEventListener("click", syncDraft);
  form.append(input, send);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const message = input.value || session.draftMessage || "";
    const run = submitAgentChatMessageWithRuntime(session, message, context, runtime)
      .then((result) => {
        if (result.status === "empty") return;
        onOpen?.();
      })
      .finally(() => onRender?.());
    if (message.trim()) {
      session.draftMessage = "";
      input.value = "";
    }
    onOpen?.();
    onRender?.();
    return run;
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
  handle.setAttribute("aria-label", "调整 AI 创作搭档宽度");
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
  if (command.edge_id) return "当前连线";
  if (command.target_chunk_id) return "当前分段";
  if (command.target_shot_id) return "当前镜头";
  if (command.target_asset_id) return "当前资产";
  if (command.node_id) return "当前节点";
  return "当前上下文";
}

function relationLabel(relation) {
  return {
    generation: "生成/派生",
    reference: "参考",
    director: "导演控制",
    fork: "分支",
    sequence: "叙事顺序",
    proposed: "待确认建议",
  }[String(relation || "generation")] || String(relation || "生成/派生").replace(/_/g, " ");
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
