import { statusTone } from "./workbench-state.js";
import { badge, button, el, sectionTitle } from "./dom.js";

function renderMetrics(counts) {
  const value = counts || {};
  return el("div", { className: "memory-facts operations-metrics" }, [
    badge(`${value.jobs || 0} jobs`, value.jobs ? "active" : "quiet"),
    badge(`${value.succeeded || 0} succeeded`, value.succeeded ? "good" : "quiet"),
    badge(`${value.blocked || 0} blocked`, value.blocked ? "blocked" : "quiet"),
    badge(`${value.activities || 0} events`, value.activities ? "ready" : "quiet"),
    badge(`${value.artifact_refs || 0} refs`, value.artifact_refs ? "ready" : "quiet"),
    badge(`${value.provider_blockers || 0} provider blockers`, value.provider_blockers ? "blocked" : "quiet"),
  ]);
}

function renderProviderControls(controls) {
  const value = controls || {};
  const action = el("button", {
    className: `btn ${value.enabled ? "primary" : "secondary"}`,
    text: value.primary_label || "Run provider preflight",
    dataset: { action: value.ui_action || "refresh" },
    attrs: value.enabled ? {} : { disabled: "disabled" },
  });
  return el("div", { className: "operations-controls" }, [
    action,
    badge(value.primary_action || "run_provider_preflight", value.enabled ? "ready" : "quiet"),
    value.blocked_reason ? badge(value.blocked_reason, "blocked") : null,
    value.summary ? el("p", { className: "artifact-note", text: value.summary }) : null,
  ]);
}

function renderProviderGate(providerGate) {
  const value = providerGate || { blockers: [] };
  const blockers = Array.isArray(value.blockers) ? value.blockers : [];
  return el("section", { className: "operations-provider-gate provider-gate" }, [
    sectionTitle("Provider Preflight", value.status || "ready_not_run"),
    el("p", { className: "card-summary", text: value.summary || "Provider preflight has not run." }),
    value.primary_artifact_id ? button("Open Provider Evidence", "open-artifact-ref", "ghost", { artifactId: value.primary_artifact_id }) : null,
    blockers.length
      ? el("div", { className: "chips" }, blockers.map((item) => badge(item.message || item.blocker_id, "blocked")))
      : el("p", { className: "muted", text: "No provider blockers recorded in this projection." }),
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
    el("div", { className: "card-head" }, [el("h3", { text: job.title || "Runtime job" }), badge(job.status, statusTone(job.status))]),
    renderProgress(job),
    el("div", { className: "job-meta" }, [
      job.action ? el("code", { text: job.action }) : null,
      job.job_id ? el("code", { text: job.job_id }) : null,
      badge(`${job.artifact_count || 0} artifacts`, job.artifact_count ? "ready" : "quiet"),
    ]),
    job.guidance ? el("p", { className: "artifact-note", text: job.guidance }) : null,
    job.primary_artifact_id ? button("Open Result", "open-artifact-ref", "ghost", { artifactId: job.primary_artifact_id }) : null,
  ]);
}

function renderJobs(operations) {
  const jobs = Array.isArray(operations.job_queue) ? operations.job_queue : [];
  return jobs.length
    ? el("div", { className: "operations-job-list job-list" }, jobs.map((item) => renderJob(item, operations.selected_job_id)))
    : el("p", { className: "muted", text: "Run a first check or provider preflight to create jobs." });
}

function renderActivity(activity) {
  const items = Array.isArray(activity) ? activity : [];
  return items.length
    ? el("div", { className: "operations-activity-list activity-list" }, items.map(renderActivityRow))
    : el("p", { className: "muted", text: "Runtime events will appear after deterministic checks or review actions." });
}

function renderActivityRow(item) {
  return el("article", { className: "activity-row" }, [
    el("div", { className: "activity-main" }, [
      el("strong", { text: item.title || "Runtime event" }),
      badge(item.status || "not_started", statusTone(item.status)),
    ]),
    el("div", { className: "activity-meta" }, [
      item.action ? el("code", { text: item.action }) : null,
      item.job_id ? el("code", { text: item.job_id }) : null,
      badge(`${item.artifact_count || 0} refs`, item.artifact_count ? "ready" : "quiet"),
    ]),
    item.primary_artifact_id ? button("Open Artifact", "open-artifact-ref", "ghost", { artifactId: item.primary_artifact_id }) : null,
  ]);
}

export function renderOperationsWorkspace(operationsWorkspace) {
  const value = operationsWorkspace || { counts: {}, job_queue: [], latest_activity: [], non_claims: [] };
  const polling = value.polling || {};
  return el("section", { className: "operations-workspace" }, [
    sectionTitle("Operations Workspace", value.status || "not_started"),
    el("p", { className: "card-summary", text: value.summary || "Runtime jobs and provider preflight appear here." }),
    renderMetrics(value.counts),
    renderProviderControls(value.provider_controls),
    renderProviderGate(value.provider_gate),
    el("div", { className: "chips" }, [
      badge(polling.enabled ? "auto refresh" : "manual refresh", polling.enabled ? "ready" : "quiet"),
      badge(`${Math.round((polling.suggested_interval_ms || 5000) / 1000)}s`, "quiet"),
    ]),
    renderJobs(value),
    renderActivity(value.latest_activity),
    value.non_claims && value.non_claims.length
      ? el("div", { className: "chips" }, value.non_claims.map((item) => badge(item, "quiet")))
      : null,
  ]);
}
