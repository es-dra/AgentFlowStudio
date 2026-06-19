from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from tools.afs_internal_beta_acceptance import run_inprocess_acceptance
from tools.afs_internal_beta_human_review_record import build_human_review_record, write_human_review_record


def _review_input(decision: str = "accepted_for_next_beta_round") -> dict:
    return {
        "reviewer_id": "operator-a",
        "decision": decision,
        "section_scores": {
            "account_project_isolation": 4,
            "asset_context_continuity": 5,
            "generated_media_quality": 4,
            "feedback_revision_loop": 4,
            "privacy_boundary": 5,
        },
        "notes": "Checked in browser. Do not include C:\\Users\\operator\\secret.png or https://example.test/signed?token=abc.",
    }


def test_human_review_record_accepts_safe_operator_decision(tmp_path: Path) -> None:
    report = run_inprocess_acceptance(runtime_root=tmp_path / "runtime")

    record = build_human_review_record(report, _review_input())

    assert record["artifact_type"] == "afs_internal_beta_human_review_record"
    assert record["status"] == "accepted_for_next_beta_round"
    assert record["human_acceptance_claim"] == "accepted_for_next_beta_round"
    assert record["business_validation_claim"] == "not_claimed"
    assert record["durable_memory_promotion"] == "not_claimed"
    assert record["source_report_status"] == "contract_verified_pending_human_acceptance"
    assert record["reviewer"]["id"] == "operator-a"
    assert record["score_summary"] == {"min_score": 4, "pass_threshold": 4, "all_required_scores_pass": True}
    assert set(record["section_scores"]) == {
        "account_project_isolation",
        "asset_context_continuity",
        "generated_media_quality",
        "feedback_revision_loop",
        "privacy_boundary",
    }
    serialized = json.dumps(record, ensure_ascii=False)
    assert str(tmp_path) not in serialized
    assert "C:\\Users" not in serialized
    assert "session_token" not in serialized
    assert "invite" not in serialized.lower()
    assert "signed" not in serialized.lower()
    assert "token=abc" not in serialized


def test_human_review_record_refuses_inconsistent_acceptance(tmp_path: Path) -> None:
    report = run_inprocess_acceptance(runtime_root=tmp_path / "runtime")
    review = _review_input()
    review["section_scores"]["generated_media_quality"] = 2

    record = build_human_review_record(report, review)

    assert record["status"] == "review_requires_followup"
    assert record["human_acceptance_claim"] == "not_claimed"
    assert "score_below_pass_threshold" in record["warnings"]


def test_human_review_record_writer_outputs_safe_json(tmp_path: Path) -> None:
    report = run_inprocess_acceptance(runtime_root=tmp_path / "runtime")
    output_path = tmp_path / "human-review-record.json"

    record = write_human_review_record(report, _review_input(), output_path)

    assert output_path.is_file()
    persisted = json.loads(output_path.read_text(encoding="utf-8"))
    assert persisted == record
    assert persisted["artifact_type"] == "afs_internal_beta_human_review_record"
    assert "provider_raw_response" not in output_path.read_text(encoding="utf-8")


def test_human_review_record_cli_reads_powershell_utf8_bom(tmp_path: Path) -> None:
    report = run_inprocess_acceptance(runtime_root=tmp_path / "runtime")
    report_path = tmp_path / "report.json"
    review_path = tmp_path / "review.json"
    output_path = tmp_path / "record.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    review_path.write_text(json.dumps(_review_input(), ensure_ascii=False), encoding="utf-8-sig")

    result = subprocess.run(
        [
            sys.executable,
            "tools/afs_internal_beta_human_review_record.py",
            "--report",
            str(report_path),
            "--review-json",
            str(review_path),
            "--output",
            str(output_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert output_path.is_file()
    assert json.loads(output_path.read_text(encoding="utf-8"))["status"] == "accepted_for_next_beta_round"
