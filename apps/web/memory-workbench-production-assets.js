import {
  action,
  arrayValue,
  assetFromBlocked,
  assetFromIncluded,
  boundaryItems,
  card,
  control,
  controlsFromPayload,
  genericStatus,
  lane,
  memoryFromIncluded,
  step,
} from "./memory-workbench-production-assets-shared.js";
import { buildAssetReviewScreen } from "./memory-workbench-production-asset-review-screen.js";

const ASSET_TYPES = {
  seed: "agentflow_production_memory_asset_profile_seed",
  profile: "agentflow_production_memory_asset_profile",
  readiness: "agentflow_production_memory_asset_profile_readiness",
  testPackage: "agentflow_production_memory_asset_test_package",
  providerPlan: "agentflow_production_memory_asset_provider_validation_plan",
  providerBlockers: "agentflow_production_memory_asset_provider_validation_blockers",
  providerResult: "agentflow_production_memory_asset_provider_validation_result",
  feedback: "agentflow_production_memory_asset_feedback_event",
  updateCandidate: "agentflow_production_memory_asset_profile_update_candidate",
  promotionDecision: "agentflow_production_memory_asset_profile_promotion_decision",
  version: "agentflow_production_memory_asset_profile_version",
  contextProjection: "agentflow_production_memory_asset_profile_context_projection",
  consistencyReview: "agentflow_production_memory_asset_consistency_review",
};

export function buildProductionMemoryAssetCockpitView(workspace, fallback) {
  const artifact = selectedAssetArtifact(workspace);
  if (!artifact) return fallback;

  const type = artifact.artifactType;
  if (type === ASSET_TYPES.contextProjection) {
    return contextProjectionView(artifact, fallback);
  }
  if (type === ASSET_TYPES.consistencyReview) {
    return consistencyReviewView(artifact, fallback);
  }
  return genericAssetView(artifact, fallback);
}

function selectedAssetArtifact(workspace) {
  return [
    workspace?.productionMemoryAssetConsistencyReview,
    workspace?.productionMemoryAssetProfileContextProjection,
    workspace?.productionMemoryAssetProfileVersion,
    workspace?.productionMemoryAssetProfilePromotionDecision,
    workspace?.productionMemoryAssetProfileUpdateCandidate,
    workspace?.productionMemoryAssetFeedbackEvent,
    workspace?.productionMemoryAssetTestPackage,
    workspace?.productionMemoryAssetProfileReadiness,
    workspace?.productionMemoryAssetProviderValidationResult,
    workspace?.productionMemoryAssetProviderValidationBlockers,
    workspace?.productionMemoryAssetProviderValidationPlan,
    workspace?.productionMemoryAssetProfile,
    workspace?.productionMemoryAssetProfileSeed,
  ].find((item) => item && item.payload?.kind === item.artifactType);
}

function contextProjectionView(artifact, fallback) {
  const payload = artifact.payload;
  const included = arrayValue(payload.included_refs);
  const blocked = arrayValue(payload.blocked_refs);
  const controls = controlsFromPayload(payload.controls, {
    profile_version_is_inclusion_authority: "profile version inclusion authority",
    provider_calls_not_started: "provider calls not started",
    writes_no_long_term_memory: "durable memory write disabled",
    writes_no_company_kb: "Company KB write disabled",
    blocked_refs_excluded: "blocked refs excluded",
  });
  const ready = payload.projection_status === "ready" && payload.provider_calls_started === false;
  return {
    ...fallback,
    state: ready ? "asset context projection ready" : "blocked",
    project: {
      title: payload.project_id || payload.projection_id || artifact.fileName,
      brief: `Asset profile context projection: ${payload.projection_status || "unknown"}`,
      format: ASSET_TYPES.contextProjection,
      route: "selected local JSON only; read-only no-provider asset context projection",
    },
    workflow_actions: [
      action("inspect_asset_context_projection", "Inspect projection", ready ? "review ready" : "blocked", "project"),
      action("inspect_included_profiles", "Inspect included", included.length ? "ready" : "missing", "memory-loaded"),
      action("inspect_blocked_profiles", "Inspect blocked", blocked.length ? "blocked" : "review ready", "review"),
      action("prepare_next_context", "Prepare context", ready ? "ready" : "blocked", "next-pass"),
    ],
    assets: [
      ...included.map((item) => assetFromIncluded(item)),
      ...blocked.map((item) => assetFromBlocked(item)),
    ],
    bundle_summary: [
      card("included_profile_refs", "Included profile refs", included.length ? "review ready" : "missing", `${included.length} profile refs available for next task context`),
      card("blocked_profile_refs", "Blocked profile refs", blocked.length ? "blocked" : "review ready", `${blocked.length} profile refs excluded from next task context`),
      card("context_policy", "Context policy", "review ready", payload.context_payload?.context_projection_policy || "not recorded"),
    ],
    memory_loaded: included.map((item) => memoryFromIncluded(item)),
    lanes: [
      lane("asset-profile-context", "Asset profile context", ready ? "ready" : "blocked", payload.projection_id || "asset context", payload.projection_status || "unknown"),
      lane("included-profiles", "Included profiles", included.length ? "review ready" : "missing", `${included.length} refs`, "eligible profile versions"),
      lane("blocked-profiles", "Blocked profiles", blocked.length ? "blocked" : "review ready", `${blocked.length} refs`, "excluded profile versions"),
    ],
    protocol_summary: {
      title: "Production memory asset profile context projection",
      status: ready ? "review ready" : "blocked",
      controls,
      boundaries: boundaryItems(payload),
    },
    review: {
      storyboard_adherence: `${included.length} included profile refs`,
      visual_consistency: `${blocked.length} blocked profile refs`,
      boundary: "asset profile context only / no provider call / no Company KB write",
    },
    feedback: {
      status: "review ready",
      summary: "Use as next-task asset context only; do not treat as acceptance or durable memory.",
    },
    asset_review_screen: buildAssetReviewScreen(payload),
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: ready ? "use_asset_profiles_for_next_task_context" : "resolve_asset_context_blockers",
    },
    timeline: [
      step("Projection", ready ? "ready" : "blocked", payload.projection_id),
      step("Included profiles", included.length ? "review ready" : "missing", `${included.length} refs`),
      step("Blocked profiles", blocked.length ? "blocked" : "review ready", `${blocked.length} refs`),
      step("Boundaries", "blocked", "not durable memory / not Company KB promotion"),
    ],
  };
}

