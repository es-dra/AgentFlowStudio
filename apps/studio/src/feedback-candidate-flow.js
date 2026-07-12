const DEFAULT_PROMOTION_RATIONALE = "Studio operator selected this feedback for the next local context pass.";
const DEFAULT_OVERLAY_INTENT = "Carry this reviewed Studio feedback into the next local context pass.";
const ARTIFACT_REF_MAX_LENGTH = 512;

export function feedbackContextOverlayRequestOptions(value) {
  const input = value && typeof value === "object" ? value : {};
  return {
    requested: Boolean(input.requested),
    decision: "promote_to_context_overlay",
    rationale: safeText(input.rationale || DEFAULT_PROMOTION_RATIONALE, 280),
    overlay_intent: safeText(input.overlay_intent || DEFAULT_OVERLAY_INTENT, 280),
  };
}

export async function promoteFeedbackCandidateToContextOverlay(runtime, feedbackResponse, options = {}) {
  const requestOptions = feedbackContextOverlayRequestOptions(options);
  if (!requestOptions.requested) return { requested: false, status: "not_requested" };
  const promotionRequest = buildFeedbackCandidatePromotionRequest(feedbackResponse, requestOptions);
  const promotionResponse = await runtime.recordFeedbackCandidatePromotion(promotionRequest);
  const overlayRequest = buildFeedbackCandidateContextOverlayRequest(promotionResponse, requestOptions);
  const overlayResponse = await runtime.recordFeedbackCandidateContextOverlay(overlayRequest);
  return {
    requested: true,
    status: "context_overlay_recorded",
    promotion_request: promotionRequest,
    overlay_request: overlayRequest,
    promotion_response: promotionResponse,
    overlay_response: overlayResponse,
  };
}

export function buildFeedbackCandidatePromotionRequest(feedbackResponse, options = {}) {
  const event = feedbackResponse?.feedback_event || {};
  const candidate = event.feedback_candidate || {};
  const feedbackArtifactId = safeToken(feedbackResponse?.artifact?.artifact_id, ARTIFACT_REF_MAX_LENGTH);
  const candidateId = safeToken(candidate.candidate_id, 180);
  if (!feedbackArtifactId || !candidateId) {
    throw new Error("feedback candidate promotion requires feedback artifact and candidate id");
  }
  return {
    feedback_artifact_id: feedbackArtifactId,
    candidate_id: candidateId,
    decision: "promote_to_context_overlay",
    rationale: safeText(options.rationale || DEFAULT_PROMOTION_RATIONALE, 280),
    reviewed_at: new Date().toISOString(),
  };
}

export function buildFeedbackCandidateContextOverlayRequest(promotionResponse, options = {}) {
  const promotionArtifactId = safeToken(promotionResponse?.artifact?.artifact_id, ARTIFACT_REF_MAX_LENGTH);
  if (!promotionArtifactId) {
    throw new Error("feedback context overlay requires promotion decision artifact id");
  }
  return {
    promotion_decision_artifact_id: promotionArtifactId,
    overlay_intent: safeText(options.overlay_intent || DEFAULT_OVERLAY_INTENT, 280),
    generated_at: new Date().toISOString(),
  };
}

export function feedbackCandidateFlowSummary(feedbackResponse, flowResult = {}) {
  const event = feedbackResponse?.feedback_event || {};
  const candidate = event.feedback_candidate || {};
  const promotion = flowResult.promotion_response?.feedback_candidate_promotion_decision || {};
  const overlay = flowResult.overlay_response?.feedback_candidate_context_overlay || {};
  return {
    feedback_id: safeToken(event.feedback_id, 180),
    feedback_artifact_id: safeToken(feedbackResponse?.artifact?.artifact_id, ARTIFACT_REF_MAX_LENGTH),
    candidate_id: safeToken(candidate.candidate_id, 180),
    candidate_scope: safeToken(candidate.candidate_scope, 120),
    context_overlay_requested: Boolean(flowResult.requested),
    promotion_decision_id: safeToken(promotion.decision_id, 180),
    promotion_artifact_id: safeToken(flowResult.promotion_response?.artifact?.artifact_id, ARTIFACT_REF_MAX_LENGTH),
    context_overlay_id: safeToken(overlay.overlay_id, 180),
    context_overlay_artifact_id: safeToken(flowResult.overlay_response?.artifact?.artifact_id, ARTIFACT_REF_MAX_LENGTH),
    status: safeToken(flowResult.status || "recorded_feedback_candidate", 120),
    provider_calls_started: false,
    writes_long_term_memory: false,
    writes_company_kb: false,
    recorded_at: new Date().toISOString(),
  };
}

function safeText(value, maxLength) {
  return String(value || "")
    .replace(/Bearer\s+\S+/gi, "Bearer <redacted>")
    .replace(/[A-Za-z]:\\[^\s"'<>]+/g, "<local-path-redacted>")
    .replace(/https?:\/\/[^\s"'<>]+/g, "<url-redacted>")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, maxLength);
}

function safeToken(value, maxLength) {
  return String(value || "").replace(/[^a-zA-Z0-9_.:-]+/g, "_").slice(0, maxLength);
}
