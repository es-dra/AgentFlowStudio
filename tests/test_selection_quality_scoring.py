from __future__ import annotations

from narratocut.candidate_sop import score_candidate_windows


def test_score_candidate_windows_prioritizes_chinese_drama_hook() -> None:
    candidates = {
        "schema_version": "0.1",
        "status": "succeeded",
        "source_transcript_id": "demo",
        "source_video": "input.mp4",
        "content_channel": "local_asr",
        "candidates": [
            _plain_candidate(
                "generic",
                0.0,
                5.0,
                "今天我们继续介绍这个普通流程",
            ),
            _plain_candidate(
                "drama_hook",
                6.0,
                11.0,
                "消失五年后他竟然重生，所有人都后悔了",
            ),
        ],
    }

    report, plan = score_candidate_windows(candidates, max_selected=1)

    top = report["candidates"][0]
    assert top["candidate_id"] == "drama_hook"
    assert top["score_breakdown"]["hook_strength"] >= 0.5
    assert top["score_breakdown"]["conflict_intensity"] >= 0.5
    assert top["score_breakdown"]["payoff_or_reversal"] >= 0.5
    assert {"strong_hook", "conflict", "payoff_or_reversal"}.issubset(set(top["reasons"]))
    assert plan.highlights[0].source_segment_ids == ["seg_drama_hook"]


def test_score_candidate_windows_penalizes_later_repeated_source_subwindows() -> None:
    candidates = {
        "schema_version": "0.1",
        "status": "succeeded",
        "source_transcript_id": "demo",
        "source_video": "input.mp4",
        "content_channel": "local_asr",
        "candidates": [
            _split_candidate(
                "cand_001",
                3.0,
                8.0,
                "末世后第三个月 广播里说疫苗结束了",
            ),
            _split_candidate(
                "cand_002",
                8.0,
                13.0,
                "末世后第三个月 广播里说疫苗结束了",
            ),
        ],
    }

    report, _ = score_candidate_windows(candidates, max_selected=2)

    first = next(item for item in report["candidates"] if item["candidate_id"] == "cand_001")
    second = next(item for item in report["candidates"] if item["candidate_id"] == "cand_002")
    assert first["selection_score"] > second["selection_score"]
    assert first["decision"] == "selected"
    assert second["decision"] == "rejected"
    assert "duplicate_source_window" in second["rejection_reasons"]


def _plain_candidate(candidate_id: str, start_sec: float, end_sec: float, text: str) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "source": "transcript_window",
        "start_sec": start_sec,
        "end_sec": end_sec,
        "duration_sec": round(end_sec - start_sec, 6),
        "segment_ids": [f"seg_{candidate_id}"],
        "text": text,
        "asr_confidence": 0.9,
        "script_alignment": None,
        "evidence": {"content_channel": "local_asr"},
    }


def _split_candidate(candidate_id: str, start_sec: float, end_sec: float, text: str) -> dict[str, object]:
    payload = _plain_candidate(candidate_id, start_sec, end_sec, text)
    payload["source"] = "transcript_subwindow"
    payload["evidence"] = {
        "window_size": 2,
        "content_channel": "local_asr",
        "boundary_strategy": "elastic_duration_split",
        "source_window_start_sec": 3.0,
        "source_window_end_sec": 23.0,
    }
    return payload