function consistencyReviewView(artifact, fallback) {
  const payload = artifact.payload;
  const findings = arrayValue(payload.consistency_findings);
  const blocked = arrayValue(payload.blocked_findings);
  const ready = payload.review_status === "ready_for_operator_review"
    && payload.provider_calls_started === false
    && blocked.length === 0;
  return {
    ...fallback,
    state: ready ? "asset consistency review ready" : "blocked",
    project: {
      title: payload.project_id || payload.review_id || artifact.fileName,
      brief: `Asset consistency review: ${payload.overall_consistency_result || "unknown"}`,
      format: ASSET_TYPES.consistencyReview,
      route: "selected local JSON only; read-only no-provider asset consistency review",
    },
    workflow_actions: [
      action("inspect_asset_consistency_review", "Inspect review", ready ? "review ready" : "blocked", "project"),
      action("inspect_consistency_findings", "Inspect findings", findings.length ? "review ready" : "missing", "review"),
      action("inspect_blocked_findings", "Inspect blocked", blocked.length ? "blocked" : "review ready", "assets"),
      action("record_tester_feedback", "Record feedback", ready ? "ready" : "blocked", "feedback"),
    ],
    assets: [
      ...findings.map((item) => ({
        id: item.profile_ref,
        label: item.profile_ref,
        detail: `${item.profile_kind || "profile"} ${item.profile_version || "version"}: ${item.review_result || "unknown"}`,
        status: item.review_result === "kept" ? "review ready" : "blocked",
      })),
      ...blocked.map((item) => ({
        id: item.profile_ref,
        label: item.profile_ref,
        detail: item.reason || "blocked finding",
        status: "blocked",
      })),
    ],
    bundle_summary: [
      card("overall_consistency", "Overall consistency", ready ? "review ready" : "blocked", payload.overall_consistency_result || "unknown"),
      card("consistency_findings", "Consistency findings", findings.length ? "review ready" : "missing", `${findings.length} findings available for tester review`),
      card("blocked_findings", "Blocked findings", blocked.length ? "blocked" : "review ready", `${blocked.length} findings excluded from reuse decisions`),
    ],
    memory_loaded: findings.map((item) => ({
      id: item.profile_ref,
      title: item.profile_ref,
      why_eligible: `review result ${item.review_result || "unknown"} from ${payload.review_id || "asset review"}`,
      source_evidence_refs: arrayValue(item.evidence_refs),
      promotion_status: item.review_result || "unknown",
      request_projection: arrayValue(item.drift_observations).join(" / ") || "no drift recorded",
      feedback_effect: "consistency review does not auto-create feedback, profile update, or promotion decision",
      status: item.review_result === "kept" ? "review ready" : "blocked",
    })),
    lanes: [
      lane("asset-consistency-review", "Asset consistency review", ready ? "ready" : "blocked", payload.source_context_projection_ref || "context projection", payload.review_status || "unknown"),
      lane("consistency-findings", "Consistency findings", findings.length ? "review ready" : "missing", `${findings.length} findings`, payload.overall_consistency_result || "unknown"),
      lane("blocked-findings", "Blocked findings", blocked.length ? "blocked" : "review ready", `${blocked.length} findings`, "excluded from next profile action"),
    ],
    protocol_summary: {
      title: "Production memory asset consistency review",
      status: ready ? "review ready" : "blocked",
      controls: controlsFromPayload(payload.controls, {
        asset_feedback_not_auto_created: "asset feedback not auto-created",
        profile_update_candidate_not_auto_created: "profile update candidate not auto-created",
        promotion_decision_not_auto_created: "promotion decision not auto-created",
        provider_calls_not_started: "provider calls not started",
        writes_no_long_term_memory: "durable memory write disabled",
        writes_no_company_kb: "Company KB write disabled",
      }),
      boundaries: boundaryItems(payload),
    },
    review: {
      storyboard_adherence: `${findings.length} consistency findings`,
      visual_consistency: payload.overall_consistency_result || "unknown",
      boundary: "asset consistency review only / no automatic feedback or promotion",
    },
    feedback: {
      status: "review ready",
      summary: "Tester feedback can be recorded later as a separate feedback event.",
    },
    asset_review_screen: buildAssetReviewScreen(payload),
    next_pass: {
      status: ready ? "ready" : "blocked",
      action: ready ? "record_tester_feedback_or_continue_next_context" : "resolve_asset_review_blockers",
    },
    timeline: [
      step("Context projection", "review ready", payload.source_context_projection_ref),
      step("Consistency review", ready ? "ready" : "blocked", payload.review_id),
      step("Findings", findings.length ? "review ready" : "missing", `${findings.length} findings`),
      step("Non-claims", "blocked", "not human acceptance / not durable memory"),
    ],
  };
}

