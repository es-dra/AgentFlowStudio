from __future__ import annotations

from narratocut.candidate_sop import generate_candidate_windows, score_candidate_windows
from narratocut.schemas import HighlightPlan, Transcript


def test_score_candidate_windows_prioritizes_ocr_hook_and_payoff() -> None:
    transcript = Transcript.model_validate(
        {
            "transcript_id": "ocr_transcript_demo",
            "source_video": "input.mp4",
            "duration": 20.0,
            "metadata": {"content_channel": "ocr_subtitle"},
            "segments": [
                {
                    "segment_id": "ocr_seg_001",
                    "start_time": 1.0,
                    "end_time": 3.0,
                    "text": "90% of creators cut the wrong part",
                    "confidence": 0.9,
                },
                {
                    "segment_id": "ocr_seg_002",
                    "start_time": 3.0,
                    "end_time": 6.0,
                    "text": "but the real problem is not effort, it is direction",
                    "confidence": 0.88,
                },
                {
                    "segment_id": "ocr_seg_003",
                    "start_time": 10.0,
                    "end_time": 13.0,
                    "text": "today we continue the regular content",
                    "confidence": 0.84,
                },
            ],
        }
    )
    candidates = generate_candidate_windows(transcript, max_window_size=2)

    report, plan = score_candidate_windows(candidates, max_selected=2)

    assert report["status"] == "succeeded"
    assert report["candidate_count"] == candidates["candidate_count"]
    assert report["selected_count"] == 2
    top = report["candidates"][0]
    assert top["candidate_id"] == "cand_002"
    assert top["decision"] == "selected"
    assert top["score_breakdown"]["on_screen_hook_strength"] > 0
    assert top["score_breakdown"]["conflict_intensity"] > 0
    assert "ocr_hook" in top["reasons"]
    assert isinstance(plan, HighlightPlan)
    assert plan.highlights[0].source_segment_ids == ["ocr_seg_001", "ocr_seg_002"]
    assert plan.highlights[0].metadata["ranking_factors"]["final_score"] == top["total_score"]


def test_score_candidate_windows_rejects_overlapping_candidates() -> None:
    transcript = Transcript.model_validate(
        {
            "transcript_id": "asr_transcript_demo",
            "metadata": {"content_channel": "asr_transcript"},
            "segments": [
                {
                    "segment_id": "seg_001",
                    "start_time": 0,
                    "end_time": 3,
                    "text": "opening hook with a reversal",
                    "confidence": 0.9,
                },
                {
                    "segment_id": "seg_002",
                    "start_time": 3,
                    "end_time": 6,
                    "text": "but the real problem comes later",
                    "confidence": 0.9,
                },
                {
                    "segment_id": "seg_003",
                    "start_time": 6,
                    "end_time": 9,
                    "text": "therefore choose the direction again",
                    "confidence": 0.9,
                },
            ],
        }
    )
    candidates = generate_candidate_windows(transcript, max_window_size=3)

    report, plan = score_candidate_windows(candidates, max_selected=2, max_overlap_ratio=0.2)

    assert len(plan.highlights) == 2
    rejected = [item for item in report["candidates"] if item["decision"] == "rejected"]
    assert any("overlap" in item["rejection_reasons"] for item in rejected)
