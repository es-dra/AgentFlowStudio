import { badge, button, el, sectionTitle } from "./dom.js";
import { statusTone } from "./workbench-state.js";

export function renderActivityTimeline(activity) {
  const value = activity || { counts: {}, items: [], non_claims: [] };
  const items = Array.isArray(value.items) ? value.items : [];
  return el("section", { className: "activity-timeline" }, [
    sectionTitle("Activity Timeline", value.status || "not_started"),
    el("p", { className: "card-summary", text: value.summary || "No runtime activity yet." }),
    renderCounts(value.counts || {}),
    items.length
      ? el("div", { className: "activity-list" }, items.map((item) => renderActivityRow(item)))
      : el("p", { className: "muted", text: "Runtime events will appear after deterministic checks or review actions." }),
    value.non_claims && value.non_claims.length
      ? el("div", { className: "chips" }, value.non_claims.map((item) => badge(item, "quiet")))
      : null,
  ]);
}

function renderCounts(counts) {
  return el("div", { className: "activity-counts" }, [
    badge(`${counts.total || 0} events`, counts.total ? "active" : "quiet"),
    badge(`${counts.blocked || 0} blocked`, counts.blocked ? "blocked" : "quiet"),
    badge(`${counts.failed || 0} failed`, counts.failed ? "blocked" : "quiet"),
    badge(`${counts.succeeded || 0} succeeded`, counts.succeeded ? "good" : "quiet"),
  ]);
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
    item.primary_artifact_id
      ? button("Open Artifact", "open-artifact-ref", "ghost", { artifactId: item.primary_artifact_id })
      : null,
  ]);
}
