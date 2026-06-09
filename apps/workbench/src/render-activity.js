import { badge, button, el, sectionTitle } from "./dom.js";
import { displayStatus, displayText } from "./display-labels.js";
import { statusTone } from "./workbench-state.js";

export function renderActivityTimeline(activity) {
  const value = activity || { counts: {}, items: [], non_claims: [] };
  const items = Array.isArray(value.items) ? value.items : [];
  return el("section", { className: "activity-timeline" }, [
    sectionTitle("运行记录", displayStatus(value.status || "not_started")),
    el("p", { className: "card-summary", text: displayText(value.summary || "No runtime activity yet.") }),
    renderCounts(value.counts || {}),
    items.length
      ? el("div", { className: "activity-list" }, items.map((item) => renderActivityRow(item)))
      : el("p", { className: "muted", text: "确定性检查或审片操作后，这里会出现运行事件。" }),
    value.non_claims && value.non_claims.length
      ? el("div", { className: "chips" }, value.non_claims.map((item) => badge(displayText(item), "quiet")))
      : null,
  ]);
}

function renderCounts(counts) {
  return el("div", { className: "activity-counts" }, [
    badge(`${counts.total || 0} 个事件`, counts.total ? "active" : "quiet"),
    badge(`${counts.blocked || 0} 个阻塞`, counts.blocked ? "blocked" : "quiet"),
    badge(`${counts.failed || 0} 个失败`, counts.failed ? "blocked" : "quiet"),
    badge(`${counts.succeeded || 0} 个完成`, counts.succeeded ? "good" : "quiet"),
  ]);
}

function renderActivityRow(item) {
  return el("article", { className: "activity-row" }, [
    el("div", { className: "activity-main" }, [
      el("strong", { text: displayText(item.title || "Runtime event") }),
      badge(displayStatus(item.status || "not_started"), statusTone(item.status)),
    ]),
    el("div", { className: "activity-meta" }, [
      item.action ? badge(displayText(item.action), "quiet") : null,
      item.job_id ? badge("运行引用", "quiet") : null,
      badge(`${item.artifact_count || 0} 份证据`, item.artifact_count ? "ready" : "quiet"),
    ]),
    item.primary_artifact_id
      ? button("查看运行证据", "open-artifact-ref", "ghost", { artifactId: item.primary_artifact_id })
      : null,
  ]);
}
