import {
  companyKbFeedbackFacts,
  productionAssetConsistencyReviewFacts,
  productionAssetFeedbackFacts,
  productionAssetProfileContextProjectionFacts,
  productionAssetProfileFacts,
  productionAssetProfilePromotionFacts,
  productionAssetProfileReadinessFacts,
  productionAssetProfileSeedFacts,
  productionAssetProfileUpdateCandidateFacts,
  productionAssetProfileVersionFacts,
  productionAssetProviderValidationFacts,
  productionAssetTestPackageFacts,
  productionAcceptanceFeedbackCandidatePromotionFacts,
  productionAcceptanceFeedbackCandidateFacts,
  productionAcceptanceFeedbackFacts,
  productionLoopFacts,
  productionNextOperatorActionResultFacts,
  productionNextOperatorStartEventFacts,
  productionNextContextHandoffFacts,
  productionNextOperatorStartPacketFacts,
  productionNextPassPromotionFacts,
  productionNextPassResultFacts,
  productionNextPassReviewFacts,
  productionNextTaskPacketFacts,
  productionOperatorFeedbackCandidateFacts,
  productionOperatorFeedbackFacts,
  productionOperatorHandoffFacts,
  productionOperatorManifestCheckFacts,
  productionOperatorLoopFacts,
  productionOperatorRunPackageCheckFacts,
  productionOperatorRunPackageFacts,
  productionSessionFacts,
} from "./memory-workbench-production-inspector-facts.js";
import { artifactLabelFor } from "./artifact-registry.js?v=m4-memory-canvas-tools";
import { TYPE_LABELS } from "./memory-workbench-inspector-labels.js";
import { focusTargetsFor } from "./memory-workbench-inspector-focus.js";
import { statusFor } from "./memory-workbench-inspector-status.js";

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
    title: artifactLabelFor(type) || TYPE_LABELS[type] || type,
    status: statusFor(type, payload),
    detail: `${artifact.fileName} | ${payload.protocol_id || payload.feedback_id || payload.schema_version || "selected JSON"}`,
    facts: factsFor(type, payload),
  };
}

function factsFor(type, payload) {
  if (type === "agentflow_feedback_event") return feedbackFacts(payload);
  if (type === "agentflow_production_memory_loop") return productionLoopFacts(payload);
  if (type === "agentflow_production_memory_session_report") return productionSessionFacts(payload);
  if (type === "agentflow_production_memory_operator_loop_run") return productionOperatorLoopFacts(payload);
  if (type === "agentflow_production_memory_operator_manifest_check") return productionOperatorManifestCheckFacts(payload);
  if (type === "agentflow_production_memory_operator_handoff_packet") return productionOperatorHandoffFacts(payload);
  if (type === "agentflow_production_memory_operator_run_package") return productionOperatorRunPackageFacts(payload);
  if (type === "agentflow_production_memory_operator_run_package_check") return productionOperatorRunPackageCheckFacts(payload);
  if (type === "agentflow_production_memory_next_operator_start_packet") return productionNextOperatorStartPacketFacts(payload);
  if (type === "agentflow_production_memory_next_operator_start_event") return productionNextOperatorStartEventFacts(payload);
  if (type === "agentflow_production_memory_next_operator_action_result") return productionNextOperatorActionResultFacts(payload);
  if (type === "agentflow_production_memory_acceptance_feedback_event") return productionAcceptanceFeedbackFacts(payload);
  if (type === "agentflow_production_memory_acceptance_feedback_candidate_packet") return productionAcceptanceFeedbackCandidateFacts(payload);
  if (type === "agentflow_production_memory_acceptance_feedback_candidate_promotion_decision") return productionAcceptanceFeedbackCandidatePromotionFacts(payload);
  if (type === "agentflow_production_memory_next_context_handoff") return productionNextContextHandoffFacts(payload);
  if (type === "agentflow_production_memory_next_task_packet") return productionNextTaskPacketFacts(payload);
  if (type === "agentflow_production_memory_next_pass_result") return productionNextPassResultFacts(payload);
  if (type === "agentflow_production_memory_next_pass_review") return productionNextPassReviewFacts(payload);
  if (type === "agentflow_production_memory_next_pass_promotion_decision") return productionNextPassPromotionFacts(payload);
  if (type === "agentflow_production_memory_next_pass_promotion_overlay") return productionNextPassPromotionFacts(payload);
  if (type === "agentflow_production_memory_operator_feedback_event") return productionOperatorFeedbackFacts(payload);
  if (type === "agentflow_production_memory_operator_feedback_candidate_packet") return productionOperatorFeedbackCandidateFacts(payload);
  if (type === "agentflow_production_memory_asset_profile_seed") return productionAssetProfileSeedFacts(payload);
  if (type === "agentflow_production_memory_asset_profile") return productionAssetProfileFacts(payload);
  if (type === "agentflow_production_memory_asset_profile_readiness") return productionAssetProfileReadinessFacts(payload);
  if (type === "agentflow_production_memory_asset_test_package") return productionAssetTestPackageFacts(payload);
  if (type === "agentflow_production_memory_asset_provider_validation_plan") return productionAssetProviderValidationFacts(payload);
  if (type === "agentflow_production_memory_asset_provider_validation_blockers") return productionAssetProviderValidationFacts(payload);
  if (type === "agentflow_production_memory_asset_provider_validation_result") return productionAssetProviderValidationFacts(payload);
  if (type === "agentflow_production_memory_asset_feedback_event") return productionAssetFeedbackFacts(payload);
  if (type === "agentflow_production_memory_asset_profile_update_candidate") return productionAssetProfileUpdateCandidateFacts(payload);
  if (type === "agentflow_production_memory_asset_profile_promotion_decision") return productionAssetProfilePromotionFacts(payload);
  if (type === "agentflow_production_memory_asset_profile_version") return productionAssetProfileVersionFacts(payload);
  if (type === "agentflow_production_memory_asset_profile_context_projection") return productionAssetProfileContextProjectionFacts(payload);
  if (type === "agentflow_production_memory_asset_consistency_review") return productionAssetConsistencyReviewFacts(payload);
  if (type === "agentflow_company_kb_feedback_candidate_packet") return companyKbFeedbackFacts(payload);
  return [
    fact("artifact_type", payload.artifact_type || "unknown"),
    fact("schema_version", payload.schema_version || "unknown"),
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
      detail: "Select Project Manifest or Production Memory JSON to inspect structure.",
      facts: [
        fact("scope", "explicit selected files only"),
        fact("auto_follow_refs", "false"),
      ],
    },
  ];
}
