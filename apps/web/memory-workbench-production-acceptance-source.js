const ACTION_RESULT_TYPE = "agentflow_production_memory_next_operator_action_result";

export function acceptanceFeedbackSourceParts(summary) {
  const source = sourceInfo(summary);
  if (!source.hasSource) {
    return { cards: [], memory: [], lanes: [], timeline: [] };
  }
  return {
    cards: [
      {
        id: "acceptance_feedback_source_artifact",
        title: source.title,
        status: source.status,
        detail: source.detail,
      },
    ],
    memory: [
      {
        id: "acceptance_feedback_source_artifact",
        title: source.title,
        why_eligible: "source evidence for the explicit acceptance feedback candidate promotion",
        source_evidence_refs: [source.path],
        promotion_status: source.detail,
        request_projection: source.type,
        feedback_effect: "source evidence only; not durable memory or Company KB",
        status: source.status,
      },
    ],
    lanes: [
      {
        id: source.id,
        title: source.title,
        status: source.status,
        input: source.path,
        output: source.detail,
      },
    ],
    timeline: [
      {
        label: source.title,
        status: source.status,
        detail: source.detail,
      },
    ],
  };
}

function sourceInfo(summary) {
  const source = objectValue(summary);
  const type = source.source_artifact_type || source.source_target_artifact_type || "unknown";
  const isActionResult = type === ACTION_RESULT_TYPE;
  const detail = source.source_artifact_status || "unknown";
  return {
    hasSource: type !== "unknown" || source.source_artifact_path || source.source_target_ref,
    id: isActionResult ? "acceptance-feedback-source-action-result" : "acceptance-feedback-source-artifact",
    title: isActionResult ? "Source action result" : "Source artifact",
    type,
    status: detail !== "unknown" ? "review ready" : "blocked",
    detail,
    path: source.source_artifact_path || source.source_target_ref || "unknown",
  };
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}
