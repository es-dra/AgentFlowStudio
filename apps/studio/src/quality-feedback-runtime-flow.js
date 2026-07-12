import { QUALITY_FEEDBACK_RESULT_EVENT } from "./quality-feedback.js";
import {
  feedbackCandidateFlowSummary,
  promoteFeedbackCandidateToContextOverlay,
} from "./feedback-candidate-flow.js";
import { formatRuntimeError } from "./runtime-error-utils.js";

export async function handleQualityFeedbackRuntime({ event, runtime, store }) {
  const requestId = String(event.detail?.request_id || "");
  try {
    const feedback = event.detail?.feedback;
    if (!feedback || typeof feedback !== "object") throw new Error("feedback payload is empty");
    const feedbackResponse = await runtime.recordFeedback(feedback);
    const flowResult = await tryPromoteToContextOverlay(runtime, feedbackResponse, event.detail?.context_overlay);
    recordQualityFeedbackCandidateOnNode(store, feedback, feedbackResponse, flowResult);
    window.dispatchEvent(new CustomEvent(QUALITY_FEEDBACK_RESULT_EVENT, {
      detail: {
        request_id: requestId,
        ok: true,
        feedback_id: feedbackResponse?.feedback_event?.feedback_id || feedbackResponse?.artifact?.artifact_id || "",
        context_overlay_status: flowResult.status || "recorded_feedback_candidate",
        context_overlay_id: flowResult.overlay_response?.feedback_candidate_context_overlay?.overlay_id || "",
        context_overlay_error: flowResult.error || "",
      },
    }));
  } catch (error) {
    window.dispatchEvent(new CustomEvent(QUALITY_FEEDBACK_RESULT_EVENT, {
      detail: { request_id: requestId, ok: false, error: formatRuntimeError(error, "unknown error") },
    }));
  }
}

async function tryPromoteToContextOverlay(runtime, feedbackResponse, options) {
  try {
    return await promoteFeedbackCandidateToContextOverlay(runtime, feedbackResponse, options);
  } catch (error) {
    return {
      requested: Boolean(options?.requested),
      status: "context_overlay_failed",
      error: formatRuntimeError(error, "unknown error"),
    };
  }
}

function recordQualityFeedbackCandidateOnNode(store, feedback, feedbackResponse, flowResult) {
  const nodeId = String(feedback?.node_id || "");
  if (!nodeId || !store?.set) return;
  const summary = feedbackCandidateFlowSummary(feedbackResponse, flowResult);
  store.set((state) => {
    const node = state.nodes?.[nodeId];
    if (!node) return;
    node.params = node.params || {};
    const prior = Array.isArray(node.params.qualityFeedbackCandidates) ? node.params.qualityFeedbackCandidates : [];
    node.params.qualityFeedbackCandidates = prior.concat(summary).slice(-8);
  }, { history: false });
}
