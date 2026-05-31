const LOULAN_PACKAGE_TYPE = "agentflow_loulan_memory_package";

export function isLoulanMemoryPackageArtifact(artifact) {
  return artifact?.artifactType === LOULAN_PACKAGE_TYPE && artifact?.payload?.artifact_type === LOULAN_PACKAGE_TYPE;
}

export function buildLoulanWorkbenchPackageView(workspace, fallback) {
  const artifact = workspace?.loulanPackage;
  if (!isLoulanMemoryPackageArtifact(artifact)) return fallback;
  const payload = artifact.payload;
  const project = payload.project || {};
  const safety = payload.provider_route_safety || {};
  const nextContext = payload.next_context_bundle_draft || {};
  const assets = (payload.asset_summary?.assets || []).slice(0, 10);
  const eligibleRefs = nextContext.eligible_memory_refs || [];
  const blockedRefs = nextContext.blocked_memory_refs || [];
  return {
    ...fallback,
    contract_type: LOULAN_PACKAGE_TYPE,
    state: payload.promotion_gates?.overall_status === "ready" ? "promotion decision ready" : "blocked",
    project: {
      title: project.title || "Loulan pilot package",
      brief: `${project.title || "Loulan pilot package"}; ${payload.package_id || "loulan package"}; ${project.current_phase || "current phase unknown"}`,
      format: project.target_format || LOULAN_PACKAGE_TYPE,
      route: "selected Loulan local package; no provider call",
    },
    assets: assets.map((asset) => ({
      id: asset.memory_ref,
      label: asset.label || asset.asset_id,
      detail: `${asset.status}; ${asset.output_ref || "no output ref"}`,
      status: asset.eligible_for_context ? "approved" : "blocked",
    })),
    bundle_summary: loulanBundleSummary(payload, eligibleRefs, blockedRefs),
    memory_loaded: loulanMemoryLoaded(eligibleRefs, blockedRefs),
    lanes: [
      {
        id: "baseline-lane",
        title: "Baseline Plan",
        status: "planned",
        input: "Loulan storyboard and selected assets without promoted memory projection",
        output: "request preview only; provider execution remains gated",
      },
      {
        id: "memory-lane",
        title: "Memory-backed Plan",
        status: eligibleRefs.length ? "planned" : "blocked",
        input: "same storyboard plus eligible approved asset memory refs",
        output: eligibleRefs.length ? `${eligibleRefs.length} eligible refs can seed next context` : "blocked until promotion decision",
      },
    ],
    protocol_summary: loulanProtocolSummary(safety, payload.claim_boundaries),
    review: {
      storyboard_adherence: `${payload.shot_summary?.total_shots || 0} Loulan shots indexed for review.`,
      visual_consistency: `${payload.asset_summary?.total_assets || 0} character assets; ${payload.asset_summary?.rejected_asset_count || 0} rejected refs blocked.`,
      boundary: "Loulan pilot package is structure evidence, not human acceptance.",
    },
    feedback: {
      status: "planned",
      summary: "Capture human review before promoting Loulan candidate memory.",
    },
    feedback_draft: loulanFeedbackDraft(payload),
    next_pass: {
      status: payload.promotion_gates?.overall_status === "ready" ? "promotion decision ready" : "blocked",
      action: `${eligibleRefs.length} eligible refs, ${blockedRefs.length} blocked refs; durable Memory runtime is not implemented.`,
    },
    artifact_inspector: loulanInspector(payload),
    timeline: loulanTimeline(payload),
  };
}

function loulanBundleSummary(payload, eligibleRefs, blockedRefs) {
  return [
    { id: "project", title: "Loulan pilot package", status: "review ready", detail: payload.project?.source_root_label || "selected package" },
    { id: "shots", title: "Shot manifest", status: "review ready", detail: `${payload.shot_summary?.total_shots || 0} shots indexed` },
    { id: "assets", title: "Asset memory", status: blockedRefs.length ? "blocked" : "review ready", detail: `${eligibleRefs.length} eligible, ${blockedRefs.length} blocked` },
    { id: "api", title: "API workbench skeleton", status: "planned", detail: "request preview only; live provider calls blocked by default" },
  ];
}

function loulanMemoryLoaded(eligibleRefs, blockedRefs) {
  const eligible = eligibleRefs.map((ref) => ({
    id: ref,
    title: ref,
    why_eligible: "approved/promoted status with source hash present",
    source_evidence_refs: [ref],
    promotion_status: "approved",
    request_projection: "eligible for next context bundle after promotion review",
    feedback_effect: "can reduce repeated character and asset restatement",
  }));
  const blocked = blockedRefs.slice(0, 8).map((ref) => ({
    id: ref,
    title: ref,
    why_eligible: "blocked until human review or repair",
    source_evidence_refs: [ref],
    promotion_status: "blocked",
    request_projection: "not loaded into next context",
    feedback_effect: "operator must repair, reject, or promote explicitly",
  }));
  return [...eligible, ...blocked];
}

function loulanProtocolSummary(safety, boundaries = {}) {
  return {
    title: "Loulan memory production protocol",
    status: safety.image_generation === "blocked_until_api_workbench" ? "blocked" : "planned",
    controls: [
      { label: "source project package", status: "review ready", detail: "explicit selected JSON package only" },
      { label: "image route", status: safety.image_generation === "blocked_until_api_workbench" ? "blocked" : "planned", detail: safety.image_generation || "unknown" },
      { label: "video route", status: "planned", detail: safety.video_generation || "dry_run_only" },
      { label: "request preview", status: "planned", detail: String(Boolean(safety.request_preview_only)) },
    ],
    boundaries: [
      { label: "human acceptance", status: "blocked", detail: boundaries.human_acceptance || "not_acceptance" },
      { label: "business validation", status: "blocked", detail: boundaries.business_validation || "not_validated" },
      { label: "durable memory runtime", status: "blocked", detail: boundaries.durable_memory_runtime || "not_implemented" },
    ],
  };
}

function loulanFeedbackDraft(payload) {
  const event = {
    schema_version: "0.1.0",
    artifact_type: "agentflow_feedback_event",
    target_type: "loulan_memory_package",
    target_id: payload.package_id,
    decision: "note",
    draft_status: "draft_not_persisted",
    reason_tags: ["loulan_pilot", "promotion_decision_required"],
    writes_long_term_memory: false,
  };
  return {
    mode: "loulan_package",
    status: "draft_not_persisted",
    title: "Loulan Feedback Draft",
    detail: "Browser-local preview; copy for review, do not persist as durable memory.",
    json_text: JSON.stringify(event, null, 2),
    copy_enabled: true,
  };
}

function loulanInspector(payload) {
  return [
    {
      id: "loulan_package",
      title: "Loulan package",
      status: "review ready",
      focus_targets: ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"],
      detail: payload.package_id,
      facts: [
        { label: "provider_calls_started", value: String(payload.provider_calls_started) },
        { label: "writes_long_term_memory", value: String(payload.writes_long_term_memory) },
      ],
    },
  ];
}

function loulanTimeline(payload) {
  return (payload.canvas_nodes || []).map((node) => ({
    label: node.label,
    status: node.status,
    detail: node.id,
  }));
}
