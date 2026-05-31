const LOULAN_PACKAGE_TYPE = "agentflow_loulan_memory_package";

export function isLoulanMemoryPackageArtifact(artifact) {
  return artifact?.artifactType === LOULAN_PACKAGE_TYPE && artifact?.payload?.artifact_type === LOULAN_PACKAGE_TYPE;
}

export function buildLoulanWorkbenchPackageView(workspace, fallback) {
  const artifact = workspace?.loulanPackage;
  if (!isLoulanMemoryPackageArtifact(artifact)) return fallback;
  const payload = artifact.payload;
  const apiPlan = workspace?.loulanApiWorkbenchPlan?.payload || null;
  const reviewPack = workspace?.loulanHumanReviewPack?.payload || null;
  const decisionTemplate = workspace?.loulanDecisionTemplate?.payload || null;
  const decisionReview = workspace?.loulanDecisionReviewPack?.payload || null;
  const contextProjection = workspace?.loulanContextBundleProjection?.payload || null;
  const project = payload.project || {};
  const safety = payload.provider_route_safety || {};
  const nextContext = payload.next_context_bundle_draft || {};
  const inventory = payload.asset_inventory || {};
  const assets = loulanDisplayAssets(payload).slice(0, 10);
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
      detail: `${asset.asset_type || "asset"}; ${asset.status}; ${asset.current_ref || asset.output_ref || "no output ref"}`,
      status: asset.eligible_for_context ? "approved" : "blocked",
    })),
    bundle_summary: loulanBundleSummary(payload, eligibleRefs, blockedRefs, apiPlan, reviewPack, decisionTemplate, decisionReview, contextProjection),
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
    protocol_summary: loulanProtocolSummary(safety, payload.claim_boundaries, apiPlan, reviewPack, decisionTemplate, decisionReview, contextProjection),
    review: {
      storyboard_adherence: reviewPack ? `${reviewPack.review_scope?.shot_count || 0} ${reviewPack.review_scope?.block_id || "Loulan"} shots queued for human review.` : `${payload.shot_summary?.total_shots || 0} Loulan shots indexed for review.`,
      visual_consistency: reviewPack ? `${reviewPack.asset_review?.candidate_memory_refs?.length || 0} candidate memory refs need decisions; ${reviewPack.asset_review?.approved_or_promoted_memory_refs?.length || 0} refs already reusable.` : `${inventory.total_assets || payload.asset_summary?.total_assets || 0} assets; ${blockedRefs.length} refs blocked.`,
      boundary: "Loulan pilot package is structure evidence, not human acceptance.",
    },
    feedback: {
      status: reviewPack?.feedback_event_draft?.draft_status || "planned",
      summary: reviewPack ? "Human review feedback draft is prepared but not persisted." : "Capture human review before promoting Loulan candidate memory.",
    },
    feedback_draft: loulanFeedbackDraft(payload, reviewPack),
    next_pass: {
      status: loulanNextPassStatus(payload, reviewPack, decisionReview, contextProjection),
      action: loulanNextPassAction(eligibleRefs, blockedRefs, apiPlan, reviewPack, decisionTemplate, decisionReview, contextProjection),
    },
    artifact_inspector: loulanInspector(payload, apiPlan, reviewPack, decisionTemplate, contextProjection),
    timeline: loulanTimeline(payload, apiPlan, reviewPack, decisionTemplate, decisionReview, contextProjection),
  };
}

function loulanDisplayAssets(payload) {
  const seen = new Set();
  const assets = [];
  for (const source of [
    payload.asset_inventory?.eligible_assets || [],
    payload.asset_inventory?.assets || [],
    payload.asset_summary?.assets || [],
  ]) {
    for (const asset of source) {
      const id = asset.memory_ref || asset.asset_id;
      if (!id || seen.has(id)) continue;
      seen.add(id);
      assets.push(asset);
    }
  }
  return assets;
}

