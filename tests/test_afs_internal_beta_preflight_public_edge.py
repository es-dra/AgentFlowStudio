from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from tools.afs_internal_beta_acceptance import run_http_preflight
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

    assert "public_edge_server=args.public_edge_server or args.three_end_server" in runner
    assert "--public-edge-status" in runner
    assert "--public-edge-check-runtime-health" in runner
