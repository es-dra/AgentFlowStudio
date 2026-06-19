from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from tools import afs_internal_beta_acceptance_client as acceptance_client_module
from tools.afs_internal_beta_acceptance import run_http_acceptance, run_http_preflight, run_inprocess_acceptance
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
    assert report["human_review_packet"]["status"] == "pending_human_review"
    assert report["human_review_packet"]["score_scale"]["pass_threshold"] == 4
    section_ids = {item["section_id"] for item in report["human_review_packet"]["required_sections"]}
    assert "account_project_isolation" in section_ids
    assert "asset_context_continuity" in section_ids
    assert "generated_media_quality" in section_ids
    assert "feedback_revision_loop" in section_ids
    assert "privacy_boundary" in section_ids
    assert "accepted_for_next_beta_round" in report["human_review_packet"]["decision_options"]
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


def test_http_preflight_uses_health_without_invite_codes_or_provider_calls(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "alpha-http-invite,beta-http-invite")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VISION", "true")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "false")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_ASR", "false")
    monkeypatch.setenv("AFS_ALLOW_EXTERNAL_DOWNLOAD", "false")

    app = create_runtime_app(runtime_root=tmp_path / "runtime")
    client = RuntimeTestClientAdapter(TestClient(app))

    def fake_http_client(base_url: str):
        assert base_url == "https://afs.example.test"
        return client

    monkeypatch.setattr("tools.afs_internal_beta_acceptance.HttpAcceptanceClient", fake_http_client)

    report = run_http_preflight(
        base_url="https://afs.example.test",
        report_path=tmp_path / "preflight-report.json",
    )

    checks = {item["check_id"]: item for item in report["checks"]}
    assert report["artifact_type"] == "afs_internal_beta_acceptance_preflight_report"
    assert report["schema_version"] == "0.1.0"
    assert report["mode"] == "deployed_http_preflight"
    assert report["status"] == "ready_for_http_acceptance"
    assert report["requires_invite_codes"] is True
    assert report["provider_calls_started"] is False
    assert report["human_acceptance_claim"] == "not_claimed"
    assert report["business_validation_claim"] == "not_claimed"
    assert report["writes_company_kb"] is False
    assert report["writes_long_term_memory"] is False
    assert report["summary"]["failed_check_count"] == 0
    assert report["summary"]["passed_check_count"] >= 4
    assert checks["runtime_health"]["status"] == "passed"
    assert checks["auth_surface"]["status"] == "passed"
    assert checks["studio_static"]["status"] == "passed"
    assert checks["provider_gate_projection"]["status"] == "passed"
    assert report["safe_health"]["provider_gates"] == {
        "llm": True,
        "image": True,
        "video": False,
        "vision": True,
        "asr": False,
        "external_download": False,
    }
    assert (tmp_path / "preflight-report.json").is_file()

    serialized = json.dumps(report, ensure_ascii=False)
    assert "https://afs.example.test" not in serialized
    assert "alpha-http-invite" not in serialized
    assert "beta-http-invite" not in serialized
    assert "session_token" not in serialized
    assert "signed_url" not in serialized
    assert "provider_raw_response" not in serialized
    assert "data_base64" not in serialized
    assert str(tmp_path) not in serialized


def test_http_preflight_rejects_missing_base_url_without_invite_code_requirement() -> None:
    try:
        run_http_preflight(base_url="")
    except ValueError as exc:
        message = str(exc)
    else:
        raise AssertionError("missing preflight base URL should fail before any request")

    assert "base url" in message.lower()
    assert "invite" not in message.lower()


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


def test_acceptance_runner_keeps_preflight_logic_split() -> None:
    runner = Path("tools/afs_internal_beta_acceptance.py").read_text(encoding="utf-8")
    preflight = Path("tools/afs_internal_beta_acceptance_preflight.py").read_text(encoding="utf-8")
    errors = Path("tools/afs_internal_beta_acceptance_errors.py").read_text(encoding="utf-8")
    review = Path("tools/afs_internal_beta_acceptance_review.py").read_text(encoding="utf-8")

    assert "from tools.afs_internal_beta_acceptance_errors import AcceptanceConfigurationError" in runner
    assert "from tools.afs_internal_beta_acceptance_preflight import run_http_preflight as _run_http_preflight" in runner
    assert "from tools.afs_internal_beta_acceptance_review import build_human_review_packet" in Path("tools/afs_internal_beta_acceptance_contract.py").read_text(encoding="utf-8")
    assert "def _build_http_preflight_report" not in runner
    assert "def _safe_health" not in runner
    assert "def run_http_preflight" in runner
    assert "def _build_http_preflight_report" in preflight
    assert "safe_three_end_status" in preflight
    assert "class AcceptanceConfigurationError" in errors
    assert "def build_human_review_packet" in review
    assert "def render_human_review_markdown" in review
    assert "human_review_path" in runner
    assert len(runner.splitlines()) <= 220
    assert len(preflight.splitlines()) <= 220
    assert len(errors.splitlines()) <= 80
    assert len(review.splitlines()) <= 220