function loulanBundleSummary(payload, eligibleRefs, blockedRefs, apiPlan, reviewPack, decisionTemplate, decisionReview, contextProjection) {
  const requestCount = apiPlan?.request_manifest?.requests?.length || 0;
  const inventory = payload.asset_inventory || {};
  const items = [
    { id: "project", title: "Loulan pilot package", status: "review ready", detail: payload.project?.source_root_label || "selected package" },
    { id: "shots", title: "Shot manifest", status: "review ready", detail: `${payload.shot_summary?.total_shots || 0} shots indexed` },
    { id: "assets", title: "Asset inventory", status: blockedRefs.length ? "blocked" : "review ready", detail: `${inventory.total_assets || payload.asset_summary?.total_assets || 0} assets; ${eligibleRefs.length} eligible, ${blockedRefs.length} blocked` },
    { id: "api", title: "API workbench skeleton", status: apiPlan ? "review ready" : "planned", detail: apiPlan ? `${requestCount} request previews; live calls blocked` : "request preview only; live provider calls blocked by default" },
  ];
  if (reviewPack) {
    items.push({
      id: "human-review",
      title: "Human review pack",
      status: reviewPack.review_scope?.evidence_status === "blocked" ? "blocked" : "review ready",
      detail: `${reviewPack.review_scope?.shot_count || 0} shots; acceptance not recorded`,
    });
  }
  if (decisionTemplate) {
    items.push({
      id: "decision-template",
      title: "Decision template",
      status: decisionTemplate.template_status || "pending_human_input",
      detail: `${decisionTemplate.decisions?.length || 0} slots; acceptance not recorded`,
    });
  }
  if (decisionReview) {
    items.push({
      id: "decision-review",
      title: "Decision review pack",
      status: decisionReview.review_status || "blocked",
      detail: `${decisionReview.decision_summary?.pending_count || 0} pending; ${decisionReview.decision_summary?.ready_count || 0} ready`,
    });
  }
  if (contextProjection) {
    items.push({
      id: "context-bundle",
      title: "Context bundle projection",
      status: contextProjection.context_bundle?.status || contextProjection.decision_audit?.status || "blocked",
      detail: `${contextProjection.context_bundle?.memory_refs?.length || 0} memory refs; ${contextProjection.context_bundle?.blocked_refs?.length || 0} blocked`,
    });
  }
  return items;
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

function loulanProtocolSummary(safety, boundaries = {}, apiPlan = null, reviewPack = null, decisionTemplate = null, decisionReview = null, contextProjection = null) {
  return {
    title: "Loulan memory production protocol",
    status: contextProjection?.context_bundle?.status || (safety.image_generation === "blocked_until_api_workbench" ? "blocked" : "planned"),
    controls: [
      { label: "source project package", status: "review ready", detail: "explicit selected JSON package only" },
      { label: "image route", status: safety.image_generation === "blocked_until_api_workbench" ? "blocked" : "planned", detail: safety.image_generation || "unknown" },
      { label: "video route", status: "planned", detail: safety.video_generation || "dry_run_only" },
      { label: "request preview", status: "planned", detail: String(Boolean(safety.request_preview_only)) },
      { label: "API adapter", status: apiPlan ? "review ready" : "planned", detail: apiPlan?.provider_adapter?.adapter_id || "not selected" },
      { label: "QA gate", status: apiPlan?.qa_gate?.status || "planned", detail: apiPlan?.promotion_gate?.status || "waiting for API workbench plan" },
      { label: "human review", status: reviewPack?.review_scope?.evidence_status || "planned", detail: reviewPack?.review_scope?.status || "not prepared" },
      { label: "decision template", status: decisionTemplate?.template_status || "planned", detail: decisionTemplate ? `${decisionTemplate.decisions?.length || 0} slots; no acceptance` : "not prepared" },
      { label: "decision review", status: decisionReview?.review_status || "planned", detail: decisionReview ? `${decisionReview.decision_summary?.pending_count || 0} pending; no acceptance` : "not prepared" },
      { label: "context bundle", status: contextProjection?.context_bundle?.status || "planned", detail: contextProjection?.decision_audit?.status || "waiting for human decisions" },
    ],
    boundaries: [
      { label: "human acceptance", status: "blocked", detail: boundaries.human_acceptance || "not_acceptance" },
      { label: "business validation", status: "blocked", detail: boundaries.business_validation || "not_validated" },
      { label: "durable memory runtime", status: "blocked", detail: boundaries.durable_memory_runtime || "not_implemented" },
    ],
  };
}

function loulanNextPassStatus(payload, reviewPack, decisionReview, contextProjection) {
  return contextProjection?.context_bundle?.status
    || decisionReview?.review_status
    || reviewPack?.next_pass_readiness?.status
    || (payload.promotion_gates?.overall_status === "ready" ? "promotion decision ready" : "blocked");
}

function loulanNextPassAction(eligibleRefs, blockedRefs, apiPlan, reviewPack = null, decisionTemplate = null, decisionReview = null, contextProjection = null) {
  const requestCount = apiPlan?.request_manifest?.requests?.length || 0;
  const reviewStatus = reviewPack?.next_pass_readiness?.status || "human review not prepared";
  const decisionStatus = decisionTemplate?.template_status ? `Decision template: ${decisionTemplate.template_status}; ` : "";
  const decisionReviewStatus = decisionReview?.review_status ? `Decision review: ${decisionReview.review_status}; ` : "";
  const projectionStatus = contextProjection?.decision_audit?.status ? `Decision audit: ${contextProjection.decision_audit.status}; ` : "";
  return `${decisionStatus}${decisionReviewStatus}${projectionStatus}${eligibleRefs.length} eligible refs, ${blockedRefs.length} blocked refs, ${requestCount} request previews; ${reviewStatus}; durable Memory runtime is not implemented.`;
}

function loulanFeedbackDraft(payload, reviewPack = null) {
  const event = reviewPack?.feedback_event_draft || {
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
    mode: reviewPack ? "loulan_human_review_pack" : "loulan_package",
    status: event.draft_status || "draft_not_persisted",
    title: reviewPack ? "Loulan Human Review Feedback Draft" : "Loulan Feedback Draft",
    detail: "Browser-local preview; copy for review, do not persist as durable memory.",
    json_text: JSON.stringify(event, null, 2),
    copy_enabled: true,
  };
}

function loulanInspector(payload, apiPlan = null, reviewPack = null, decisionTemplate = null, contextProjection = null) {
  const items = [
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
  if (apiPlan) {
    items.push({
      id: "loulan_api_workbench_plan",
      title: "Loulan API workbench plan",
      status: apiPlan.request_manifest?.status || "planned",
      focus_targets: ["baseline-run", "memory-backed-run", "review", "next-pass"],
      detail: `${apiPlan.provider_adapter?.adapter_id || "adapter"}; ${apiPlan.response_ledger?.status || "not_submitted"}`,
      facts: [
        { label: "dry_run_only", value: String(apiPlan.dry_run_only) },
        { label: "provider_calls_started", value: String(apiPlan.provider_calls_started) },
        { label: "requests", value: String(apiPlan.request_manifest?.requests?.length || 0) },
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
        { label: "human_acceptance_recorded", value: String(reviewPack.human_acceptance_recorded) },
        { label: "shots", value: String(reviewPack.review_scope?.shot_count || 0) },
        { label: "required_decisions", value: String(reviewPack.next_pass_readiness?.required_decisions?.length || 0) },
      ],
    });
  }
  return items;
}

function loulanTimeline(payload, apiPlan = null, reviewPack = null, decisionTemplate = null, decisionReview = null, contextProjection = null) {
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
  if (contextProjection) {
    nodes.push({
      label: "Context Bundle",
      status: contextProjection.context_bundle?.status || contextProjection.decision_audit?.status || "blocked",
      detail: contextProjection.decision_audit?.status || "decision audit not run",
    });
  }
  return nodes;
}
