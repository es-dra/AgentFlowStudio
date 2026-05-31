export const ARTIFACT_ALIASES = {
  run_manifest: ["run_manifest.json"],
  package_manifest: ["package_manifest.json", "finished_package_manifest.json"],
  quality_report: ["quality_report.json"],
  review_report: ["review_report.json"],
  delivery_readiness: ["delivery_readiness.json"],
  markdown_report: ["package_report.md", "delivery_readiness.md"],
  selection_diagnostics: ["selection_diagnostics.json"],
  highlight_score_report: ["highlight_score_report.json"],
  candidate_windows: ["candidate_windows.json"],
  clip_plan: ["clip_plan.json"],
  real_slice_manifest: ["real_slice_manifest.json"],
  final_video_manifest: ["final_video_manifest.json"],
  subtitle_manifest: ["subtitle_manifest.json"],
  audio_mix_manifest: ["audio_mix_manifest.json"],
  cover_manifest: ["cover_manifest.json"],
  agentflow_memory_video_pipeline_protocol: ["memory_video_pipeline_protocol.json", "memory_video_pipeline_protocol.example.json"],
  agentflow_memory_video_pipeline_package: ["memory_video_pipeline_package.json", "memory_video_pipeline_package.example.json"],
  agentflow_memory_video_pipeline_review: ["memory_video_pipeline_review.json", "memory_video_pipeline_review.example.json"],
  agentflow_memory_video_pipeline_human_observation: ["memory_video_pipeline_human_observation.json", "memory_video_pipeline_human_observation.example.json"],
  agentflow_memory_video_pipeline_presentation_package: ["memory_video_pipeline_presentation_package.json", "memory_video_pipeline_presentation_package.example.json"],
  agentflow_feedback_event: ["memory_video_pipeline_feedback_event_draft.json", "feedback_event.json"],
  loulan_afs_b01_feedback_loop_gate: ["afs_b01_feedback_loop_gate.json"],
  loulan_afs_b01_decision_crosswalk: ["afs_b01_decision_crosswalk.json"],
  loulan_b01_human_review_decision_template: ["b01_human_review_decision_template.json"],
  loulan_b01_decision_validation_report: ["human_review_decision_validation_report.json", "b01_decision_validation_report.json"],
  loulan_b01_decision_apply_result: ["b01_decision_apply_result.json"],
  loulan_unified_asset_registry: ["asset_registry.json"],
  loulan_next_generation_context_bundle_draft: ["next_context_bundle_draft.json"],
};

export const RECOMMENDED_ARTIFACTS = [
  "run_manifest",
  "package_manifest",
  "quality_report",
  "review_report",
  "markdown_report",
];

export const ARTIFACT_CLASSES = {
  KNOWN_CONTRACT: "known_contract",
  UNKNOWN_JSON: "unknown_json",
  UNSUPPORTED_FILE: "unsupported_file",
  LOCAL_MEDIA: "local_media",
  INVALID: "invalid",
};

export const VIDEO_EXTENSIONS = new Set(["mp4", "webm", "mov"]);
const LOULAN_MEMORY_ARTIFACT_TYPES = new Set([
  "loulan_afs_b01_feedback_loop_gate",
  "loulan_afs_b01_decision_crosswalk",
  "loulan_b01_human_review_decision_template",
  "loulan_b01_decision_validation_report",
  "loulan_b01_decision_apply_result",
  "loulan_unified_asset_registry",
  "loulan_next_generation_context_bundle_draft",
]);

export function isMemoryArtifactType(type) {
  return typeof type === "string" && (type.startsWith("agentflow_") || LOULAN_MEMORY_ARTIFACT_TYPES.has(type));
}

export function sourceRoleFor(type, fileName) {
  if (type === "markdown_report") {
    return fileName.toLowerCase() === "delivery_readiness.md" ? "delivery handoff" : "human package report";
  }
  if (type === "quality_report") return "inspection trust artifact";
  if (type === "review_report") return "agent review artifact";
  if (type === "package_manifest") return "package asset index";
  if (type === "run_manifest") return "workflow run index";
  if (type === "delivery_readiness") return "release gate";
  if (type === "selection_diagnostics") return "selection risk evidence";
  if (type === "highlight_score_report") return "candidate scoring evidence";
  if (type === "candidate_windows") return "candidate source windows";
  if (type === "clip_plan") return "clip execution plan";
  if (type === "real_slice_manifest") return "clip output manifest";
  if (type === "final_video_manifest") return "final video manifest";
  if (type === "subtitle_manifest") return "subtitle asset manifest";
  if (type === "audio_mix_manifest") return "audio mix manifest";
  if (type === "cover_manifest") return "cover asset manifest";
  if (type === "agentflow_memory_video_pipeline_protocol") return "memory video pipeline protocol";
  if (type === "agentflow_memory_video_pipeline_package") return "memory video pipeline package";
  if (type === "agentflow_memory_video_pipeline_review") return "memory video pipeline review";
  if (type === "agentflow_memory_video_pipeline_human_observation") return "memory video pipeline human observation";
  if (type === "agentflow_memory_video_pipeline_presentation_package") return "memory video pipeline presentation package";
  if (type === "agentflow_loulan_decision_worksheet") return "Loulan manual decision worksheet";
  if (type === "agentflow_loulan_decision_intake_report") return "Loulan decision intake report";
  if (type === "loulan_afs_b01_feedback_loop_gate") return "Loulan B01 feedback loop gate";
  if (type === "loulan_afs_b01_decision_crosswalk") return "Loulan B01 decision crosswalk";
  if (type === "loulan_b01_human_review_decision_template") return "Loulan B01 human decision template";
  if (type === "loulan_b01_decision_validation_report") return "Loulan B01 decision validation report";
  if (type === "loulan_b01_decision_apply_result") return "Loulan B01 decision apply result";
  if (type === "loulan_unified_asset_registry") return "Loulan unified asset registry";
  if (type === "loulan_next_generation_context_bundle_draft") return "Loulan next context bundle draft";
  if (type === "agentflow_feedback_event") return "memory feedback event draft";
  if (type === "local_video") return "user selected local preview media";
  if (type === "unsupported_file") return "unsupported file";
  return "unclassified";
}
