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


def test_score_candidate_windows_rejects_repeated_split_source_window() -> None:
    candidates = {
        "schema_version": "0.1",
        "status": "succeeded",
        "source_transcript_id": "demo_transcript",
        "source_video": "input.mp4",
        "content_channel": "local_asr",
        "candidates": [
            _candidate(
                "cand_001",
                0.0,
                5.0,
                "The first short beat explains the setup.",
                source_window_start_sec=0.0,
                source_window_end_sec=20.0,
            ),
            _candidate(
                "cand_002",
                5.0,
                10.0,
                "The second short beat repeats the same setup.",
                source_window_start_sec=0.0,
                source_window_end_sec=20.0,
            ),
            _candidate(
                "cand_003",
                30.0,
                35.0,
                "A separate payoff gives the edit a different beat.",
                source_window_start_sec=30.0,
                source_window_end_sec=40.0,
            ),
        ],
    }

    report, plan = score_candidate_windows(candidates, max_selected=3)

    selected_ids = [candidate["candidate_id"] for candidate in report["candidates"] if candidate["decision"] == "selected"]
    assert selected_ids == ["cand_001", "cand_003"]
    assert len(plan.highlights) == 2
    assert any(
        candidate["candidate_id"] == "cand_002"
        and candidate["decision"] == "rejected"
        and "duplicate_source_window" in candidate["rejection_reasons"]
        for candidate in report["candidates"]
    )


def test_score_candidate_windows_dedupes_audio_refined_split_source_window() -> None:
    candidates = {
        "schema_version": "0.1",
        "status": "succeeded",
        "source_transcript_id": "demo_transcript",
        "source_video": "input.mp4",
        "content_channel": "local_asr",
        "candidates": [
            _candidate(
                "cand_001",
                0.2,
                5.1,
                "The first refined beat explains the setup.",
                source_window_start_sec=0.0,
                source_window_end_sec=20.0,
                boundary_strategy="audio_boundary_refined",
                base_boundary_strategy="elastic_duration_split",
            ),
            _candidate(
                "cand_002",
                5.2,
                10.1,
                "The second refined beat repeats the same setup.",
                source_window_start_sec=0.0,
                source_window_end_sec=20.0,
                boundary_strategy="audio_boundary_refined",
                base_boundary_strategy="elastic_duration_split",
            ),
            _candidate(
                "cand_003",
                30.0,
                35.0,
                "A separate payoff gives the edit a different beat.",
                source_window_start_sec=30.0,
                source_window_end_sec=40.0,
            ),
        ],
    }

    report, plan = score_candidate_windows(candidates, max_selected=3)

    selected_ids = [candidate["candidate_id"] for candidate in report["candidates"] if candidate["decision"] == "selected"]
    assert selected_ids == ["cand_001", "cand_003"]
    assert len(plan.highlights) == 2
    assert any(
        candidate["candidate_id"] == "cand_002"
        and "duplicate_source_window" in candidate["rejection_reasons"]
        for candidate in report["candidates"]
    )


def test_score_candidate_windows_prefers_short_clip_duration() -> None:
    candidates = {
        "schema_version": "0.1",
        "status": "succeeded",
        "source_transcript_id": "demo",
        "source_video": "input.mp4",
        "content_channel": "asr_transcript",
        "candidates": [
            {
                "candidate_id": "long",
                "source": "transcript_window",
                "start_sec": 0.0,
                "end_sec": 20.0,
                "duration_sec": 20.0,
                "segment_ids": ["seg_001"],
                "text": "90% of creators cut the wrong part but the real problem is direction",
                "asr_confidence": 0.9,
                "script_alignment": None,
                "evidence": {"content_channel": "asr_transcript"},
            },
            {
                "candidate_id": "short",
                "source": "transcript_subwindow",
                "start_sec": 4.0,
                "end_sec": 9.0,
                "duration_sec": 5.0,
                "segment_ids": ["seg_001"],
                "text": "90% of creators cut the wrong part",
                "asr_confidence": 0.9,
                "script_alignment": None,
                "evidence": {"content_channel": "asr_transcript"},
            },
        ],
    }

    report, plan = score_candidate_windows(candidates, max_selected=1)

    assert report["candidates"][0]["candidate_id"] == "short"
    assert plan.highlights[0].start_time == 4.0
    assert plan.highlights[0].end_time == 9.0


def _candidate(
    candidate_id: str,
    start_sec: float,
    end_sec: float,
    text: str,
    *,
    source_window_start_sec: float,
    source_window_end_sec: float,
    boundary_strategy: str = "fixed_duration_split",
    base_boundary_strategy: str | None = None,
) -> dict[str, object]:
    evidence = {
        "window_size": 2,
        "content_channel": "local_asr",
        "boundary_strategy": boundary_strategy,
        "source_window_start_sec": source_window_start_sec,
        "source_window_end_sec": source_window_end_sec,
    }
    if base_boundary_strategy is not None:
        evidence["base_boundary_strategy"] = base_boundary_strategy
    return {
        "candidate_id": candidate_id,
        "source": "transcript_subwindow",
        "start_sec": start_sec,
        "end_sec": end_sec,
        "duration_sec": round(end_sec - start_sec, 6),
        "segment_ids": [candidate_id.replace("cand", "seg")],
        "text": text,
        "asr_confidence": 0.8,
        "script_alignment": None,
        "evidence": evidence,
    }
