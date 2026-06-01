import { isLoulanB01Artifact, loulanB01Facts, loulanB01FocusTargets, loulanB01Status, loulanB01TypeLabel } from "./memory-workbench-loulan-b01-inspector.js";
import { isLoulanContextDraftArtifact, loulanContextDraftFacts, loulanContextDraftFocusTargets, loulanContextDraftStatus, loulanContextDraftTypeLabel } from "./memory-workbench-loulan-context-draft-inspector.js";
import { isLoulanGovernanceAuditArtifact, loulanGovernanceAuditFacts, loulanGovernanceAuditFocusTargets, loulanGovernanceAuditStatus, loulanGovernanceAuditTypeLabel } from "./memory-workbench-loulan-governance-audit-inspector.js";
import { isLoulanPhaseAuditArtifact, loulanPhaseAuditFacts, loulanPhaseAuditFocusTargets, loulanPhaseAuditStatus, loulanPhaseAuditTypeLabel } from "./memory-workbench-loulan-phase-audit-inspector.js";
import { isLoulanProjectAuditProbe, loulanProjectAuditProbeFacts, loulanProjectAuditProbeFocusTargets, loulanProjectAuditProbeStatus, loulanProjectAuditProbeTypeLabel } from "./memory-workbench-loulan-project-audit-probe-inspector.js";
import { isLoulanProjectManifest, loulanProjectManifestFacts, loulanProjectManifestFocusTargets, loulanProjectManifestStatus, loulanProjectManifestTypeLabel } from "./memory-workbench-loulan-project-manifest-inspector.js";
import { loulanApiWorkbenchFacts, loulanContextBundleFacts, loulanDecisionFacts, loulanDecisionIntakeFacts, loulanDecisionReviewFacts, loulanDecisionWorksheetFacts, loulanHumanReviewFacts, loulanPackageFacts } from "./memory-workbench-loulan-package-inspector.js";
import { isLoulanRegistryArtifact, loulanRegistryFacts, loulanRegistryFocusTargets, loulanRegistryStatus, loulanRegistryTypeLabel } from "./memory-workbench-loulan-registry-inspector.js";
import { isLoulanRequestManifest, loulanRequestManifestFacts, loulanRequestManifestFocusTargets, loulanRequestManifestStatus, loulanRequestManifestTypeLabel } from "./memory-workbench-loulan-request-manifest-inspector.js";

const TYPE_LABELS = {
  agentflow_memory_video_pipeline_package: "Pipeline package",
  agentflow_memory_video_pipeline_protocol: "Pipeline protocol",
  agentflow_memory_video_pipeline_review: "Review artifact",
  agentflow_memory_video_pipeline_human_observation: "Human observation",
  agentflow_memory_video_pipeline_presentation_package: "Presentation package",
  agentflow_loulan_memory_package: "Loulan memory package",
  agentflow_loulan_api_workbench_plan: "Loulan API workbench plan",
  agentflow_loulan_human_review_pack: "Loulan human review pack",
  agentflow_loulan_promotion_decisions: "Loulan decision template",
  agentflow_loulan_decision_review_pack: "Loulan decision review pack",
  agentflow_loulan_decision_worksheet: "Loulan decision worksheet",
  agentflow_loulan_decision_intake_report: "Loulan decision intake report",
  agentflow_loulan_context_bundle_projection: "Loulan context bundle projection",
  agentflow_feedback_event: "Feedback draft",
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
    title:
      TYPE_LABELS[type] ||
      loulanProjectAuditProbeTypeLabel(type) ||
      loulanGovernanceAuditTypeLabel(type) ||
      loulanPhaseAuditTypeLabel(type) ||
      loulanB01TypeLabel(type) ||
      loulanContextDraftTypeLabel(type) ||
      loulanRegistryTypeLabel(type) ||
      loulanRequestManifestTypeLabel(type) ||
      loulanProjectManifestTypeLabel(type) ||
      type,
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
  if (type === "agentflow_loulan_memory_package") return ["project", "assets", "memory-loaded", "next-pass"];
  if (type === "agentflow_loulan_api_workbench_plan") return ["baseline-run", "memory-backed-run", "review", "next-pass"];
  if (type === "agentflow_loulan_human_review_pack") return ["review", "feedback", "next-pass"];
  if (type === "agentflow_loulan_promotion_decisions") return ["feedback", "next-pass"];
  if (type === "agentflow_loulan_decision_review_pack") return ["review", "feedback", "next-pass"];
  if (type === "agentflow_loulan_decision_worksheet") return ["review", "feedback", "next-pass"];
  if (type === "agentflow_loulan_decision_intake_report") return ["review", "feedback", "next-pass"];
  if (type === "agentflow_loulan_context_bundle_projection") return ["memory-loaded", "next-pass"];
  if (isLoulanProjectAuditProbe(type)) return loulanProjectAuditProbeFocusTargets(type);
  if (isLoulanGovernanceAuditArtifact(type)) return loulanGovernanceAuditFocusTargets(type);
  if (isLoulanPhaseAuditArtifact(type)) return loulanPhaseAuditFocusTargets(type);
  if (isLoulanB01Artifact(type)) return loulanB01FocusTargets(type);
  if (isLoulanContextDraftArtifact(type)) return loulanContextDraftFocusTargets(type);
  if (isLoulanRegistryArtifact(type)) return loulanRegistryFocusTargets(type);
  if (isLoulanRequestManifest(type)) return loulanRequestManifestFocusTargets(type);
  if (isLoulanProjectManifest(type)) return loulanProjectManifestFocusTargets(type);
  return [];
}

