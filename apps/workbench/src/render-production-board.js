import { badge, button, el, sectionTitle } from "./dom.js";
import { statusTone } from "./workbench-state.js";

export function renderProductionBoard(board) {
  const value = board || { lanes: [], non_claims: [] };
  const lanes = Array.isArray(value.lanes) ? value.lanes : [];
  return el("section", { className: "production-board" }, [
    sectionTitle("Production Board", value.status || "not_started"),
    el("p", { className: "card-summary", text: value.summary || "No production flow yet." }),
    lanes.length ? el("div", { className: "production-lanes" }, lanes.map(renderLane)) : el("p", { className: "muted", text: "Open a project to see the production flow." }),
    value.current_action_label ? badge(`Next: ${value.current_action_label}`, "active") : null,
    value.non_claims && value.non_claims.length ? el("div", { className: "chips" }, value.non_claims.map((item) => badge(item, "quiet"))) : null,
  ]);
}

function renderLane(lane) {
  const tone = statusTone(lane.status);
  return el("article", { className: `production-lane ${tone}` }, [
    el("div", { className: "production-lane-head" }, [
      el("strong", { text: lane.label || "Stage" }),
      badge(lane.status || "not_started", tone),
    ]),
    el("p", { className: "card-summary", text: lane.summary || lane.action_label || "Continue." }),
    el("div", { className: "production-lane-meta" }, [
      lane.action ? el("code", { text: lane.action }) : null,
      badge(`${lane.artifact_count || 0} refs`, lane.artifact_count ? "ready" : "quiet"),
    ]),
    lane.primary_artifact_id ? button("Open Artifact", "open-artifact-ref", "ghost", { artifactId: lane.primary_artifact_id }) : null,
  ]);
}
