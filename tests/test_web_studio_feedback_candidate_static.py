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


def test_studio_feedback_overlay_review_surface_reads_context_bundle_only() -> None:
    overlay_helper = STUDIO_ROOT / "src" / "feedback-context-overlays.js"
    inspector_summary = (STUDIO_ROOT / "src" / "panels" / "inspector-context-summary.js").read_text(encoding="utf-8")
    algorithm_panel = (STUDIO_ROOT / "src" / "panels" / "algorithm-context-panel.js").read_text(encoding="utf-8")

    assert overlay_helper.is_file()
    overlay_source = overlay_helper.read_text(encoding="utf-8")
    assert "feedback_context_overlays" in overlay_source
    assert "feedbackContextOverlaysFromBundle" in overlay_source
    assert "provider_calls_started" in overlay_source
    assert "writes_long_term_memory" in overlay_source
    assert "writes_company_kb" in overlay_source
    assert "fetch(" not in overlay_source
    assert "recordFeedbackCandidateContextOverlay" not in overlay_source
    assert "AFS_ALLOW_REMOTE" not in overlay_source

    assert "feedbackContextOverlaysFromBundle" in inspector_summary
    assert "反馈上下文" in inspector_summary
    assert "feedbackOverlaySummaryText" in inspector_summary
    assert "反馈" in algorithm_panel
