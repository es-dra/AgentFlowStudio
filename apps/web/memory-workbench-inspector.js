const TYPE_LABELS = {
  agentflow_memory_video_pipeline_package: "Pipeline package",
  agentflow_memory_video_pipeline_protocol: "Pipeline protocol",
  agentflow_memory_video_pipeline_review: "Review artifact",
  agentflow_memory_video_pipeline_human_observation: "Human observation",
  agentflow_memory_video_pipeline_presentation_package: "Presentation package",
  agentflow_feedback_event: "Feedback draft",
  agentflow_production_memory_loop: "Production memory loop",
  agentflow_production_memory_session_report: "Production memory session",
  agentflow_production_memory_operator_loop_run: "Production memory operator loop",
  agentflow_production_memory_next_context_handoff: "Production memory next context handoff",
  agentflow_production_memory_next_task_packet: "Production memory next task packet",
  agentflow_production_memory_next_pass_review: "Production memory next pass review",
  agentflow_company_kb_feedback_candidate_packet: "Company KB candidate packet",
};

export function buildMemoryArtifactInspector(workspace, fallback = []) {
  const artifacts = Array.isArray(workspace?.memoryBundle) ? workspace.memoryBundle : [];
  if (!artifacts.length) return fallback.length ? fallback : emptyInspector();
  return artifacts.map((artifact) => summarizeArtifact(artifact));
}

function summarizeArtifact(artifact) {
  const payload = objectValue(artifact.payload);
  const type = artifact.artifactType || payload.artifact_type || "unknown";
  return {
    id: artifact.fileName,
    artifact_type: type,
    focus_targets: focusTargetsFor(type),
    title: TYPE_LABELS[type] || type,
    status: statusFor(type, payload),
    detail: `${artifact.fileName} | ${payload.protocol_id || payload.feedback_id || payload.schema_version || "selected JSON"}`,
    facts: factsFor(type, payload),
  };
}

function focusTargetsFor(type) {
  if (type === "agentflow_memory_video_pipeline_protocol") return ["project", "assets", "memory-loaded"];
  if (type === "agentflow_memory_video_pipeline_package") return ["project", "next-pass"];
  if (type === "agentflow_memory_video_pipeline_review") return ["baseline-run", "memory-backed-run", "review"];
  if (type === "agentflow_memory_video_pipeline_human_observation") return ["assets", "review"];
  if (type === "agentflow_memory_video_pipeline_presentation_package") return ["memory-loaded", "review"];
  if (type === "agentflow_feedback_event") return ["feedback", "next-pass"];
  if (type === "agentflow_production_memory_loop") return ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"];
  if (type === "agentflow_production_memory_session_report") return ["project", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_operator_loop_run") return ["project", "assets", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_next_context_handoff") return ["project", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_next_task_packet") return ["project", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_next_pass_review") return ["project", "memory-loaded", "review", "feedback", "next-pass"];
  if (type === "agentflow_company_kb_feedback_candidate_packet") return ["project", "memory-loaded", "review", "next-pass"];
  return [];
}

function factsFor(type, payload) {
  if (type === "agentflow_memory_video_pipeline_package") return packageFacts(payload);
  if (type === "agentflow_memory_video_pipeline_protocol") return protocolFacts(payload);
  if (type === "agentflow_memory_video_pipeline_review") return reviewFacts(payload);
  if (type === "agentflow_memory_video_pipeline_human_observation") return observationFacts(payload);
  if (type === "agentflow_memory_video_pipeline_presentation_package") return presentationFacts(payload);
  if (type === "agentflow_feedback_event") return feedbackFacts(payload);
  if (type === "agentflow_production_memory_loop") return productionLoopFacts(payload);
  if (type === "agentflow_production_memory_session_report") return productionSessionFacts(payload);
  if (type === "agentflow_production_memory_operator_loop_run") return productionOperatorLoopFacts(payload);
  if (type === "agentflow_production_memory_next_context_handoff") return productionNextContextHandoffFacts(payload);
  if (type === "agentflow_production_memory_next_task_packet") return productionNextTaskPacketFacts(payload);
  if (type === "agentflow_production_memory_next_pass_review") return productionNextPassReviewFacts(payload);
  if (type === "agentflow_company_kb_feedback_candidate_packet") return companyKbFeedbackFacts(payload);
  return [
    fact("artifact_type", payload.artifact_type || "unknown"),
    fact("schema_version", payload.schema_version || "unknown"),
  ];
}

