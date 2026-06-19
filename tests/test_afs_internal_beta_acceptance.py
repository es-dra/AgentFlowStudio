from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from tools import afs_internal_beta_acceptance_client as acceptance_client_module
from tools.afs_internal_beta_acceptance import run_http_acceptance, run_inprocess_acceptance
from tools.afs_internal_beta_acceptance_client import RuntimeTestClientAdapter


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


def test_http_acceptance_requires_invite_code_without_leaking_value(tmp_path: Path) -> None:
    try:
        run_http_acceptance(
            base_url="http://127.0.0.1:8790",
            invite_code="",
            beta_invite_code="server-secret-beta",
            report_path=tmp_path / "report.json",
        )
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("missing HTTP invite code should fail before any request")

    assert "invite code" in message.lower()
    assert "server-secret-beta" not in message


def test_http_acceptance_requires_beta_invite_code_for_scope_check(tmp_path: Path) -> None:
    try:
        run_http_acceptance(
            base_url="http://127.0.0.1:8790",
            invite_code="server-secret-alpha",
            beta_invite_code="",
            report_path=tmp_path / "report.json",
        )
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("HTTP acceptance needs a second invite code for beta-user isolation")

    assert "beta invite code" in message.lower()
    assert "server-secret-alpha" not in message


def test_http_acceptance_reuses_contract_with_safe_report(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "alpha-http-invite,beta-http-invite")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "false")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "false")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VISION", "false")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "false")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_ASR", "false")
    monkeypatch.setenv("AFS_ALLOW_EXTERNAL_DOWNLOAD", "false")

    app = create_runtime_app(runtime_root=tmp_path / "runtime")
    client = RuntimeTestClientAdapter(TestClient(app))

    def fake_http_client(base_url: str):
        assert base_url == "https://afs.example.test"
        return client

    monkeypatch.setattr("tools.afs_internal_beta_acceptance.HttpAcceptanceClient", fake_http_client)

    report = run_http_acceptance(
        base_url="https://afs.example.test",
        invite_code="alpha-http-invite",
        beta_invite_code="beta-http-invite",
        report_path=tmp_path / "http-report.json",
        run_id="unit-http",
    )

    assert report["mode"] == "deployed_http_runtime"
    assert report["status"] == "contract_verified_pending_human_acceptance"
    assert report["provider_calls_started"] is False
    assert (tmp_path / "http-report.json").is_file()

    serialized = json.dumps(report, ensure_ascii=False)
    assert "alpha-http-invite" not in serialized
    assert "beta-http-invite" not in serialized
    assert "session_token" not in serialized
    assert "https://afs.example.test" not in serialized
    assert "data_base64" not in serialized
    assert "iVBOR" not in serialized


def test_http_acceptance_client_bypasses_system_proxy(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeHttpxClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def close(self) -> None:
            pass

    monkeypatch.setattr(acceptance_client_module.httpx, "Client", FakeHttpxClient)

    client = acceptance_client_module.HttpAcceptanceClient("http://127.0.0.1:8790")
    client.close()

    assert captured["trust_env"] is False
    assert captured["follow_redirects"] is True