function genericAssetView(artifact, fallback) {
  const payload = artifact.payload;
  const status = genericStatus(payload);
  const title = payload.profile_id || payload.candidate_id || payload.decision_id || payload.version_id || payload.package_id || payload.project_id || artifact.fileName;
  return {
    ...fallback,
    state: status === "blocked" ? "blocked" : "asset cockpit ready",
    project: {
      title,
      brief: `Production memory asset artifact: ${status}`,
      format: artifact.artifactType,
      route: "selected local JSON only; read-only asset cockpit",
    },
    workflow_actions: [
      action("inspect_asset_artifact", "Inspect artifact", status === "blocked" ? "blocked" : "review ready", "project"),
      action("inspect_asset_boundaries", "Inspect boundaries", "blocked", "memory-loaded"),
      action("inspect_next_step", "Inspect next step", status === "blocked" ? "blocked" : "review ready", "next-pass"),
    ],
    assets: [{
      id: title,
      label: title,
      detail: artifact.sourceRole,
      status: status === "blocked" ? "blocked" : "review ready",
    }],
    bundle_summary: [
      card("asset_artifact", "Asset artifact", status === "blocked" ? "blocked" : "review ready", artifact.sourceRole),
      card("provider_boundary", "Provider boundary", payload.provider_calls_started === false ? "review ready" : "blocked", "provider calls not started"),
      card("company_kb_boundary", "Company KB boundary", payload.writes_company_kb === false ? "review ready" : "blocked", "Company KB write disabled"),
    ],
    memory_loaded: [{
      id: title,
      title,
      why_eligible: "selected asset artifact for read-only inspection",
      source_evidence_refs: arrayValue(payload.evidence_refs),
      promotion_status: status,
      request_projection: payload.review_dimension || payload.decision || payload.profile_version || "asset artifact",
      feedback_effect: "read-only cockpit does not create feedback, version, or promotion artifacts",
      status,
    }],
    lanes: [
      lane("asset-artifact", "Asset artifact", status === "blocked" ? "blocked" : "review ready", artifact.fileName, artifact.sourceRole),
      lane("asset-boundaries", "Asset boundaries", "blocked", "no automatic writes", "operator review required"),
    ],
    protocol_summary: {
      title: "Production memory asset cockpit",
      status: status === "blocked" ? "blocked" : "review ready",
      controls: [
        control("provider calls not started", payload.provider_calls_started === false),
        control("durable memory write disabled", payload.writes_long_term_memory === false),
        control("Company KB write disabled", payload.writes_company_kb === false),
      ],
      boundaries: boundaryItems(payload),
    },
    review: {
      storyboard_adherence: artifact.sourceRole,
      visual_consistency: status,
      boundary: "read-only asset artifact inspection",
    },
    feedback: {
      status: "review ready",
      summary: "Use the dedicated CLI nodes to record feedback or apply profile versions.",
    },
    next_pass: {
      status: status === "blocked" ? "blocked" : "ready",
      action: "inspect_asset_artifact_before_next_step",
    },
    timeline: [
      step("Selected artifact", status === "blocked" ? "blocked" : "review ready", artifact.fileName),
      step("Boundaries", "blocked", "no automatic writes"),
    ],
  };
}
