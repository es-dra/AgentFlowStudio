export function buildFeedbackEvent({ artifactFile, decision, riskCategory, note, videoTimeSec }) {
  return {
    schema_version: "0.1.0",
    event_type: "feedback_event",
    source: "narratocut_web_static_viewer",
    created_at: new Date().toISOString(),
    artifact_file: artifactFile || null,
    decision: decision || "needs_changes",
    risk_category: riskCategory || "general_review",
    reviewer_note: note || "",
    video_time_sec: parseOptionalNumber(videoTimeSec),
  };
}

export function buildRunFeedbackEvent({ run, workflow, review, decision, riskCategory, note, videoTimeSec }) {
  const reviewArtifacts = run?.review_artifacts || review?.artifacts || {};
  const reviewStatus = run?.review_status || review?.status || review?.review?.status || null;
  return {
    schema_version: "0.1.0",
    event_type: "run_feedback_event",
    source: "narratocut_web_production_mode",
    created_at: new Date().toISOString(),
    run_dir: run?.run_dir || null,
    run_id: run?.run_id || null,
    workflow: workflow?.name || run?.workflow || null,
    artifact_file: run?.manifest_path || run?.bridge_status_path || null,
    review_status: reviewStatus,
    review_report: reviewArtifacts.review_report || null,
    quality_report: reviewArtifacts.quality_report || null,
    decision: decision || "needs_changes",
    risk_category: riskCategory || "production_readiness",
    reviewer_note: note || "",
    video_time_sec: parseOptionalNumber(videoTimeSec),
  };
}

export function formatFeedbackEvent(event) {
  return `${JSON.stringify(event)}\n`;
}

export async function copyFeedbackText(text, textarea, statusNode, copy) {
  textarea.value = text;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      statusNode.textContent = copy.feedbackCopied;
      return;
    }
  } catch (_error) {
    statusNode.textContent = copy.feedbackCopyFallback;
  }
  textarea.focus();
  textarea.select();
  statusNode.textContent = copy.feedbackCopyFallback;
}

function parseOptionalNumber(value) {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : null;
}
