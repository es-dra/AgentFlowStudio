const COMPANY_KB_PACKET_TYPE = "agentflow_company_kb_feedback_candidate_packet";

export function buildCompanyKbFeedbackCandidatePacketView(workspace, fallback) {
  const artifact = workspace?.companyKbFeedbackCandidatePacket;
  if (!isCompanyKbPacketArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const candidates = arrayValue(payload.candidate_items);
  const nonPromotions = arrayValue(payload.explicit_non_promotions);
  const candidateOnly = payload.promotion_status === "candidate_only";
  return {
    ...fallback,
    state: candidateOnly ? "candidate review" : "blocked",
    project: {
      title: payload.packet_id || artifact.fileName,
      brief: `Company KB feedback packet: ${payload.source_report?.project_id || "unknown project"}`,
      format: COMPANY_KB_PACKET_TYPE,
      route: "selected local JSON only; candidate-only Company KB review packet",
    },
    workflow_actions: [
      action("inspect_packet", "Inspect packet", "review ready", "project"),
      action("inspect_candidates", "Inspect candidates", candidates.length ? "review ready" : "missing", "memory-loaded"),
      action("review_non_promotions", "Review non-promotions", nonPromotions.length ? "blocked" : "review ready", "review"),
      action("human_review", "Human review", payload.requires_human_review ? "blocked" : "review ready", "feedback"),
    ],
    assets: candidates.map((item) => ({
      id: item.candidate_id,
      label: item.candidate_id,
      detail: item.summary || "candidate item",
      status: item.status || "candidate",
    })),
    bundle_summary: [
      card("candidate_items", "Candidate items", candidates.length ? "review ready" : "missing", `${candidates.length} candidate-only items`),
      card("human_review", "Human review", payload.requires_human_review ? "blocked" : "review ready", "required before Company KB promotion"),
      card("company_kb_write", "Company KB write", payload.writes_company_kb === false ? "review ready" : "blocked", targetWriteStatus(payload)),
    ],
    memory_loaded: candidates.map((item) => ({
      id: item.candidate_id,
      title: item.candidate_id,
      why_eligible: item.promotion_boundary || "candidate-only reusable lesson",
      source_evidence_refs: arrayValue(item.source_refs),
      promotion_status: payload.promotion_status || "candidate_only",
      request_projection: item.summary || "candidate feedback for human Company KB review",
      feedback_effect: "visible as candidate feedback only; no Company KB or durable memory write",
      status: item.status || "candidate",
    })),
    lanes: [
      lane("candidate-packet", "Candidate packet", candidateOnly ? "review ready" : "blocked", payload.packet_id || artifact.fileName, payload.source_kb_status || "unknown"),
      lane("candidate-items", "Candidate items", candidates.length ? "review ready" : "missing", `${candidates.length} candidates`, "candidate-only"),
      lane("explicit-non-promotions", "Explicit non-promotions", nonPromotions.length ? "blocked" : "review ready", `${nonPromotions.length} boundaries`, "not promoted"),
    ],
    protocol_summary: {
      title: "Company KB feedback candidate packet",
      status: candidateOnly ? "review ready" : "blocked",
      controls: [
        control("Candidate only", candidateOnly, "not durable Company memory"),
        control("Company KB write disabled", payload.writes_company_kb === false, "no source KB mutation"),
        control("Durable memory write disabled", payload.writes_long_term_memory === false, "no long-term memory write"),
        control("Human review required", payload.requires_human_review === true, "promotion needs human review", "blocked"),
      ],
      boundaries: boundaryItems(payload),
    },
    review: {
      storyboard_adherence: `${candidates.length} candidate items`,
      visual_consistency: `${nonPromotions.length} explicit non-promotions`,
      boundary: "candidate feedback only / no Company KB write / no durable memory claim",
    },
    feedback: {
      status: "candidate",
      summary: `${candidates.length} candidate items require human review before any Company KB promotion`,
    },
    next_pass: {
      status: "blocked",
      action: "human_review_required_before_company_memory_promotion",
    },
    timeline: [
      step("Packet", candidateOnly ? "review ready" : "blocked", payload.packet_id),
      step("Candidates", candidates.length ? "review ready" : "missing", `${candidates.length} items`),
      step("Company KB write", payload.writes_company_kb === false ? "review ready" : "blocked", targetWriteStatus(payload)),
      step("Human review", payload.requires_human_review ? "blocked" : "review ready", "required before promotion"),
    ],
  };
}

function targetWriteStatus(payload) {
  return payload.target?.write_status || (payload.writes_company_kb === false ? "not_written" : "unknown");
}

function boundaryItems(payload) {
  const boundaries = payload.non_claim_boundaries || {};
  return [
    { label: "human acceptance", status: "blocked", detail: boundaries.human_acceptance || "not_reviewed" },
    { label: "business validation", status: "blocked", detail: boundaries.business_validation || "not_validated" },
    { label: "durable memory runtime", status: "blocked", detail: boundaries.durable_memory_runtime || "not_implemented" },
    { label: "provider success", status: "blocked", detail: boundaries.provider_success || "not_attempted" },
  ];
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

function control(label, passed, detail, forcedStatus = null) {
  return { label, status: forcedStatus || (passed ? "review ready" : "blocked"), detail };
}

function step(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

function isCompanyKbPacketArtifact(artifact) {
  return artifact?.artifactType === COMPANY_KB_PACKET_TYPE && artifact?.payload?.kind === COMPANY_KB_PACKET_TYPE;
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
