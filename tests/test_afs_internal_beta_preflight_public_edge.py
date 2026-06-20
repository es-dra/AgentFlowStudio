from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from tools.afs_internal_beta_acceptance import run_http_acceptance, run_http_preflight
from tools.afs_internal_beta_acceptance_client import RuntimeTestClientAdapter
from tools.afs_internal_beta_preflight_public_edge import default_public_studio_url, safe_public_edge_status


def test_http_preflight_can_include_public_edge_auth_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "alpha-http-invite,beta-http-invite")
    app = create_runtime_app(runtime_root=tmp_path / "runtime")
    client = RuntimeTestClientAdapter(TestClient(app))

    def fake_http_client(base_url: str):
        assert base_url == "https://afs.example.test"
        return client

    monkeypatch.setattr("tools.afs_internal_beta_acceptance.HttpAcceptanceClient", fake_http_client)
    monkeypatch.setattr(
        "tools.afs_internal_beta_acceptance_preflight.collect_public_edge_status",
        lambda **_kwargs: {
            "status": "blocked_by_edge_basic_auth",
            "provider_calls_started": False,
            "writes_company_kb": False,
            "writes_long_term_memory": False,
            "summary": {"public_edge_http_status": 401, "edge_basic_auth": True, "runtime_status": "ready"},
        },
    )

    report = run_http_preflight(
        base_url="https://afs.example.test",
        include_public_edge_status=True,
        public_edge_url="https://afs.example.test/studio/",
        report_path=tmp_path / "preflight-edge-report.json",
    )

    checks = {item["check_id"]: item for item in report["checks"]}
    assert report["status"] == "needs_attention"
    assert report["provider_calls_started"] is False
    assert checks["runtime_health"]["status"] == "passed"
    assert checks["public_edge_auth"]["status"] == "failed"
    assert checks["public_edge_auth"]["evidence"]["edge_basic_auth"] is True
    assert report["public_edge_status"]["status"] == "blocked_by_edge_basic_auth"
    assert report["public_edge_status"]["summary"]["public_edge_http_status"] == 401


def test_public_edge_preflight_safe_helpers() -> None:
    assert default_public_studio_url("https://afstudio.art") == "https://afstudio.art/studio/"
    assert default_public_studio_url("https://afstudio.art/studio") == "https://afstudio.art/studio/"

    safe = safe_public_edge_status({
        "status": "ready_for_public_auth",
        "summary": {"public_edge_http_status": 200, "edge_basic_auth": False, "runtime_status": "ready"},
        "provider_calls_started": False,
    })

    assert safe["status"] == "ready_for_public_auth"
    assert safe["summary"] == {"public_edge_http_status": 200, "edge_basic_auth": False, "runtime_status": "ready"}


def test_acceptance_runner_reuses_three_end_server_for_public_edge_by_default() -> None:
    runner = Path("tools/afs_internal_beta_acceptance.py").read_text(encoding="utf-8")
    args_module = Path("tools/afs_internal_beta_acceptance_args.py").read_text(encoding="utf-8")

    assert "public_edge_server=args.public_edge_server or args.three_end_server" in runner
    assert "--public-edge-status" in args_module
    assert "--public-edge-check-runtime-health" in args_module


def test_http_acceptance_public_edge_gate_runs_before_invite_codes(monkeypatch) -> None:
    def fail_http_client(_base_url: str):
        raise AssertionError("HTTP acceptance client must not start when public edge is blocked")

    monkeypatch.setattr("tools.afs_internal_beta_acceptance.HttpAcceptanceClient", fail_http_client)
    monkeypatch.setattr(
        "tools.afs_internal_beta_acceptance_edge_gate.collect_public_edge_status",
        lambda **_kwargs: {
            "status": "blocked_by_edge_basic_auth",
            "provider_calls_started": False,
            "writes_company_kb": False,
            "writes_long_term_memory": False,
            "summary": {"public_edge_http_status": 401, "edge_basic_auth": True, "runtime_status": "ready"},
        },
    )

    report = run_http_acceptance(
        base_url="https://afs.example.test",
        invite_code="",
        beta_invite_code="",
        include_public_edge_status=True,
        public_edge_url="https://afs.example.test/studio/",
    )

    assert report["artifact_type"] == "afs_internal_beta_acceptance_edge_gate_report"
    assert report["status"] == "public_edge_not_ready"
    assert report["provider_calls_started"] is False
    assert report["writes_company_kb"] is False
    assert report["writes_long_term_memory"] is False
    assert report["public_edge_status"]["status"] == "blocked_by_edge_basic_auth"
    assert report["summary"]["public_edge_http_status"] == 401


def test_http_acceptance_public_edge_ready_continues_contract(tmp_path: Path, monkeypatch) -> None:
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

    monkeypatch.setattr("tools.afs_internal_beta_acceptance.HttpAcceptanceClient", lambda _base_url: client)
    monkeypatch.setattr(
        "tools.afs_internal_beta_acceptance_edge_gate.collect_public_edge_status",
        lambda **_kwargs: {
            "status": "ready_for_public_auth",
            "provider_calls_started": False,
            "writes_company_kb": False,
            "writes_long_term_memory": False,
            "summary": {"public_edge_http_status": 200, "edge_basic_auth": False, "runtime_status": "ready"},
        },
    )

    report = run_http_acceptance(
        base_url="https://afs.example.test",
        invite_code="alpha-http-invite",
        beta_invite_code="beta-http-invite",
        include_public_edge_status=True,
        public_edge_url="https://afs.example.test/studio/",
        report_path=tmp_path / "acceptance-with-edge.json",
        run_id="edge-ready",
    )

    persisted = (tmp_path / "acceptance-with-edge.json").read_text(encoding="utf-8")
    assert report["status"] == "contract_verified_pending_human_acceptance"
    assert report["mode"] == "deployed_http_runtime"
    assert report["public_edge_status"]["status"] == "ready_for_public_auth"
    assert "ready_for_public_auth" in persisted
    assert "alpha-http-invite" not in persisted
    assert "beta-http-invite" not in persisted
