const OPERATOR_LOOP_TYPE = "agentflow_production_memory_operator_loop_run";

export function buildProductionMemoryOperatorLoopView(workspace, fallback) {
  const artifact = workspace?.productionMemoryOperatorLoopRun;
  if (!isOperatorLoopArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const nodes = arrayValue(payload.operator_loop_nodes);
  const outputs = arrayValue(payload.output_artifacts);
  const postCheckArtifacts = arrayValue(payload.post_check_artifacts);
  const company = payload.company_kb_feedback || {};
  const resultScaffold = objectValue(payload.next_pass_result);
  const promotion = payload.next_pass_promotion || null;
  const feedbackCandidatePromotion = payload.operator_feedback_candidate_promotion || null;
  const acceptanceCandidatePromotion = payload.acceptance_feedback_candidate_promotion || null;
  const startPacket = objectValue(payload.next_operator_start_packet);
  const startPacketReady = startPacket?.start_packet_status === "ready" && startPacket.ready_for_next_operator === true;
  const ready = payload.chain_status === "ready" && payload.provider_calls_started === false;
  return {
    ...fallback,
    state: ready ? "operator loop ready" : "blocked",
    project: {
      title: payload.project_id || payload.loop_id || artifact.fileName,
      brief: `Production memory operator loop: ${payload.chain_status || "unknown"}`,
      format: OPERATOR_LOOP_TYPE,
      route: "selected local JSON only; read-only no-provider operator loop manifest",
    },
    workflow_actions: [
      action("inspect_operator_loop", "Inspect operator loop", "review ready", "project"),
      action("inspect_generated_artifacts", "Inspect artifacts", outputs.length ? "ready" : "missing", "assets"),
      action("inspect_next_pass_result", "Inspect result scaffold", resultScaffold ? "review ready" : "missing", "next-pass"),
      action("inspect_next_pass_promotion", "Inspect promotion", promotion ? "review ready" : "missing", "next-pass"),
      action(
        "inspect_operator_feedback_candidate_promotion",
        "Inspect feedback candidate",
        feedbackCandidatePromotion ? "review ready" : "missing",
        "review",
      ),
      action(
        "inspect_acceptance_feedback_candidate_promotion",
        "Inspect acceptance candidate",
        acceptanceCandidatePromotion ? "review ready" : "missing",
        "review",
      ),
      ...(startPacket ? [
        action("inspect_next_operator_start_packet", "Inspect start packet", startPacketReady ? "review ready" : "blocked", "next-pass"),
      ] : []),
      action("review_company_candidates", "Review candidates", company.requires_human_review ? "blocked" : "review ready", "review"),
      action("prepare_next_pass", "Prepare next pass", ready ? "ready" : "blocked", "next-pass"),
    ],
    assets: [
      ...outputs.map((item) => ({
        id: item.path || item.artifact_type,
        label: item.artifact_type || item.path,
        detail: item.path || "generated artifact",
        status: item.required === false ? "optional" : "required",
      })),
      ...postCheckArtifacts.map((item) => ({
        id: item.path || item.artifact_type,
        label: item.artifact_type || item.path,
        detail: item.path || "post-check artifact",
        status: "post-check",
      })),
    ],
    bundle_summary: [
      card("operator_nodes", "Operator nodes", nodes.length ? "review ready" : "missing", `${nodes.length} chain nodes`),
      card("output_artifacts", "Output artifacts", outputs.length ? "review ready" : "missing", `${outputs.length} generated artifact refs`),
      ...(postCheckArtifacts.length ? [
        card("post_check_artifacts", "Post-check artifacts", "review ready", `${postCheckArtifacts.length} post-check refs`),
      ] : []),
      ...(resultScaffold ? [
        card(
          "next_pass_result",
          "Next pass result",
          resultScaffold.result_status || "unknown",
          `${resultScaffold.output_artifact_count ?? 0} scaffolded outputs`,
        ),
      ] : []),
      ...(promotion ? [card("next_pass_promotion", "Next pass promotion", promotion.decision || "unknown", promotion.decision_effect || "unknown")] : []),
      ...(feedbackCandidatePromotion ? [
        card(
          "operator_feedback_candidate_promotion",
          "Operator feedback candidate promotion",
          feedbackCandidatePromotion.decision || "unknown",
          feedbackCandidatePromotion.decision_effect || "unknown",
        ),
      ] : []),
      ...(acceptanceCandidatePromotion ? [
        card(
          "acceptance_feedback_candidate_promotion",
          "Acceptance feedback candidate promotion",
          acceptanceCandidatePromotion.decision || "unknown",
          acceptanceCandidatePromotion.decision_effect || "unknown",
        ),
      ] : []),
      ...(startPacket ? [
        card(
          "next_operator_start_packet",
          "Next operator start packet",
          startPacket.start_packet_status || "unknown",
          startPacketReady ? "ready" : "blocked",
        ),
      ] : []),
      card("company_kb_feedback", "Company KB feedback", company.promotion_status || "unknown", companyBoundary(company)),
    ],
    memory_loaded: [
      ...nodes.map((node) => ({
        id: node.node_id,
        title: node.node_id,
        why_eligible: node.artifact_type ? `generated ${node.artifact_type}` : "operator chain source node",
        source_evidence_refs: [node.artifact_type || node.status || "operator node"],
        promotion_status: node.status || "unknown",
        request_projection: node.detail || "operator loop node",
        feedback_effect: "operator manifest only; no durable memory or Company KB write",
        status: node.status || "unknown",
      })),
      ...(startPacket ? [
        {
          id: "next_operator_start_packet",
          title: "Next operator start packet",
          why_eligible: "post-check artifact generated after a passed operator run package check",
          source_evidence_refs: [startPacket.path || "next_operator_start_packet/next_operator_start_packet.json"],
          promotion_status: startPacket.start_packet_status || "unknown",
          request_projection: startPacket.next_operator_action || "next operator action recorded",
          feedback_effect: "start packet only; no durable memory or Company KB write",
          status: startPacketReady ? "review ready" : "blocked",
        },
      ] : []),
    ],
    lanes: [
      lane("operator-loop", "Operator loop", ready ? "ready" : "blocked", payload.loop_id || "loop", payload.chain_status || "unknown"),
      lane("generated-artifacts", "Generated artifacts", outputs.length ? "review ready" : "missing", `${outputs.length} outputs`, "explicit artifact refs"),
      ...(postCheckArtifacts.length ? [
        lane("post-check-artifacts", "Post-check artifacts", "review ready", `${postCheckArtifacts.length} refs`, "generated after final checks"),
      ] : []),
      ...(resultScaffold ? [
        lane(
          "next-pass-result",
          "Next pass result",
          resultScaffold.result_status || "unknown",
          `${resultScaffold.output_artifact_count ?? 0} outputs`,
          "scaffolded for operator completion",
        ),
      ] : []),
      ...(promotion ? [lane("next-pass-promotion", "Next pass promotion", promotion.decision || "unknown", promotion.candidate_id || "candidate", promotion.decision_effect || "unknown")] : []),
      ...(feedbackCandidatePromotion ? [
        lane(
          "operator-feedback-candidate-promotion",
          "Operator feedback candidate promotion",
          feedbackCandidatePromotion.decision || "unknown",
          feedbackCandidatePromotion.candidate_id || "candidate",
          feedbackCandidatePromotion.decision_effect || "unknown",
        ),
      ] : []),
      ...(acceptanceCandidatePromotion ? [
        lane(
          "acceptance-feedback-candidate-promotion",
          "Acceptance feedback candidate promotion",
          acceptanceCandidatePromotion.decision || "unknown",
          acceptanceCandidatePromotion.candidate_id || "candidate",
          acceptanceCandidatePromotion.decision_effect || "unknown",
        ),
      ] : []),
      ...(startPacket ? [
        lane(
          "next-operator-start-packet",
          "Next operator start packet",
          startPacketReady ? "ready" : "blocked",
          startPacket.path || "next_operator_start_packet.json",
          startPacket.start_packet_status || "unknown",
        ),
      ] : []),
      lane("company-kb-feedback", "Company KB feedback", company.promotion_status || "unknown", `${company.candidate_item_count ?? 0} candidates`, companyBoundary(company)),
    ],
    protocol_summary: {
      title: "Production memory operator loop",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("no-provider mode", payload.provider_mode === "no-provider"),
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
        ...(resultScaffold ? [
          control(
            "next-pass result no-provider mode",
            resultScaffold.provider_mode === "no-provider" && resultScaffold.provider_calls_started === false,
          ),
          control("next-pass result memory write disabled", resultScaffold.writes_long_term_memory === false),
        ] : []),
        ...(promotion ? [
          control("next-pass promotion no-provider mode", hasPassedControl(payload, "next_pass_promotion_no_provider_mode")),
          control("next-pass promotion memory write disabled", hasPassedControl(payload, "next_pass_promotion_long_term_memory_write_disabled")),
        ] : []),
        ...(feedbackCandidatePromotion ? [
          control(
            "operator feedback candidate promotion no-provider mode",
            hasPassedControl(payload, "operator_feedback_candidate_promotion_no_provider_mode"),
          ),
          control(
            "operator feedback candidate promotion memory write disabled",
            hasPassedControl(payload, "operator_feedback_candidate_promotion_long_term_memory_write_disabled"),
          ),
        ] : []),
        ...(acceptanceCandidatePromotion ? [
          control(
            "acceptance feedback candidate promotion no-provider mode",
            hasPassedControl(payload, "acceptance_feedback_candidate_promotion_no_provider_mode"),
          ),
          control(
            "acceptance feedback candidate promotion memory write disabled",
            hasPassedControl(payload, "acceptance_feedback_candidate_promotion_long_term_memory_write_disabled"),
          ),
        ] : []),
        ...(startPacket ? [
          control("next operator start packet ready", startPacketReady),
          control("next operator start packet provider calls not started", startPacket.provider_calls_started === false),
          control("next operator start packet memory write disabled", startPacket.writes_long_term_memory === false),
          control("next operator start packet Company KB write disabled", startPacket.writes_company_kb === false),
        ] : []),
        control("Company feedback candidate only", company.promotion_status === "candidate_only"),
        control("Human review required for Company feedback", company.requires_human_review === true, "blocked"),
      ],
      boundaries: boundaryItems(payload.non_claim_boundaries),
    },
    review: {
      storyboard_adherence: `${nodes.length} operator nodes`,
      visual_consistency: `${outputs.length} output artifacts`,
      boundary: "read-only operator manifest / no provider call / no Company KB write",
    },
    feedback: {
      status: company.requires_human_review ? "blocked" : "review ready",
      summary: `${company.candidate_item_count ?? 0} Company KB feedback candidates remain candidate-only`,
    },
    next_pass: {
      status: startPacket ? (startPacketReady ? "ready" : "blocked") : (ready ? "ready" : "blocked"),
      action: nextPassAction(ready, resultScaffold, promotion, feedbackCandidatePromotion, acceptanceCandidatePromotion, startPacket, startPacketReady),
    },
    timeline: [
      ...nodes.map((node) => step(node.node_id, node.status || "unknown", node.detail)),
      ...(startPacket ? [
        step("Next operator start packet", startPacketReady ? "ready" : "blocked", startPacket.path || "not recorded"),
      ] : []),
    ],
  };
}

