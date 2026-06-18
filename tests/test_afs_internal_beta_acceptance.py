from __future__ import annotations

import json
from pathlib import Path

from tools.afs_internal_beta_acceptance import run_inprocess_acceptance


def test_internal_beta_acceptance_contract_keeps_report_safe(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VISION", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)

    report = run_inprocess_acceptance(runtime_root=tmp_path)

    steps = {item["step_id"]: item for item in report["steps"]}
    assert report["artifact_type"] == "afs_internal_beta_acceptance_report"
    assert report["status"] == "contract_verified_pending_human_acceptance"
    assert report["mode"] == "inprocess_deterministic"
    assert report["provider_calls_started"] is False
    assert report["human_acceptance_claim"] == "not_claimed"
    assert report["business_validation_claim"] == "not_claimed"
    assert report["writes_company_kb"] is False
    assert report["writes_long_term_memory"] is False

    assert steps["runtime_health"]["status"] == "passed"
    assert steps["auth_registration"]["status"] == "passed"
    assert steps["project_owner_isolation"]["status"] == "passed"
    assert steps["studio_state_isolation"]["status"] == "passed"
    assert steps["image_asset_isolation"]["status"] == "passed"
    assert steps["vision_draft_gate_closed"]["status"] == "expected_blocked"
    assert steps["fixed_assets_not_polluted"]["status"] == "passed"
    assert steps["feedback_raw_evidence"]["status"] == "passed"
    assert steps["artifact_scope"]["status"] == "passed"
    assert steps["video_gate_closed"]["status"] == "passed"

    serialized = json.dumps(report, ensure_ascii=False)
    assert str(tmp_path) not in serialized
    assert "session_token" not in serialized
    assert "strong-password" not in serialized
    assert "data_base64" not in serialized
    assert "iVBOR" not in serialized
    assert "provider_raw_response" not in serialized
    assert "signed_url" not in serialized


def test_internal_beta_acceptance_writes_optional_report_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VISION", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    report_path = tmp_path / "report.json"

    report = run_inprocess_acceptance(runtime_root=tmp_path / "runtime", report_path=report_path)

    assert report_path.is_file()
    persisted = json.loads(report_path.read_text(encoding="utf-8"))
    assert persisted["status"] == report["status"]
    assert persisted["summary"]["passed_step_count"] >= 1
