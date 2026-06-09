import { badge, button, el, sectionTitle } from "./dom.js";
import { displayList, displayStatus, displayText } from "./display-labels.js";
import { statusTone } from "./workbench-state.js";

const METRICS = [
  ["source_assets", "素材"],
  ["content_cards", "卡片"],
  ["runs", "运行"],
  ["jobs", "任务"],
  ["feedback_refs", "审片"],
  ["profile_versions", "记忆版本"],
];

export function renderProjectHub(projectHub) {
  const value = projectHub || {};
  const project = value.active_project || {};
  const counts = value.counts || {};
  const jobs = Array.isArray(value.recent_jobs) ? value.recent_jobs : [];
  return el("section", { className: "project-hub-panel" }, [
    sectionTitle("项目总览", displayStatus(value.status || "not_started")),
    el("div", { className: "project-hub-hero" }, [
      el("div", { className: "project-hub-copy" }, [
        badge(displayText(project.project_type || "project"), statusTone(value.status)),
        el("h3", { text: displayText(project.goal || project.project_id, "还没有打开项目") }),
        el("p", { text: displayText(value.summary || "创建或打开项目后继续。") }),
      ]),
      renderNextCommand(value.next_command),
    ]),
    el("div", { className: "project-metric-grid" }, METRICS.map(([key, label]) => renderMetric(label, counts[key]))),
    jobs.length
      ? el("div", { className: "project-job-list" }, jobs.map(renderRecentJob))
      : el("p", { className: "muted", text: "还没有运行任务。" }),
    project.artifact_id ? button("打开项目档案", "open-artifact-ref", "ghost", { artifactId: project.artifact_id }) : null,
    value.non_claims && value.non_claims.length ? el("div", { className: "chips" }, displayList(value.non_claims).map((item) => badge(item, "quiet"))) : null,
  ]);
}

function renderMetric(label, value) {
  return el("div", { className: "project-metric" }, [
    el("span", { text: label }),
    el("strong", { text: String(value || 0) }),
  ]);
}

function renderNextCommand(command) {
  const value = command || {};
  const tone = value.blocked_reason ? "blocked" : statusTone(value.enabled ? "running" : "ready_not_run");
  return el("div", { className: `project-next-command ${tone}` }, [
    badge(displayText(value.view || "Create"), tone),
    el("strong", { text: displayText(value.label || "继续") }),
    value.summary ? el("p", { text: displayText(value.summary) }) : null,
    value.blocked_reason
      ? badge(displayText(value.blocked_reason), "blocked")
      : value.enabled && value.ui_action
        ? button("执行", value.ui_action, "primary", { commandId: value.command_id || "" })
        : el("button", { className: "btn ghost disabled", text: "等待输入", attrs: { disabled: "disabled" } }),
  ]);
}

function renderRecentJob(job) {
  const tone = statusTone(job.status);
  return el("div", { className: `project-job-row ${tone}` }, [
    el("div", {}, [
      el("strong", { text: displayText(job.title || "运行任务") }),
      el("span", { text: displayText(job.action || "runtime_event") }),
    ]),
    badge(displayStatus(job.status || "not_started"), tone),
    job.primary_artifact_id ? button("打开产物", "open-artifact-ref", "ghost", { artifactId: job.primary_artifact_id }) : null,
  ]);
}