function factsFor(type, payload) {
  if (type === "agentflow_memory_video_pipeline_package") return packageFacts(payload);
  if (type === "agentflow_memory_video_pipeline_protocol") return protocolFacts(payload);
  if (type === "agentflow_memory_video_pipeline_review") return reviewFacts(payload);
  if (type === "agentflow_memory_video_pipeline_human_observation") return observationFacts(payload);
  if (type === "agentflow_memory_video_pipeline_presentation_package") return presentationFacts(payload);
  if (type === "agentflow_loulan_memory_package") return loulanPackageFacts(payload);
  if (type === "agentflow_loulan_api_workbench_plan") return loulanApiWorkbenchFacts(payload);
  if (type === "agentflow_loulan_human_review_pack") return loulanHumanReviewFacts(payload);
  if (type === "agentflow_loulan_promotion_decisions") return loulanDecisionFacts(payload);
  if (type === "agentflow_loulan_decision_review_pack") return loulanDecisionReviewFacts(payload);
  if (type === "agentflow_loulan_decision_worksheet") return loulanDecisionWorksheetFacts(payload);
  if (type === "agentflow_loulan_decision_intake_report") return loulanDecisionIntakeFacts(payload);
  if (type === "agentflow_loulan_context_bundle_projection") return loulanContextBundleFacts(payload);
  if (isLoulanProjectAuditProbe(type)) return loulanProjectAuditProbeFacts(payload);
  if (isLoulanGovernanceAuditArtifact(type)) return loulanGovernanceAuditFacts(type, payload);
  if (isLoulanPhaseAuditArtifact(type)) return loulanPhaseAuditFacts(payload);
  if (isLoulanB01Artifact(type)) return loulanB01Facts(type, payload);
  if (isLoulanContextDraftArtifact(type)) return loulanContextDraftFacts(payload);
  if (isLoulanRegistryArtifact(type)) return loulanRegistryFacts(payload);
  if (isLoulanRequestManifest(type)) return loulanRequestManifestFacts(payload);
  if (isLoulanProjectManifest(type)) return loulanProjectManifestFacts(type, payload);
  if (type === "agentflow_feedback_event") return feedbackFacts(payload);
  return [
    fact("artifact_type", payload.artifact_type || "unknown"),
    fact("schema_version", payload.schema_version || "unknown"),
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
  if (isLoulanProjectAuditProbe(type)) return loulanProjectAuditProbeStatus(payload);
  if (isLoulanGovernanceAuditArtifact(type)) return loulanGovernanceAuditStatus(payload);
  if (isLoulanPhaseAuditArtifact(type)) return loulanPhaseAuditStatus(payload);
  if (isLoulanB01Artifact(type)) return loulanB01Status(type, payload);
  if (isLoulanContextDraftArtifact(type)) return loulanContextDraftStatus(payload);
  if (isLoulanRegistryArtifact(type)) return loulanRegistryStatus(payload);
  if (isLoulanRequestManifest(type)) return loulanRequestManifestStatus(payload);
  if (isLoulanProjectManifest(type)) return loulanProjectManifestStatus(type, payload);
  if (type === "agentflow_feedback_event") return payload.draft_status || "feedback captured";
  if (type === "agentflow_memory_video_pipeline_human_observation") return payload.observation_status || "review ready";
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
