export const MEMORY_PACKAGE_TYPE = "agentflow_memory_video_pipeline_package";

export const PACKAGE_REFS = [
  ["plan_ref", "Project", "planned", ""],
  ["review_ref", "Review", "review ready", "agentflow_memory_video_pipeline_review"],
  ["observation_ref", "Assets", "review ready", "agentflow_memory_video_pipeline_human_observation"],
  ["presentation_ref", "Memory Loaded", "review ready", "agentflow_memory_video_pipeline_presentation_package"],
  ["feedback_event_draft_ref", "Feedback", "feedback captured", "agentflow_feedback_event"],
];
