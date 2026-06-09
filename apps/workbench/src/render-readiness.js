import { badge, button, el, sectionTitle } from "./dom.js";
import { statusTone } from "./workbench-state.js";

export function renderProjectReadiness(readiness) {
  if (!readiness) {
    return el("section", { className: "project-readiness" }, [sectionTitle("Project Readiness", "not loaded")]);
  }
  const steps = Array.isArray(readiness.steps) ? readiness.steps : [];
  return el("section", { className: "project-readiness" }, [
    el("div", { className: "readiness-head" }, [
      sectionTitle("Project Readiness", readiness.status || "not_started"),
      el("div", { className: "readiness-action" }, [
        el("span", { text: "Next" }),
        badge(readiness.current_action_label || "Next action", statusTone(readiness.status)),
      ]),
    ]),
    readiness.summary ? el("p", { className: "card-summary", text: readiness.summary }) : null,
    steps.length
      ? el("div", { className: "readiness-steps" }, steps.map((step) => renderStep(step)))
      : el("p", { className: "muted", text: "Runtime state has no readiness steps yet." }),
    readiness.current_action ? button(readiness.current_action_label, uiAction(readiness.current_action), "primary") : null,
    readiness.non_claims.length ? el("div", { className: "chips" }, readiness.non_claims.map((item) => badge(item, "quiet"))) : null,
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
    el("strong", { text: step.label || "Step" }),
    badge(step.status || "not_started", statusTone(step.status)),
    step.action_label ? el("small", { text: step.action_label }) : null,
  ]);
}
