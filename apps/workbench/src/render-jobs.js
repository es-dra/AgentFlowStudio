import { statusTone } from "./workbench-state.js";
import { badge, button, el, sectionTitle } from "./dom.js";

function renderProgress(job) {
  return el("div", { className: "job-progress" }, [
    el("div", { className: "job-progress-bar", attrs: { style: `width: ${Math.max(0, Math.min(100, job.percent))}%` } }),
  ]);
}

function renderJob(job) {
  return el("article", { className: "job-card" }, [
    el("div", { className: "card-head" }, [el("h3", { text: job.title }), badge(job.status, statusTone(job.status))]),
    renderProgress(job),
    el("div", { className: "job-meta" }, [
      job.job_id ? el("code", { text: job.job_id }) : null,
      badge(`${job.artifact_count || 0} artifacts`, job.artifact_count ? "ready" : "quiet"),
    ]),
    job.guidance ? el("p", { className: "artifact-note", text: job.guidance }) : null,
    job.primary_artifact_id ? button("Open Result", "open-artifact-ref", "ghost", { artifactId: job.primary_artifact_id }) : null,
  ]);
}

function renderCounts(counts) {
  const value = counts || {};
  return el("div", { className: "memory-facts" }, [
    badge(`${value.total || 0} total`, value.total ? "ready" : "quiet"),
    badge(`${value.succeeded || 0} succeeded`, value.succeeded ? "good" : "quiet"),
    badge(`${value.blocked || 0} blocked`, value.blocked ? "blocked" : "quiet"),
    badge(`${value.failed || 0} failed`, value.failed ? "blocked" : "quiet"),
  ]);
}

export function renderJobCenter(jobCenter) {
  const value = jobCenter || { items: [], counts: {} };
  const items = Array.isArray(value.items) ? value.items : [];
  const polling = value.polling || {};
  return el("section", { className: "job-center" }, [
    sectionTitle("Job Center", value.status || "not_started"),
    el("p", { className: "card-summary", text: value.summary || "No runtime jobs yet." }),
    renderCounts(value.counts),
    el("div", { className: "chips" }, [
      badge(polling.enabled ? "auto refresh" : "manual refresh", polling.enabled ? "ready" : "quiet"),
      badge(`${Math.round((polling.suggested_interval_ms || 5000) / 1000)}s`, "quiet"),
    ]),
    items.length
      ? el("div", { className: "job-list" }, items.map(renderJob))
      : el("p", { className: "muted", text: "Run a first check or provider preflight to create jobs." }),
    button("Refresh Jobs", "refresh", "secondary"),
  ]);
}
