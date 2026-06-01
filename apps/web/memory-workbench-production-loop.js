const PRODUCTION_MEMORY_LOOP_TYPE = "agentflow_production_memory_loop";
const INCLUDED_ARTIFACT_STATUSES = new Set(["approved", "accepted", "ready", "promoted"]);
const BLOCKED_STATUSES = new Set(["rejected", "pending", "blocked", "expired"]);
const ALLOWING_DECISIONS = new Set(["promoted", "merged"]);

export function buildProductionMemoryLoopView(workspace, fallback) {
  const artifact = workspace?.productionMemoryLoop;
  if (!isProductionLoopArtifact(artifact)) return fallback;

  const payload = artifact.payload;
  const context = buildContext(payload);
  const ready = payload.provider_mode === "no-provider" && payload.writes_long_term_memory === false && context.included.length > 0;
  return {
    ...fallback,
    state: ready ? "pass ready" : "blocked",
    project: {
      title: payload.project_input?.project_id || payload.loop_id || artifact.fileName,
      brief: payload.project_input?.operator_goal || "Generic production-memory loop.",
      format: PRODUCTION_MEMORY_LOOP_TYPE,
      route: "selected local JSON only; read-only no-provider canvas",
    },
    workflow_actions: productionActions(ready, context),
    assets: artifactAssets(payload),
    bundle_summary: [
      {
        id: "included_refs",
        title: "Included refs",
        status: context.included.length ? "review ready" : "missing",
        detail: `${context.included.length} refs eligible for the next context bundle`,
      },
      {
        id: "blocked_refs",
        title: "Blocked refs",
        status: context.blocked.length ? "blocked" : "review ready",
        detail: `${context.blocked.length} refs blocked or excluded from next context`,
      },
      {
        id: "source_records",
        title: "Source records",
        status: "review ready",
        detail: recordSummary(payload),
      },
    ],
    memory_loaded: context.included.map((item) => provenanceFor(item)),
    lanes: [
      {
        id: "artifact-ledger",
        title: "Artifact ledger",
        status: context.blocked.some((item) => item.source_record_type === "artifact") ? "blocked" : "review ready",
        input: `${arrayValue(payload.artifact_ledger).length} source artifact records`,
        output: `${context.included.filter((item) => item.source_record_type === "artifact").length} artifact refs included`,
      },
      {
        id: "memory-candidates",
        title: "Memory candidates",
        status: context.blocked.some((item) => item.source_record_type === "memory_candidate") ? "blocked" : "review ready",
        input: `${arrayValue(payload.memory_candidates).length} candidate records`,
        output: `${context.included.filter((item) => item.source_record_type === "memory_candidate").length} promoted candidates included`,
      },
    ],
    protocol_summary: {
      title: "Production memory architecture",
      status: ready ? "review ready" : "blocked",
      controls: [
        control("feedback is not memory", context.blocked.some((item) => item.reason === "feedback_is_not_memory")),
        control("candidate needs promotion", context.included.every((item) => item.source_record_type !== "memory_candidate" || item.decision_id)),
        control("no-provider mode", payload.provider_mode === "no-provider"),
        control("durable write disabled", payload.writes_long_term_memory === false),
      ],
      boundaries: boundaryItems(payload.claim_boundaries),
    },
    review: {
      storyboard_adherence: `${context.included.length} included refs`,
      visual_consistency: `${context.blocked.length} blocked refs`,
      boundary: "no provider call / no durable memory write / no human acceptance claim",
    },
    feedback: {
      status: "review ready",
      summary: `${arrayValue(payload.feedback_events).length} feedback events remain source evidence only`,
    },
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: ready
        ? "use included_refs only when assembling the next context bundle"
        : "resolve validation or promotion blockers before next pass",
    },
    timeline: productionTimeline(payload, context, ready),
  };
}

function buildContext(payload) {
  const indexes = indexesFor(payload);
  const included = [];
  const blocked = [];
  for (const refId of requestedRefs(payload)) {
    const result = classifyRef(refId, indexes);
    if (result.included) included.push(result.included);
    if (result.blocked) blocked.push(result.blocked);
  }
  return { included, blocked };
}

function classifyRef(refId, indexes) {
  if (indexes.artifacts.has(refId)) return classifyArtifact(refId, indexes.artifacts.get(refId));
  if (indexes.feedback.has(refId)) {
    return { blocked: blockedRef(refId, "feedback_event", "feedback_is_not_memory", indexes.feedback.get(refId).decision) };
  }
  if (indexes.candidates.has(refId)) return classifyCandidate(refId, indexes);
  if (indexes.decisions.has(refId)) {
    return { blocked: blockedRef(refId, "promotion_decision", "promotion_decision_is_not_context", indexes.decisions.get(refId).decision) };
  }
  return { blocked: blockedRef(refId, "missing", "missing_reference", "missing") };
}

function classifyArtifact(refId, artifact) {
  const status = String(artifact.status || "unknown");
  if (artifact.eligible_for_next_context === true && INCLUDED_ARTIFACT_STATUSES.has(status)) {
    return {
      included: {
        ref_id: refId,
        source_record_type: "artifact",
        title: artifact.title || refId,
        status,
        summary: artifact.summary || "",
      },
    };
  }
  const reason = BLOCKED_STATUSES.has(status) ? `artifact_status_${status}` : "artifact_not_eligible";
  return { blocked: blockedRef(refId, "artifact", reason, status) };
}

