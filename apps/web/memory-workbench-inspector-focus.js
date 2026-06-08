import { artifactFocusTargetsFor } from "./artifact-registry.js?v=m4-memory-canvas-tools";

export function focusTargetsFor(type) {
  const registryTargets = artifactFocusTargetsFor(type);
  if (registryTargets.length) return registryTargets;
  if (type === "agentflow_memory_video_pipeline_protocol") return ["project", "assets", "memory-loaded"];
  if (type === "agentflow_memory_video_pipeline_package") return ["project", "next-pass"];
  if (type === "agentflow_memory_video_pipeline_review") return ["baseline-run", "memory-backed-run", "review"];
  if (type === "agentflow_memory_video_pipeline_human_observation") return ["assets", "review"];
  if (type === "agentflow_memory_video_pipeline_presentation_package") return ["memory-loaded", "review"];
  if (type === "agentflow_feedback_event") return ["feedback", "next-pass"];
  if (type === "agentflow_production_memory_loop") return ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"];
  if (type === "agentflow_production_memory_session_report") return ["project", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_operator_loop_run") return ["project", "assets", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_operator_manifest_check") return ["project", "assets", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_operator_handoff_packet") return ["project", "assets", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_operator_run_package") return ["project", "assets", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_operator_run_package_check") return ["project", "assets", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_next_operator_start_packet") return ["project", "assets", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_next_operator_start_event") return ["project", "assets", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_next_operator_action_result") return ["project", "assets", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_acceptance_feedback_event") return ["project", "memory-loaded", "review", "feedback", "next-pass"];
  if (type === "agentflow_production_memory_acceptance_feedback_candidate_packet") return ["project", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_acceptance_feedback_candidate_promotion_decision") return ["project", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_next_context_handoff") return ["project", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_next_task_packet") return ["project", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_next_pass_result") return ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"];
  if (type === "agentflow_production_memory_next_pass_review") return ["project", "memory-loaded", "review", "feedback", "next-pass"];
  if (type === "agentflow_production_memory_next_pass_promotion_decision") return ["project", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_next_pass_promotion_overlay") return ["project", "memory-loaded", "review", "next-pass"];
  if (type === "agentflow_production_memory_operator_feedback_event") return ["project", "memory-loaded", "review", "feedback"];
  if (type === "agentflow_production_memory_operator_feedback_candidate_packet") return ["project", "memory-loaded", "review", "next-pass"];
  if (type.startsWith("agentflow_production_memory_asset_")) return ["project", "assets", "memory-loaded", "review", "feedback", "next-pass"];
  if (type === "agentflow_company_kb_feedback_candidate_packet") return ["project", "memory-loaded", "review", "next-pass"];
  return [];
}
