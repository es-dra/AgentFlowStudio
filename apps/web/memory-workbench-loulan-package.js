import { loulanInspector, loulanTimeline } from "./memory-workbench-loulan-artifacts.js";

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
  const decisionWorksheet = workspace?.loulanDecisionWorksheet?.payload || null;
  const decisionIntake = workspace?.loulanDecisionIntakeReport?.payload || null;
  const contextProjection = workspace?.loulanContextBundleProjection?.payload || null;
  const project = payload.project || {};
  const safety = payload.provider_route_safety || {};
  const b01FeedbackGate = payload.feedback_loop_gates?.b01 || null;
  const b01DecisionCrosswalk = payload.feedback_loop_gates?.b01_decision_crosswalk || null;
  const b01OperatorEntrypoint = payload.feedback_loop_gates?.b01_operator_entrypoint || null;
  const nextContext = payload.next_context_bundle_draft || {};
  const inventory = payload.asset_inventory || {};
  const projectAudits = payload.project_audits || {};
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
    bundle_summary: loulanBundleSummary(payload, eligibleRefs, blockedRefs, apiPlan, reviewPack, decisionTemplate, decisionReview, decisionWorksheet, decisionIntake, contextProjection, b01FeedbackGate, b01DecisionCrosswalk, b01OperatorEntrypoint, projectAudits),
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
    protocol_summary: loulanProtocolSummary(safety, payload.claim_boundaries, apiPlan, reviewPack, decisionTemplate, decisionReview, decisionWorksheet, decisionIntake, contextProjection, b01FeedbackGate, b01DecisionCrosswalk, b01OperatorEntrypoint, projectAudits),
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
      status: loulanNextPassStatus(payload, reviewPack, decisionTemplate, decisionReview, decisionWorksheet, decisionIntake, contextProjection),
      action: loulanNextPassAction(eligibleRefs, blockedRefs, apiPlan, reviewPack, decisionTemplate, decisionReview, decisionWorksheet, decisionIntake, contextProjection),
    },
    artifact_inspector: loulanInspector(payload, apiPlan, reviewPack, decisionTemplate, decisionWorksheet, contextProjection),
    timeline: loulanTimeline(payload, apiPlan, reviewPack, decisionTemplate, decisionReview, decisionWorksheet, decisionIntake, contextProjection),
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

