import { statusTone } from "./workbench-state.js";
import { badge, button, el, sectionTitle } from "./dom.js";
import { displayList, displayStatus, displayText } from "./display-labels.js";

function renderMetrics(counts) {
  const value = counts || {};
  return el("div", { className: "memory-facts operations-metrics" }, [
    badge(`${value.jobs || 0} 个任务`, value.jobs ? "active" : "quiet"),
    badge(`${value.succeeded || 0} 已完成`, value.succeeded ? "good" : "quiet"),
    badge(`${value.blocked || 0} 阻塞`, value.blocked ? "blocked" : "quiet"),
    badge(`${value.activities || 0} 个事件`, value.activities ? "ready" : "quiet"),
    badge(`${value.artifact_refs || 0} 份证据`, value.artifact_refs ? "ready" : "quiet"),
    badge(`${value.provider_blockers || 0} 个预检阻塞`, value.provider_blockers ? "blocked" : "quiet"),
  ]);
}

function renderProviderControls(controls) {
  const value = controls || {};
  const action = el("button", {
    className: `btn ${value.enabled ? "primary" : "secondary"}`,
    text: displayText(value.primary_label, "生成能力预检"),
    dataset: { action: value.ui_action || "refresh" },
    attrs: value.enabled ? {} : { disabled: "disabled" },
  });
  return el("div", { className: "operations-controls" }, [
    action,
    badge(value.enabled ? "可执行" : "等待输入", value.enabled ? "ready" : "quiet"),
    value.blocked_reason ? badge(displayText(value.blocked_reason), "blocked") : null,
    value.summary ? el("p", { className: "artifact-note", text: displayText(value.summary) }) : null,
    value.requires_input?.length ? el("div", { className: "chips" }, displayList(value.requires_input).map((item) => badge(item, "quiet"))) : null,
  ]);
}

function renderProviderGate(providerGate) {
  const value = providerGate || { blockers: [] };
  const blockers = Array.isArray(value.blockers) ? value.blockers : [];
  return el("section", { className: "operations-provider-gate provider-gate" }, [
    sectionTitle("生成能力预检", displayStatus(value.status || "ready_not_run")),
    el("p", { className: "card-summary", text: displayText(value.summary || "Provider preflight has not run.") }),
    value.primary_artifact_id ? button("查看预检证据", "open-artifact-ref", "ghost", { artifactId: value.primary_artifact_id }) : null,
    blockers.length
      ? el("div", { className: "provider-blockers" }, blockers.map(renderProviderBlocker))
      : el("p", { className: "muted", text: "当前没有生成能力预检阻塞。" }),
  ]);
}

function renderProviderBlocker(item) {
  return el("div", { className: "provider-blocker" }, [
    badge(displayText(item.blocker_id || "blocked"), "blocked"),
    el("span", { text: displayText(item.message || item.blocker_id || "blocked") }),
    item.user_action ? el("small", { text: displayText(item.user_action) }) : null,
  ]);
}

function renderProgress(job) {
  return el("div", { className: "job-progress" }, [
    el("div", { className: "job-progress-bar", attrs: { style: `width: ${Math.max(0, Math.min(100, job.percent || 0))}%` } }),
  ]);
}

function renderJob(job, selectedJobId) {
  const selected = job.job_id && job.job_id === selectedJobId;
  return el("article", { className: `job-card${selected ? " selected" : ""}` }, [
    el("div", { className: "card-head" }, [
      el("h3", { text: displayText(job.title, "运行任务") }),
      badge(displayStatus(job.status), statusTone(job.status)),
    ]),
    renderProgress(job),
    el("div", { className: "job-meta" }, [
      badge(displayText(job.stage || job.action || "runtime_event"), "quiet"),
      badge(`${job.artifact_count || 0} 份证据`, job.artifact_count ? "ready" : "quiet"),
    ]),
    job.guidance ? el("p", { className: "artifact-note", text: displayText(job.guidance) }) : null,
    job.primary_artifact_id ? button("查看结果证据", "open-artifact-ref", "ghost", { artifactId: job.primary_artifact_id }) : null,
  ]);
}

function renderJobs(operations) {
  const jobs = Array.isArray(operations.job_queue) ? operations.job_queue : [];
  return jobs.length
    ? el("div", { className: "operations-job-list job-list" }, jobs.map((item) => renderJob(item, operations.selected_job_id)))
    : el("p", { className: "muted", text: "运行首轮检查或生成能力预检后，这里会出现任务。" });
}

function renderActivity(activity) {
  const items = Array.isArray(activity) ? activity : [];
  return items.length
    ? el("div", { className: "operations-activity-list activity-list" }, items.map(renderActivityRow))
    : el("p", { className: "muted", text: "确定性检查或审片操作后，这里会出现运行事件。" });
}

function renderActivityRow(item) {
  return el("article", { className: "activity-row" }, [
    el("div", { className: "activity-main" }, [
      el("strong", { text: displayText(item.title, "运行事件") }),
      badge(displayStatus(item.status || "not_started"), statusTone(item.status)),
    ]),
    el("div", { className: "activity-meta" }, [
      badge(displayText(item.action || "runtime_event"), "quiet"),
      badge(`${item.artifact_count || 0} 份证据`, item.artifact_count ? "ready" : "quiet"),
    ]),
    item.primary_artifact_id ? button("查看运行证据", "open-artifact-ref", "ghost", { artifactId: item.primary_artifact_id }) : null,
  ]);
}

export function renderOperationsWorkspace(operationsWorkspace) {
  const value = operationsWorkspace || { counts: {}, job_queue: [], latest_activity: [], non_claims: [] };
  const polling = value.polling || {};
  return el("section", { className: "operations-workspace" }, [
    sectionTitle("任务中心", displayStatus(value.status || "not_started")),
    el("p", { className: "card-summary", text: displayText(value.summary || "Runtime jobs and provider preflight appear here.") }),
    renderMetrics(value.counts),
    renderProviderControls(value.provider_controls),
    renderProviderGate(value.provider_gate),
    el("div", { className: "chips" }, [
      badge(polling.enabled ? "自动刷新" : "手动刷新", polling.enabled ? "ready" : "quiet"),
      badge(`${Math.round((polling.suggested_interval_ms || 5000) / 1000)} 秒`, "quiet"),
    ]),
    renderJobs(value),
    renderActivity(value.latest_activity),
    value.non_claims && value.non_claims.length
      ? el("div", { className: "chips" }, displayList(value.non_claims).map((item) => badge(item, "quiet")))
      : null,
  ]);
}
