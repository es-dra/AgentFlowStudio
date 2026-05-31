export function loulanInspector(
  payload,
  apiPlan = null,
  reviewPack = null,
  decisionTemplate = null,
  decisionWorksheet = null,
  contextProjection = null,
) {
  const items = [
    {
      id: "loulan_package",
      title: "Loulan package",
      status: "review ready",
      focus_targets: ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"],
      detail: payload.package_id,
      facts: [
        fact("provider_calls_started", String(payload.provider_calls_started)),
        fact("writes_long_term_memory", String(payload.writes_long_term_memory)),
      ],
    },
  ];
  if (apiPlan) {
    items.push({
      id: "loulan_api_workbench_plan",
      title: "Loulan API workbench plan",
      status: apiPlan.request_manifest?.status || "planned",
      focus_targets: ["baseline-run", "memory-backed-run", "review", "next-pass"],
      detail: `${apiPlan.provider_adapter?.adapter_id || "adapter"}; ${apiPlan.response_ledger?.status || "not_submitted"}`,
      facts: [
        fact("dry_run_only", String(apiPlan.dry_run_only)),
        fact("provider_calls_started", String(apiPlan.provider_calls_started)),
        fact("requests", String(apiPlan.request_manifest?.requests?.length || 0)),
      ],
    });
  }
  if (reviewPack) {
    items.push({
      id: "loulan_human_review_pack",
      title: "Loulan human review pack",
      status: reviewPack.next_pass_readiness?.status || "pending_human_review",
      focus_targets: ["review", "feedback", "next-pass"],
      detail: `${reviewPack.review_scope?.block_id || "block"}; ${reviewPack.review_scope?.evidence_status || "review"}`,
      facts: [
        fact("human_acceptance_recorded", String(reviewPack.human_acceptance_recorded)),
        fact("shots", String(reviewPack.review_scope?.shot_count || 0)),
        fact("required_decisions", String(reviewPack.next_pass_readiness?.required_decisions?.length || 0)),
      ],
    });
  }
  if (decisionWorksheet) {
    items.push({
      id: "loulan_decision_worksheet",
      title: "Loulan decision worksheet",
      status: decisionWorksheet.worksheet_status || "awaiting_manual_decisions",
      focus_targets: ["review", "feedback", "next-pass"],
      detail: `${decisionWorksheet.decision_rows?.length || 0} manual-fill rows; acceptance not recorded`,
      facts: [
        fact("human_acceptance_recorded", String(decisionWorksheet.human_acceptance_recorded)),
        fact("provider_calls_started", String(decisionWorksheet.provider_calls_started)),
        fact("rows", String(decisionWorksheet.decision_rows?.length || 0)),
      ],
    });
  }
  return items;
}

export function loulanTimeline(
  payload,
  apiPlan = null,
  reviewPack = null,
  decisionTemplate = null,
  decisionReview = null,
  decisionWorksheet = null,
  decisionIntake = null,
  contextProjection = null,
) {
  const nodes = (payload.canvas_nodes || []).map((node) => ({
    label: node.label,
    status: node.status,
    detail: node.id,
  }));
  if (apiPlan) {
    nodes.push({
      label: "API Workbench",
      status: apiPlan.request_manifest?.status || "planned",
      detail: `${apiPlan.request_manifest?.requests?.length || 0} request previews`,
    });
  }
  if (reviewPack) {
    nodes.push({
      label: "Human Review",
      status: reviewPack.next_pass_readiness?.status || "pending_human_review",
      detail: `${reviewPack.review_scope?.shot_count || 0} shots queued`,
    });
  }
  if (decisionTemplate) {
    nodes.push({
      label: "Decision Template",
      status: decisionTemplate.template_status || "pending_human_input",
      detail: `${decisionTemplate.decisions?.length || 0} human decision slots`,
    });
  }
  if (decisionReview) {
    nodes.push({
      label: "Decision Review",
      status: decisionReview.review_status || "blocked",
      detail: `${decisionReview.decision_summary?.pending_count || 0} pending human decisions`,
    });
  }
  if (decisionWorksheet) {
    nodes.push({
      label: "Decision Worksheet",
      status: decisionWorksheet.worksheet_status || "awaiting_manual_decisions",
      detail: `${decisionWorksheet.decision_rows?.length || 0} manual-fill rows`,
    });
  }
  if (decisionIntake) {
    nodes.push({
      label: "Decision Intake",
      status: decisionIntake.intake_status || "blocked",
      detail: `context ready: ${String(decisionIntake.context_bundle_command_ready)}`,
    });
  }
  if (contextProjection) {
    nodes.push({
      label: "Context Bundle",
      status: contextProjection.context_bundle?.status || contextProjection.decision_audit?.status || "blocked",
      detail: `${contextProjection.decision_audit?.status || "decision audit not run"}; intake gate: ${contextProjection.decision_intake_gate?.status || "not_supplied"}`,
    });
  }
  return nodes;
}

function fact(label, value) {
  return { label, value: String(value) };
}