function loulanBundleSummary(payload, eligibleRefs, blockedRefs, apiPlan, reviewPack, decisionTemplate, decisionReview, decisionWorksheet, decisionIntake, contextProjection, b01FeedbackGate = null, b01DecisionCrosswalk = null, b01OperatorEntrypoint = null, projectAudits = {}) {
  const requestCount = apiPlan?.request_manifest?.requests?.length || 0;
  const inventory = payload.asset_inventory || {};
  const items = [
    { id: "project", title: "Loulan pilot package", status: "review ready", detail: payload.project?.source_root_label || "selected package" },
    { id: "project-audits", title: "Project audits", status: auditStatus(projectAudits, "manifest_reference") === "pass" && auditStatus(projectAudits, "text_encoding") === "pass" ? "pass" : "review", detail: auditBundleDetail(projectAudits) },
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
  if (b01FeedbackGate) {
    items.push({
      id: "b01-feedback-loop-gate",
      title: "B01 feedback loop gate",
      status: b01FeedbackGate.status || "unknown",
      detail: `${b01FeedbackGate.pending_decisions || 0} pending decisions; context ready: ${String(b01FeedbackGate.context_projection_ready === true)}`,
    });
  }
  if (b01DecisionCrosswalk) {
    const localGate = b01DecisionCrosswalk.local_shot_gate || {};
    const importGate = b01DecisionCrosswalk.afs_b01_import_gate || {};
    items.push({
      id: "b01-decision-crosswalk",
      title: "B01 decision crosswalk",
      status: b01DecisionCrosswalk.status || "unknown",
      detail: `${localGate.decision_count || 0} local shot decisions; ${importGate.decision_count || 0} AFS import slots`,
    });
  }
  if (b01OperatorEntrypoint) items.push({ id: "b01-operator-entrypoint", title: "B01 operator entrypoint", status: b01OperatorEntrypoint.status || "unknown", detail: `${b01OperatorEntrypoint.pending_decisions || 0} pending decisions; ${b01OperatorEntrypoint.operator_steps || 0} operator steps` });
  if (decisionTemplate) {
    items.push({
      id: "decision-template",
      title: isDecisionImport(decisionTemplate) ? "B01 decision import" : "Decision template",
      status: decisionTemplate.template_status || "pending_human_input",
      detail: decisionTemplateDetail(decisionTemplate),
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
  if (decisionWorksheet) {
    items.push({
      id: "decision-worksheet",
      title: "Decision worksheet",
      status: decisionWorksheet.worksheet_status || "awaiting_manual_decisions",
      detail: `${decisionWorksheet.decision_rows?.length || 0} manual-fill rows; acceptance not recorded`,
    });
  }
  if (decisionIntake) {
    items.push({
      id: "decision-intake",
      title: "Decision intake report",
      status: decisionIntake.intake_status || "blocked",
      detail: `${decisionIntake.intake_summary?.ready_count || 0} ready; ${decisionIntake.intake_summary?.pending_count || 0} pending`,
    });
  }
  if (contextProjection) {
    const intakeGate = contextProjection.decision_intake_gate?.status || "not_supplied";
    items.push({
      id: "context-bundle",
      title: "Context bundle projection",
      status: contextProjection.context_bundle?.status || contextProjection.decision_audit?.status || "blocked",
      detail: `${contextProjection.context_bundle?.memory_refs?.length || 0} memory refs; ${contextProjection.context_bundle?.blocked_refs?.length || 0} blocked; intake gate: ${intakeGate}`,
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

function loulanProtocolSummary(safety, boundaries = {}, apiPlan = null, reviewPack = null, decisionTemplate = null, decisionReview = null, decisionWorksheet = null, decisionIntake = null, contextProjection = null, b01FeedbackGate = null, b01DecisionCrosswalk = null, b01OperatorEntrypoint = null, projectAudits = {}) {
  return {
    title: "Loulan memory production protocol",
    status: contextProjection?.context_bundle?.status || (safety.image_generation === "blocked_until_api_workbench" ? "blocked" : "planned"),
    controls: [
      { label: "source project package", status: "review ready", detail: "explicit selected JSON package only" },
      { label: "manifest reference audit", status: auditStatus(projectAudits, "manifest_reference"), detail: auditControlDetail(projectAudits, "manifest_reference", [["errors", "errors"], ["invalid asset types", "invalid_asset_types"], ["invalid statuses", "invalid_statuses"]]) },
      { label: "text encoding audit", status: auditStatus(projectAudits, "text_encoding"), detail: auditControlDetail(projectAudits, "text_encoding", [["errors", "errors"]]) },
      { label: "phase gate audit", status: auditStatus(projectAudits, "phase_gate"), detail: auditControlDetail(projectAudits, "phase_gate", [["failures", "failures"], ["pending B01", "pending_b01_decisions"]]) },
      { label: "image route", status: safety.image_generation === "blocked_until_api_workbench" ? "blocked" : "planned", detail: safety.image_generation || "unknown" },
      { label: "video route", status: "planned", detail: safety.video_generation || "dry_run_only" },
      { label: "request preview", status: "planned", detail: String(Boolean(safety.request_preview_only)) },
      { label: "API adapter", status: apiPlan ? "review ready" : "planned", detail: apiPlan?.provider_adapter?.adapter_id || "not selected" },
      { label: "api context intake gate", status: apiPlan?.context_projection?.decision_intake_gate?.status || "not_recorded", detail: apiPlan ? `context ready: ${String(apiPlan.context_projection?.decision_intake_gate?.context_bundle_command_ready === true)}` : "not prepared" },
      { label: "QA gate", status: apiPlan?.qa_gate?.status || "planned", detail: apiPlan?.promotion_gate?.status || "waiting for API workbench plan" },
      { label: "B01 feedback loop", status: b01FeedbackGate?.status || "not_supplied", detail: b01FeedbackGate ? `${b01FeedbackGate.pending_decisions || 0} pending; context ready: ${String(b01FeedbackGate.context_projection_ready === true)}` : "not supplied" },
      { label: "B01 decision crosswalk", status: b01DecisionCrosswalk?.status || "not_supplied", detail: b01DecisionCrosswalk ? `${b01DecisionCrosswalk.local_shot_gate?.decision_count || 0} local shot decisions; ${b01DecisionCrosswalk.afs_b01_import_gate?.decision_count || 0} AFS import slots` : "not supplied" },
      { label: "B01 operator entrypoint", status: b01OperatorEntrypoint?.status || "not_supplied", detail: b01OperatorEntrypoint ? `${b01OperatorEntrypoint.pending_decisions || 0} pending; ${b01OperatorEntrypoint.operator_steps || 0} operator steps` : "not supplied" },
      { label: "human review", status: reviewPack?.review_scope?.evidence_status || "planned", detail: reviewPack?.review_scope?.status || "not prepared" },
      { label: isDecisionImport(decisionTemplate) ? "B01 decision import" : "decision template", status: decisionTemplate?.template_status || "planned", detail: decisionTemplate ? `${decisionTemplateDetail(decisionTemplate)}; no acceptance` : "not prepared" },
      { label: "decision review", status: decisionReview?.review_status || "planned", detail: decisionReview ? `${decisionReview.decision_summary?.pending_count || 0} pending; no acceptance` : "not prepared" },
      { label: "decision worksheet", status: decisionWorksheet?.worksheet_status || "planned", detail: decisionWorksheet ? `${decisionWorksheet.decision_rows?.length || 0} manual-fill rows; no acceptance` : "not prepared" },
      { label: "decision intake", status: decisionIntake?.intake_status || "planned", detail: decisionIntake ? `context ready: ${String(decisionIntake.context_bundle_command_ready)}` : "not prepared" },
      { label: "context bundle", status: contextProjection?.context_bundle?.status || "planned", detail: contextProjection ? `${contextProjection.decision_audit?.status || "decision audit not run"}; intake gate: ${contextProjection.decision_intake_gate?.status || "not_supplied"}` : "waiting for human decisions" },
    ],
    boundaries: [
      { label: "human acceptance", status: "blocked", detail: boundaries.human_acceptance || "not_acceptance" },
      { label: "business validation", status: "blocked", detail: boundaries.business_validation || "not_validated" },
      { label: "durable memory runtime", status: "blocked", detail: boundaries.durable_memory_runtime || "not_implemented" },
    ],
  };
}

function auditStatus(projectAudits, key) { return projectAudits?.[key]?.status || "not_provided"; }

function auditRef(projectAudits, key) { const audit = projectAudits?.[key] || {}; return audit.report_ref || audit.artifact_ref || "not provided"; }

function auditSummary(projectAudits, key) { const summary = projectAudits?.[key]?.summary; return summary && typeof summary === "object" && !Array.isArray(summary) ? summary : {}; }

function auditSummaryValue(projectAudits, key, field) { const value = auditSummary(projectAudits, key)[field]; return value ?? "unknown"; }

function auditBundleDetail(projectAudits) {
  return `manifest reference: ${auditStatus(projectAudits, "manifest_reference")} (errors ${auditSummaryValue(projectAudits, "manifest_reference", "errors")}; invalid types ${auditSummaryValue(projectAudits, "manifest_reference", "invalid_asset_types")}; invalid statuses ${auditSummaryValue(projectAudits, "manifest_reference", "invalid_statuses")}); text encoding: ${auditStatus(projectAudits, "text_encoding")} (errors ${auditSummaryValue(projectAudits, "text_encoding", "errors")}); phase gate: ${auditStatus(projectAudits, "phase_gate")} (failures ${auditSummaryValue(projectAudits, "phase_gate", "failures")})`;
}

function auditControlDetail(projectAudits, key, fields) {
  const details = fields.map(([label, field]) => `${label}: ${auditSummaryValue(projectAudits, key, field)}`);
  return `${auditRef(projectAudits, key)}; ${details.join("; ")}`;
}

function loulanNextPassStatus(payload, reviewPack, decisionTemplate, decisionReview, decisionWorksheet, decisionIntake, contextProjection) {
  return contextProjection?.context_bundle?.status
    || decisionIntake?.intake_status
    || decisionWorksheet?.worksheet_status
    || decisionReview?.review_status
    || decisionTemplate?.template_status
    || reviewPack?.next_pass_readiness?.status
    || (payload.promotion_gates?.overall_status === "ready" ? "promotion decision ready" : "blocked");
}

function loulanNextPassAction(eligibleRefs, blockedRefs, apiPlan, reviewPack = null, decisionTemplate = null, decisionReview = null, decisionWorksheet = null, decisionIntake = null, contextProjection = null) {
  const requestCount = apiPlan?.request_manifest?.requests?.length || 0;
  const reviewStatus = reviewPack?.next_pass_readiness?.status || "human review not prepared";
  const decisionStatus = decisionTemplate?.template_status ? `${isDecisionImport(decisionTemplate) ? "Decision import" : "Decision template"}: ${decisionTemplate.template_status}; ` : "";
  const decisionReviewStatus = decisionReview?.review_status ? `Decision review: ${decisionReview.review_status}; ` : "";
  const decisionWorksheetStatus = decisionWorksheet?.worksheet_status ? `Decision worksheet: ${decisionWorksheet.worksheet_status}; ` : "";
  const decisionIntakeStatus = decisionIntake?.intake_status ? `Decision intake: ${decisionIntake.intake_status}; ` : "";
  const projectionStatus = contextProjection?.decision_audit?.status ? `Decision audit: ${contextProjection.decision_audit.status}; ` : "";
  return `${decisionStatus}${decisionReviewStatus}${decisionWorksheetStatus}${decisionIntakeStatus}${projectionStatus}${eligibleRefs.length} eligible refs, ${blockedRefs.length} blocked refs, ${requestCount} request previews; ${reviewStatus}; durable Memory runtime is not implemented.`;
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

function isDecisionImport(decisionTemplate = null) {
  return Boolean(decisionTemplate?.import_summary);
}

function decisionTemplateDetail(decisionTemplate) {
  if (isDecisionImport(decisionTemplate)) {
    const summary = decisionTemplate.import_summary || {};
    return `${summary.imported_ready_decisions || 0} imported ready; ${summary.pending_decisions || 0} pending; ${summary.skipped_local_items || 0} skipped`;
  }
  return `${decisionTemplate.decisions?.length || 0} slots; acceptance not recorded`;
}
