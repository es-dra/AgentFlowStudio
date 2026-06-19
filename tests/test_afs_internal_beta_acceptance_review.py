from __future__ import annotations

import json
from pathlib import Path

from tools.afs_internal_beta_acceptance import run_inprocess_acceptance


def test_internal_beta_acceptance_report_has_review_packet_without_acceptance_claim(tmp_path: Path) -> None:
    report = run_inprocess_acceptance(runtime_root=tmp_path)

    packet = report["human_review_packet"]
    sections = {item["section_id"]: item for item in packet["required_sections"]}

    assert packet["schema_version"] == "0.1.0"
    assert packet["status"] == "pending_human_review"
    assert packet["reviewer_role"] == "internal_beta_operator"
    assert packet["score_scale"] == {"min": 1, "max": 5, "pass_threshold": 4}
    assert packet["acceptance_claim"] == "not_claimed"
    assert packet["forbidden_claims"] == [
        "human acceptance",
        "business validation",
        "durable memory promotion",
        "live provider quality approval",
    ]
    assert sections["generated_media_quality"]["requires_human_score"] is True
    assert sections["generated_media_quality"]["evidence_step_ids"] == ["video_gate_closed"]
    assert sections["asset_context_continuity"]["evidence_step_ids"] == [
        "asset_confirmation",
        "fixed_asset_context_reuse",
    ]
    assert packet["manual_artifacts_required"][0]["artifact_id"] == "browser_session_notes"
    serialized = json.dumps(packet, ensure_ascii=False)
    assert str(tmp_path) not in serialized
    assert "session_token" not in serialized
    assert "invite" not in serialized.lower()
    assert "signed_url" not in serialized


def test_internal_beta_acceptance_writes_optional_human_review_markdown(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VISION", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    review_path = tmp_path / "human-review.md"

    report = run_inprocess_acceptance(runtime_root=tmp_path / "runtime", human_review_path=review_path)

    assert review_path.is_file()
    markdown = review_path.read_text(encoding="utf-8")
    assert "# AFS Internal Beta Human Review" in markdown
    assert f"Report status: `{report['status']}`" in markdown
    assert "- [ ] Account and project isolation" in markdown
    assert "- [ ] Generated media quality" in markdown
    assert "Score (1-5): ____" in markdown
    assert "Decision: `accepted_for_next_beta_round` / `needs_fix_before_next_beta_round` / `blocked_by_provider_or_configuration`" in markdown
    assert "Human acceptance is not claimed until this checklist is completed by an operator." in markdown
    assert str(tmp_path) not in markdown
    assert "session_token" not in markdown
    assert "invite" not in markdown.lower()
    assert "signed_url" not in markdown
