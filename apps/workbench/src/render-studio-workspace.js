import { badge, button, el, sectionTitle } from "./dom.js";
import { renderStudioCanvas, renderStudioFilmstrip, selectedStudioCardId, selectedStudioInspector } from "./render-studio-canvas.js";
import { renderStudioInspector } from "./render-studio-inspector.js";
import { renderStudioSideRail } from "./render-studio-side-rail.js";
import { displayStatus, displayText } from "./display-labels.js";
import { statusTone } from "./workbench-state.js";

export function renderStudioWorkspace(workspace, state) {
  const value = workspace || { canvas: { cards: [] }, counts: {}, side_rail: {}, operations_summary: {} };
  const cards = Array.isArray(value.canvas?.cards) ? value.canvas.cards : [];
  const selectedCardId = selectedStudioCardId(cards, value, state);
  const inspector = selectedStudioInspector(cards, selectedCardId, value.inspector || {});
  return el("section", { className: "studio-workspace" }, [
    renderCommandStrip(value),
    el("div", { className: "studio-layout" }, [
      renderStudioSideRail(value.side_rail || {}, value.counts || {}),
      renderStudioCanvas(value, selectedCardId),
      renderStudioInspector(inspector, state),
    ]),
    renderStudioFilmstrip(value.filmstrip || []),
    renderOperationsSummary(value.operations_summary || {}, value.provider_status),
  ]);
}

function renderCommandStrip(workspace) {
  const command = workspace.primary_command || {};
  const counts = workspace.counts || {};
  const canRunHere = command.ui_action && command.enabled && (!command.view || command.view === "Create");
  const canOpenView = command.enabled && command.view && command.view !== "Create" && !command.blocked_reason;
  return el("div", { className: "studio-command-strip" }, [
    el("div", { className: "studio-project-lockup" }, [
      el("span", { text: "创作工作区" }),
      el("strong", { text: displayText(workspace.active_project?.goal || workspace.active_project?.project_id, "打开项目") }),
      el("small", { text: displayText(workspace.summary || "安全内容制作工作区。") }),
    ]),
    el("div", { className: "studio-strip-metrics" }, [
      badge(displayStatus(workspace.status || "not_started"), statusTone(workspace.status)),
      badge(`${counts.canvas_cards || 0} 张卡片`, counts.canvas_cards ? "ready" : "quiet"),
      badge(`${counts.review_candidates || 0} 个审片候选`, counts.review_candidates ? "active" : "quiet"),
      badge(`Provider ${displayStatus(workspace.provider_status || "ready_not_run")}`, workspace.provider_status === "blocked" ? "blocked" : "quiet"),
    ]),
    canRunHere
      ? button(displayText(command.label || "Continue", "继续"), command.ui_action, "primary")
      : canOpenView
        ? el("button", { className: "btn ghost", text: commandLabel(command), dataset: { view: command.view } })
        : el("button", { className: "btn ghost disabled", text: commandLabel(command), attrs: { disabled: "disabled" } }),
  ]);
}

function commandLabel(command) {
  if (command.blocked_reason) return displayText(command.blocked_reason);
  if (command.view && command.view !== "Create") return `打开 ${displayText(command.view)} 继续`;
  return displayText(command.label || "继续");
}


function renderOperationsSummary(summary, providerStatus) {
  const counts = summary.counts || {};
  return el("div", { className: "studio-ops-summary" }, [
    sectionTitle("运行摘要", displayStatus(summary.status || "not_started")),
    el("div", { className: "studio-strip-metrics" }, [
      badge(`${counts.jobs || 0} 个任务`, counts.jobs ? "ready" : "quiet"),
      badge(`${counts.blocked || 0} 个阻塞`, counts.blocked ? "blocked" : "quiet"),
      badge(`Provider ${displayStatus(providerStatus || "ready_not_run")}`, providerStatus === "blocked" ? "blocked" : "quiet"),
    ]),
    summary.primary_artifact_id ? button("打开 Provider 产物", "open-artifact-ref", "ghost", { artifactId: summary.primary_artifact_id }) : null,
  ]);
}
