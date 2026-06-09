import { badge, button, el, sectionTitle } from "./dom.js";
import { displayList, displayStatus, displayText } from "./display-labels.js";
import { statusTone } from "./workbench-state.js";

export function renderProductionBoard(board) {
  const value = board || { lanes: [], non_claims: [] };
  const lanes = Array.isArray(value.lanes) ? value.lanes : [];
  return el("section", { className: "production-board" }, [
    sectionTitle("制作流程", displayStatus(value.status)),
    el("p", { className: "card-summary", text: displayText(value.summary, "还没有制作流程。") }),
    lanes.length ? el("div", { className: "production-lanes" }, lanes.map(renderLane)) : el("p", { className: "muted", text: "打开项目后查看制作流程。" }),
    value.current_action_label ? badge(`下一步：${displayText(value.current_action_label)}`, "active") : null,
    value.non_claims && value.non_claims.length ? el("div", { className: "chips" }, displayList(value.non_claims).map((item) => badge(item, "quiet"))) : null,
  ]);
}

function renderLane(lane) {
  const tone = statusTone(lane.status);
  return el("article", { className: `production-lane ${tone}` }, [
    el("div", { className: "production-lane-head" }, [
      el("strong", { text: displayText(lane.label, "阶段") }),
      badge(displayStatus(lane.status), tone),
    ]),
    el("p", { className: "card-summary", text: displayText(lane.summary || lane.action_label, "继续。") }),
    el("div", { className: "production-lane-meta" }, [
      lane.action ? badge(displayText(lane.action), "quiet") : null,
      badge(`${lane.artifact_count || 0} 个引用`, lane.artifact_count ? "ready" : "quiet"),
    ]),
    lane.primary_artifact_id ? button("打开产物", "open-artifact-ref", "ghost", { artifactId: lane.primary_artifact_id }) : null,
  ]);
}
