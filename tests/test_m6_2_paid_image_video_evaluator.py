from __future__ import annotations

from pathlib import Path

from agentflow.harness.json_io import write_json
from tools import evaluate_m6_2_paid_image_video_evidence as evaluator


def test_m6_2_paid_evidence_evaluator_counts_two_clean_cases_and_recovery_case(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(evaluator, "_is_inside_git_worktree", lambda path: False)
    monkeypatch.setattr(
        evaluator,
        "_ffprobe",
        lambda path: {
            "status": "PASS",
            "streams": [
                {
                    "codec_type": "video",
                    "width": 864,
                    "height": 496,
                    "avg_frame_rate": "24/1",
                    "r_frame_rate": "24/1",
                    "nb_frames": "240",
                }
            ],
            "format": {"duration": "10.0"},
        },
    )
    monkeypatch.setattr(evaluator, "_video_event_scan", lambda path: {"status": "PASS", "black_segments": [], "freeze_events": []})
    run_root = tmp_path / "evidence"
    _write_smoke(run_root)
    _write_case(run_root, "dialogue_room", with_resolved_retry=True)
    _write_case(run_root, "four_person_action")
    _write_case(run_root, "sci_fi_chamber", recovery_ledger=True)

    report = evaluator.evaluate(run_root, budget_usd=100)

    assert report["verdict"] == "PASS"
    assert report["P0"] == 0
    assert report["P1"] == 0
    assert report["clean_case_count"] == 2
    assert {case["case_id"] for case in report["cases"] if case["clean_counted"]} == {
        "dialogue_room",
        "four_person_action",
    }
    sci_fi = next(case for case in report["cases"] if case["case_id"] == "sci_fi_chamber")
    assert sci_fi["classification"] == "RECOVERY_EVIDENCE_NOT_COUNTED"
    dialogue = next(case for case in report["cases"] if case["case_id"] == "dialogue_room")
    assert dialogue["media_metrics"]["width"] == 864
    assert dialogue["media_metrics"]["fps"] == 24.0
    assert dialogue["technical_scores"]["black_freeze_repeat_anomaly"] == 5
    assert report["budget"]["within_budget"] is True
    assert any(issue["id"] == "m6_2_sci_fi_chamber_recovery_ledger" for issue in report["issue_ledger"]["resolved"])


def _write_smoke(run_root: Path) -> None:
    write_json(
        run_root / "paid_smoke" / "paid_smoke_technical_qa.json",
        {
            "status": "PASS",
            "image_smoke": {"status": "PASS", "model": "gpt-image-2"},
            "image_retry_safe_reference": {"status": "PASS", "model": "gpt-image-2"},
            "video_first_fail": {"status": "FAIL", "provider": "volc_seedance", "safe_error": {"message": "safety blocked"}},
            "video_retry_fail": {"status": "FAIL", "provider": "volc_seedance", "safe_error": {"message": "safety blocked"}},
            "video_safe_reference": {
                "status": "PASS",
                "model": "doubao-seedance-2-0",
                "outputs": [{"duration_sec": 5.0}],
            },
        },
    )


def _write_case(
    run_root: Path,
    case_id: str,
    *,
    with_resolved_retry: bool = False,
    recovery_ledger: bool = False,
) -> None:
    case_root = run_root / "cases" / case_id
    media_root = run_root / "candidate_runtime" / "projects" / f"m6-2-{case_id}" / "adaptive_canvas_v2" / "paid-media-v2"
    final = media_root / "final" / "adaptive_canvas_v2_final.mp4"
    contact_sheet = media_root / "qa" / "contact_sheet_1fps.jpg"
    final.parent.mkdir(parents=True, exist_ok=True)
    contact_sheet.parent.mkdir(parents=True, exist_ok=True)
    final.write_bytes(b"not-a-real-video-in-unit-test")
    contact_sheet.write_bytes(b"not-a-real-contact-sheet-in-unit-test")
    write_json(
        case_root / "case_result.json",
        {
            "status": "PASS",
            "case_id": case_id,
            "shot_count": 2,
            "video_seconds": 10.0,
            "idempotency": {
                "status": "PASS",
                "paid_attempt_count_before": 5,
                "paid_attempt_count_after": 5,
                "attempt_rows_before": 5,
                "attempt_rows_after": 5,
            },
        },
    )
    write_json(
        media_root / "delivery_manifest.json",
        {
            "status": "registered",
            "shot_count": 2,
            "keyframe_count": 2,
            "video_chunk_count": 2,
            "final_duration_sec": 10.0,
            "final_sha256": "a" * 64,
        },
    )
    write_json(
        media_root / "qa" / "technical_qa.json",
        {
            "status": "pass",
            "findings": [],
            "final_decode_status": "pass",
            "contact_sheet_sha256": "b" * 64,
        },
    )
    attempts = [
        _attempt("reference_sheet", "image", "fp-reference", "succeeded"),
        _attempt("keyframe", "image", "fp-keyframe-1", "succeeded"),
        _attempt("keyframe", "image", "fp-keyframe-2", "succeeded"),
        _attempt("video_chunk", "video", "fp-video-1", "succeeded"),
        _attempt("video_chunk", "video", "fp-video-2", "succeeded"),
    ]
    if with_resolved_retry:
        attempts.insert(0, _attempt("reference_sheet", "image", "fp-reference", "failed", suffix="attempt-0", safe_error=True))
    if recovery_ledger:
        attempts[-1]["safe_error"] = {"message": "old failure leaked into success"}
        attempts.append({**attempts[-1], "status": "reserved"})
    write_json(
        media_root / "charge_ledger.json",
        {
            "paid_attempt_count": sum(1 for item in attempts if item["provider_calls_started"]),
            "attempts": attempts,
        },
    )


def _attempt(stage: str, capability: str, fingerprint: str, status: str, *, suffix: str = "attempt-1", safe_error: bool = False) -> dict:
    payload = {
        "attempt_id": f"{stage}-{capability}-{fingerprint}-{suffix}",
        "stage": stage,
        "capability": capability,
        "charge_fingerprint": fingerprint,
        "status": status,
        "provider_calls_started": status != "reserved",
    }
    if safe_error:
        payload["safe_error"] = {"message": "download failed"}
    return payload
