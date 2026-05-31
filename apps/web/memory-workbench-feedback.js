const MEMORY_PACKAGE_TYPE = "agentflow_memory_video_pipeline_package";
const REVIEW_TYPE = "agentflow_memory_video_pipeline_review";
const OBSERVATION_TYPE = "agentflow_memory_video_pipeline_human_observation";
const PRESENTATION_TYPE = "agentflow_memory_video_pipeline_presentation_package";
const FEEDBACK_TYPE = "agentflow_feedback_event";

export function buildMemoryFeedbackDraft(workspace) {
  const bundle = Array.isArray(workspace?.memoryBundle) ? workspace.memoryBundle : [];
  const byType = (type) => bundle.find((artifact) => artifact.artifactType === type);
  const packageArtifact = byType(MEMORY_PACKAGE_TYPE);
  const reviewArtifact = byType(REVIEW_TYPE);
  const observationArtifact = byType(OBSERVATION_TYPE);
  const presentationArtifact = byType(PRESENTATION_TYPE);
  const selectedFeedback = byType(FEEDBACK_TYPE);

  if (selectedFeedback?.payload) return normalizeSelectedFeedback(selectedFeedback);

  const draft = {
    schema_version: "0.1.0",
    artifact_type: FEEDBACK_TYPE,
    feedback_id: feedbackIdFor(packageArtifact, reviewArtifact, observationArtifact),
    decision: "note",
    draft_status: "draft_not_persisted",
    reason_tags: reasonTagsFor({ reviewArtifact, observationArtifact, presentationArtifact }),
    user_note: userNoteFor({ observationArtifact, presentationArtifact }),
    refs: refsFor({ packageArtifact, reviewArtifact, observationArtifact, presentationArtifact }),
    writes_long_term_memory: false,
    provider_calls_started: false,
    browser_generated_only: true,
    next_pass_hint: nextPassHintFor({ observationArtifact, presentationArtifact }),
  };

  return {
    mode: packageArtifact ? "draft" : "empty",
    status: packageArtifact ? "draft_not_persisted" : "no package selected",
    title: packageArtifact ? "Feedback Draft Preview" : "No feedback draft",
    detail: packageArtifact
      ? "Generated from explicitly selected memory artifacts; copy only, no file write."
      : "Select a memory video pipeline package JSON to preview a browser-local feedback draft.",
    draft,
    json_text: packageArtifact ? `${JSON.stringify(draft, null, 2)}\n` : "",
    copy_enabled: Boolean(packageArtifact),
  };
}

function normalizeSelectedFeedback(artifact) {
  const payload = objectValue(artifact.payload);
  const draft = {
    ...payload,
    writes_long_term_memory: false,
    browser_generated_only: payload.browser_generated_only === true,
  };
  return {
    mode: "selected",
    status: payload.draft_status || payload.decision || "feedback selected",
    title: "Selected Feedback Draft",
    detail: `${artifact.fileName} selected explicitly; displayed read-only for copy/review.`,
    draft,
    json_text: `${JSON.stringify(draft, null, 2)}\n`,
    copy_enabled: true,
  };
}

function feedbackIdFor(packageArtifact, reviewArtifact, observationArtifact) {
  const protocolId =
    packageArtifact?.payload?.protocol_id ||
    reviewArtifact?.payload?.protocol_id ||
    observationArtifact?.payload?.protocol_id ||
    "memory_video_pipeline";
  return `${protocolId}_feedback_draft`;
}

function reasonTagsFor({ reviewArtifact, observationArtifact, presentationArtifact }) {
  const tags = ["memory_video_pipeline", "draft_not_persisted"];
  const signal = objectValue(observationArtifact?.payload?.observed_signal_summary);
  if (signal.baseline_more_variable === true) tags.push("baseline_more_variable");
  if (signal.memory_backed_more_stable === true) tags.push("memory_backed_more_stable");
  if (reviewArtifact?.payload?.cross_run_stability) tags.push("cross_run_stability_reviewed");
  if (presentationArtifact?.payload?.result_summary?.residual_risk) tags.push("bounded_visual_signal");
  return tags;
}

function refsFor({ packageArtifact, reviewArtifact, observationArtifact, presentationArtifact }) {
  return {
    package: artifactRef(packageArtifact),
    review: artifactRef(reviewArtifact),
    observation: artifactRef(observationArtifact),
    presentation: artifactRef(presentationArtifact),
  };
}

function artifactRef(artifact) {
  if (!artifact) return null;
  return {
    file_name: artifact.fileName,
    artifact_type: artifact.artifactType,
    protocol_id: artifact.payload?.protocol_id || null,
  };
}

function userNoteFor({ observationArtifact, presentationArtifact }) {
  const takeaway = presentationArtifact?.payload?.one_sentence_takeaway;
  if (takeaway) return takeaway;
  const observations = Array.isArray(observationArtifact?.payload?.observations) ? observationArtifact.payload.observations : [];
  const firstMemorySignal = observations.find((item) => String(item?.verdict || "").includes("memory_backed"));
  return firstMemorySignal?.note || "Record operator observation before promotion review.";
}

function nextPassHintFor({ observationArtifact, presentationArtifact }) {
  const setup = objectValue(presentationArtifact?.payload?.experiment_setup);
  const checkpoints = Array.isArray(setup.storyboard_checkpoints)
    ? setup.storyboard_checkpoints.length
    : Array.isArray(observationArtifact?.payload?.storyboard?.shot_checkpoints)
      ? observationArtifact.payload.storyboard.shot_checkpoints.length
      : 0;
  return checkpoints
    ? `Use ${checkpoints} storyboard checkpoints plus accepted memory context in the next pass review.`
    : "Use reviewed memory context only after a promotion decision.";
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}
