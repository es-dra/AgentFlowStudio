from __future__ import annotations

from pathlib import Path


STUDIO_ROOT = Path("apps/studio")


def test_studio_runtime_client_exposes_feedback_candidate_promotion_contract() -> None:
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")

    assert "recordFeedbackCandidatePromotion(payload)" in runtime_client
    assert "/feedback-candidate-promotions" in runtime_client
    assert "record_feedback_candidate_promotion" in runtime_client
    assert "recordFeedbackCandidateContextOverlay(payload)" in runtime_client
    assert "/feedback-candidate-context-overlays" in runtime_client
    assert "record_feedback_candidate_context_overlay" in runtime_client