function nextPassAction(ready, resultScaffold, promotion, feedbackCandidatePromotion, acceptanceCandidatePromotion, startPacket, startPacketReady) {
  if (!ready) return "resolve_operator_loop_blockers";
  if (startPacket) return startPacketReady ? "start_next_operator_action" : "resolve_next_operator_start_packet_blockers";
  if (acceptanceCandidatePromotion) return "inspect_acceptance_feedback_candidate_overlay_before_next_pass";
  if (feedbackCandidatePromotion) return "inspect_operator_feedback_candidate_overlay_before_next_pass";
  if (promotion) return "inspect_next_pass_promotion_overlay_before_followup_context";
  if (resultScaffold) return "inspect_next_pass_result_scaffold_before_review";
  return "inspect_generated_artifacts_before_next_pass";
}

function companyBoundary(company) {
  if (company.requires_human_review) return "candidate-only; human review required before Company KB promotion";
  return company.writes_company_kb === false ? "Company KB write disabled" : "unknown";
}

function action(id, label, status, focusTarget) {
  return { id, label, status, focusTarget, focus_target: focusTarget };
}

function card(id, title, status, detail) {
  return { id, title, status, detail };
}

function lane(id, title, status, input, output) {
  return { id, title, status, input, output };
}

function control(label, passed, forcedStatus = null) {
  return { label, status: forcedStatus || (passed ? "review ready" : "blocked"), detail: passed ? "confirmed by manifest" : "not confirmed" };
}

function boundaryItems(boundaries = {}) {
  return [
    { label: "human acceptance", status: "blocked", detail: boundaries.human_acceptance || "not_reviewed" },
    { label: "business validation", status: "blocked", detail: boundaries.business_validation || "not_validated" },
    { label: "durable memory runtime", status: "blocked", detail: boundaries.durable_memory_runtime || "not_implemented" },
    { label: "provider success", status: "blocked", detail: boundaries.provider_success || "not_attempted" },
  ];
}

function hasPassedControl(payload, controlId) {
  return arrayValue(payload.controls).some((item) => item?.control_id === controlId && item?.status === "passed");
}

function step(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

function isOperatorLoopArtifact(artifact) {
  return artifact?.artifactType === OPERATOR_LOOP_TYPE && artifact?.payload?.kind === OPERATOR_LOOP_TYPE;
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : null;
}
