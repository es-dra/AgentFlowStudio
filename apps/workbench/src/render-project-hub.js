import { badge, button, el, sectionTitle } from "./dom.js";
import { statusTone } from "./workbench-state.js";

const METRICS = [
  ["source_assets", "Sources"],
  ["content_cards", "Cards"],
  ["runs", "Runs"],
  ["jobs", "Jobs"],
  ["feedback_refs", "Reviews"],
  ["profile_versions", "Profiles"],
];

export function renderProjectHub(projectHub) {
  const value = projectHub || {};
  const project = value.active_project || {};
  const counts = value.counts || {};
  const jobs = Array.isArray(value.recent_jobs) ? value.recent_jobs : [];
  return el("section", { className: "project-hub-panel" }, [
    sectionTitle("Project Hub", value.status || "not_started"),
    el("div", { className: "project-hub-hero" }, [
      el("div", { className: "project-hub-copy" }, [
        badge(project.project_type || "project", statusTone(value.status)),
        el("h3", { text: project.project_id || "No project loaded" }),
        el("p", { text: project.goal || value.summary || "Open a project to continue." }),
      ]),
      renderNextCommand(value.next_command),
    ]),
    el("div", { className: "project-metric-grid" }, METRICS.map(([key, label]) => renderMetric(label, counts[key]))),
    jobs.length
      ? el("div", { className: "project-job-list" }, jobs.map(renderRecentJob))
      : el("p", { className: "muted", text: "No runtime jobs yet." }),
    project.artifact_id ? button("Open Manifest", "open-artifact-ref", "ghost", { artifactId: project.artifact_id }) : null,
    value.non_claims && value.non_claims.length ? el("div", { className: "chips" }, value.non_claims.map((item) => badge(item, "quiet"))) : null,
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
    badge(value.view || "Create", tone),
    el("strong", { text: value.label || "Continue" }),
    value.summary ? el("p", { text: value.summary }) : null,
    value.blocked_reason
      ? badge(value.blocked_reason, "blocked")
      : value.enabled && value.ui_action
        ? button("Run", value.ui_action, "primary", { commandId: value.command_id || "" })
        : el("button", { className: "btn ghost disabled", text: "Pending", attrs: { disabled: "disabled" } }),
  ]);
}

function renderRecentJob(job) {
  const tone = statusTone(job.status);
  return el("div", { className: `project-job-row ${tone}` }, [
    el("div", {}, [
      el("strong", { text: job.title || "Runtime job" }),
      el("span", { text: job.action || "runtime_event" }),
    ]),
    badge(job.status || "not_started", tone),
    job.primary_artifact_id ? button("Open Artifact", "open-artifact-ref", "ghost", { artifactId: job.primary_artifact_id }) : null,
  ]);
}
