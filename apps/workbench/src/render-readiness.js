import { badge, button, el, sectionTitle } from "./dom.js";
import { displayList, displayStatus, displayText } from "./display-labels.js";
import { statusTone } from "./workbench-state.js";

export function renderProjectReadiness(readiness) {
  if (!readiness) {
    return el("section", { className: "project-readiness" }, [sectionTitle("项目就绪度", "not loaded")]);
  }
  const steps = Array.isArray(readiness.steps) ? readiness.steps : [];
  return el("section", { className: "project-readiness" }, [
    el("div", { className: "readiness-head" }, [
      sectionTitle("项目就绪度", displayStatus(readiness.status)),
      el("div", { className: "readiness-action" }, [
        el("span", { text: "下一步" }),
        badge(displayText(readiness.current_action_label, "下一步操作"), statusTone(readiness.status)),
      ]),
    ]),
    readiness.summary ? el("p", { className: "card-summary", text: displayText(readiness.summary) }) : null,
    steps.length
      ? el("div", { className: "readiness-steps" }, steps.map((step) => renderStep(step)))
      : el("p", { className: "muted", text: "运行状态里还没有就绪步骤。" }),
    readiness.current_action ? button(displayText(readiness.current_action_label), uiAction(readiness.current_action), "primary") : null,
    readiness.non_claims.length ? el("div", { className: "chips" }, displayList(readiness.non_claims).map((item) => badge(item, "quiet"))) : null,
  ]);
}

function uiAction(action) {
  return {
    add_reference: "register-source-asset",
    draft_canvas: "draft-canvas",
    start_first_generation_check: "run-asset-test",
    record_review_note: "record-review-decision",
    start_next_round: "run-two-round",
    run_provider_preflight: "run-provider-preflight",
    resolve_provider_preflight: "run-provider-preflight",
  }[action] || "refresh";
}

function renderStep(step) {
  return el("div", { className: "readiness-step", dataset: { stepId: step.step_id || "" } }, [
    el("strong", { text: displayText(step.label, "步骤") }),
    badge(displayStatus(step.status), statusTone(step.status)),
    step.action_label ? el("small", { text: displayText(step.action_label) }) : null,
  ]);
}
