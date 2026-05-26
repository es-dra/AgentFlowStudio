export const FALLBACK_WORKFLOW_INPUTS = {
  video_to_finished_package_local_asr: "examples/demo_asr/video_to_finished_package_local_asr_input.example.json",
  video_script_to_finished_package_local_asr: "examples/demo_asr/video_script_to_finished_package_local_asr_input.example.json",
  mock_text_to_slices: "examples/demo_text/story.txt",
  mock_roi_to_script: "examples/demo_text/story.txt",
};

export const DEMO_WORKFLOW_NAME = "mock_text_to_slices";
export const PRODUCT_WORKFLOW_NAME = "video_to_finished_package_local_asr";

export function preferredWorkflow(workflows) {
  return workflowByName(workflows, PRODUCT_WORKFLOW_NAME)?.path || workflows[0]?.path || "";
}

export function workflowByName(workflows, name) {
  return workflows.find((workflow) => workflow.name === name);
}

export function workflowDefaultInput(workflow) {
  return workflow?.web_profile?.recommended_input || FALLBACK_WORKFLOW_INPUTS[workflow?.name] || "examples/demo_text/story.txt";
}

export function workflowDefaultOutput(workflow) {
  return `data/processed/runs/web_bridge/${workflow?.name || "manual_run"}`;
}

export function knownWorkflowInputs() {
  return Object.values(FALLBACK_WORKFLOW_INPUTS);
}

export function workflowProfileSummary(workflow) {
  const profile = workflow?.web_profile || {};
  if (!workflow) return "请选择一个 workflow。";
  if (profile.summary) return profile.summary;
  return workflow.metadata?.description || "从 workflows/*.yaml 读取的本地 workflow。";
}

export function workflowDisplayName(workflow) {
  return workflow?.web_profile?.display_name || workflow?.name || "未选择 workflow";
}

export function workflowRequirementsText(workflow) {
  const requirements = workflow?.web_profile?.requirements || [];
  return requirements.length ? requirements.join(", ") : "无额外依赖";
}

export function workflowRequires(workflow, requirement) {
  return (workflow?.web_profile?.requirements || []).includes(requirement);
}