function classifyCandidate(refId, indexes) {
  const candidate = indexes.candidates.get(refId);
  const status = String(candidate.status || "candidate");
  if (BLOCKED_STATUSES.has(status)) return { blocked: blockedRef(refId, "memory_candidate", `memory_candidate_${status}`, status) };
  const decision = indexes.decisionsByCandidate.get(refId);
  if (!decision) return { blocked: blockedRef(refId, "memory_candidate", "memory_candidate_without_promotion_decision", status) };
  const decisionStatus = String(decision.decision || "unknown");
  if (!ALLOWING_DECISIONS.has(decisionStatus)) {
    return { blocked: blockedRef(refId, "memory_candidate", `promotion_decision_${decisionStatus}`, decisionStatus) };
  }
  return {
    included: {
      ref_id: refId,
      source_record_type: "memory_candidate",
      title: refId,
      status,
      decision_id: decision.decision_id,
      promotion_decision: decisionStatus,
      summary: candidate.statement || "",
    },
  };
}

function productionActions(ready, context) {
  return [
    action("load_package", "Load loop", "review ready", "project"),
    action("inspect_evidence", "Inspect ledger", "review ready", "assets"),
    action("compare_lanes", "Compare statuses", context.blocked.length ? "blocked" : "review ready", "review"),
    action("capture_feedback", "Review feedback", "review ready", "feedback"),
    action("prepare_next_pass", "Prepare next pass", ready ? "ready" : "blocked", "next-pass"),
  ];
}

function action(id, label, status, focusTarget) {
  return { id, label, status, focusTarget, focus_target: focusTarget };
}

function artifactAssets(payload) {
  return arrayValue(payload.artifact_ledger).map((item) => ({
    id: item.ref_id,
    label: item.title || item.ref_id,
    detail: item.summary || item.artifact_kind || "artifact ledger record",
    status: item.status || "unknown",
  }));
}

function provenanceFor(item) {
  return {
    id: item.ref_id,
    title: item.title || item.ref_id,
    why_eligible: item.source_record_type === "memory_candidate" ? `explicit decision ${item.decision_id}` : "approved artifact ledger record",
    source_evidence_refs: item.source_feedback_ids || [item.status],
    promotion_status: item.promotion_decision || item.status,
    request_projection: item.summary || "eligible for next context bundle",
    feedback_effect: "included in context_bundle.included_refs only; no durable memory write",
    status: item.promotion_decision ? "promotion decision ready" : "review ready",
  };
}

function productionTimeline(payload, context, ready) {
  return [
    step("Project", "review ready", payload.project_input?.project_id || payload.loop_id),
    step("Assets", "review ready", `${arrayValue(payload.artifact_ledger).length} ledger records`),
    step("Memory Loaded", context.included.length ? "review ready" : "missing", `${context.included.length} included refs`),
    step("Baseline Run", "planned", "provider execution is outside this static slice"),
    step("Memory-backed Run", "planned", "next pass uses context bundle only after review"),
    step("Review", context.blocked.length ? "blocked" : "review ready", `${context.blocked.length} blocked refs`),
    step("Feedback", "review ready", `${arrayValue(payload.feedback_events).length} feedback events`),
    step("Next Pass", ready ? "ready" : "blocked", "context bundle is read-only"),
  ];
}

function indexesFor(payload) {
  const artifacts = new Map(arrayValue(payload.artifact_ledger).filter((item) => item.ref_id).map((item) => [String(item.ref_id), item]));
  const feedback = new Map(arrayValue(payload.feedback_events).filter((item) => item.feedback_id).map((item) => [String(item.feedback_id), item]));
  const candidates = new Map(arrayValue(payload.memory_candidates).filter((item) => item.candidate_id).map((item) => [String(item.candidate_id), item]));
  const decisions = new Map(arrayValue(payload.promotion_decisions).filter((item) => item.decision_id).map((item) => [String(item.decision_id), item]));
  const decisionsByCandidate = new Map();
  for (const decision of decisions.values()) {
    if (decision.candidate_id) decisionsByCandidate.set(String(decision.candidate_id), decision);
  }
  return { artifacts, feedback, candidates, decisions, decisionsByCandidate };
}

function requestedRefs(payload) {
  return arrayValue(payload.next_pass_request?.requested_refs).map((item) => String(item));
}

function blockedRef(refId, sourceType, reason, status) {
  return { ref_id: refId, source_record_type: sourceType, reason, status: String(status || "unknown") };
}

function recordSummary(payload) {
  return [
    `${arrayValue(payload.artifact_ledger).length} artifacts`,
    `${arrayValue(payload.feedback_events).length} feedback events`,
    `${arrayValue(payload.memory_candidates).length} candidates`,
    `${arrayValue(payload.promotion_decisions).length} decisions`,
  ].join(" / ");
}

function control(label, passed) {
  return { label, status: passed ? "review ready" : "blocked", detail: passed ? "confirmed by selected loop" : "not confirmed" };
}

function boundaryItems(boundaries = {}) {
  return [
    { label: "human acceptance", status: "blocked", detail: boundaries.human_acceptance || "not_reviewed" },
    { label: "business validation", status: "blocked", detail: boundaries.business_validation || "not_validated" },
    { label: "durable memory runtime", status: "blocked", detail: boundaries.durable_memory_runtime || "not_implemented" },
    { label: "provider success", status: "blocked", detail: boundaries.provider_success || "not_attempted" },
  ];
}

function step(label, status, detail) {
  return { label, status, detail: detail || "not recorded" };
}

function isProductionLoopArtifact(artifact) {
  return artifact?.artifactType === PRODUCTION_MEMORY_LOOP_TYPE && artifact?.payload?.kind === PRODUCTION_MEMORY_LOOP_TYPE;
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