function companyKbFeedbackFacts(payload) {
  return [
    fact("promotion_status", payload.promotion_status || "unknown"),
    fact("candidate_items", String(arrayValue(payload.candidate_items).length)),
    fact("source_kb_status", payload.source_kb_status || "unknown"),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("requires_human_review", yesNo(payload.requires_human_review)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

function productionNextContextHandoffFacts(payload) {
  return [
    fact("handoff_status", payload.handoff_status || "unknown"),
    fact("next_context_refs", String(arrayValue(payload.next_context_refs).length)),
    fact("blocked_refs", String(arrayValue(payload.blocked_refs).length)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

function productionNextTaskPacketFacts(payload) {
  return [
    fact("packet_status", payload.packet_status || "unknown"),
    fact("allowed_context_refs", String(arrayValue(payload.allowed_context_refs).length)),
    fact("blocked_refs", String(arrayValue(payload.blocked_refs).length)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

function productionNextPassReviewFacts(payload) {
  return [
    fact("review_status", payload.review_status || "unknown"),
    fact("used_allowed_refs", String(arrayValue(payload.used_allowed_refs).length)),
    fact("blocked_or_unknown_refs", String(arrayValue(payload.blocked_or_unknown_refs).length)),
    fact("feedback_candidates", String(arrayValue(payload.feedback_candidates).length)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

function productionOperatorLoopFacts(payload) {
  return [
    fact("chain_status", payload.chain_status || "unknown"),
    fact("operator_nodes", String(arrayValue(payload.operator_loop_nodes).length)),
    fact("output_artifacts", String(arrayValue(payload.output_artifacts).length)),
    fact("writes_company_kb", yesNo(payload.writes_company_kb)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
  ];
}

function productionSessionFacts(payload) {
  return [
    fact("session_status", payload.session_status || "unknown"),
    fact("included_refs", String(payload.context_summary?.included_ref_count ?? 0)),
    fact("blocked_refs", String(payload.context_summary?.blocked_ref_count ?? 0)),
    fact("next_action", payload.next_operator_action?.action || "unknown"),
    fact("provider_mode", payload.provider_mode || "unknown"),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
  ];
}

function productionLoopFacts(payload) {
  return [
    fact("artifacts", String(arrayValue(payload.artifact_ledger).length)),
    fact("feedback_events", String(arrayValue(payload.feedback_events).length)),
    fact("memory_candidates", String(arrayValue(payload.memory_candidates).length)),
    fact("promotion_decisions", String(arrayValue(payload.promotion_decisions).length)),
    fact("provider_mode", payload.provider_mode || "unknown"),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
  ];
}

function packageFacts(payload) {
  const refs = ["plan_ref", "review_ref", "observation_ref", "presentation_ref", "feedback_event_draft_ref"].filter((key) => payload[key]);
  return [
    fact("refs", `${refs.length} linked refs`),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
    fact("provider_calls_started", yesNo(payload.provider_calls_started)),
    fact("claim_boundary", claimBoundary(payload.claim_boundaries)),
  ];
}

function protocolFacts(payload) {
  const cards = arrayValue(payload.memory_context?.cards);
  const lanes = arrayValue(payload.lanes);
  const checkpoints = arrayValue(payload.storyboard?.shot_checkpoints);
  return [
    fact("memory_cards", String(cards.length)),
    fact("lanes", lanes.map((lane) => lane.lane_id).filter(Boolean).join(" / ") || "none"),
    fact("checkpoints", String(checkpoints.length)),
    fact("provider_route", payload.provider_route?.video_service_id || "not selected"),
  ];
}

function reviewFacts(payload) {
  const artifacts = arrayValue(payload.video_artifacts);
  const checkpoints = arrayValue(payload.storyboard?.shot_checkpoints);
  const parity = objectValue(payload.lane_parity);
  const parityPass = Object.values(parity).filter((value) => value === true).length;
  return [
    fact("video_artifacts", String(artifacts.length)),
    fact("lane_parity", `${parityPass}/${Object.keys(parity).length} true`),
    fact("storyboard", `${payload.storyboard?.scene_id || "storyboard"} | ${checkpoints.length} checkpoints`),
    fact("machine_judgement", payload.cross_run_stability?.machine_judgement || "not_performed"),
  ];
}

function observationFacts(payload) {
  const observations = arrayValue(payload.observations);
  return [
    fact("observations", String(observations.length)),
    fact("verdicts", verdictCounts(observations)),
    fact("signal", signalSummary(payload.observed_signal_summary)),
    fact("claim_boundary", claimBoundary(payload.claim_boundaries)),
  ];
}

function presentationFacts(payload) {
  const setup = objectValue(payload.experiment_setup);
  const result = objectValue(payload.result_summary);
  return [
    fact("takeaway", payload.one_sentence_takeaway || "not provided"),
    fact("same_for_both_lanes", arrayValue(setup.same_for_both_lanes).length),
    fact("run_count", result.run_count ?? "unknown"),
    fact("residual_risk", result.residual_risk || "unknown"),
  ];
}

function feedbackFacts(payload) {
  return [
    fact("decision", payload.decision || "unknown"),
    fact("draft_status", payload.draft_status || "unknown"),
    fact("reason_tags", arrayValue(payload.reason_tags).join(", ") || "none"),
    fact("writes_long_term_memory", yesNo(payload.writes_long_term_memory)),
  ];
}

function statusFor(type, payload) {
  if (type === "agentflow_feedback_event") return payload.draft_status || "feedback captured";
  if (type === "agentflow_memory_video_pipeline_human_observation") return payload.observation_status || "review ready";
  if (type === "agentflow_production_memory_next_pass_review") return payload.review_status || "review ready";
  if (payload.writes_long_term_memory === true) return "blocked";
  return "review ready";
}

function verdictCounts(observations) {
  const counts = {};
  for (const item of observations) {
    const verdict = item?.verdict || "unknown";
    counts[verdict] = (counts[verdict] || 0) + 1;
  }
  return Object.entries(counts).map(([verdict, count]) => `${verdict}: ${count}`).join(", ") || "none";
}

function signalSummary(signal) {
  const data = objectValue(signal);
  return Object.entries(data)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(", ") || "not recorded";
}

function claimBoundary(boundaries) {
  const data = objectValue(boundaries);
  return [
    data.human_acceptance || "not_acceptance",
    data.business_validation || "not_validated",
    data.durable_memory_runtime || "not_implemented",
  ].join(" / ");
}

function fact(label, value) {
  return { label, value: String(value) };
}

function yesNo(value) {
  return value === true ? "true" : "false";
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}

function emptyInspector() {
  return [
    {
      id: "no_memory_artifacts",
      artifact_type: "fixture",
      focus_targets: ["project", "assets", "memory-loaded", "baseline-run", "memory-backed-run", "review", "feedback", "next-pass"],
      title: "No selected memory artifacts",
      status: "planned",
      detail: "Select memory package, review, observation, presentation, protocol, or feedback JSON to inspect structure.",
      facts: [
        fact("scope", "explicit selected files only"),
        fact("auto_follow_refs", "false"),
      ],
    },
  ];
}
