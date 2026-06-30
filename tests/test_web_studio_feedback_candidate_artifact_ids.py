from __future__ import annotations

import json
import subprocess


def test_studio_feedback_candidate_flow_preserves_long_runtime_artifact_ids() -> None:
    script = r'''
import {
  buildFeedbackCandidateContextOverlayRequest,
  buildFeedbackCandidatePromotionRequest,
  feedbackCandidateFlowSummary,
} from "./apps/studio/src/feedback-candidate-flow.js";

const feedbackArtifactId = `feedback-${"x".repeat(260)}-runtime_feedback_event`;
const promotionArtifactId = `feedback-${"y".repeat(260)}-runtime_feedback_candidate_promotion_decision`;
const overlayArtifactId = `feedback-${"z".repeat(260)}-runtime_feedback_candidate_context_overlay`;
const feedbackResponse = {
  artifact: { artifact_id: feedbackArtifactId },
  feedback_event: {
    feedback_id: "runtime-feedback:project:001",
    feedback_candidate: { candidate_id: "runtime-feedback-candidate:001", candidate_scope: "quality_feedback_candidate" },
  },
};
const promotionRequest = buildFeedbackCandidatePromotionRequest(feedbackResponse, {});
const overlayRequest = buildFeedbackCandidateContextOverlayRequest(
  { artifact: { artifact_id: promotionArtifactId } },
  {}
);
const summary = feedbackCandidateFlowSummary(feedbackResponse, {
  requested: true,
  status: "context_overlay_recorded",
  promotion_response: {
    artifact: { artifact_id: promotionArtifactId },
    feedback_candidate_promotion_decision: { decision_id: "promotion_decision_001" },
  },
  overlay_response: {
    artifact: { artifact_id: overlayArtifactId },
    feedback_candidate_context_overlay: { overlay_id: "runtime-feedback-overlay:001" },
  },
});
process.stdout.write(JSON.stringify({ promotionRequest, overlayRequest, summary, feedbackArtifactId, promotionArtifactId, overlayArtifactId }));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)

    assert len(payload["feedbackArtifactId"]) > 180
    assert len(payload["promotionArtifactId"]) > 180
    assert payload["promotionRequest"]["feedback_artifact_id"] == payload["feedbackArtifactId"]
    assert payload["overlayRequest"]["promotion_decision_artifact_id"] == payload["promotionArtifactId"]
    assert payload["summary"]["feedback_artifact_id"] == payload["feedbackArtifactId"]
    assert payload["summary"]["promotion_artifact_id"] == payload["promotionArtifactId"]
    assert payload["summary"]["context_overlay_artifact_id"] == payload["overlayArtifactId"]
