from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app
from tools.afs_internal_beta_acceptance import run_http_preflight
from tools.afs_internal_beta_acceptance_client import RuntimeTestClientAdapter


def test_http_preflight_can_embed_safe_three_end_status(tmp_path: Path, monkeypatch) -> None:
    _enable_auth_preflight_env(monkeypatch)
    client = RuntimeTestClientAdapter(TestClient(create_runtime_app(runtime_root=tmp_path / "runtime")))
    captured: dict[str, object] = {}

    def fake_http_client(base_url: str):
        assert base_url == "https://afs.example.test"
        return client

    def fake_three_end_status(**kwargs):
        captured.update(kwargs)
        return {
            "artifact_type": "afs_three_end_status_report",
            "schema_version": "0.1.0",
            "status": "aligned",
            "provider_calls_started": False,
            "writes_company_kb": False,
            "writes_long_term_memory": False,
            "summary": {
                "checked_end_count": 3,
                "aligned_end_count": 3,
                "dirty_end_count": 0,
                "runtime_status": "ready",
            },
            "ends": {"local": _unsafe_repo_snapshot(tmp_path)},
            "runtime_health": {
                "service": "agentflow_runtime_service",
                "status": "ready",
                "runtime_root": str(tmp_path / "unsafe-runtime-root"),
                "provider_gates": {"llm": True, "image": True, "video": False, "unknown": "secret"},
                "readiness": {"service_ready": True, "runtime_three_end_alignment_evidence": False, "acceptance_ready": False},
            },
            "readiness_claims": {
                "repo_ends_aligned": True,
                "runtime_service_ready": True,
                "runtime_three_end_alignment_evidence": True,
                "runtime_loaded_code_freshness_claim": "not_claimed",
                "acceptance_ready": False,
                "human_creative_acceptance": False,
                "product_readiness": False,
            },
            "unsafe_absolute_path": str(tmp_path),
        }

    monkeypatch.setattr("tools.afs_internal_beta_acceptance.HttpAcceptanceClient", fake_http_client)
    monkeypatch.setattr("tools.afs_internal_beta_preflight_three_end.run_three_end_status", fake_three_end_status)

    report = run_http_preflight(
        base_url="https://afs.example.test",
        report_path=tmp_path / "preflight-three-end.json",
        include_three_end_status=True,
        three_end_repo_root=tmp_path / "repo",
        three_end_server="afs-bwg-ops",
    )

    checks = {item["check_id"]: item for item in report["checks"]}
    assert captured["repo_root"] == tmp_path / "repo"
    assert captured["server"] == "afs-bwg-ops"
    assert report["status"] == "ready_for_http_acceptance"
    assert report["three_end_status"]["status"] == "aligned"
    assert report["three_end_status"]["readiness_claims"]["runtime_three_end_alignment_evidence"] is True
    assert report["three_end_status"]["readiness_claims"]["runtime_loaded_code_freshness_claim"] == "not_claimed"
    assert report["three_end_status"]["readiness_claims"]["acceptance_ready"] is False
    assert report["readiness_claims"]["runtime_three_end_alignment_evidence"] is True
    assert report["readiness_claims"]["runtime_loaded_code_freshness_claim"] == "not_claimed"
    assert report["readiness_claims"]["acceptance_ready"] is False
    assert report["three_end_status"]["summary"]["checked_end_count"] == 3
    assert checks["three_end_status"]["status"] == "passed"
    assert checks["three_end_status"]["evidence"] == {
        "status": "aligned",
        "checked_end_count": 3,
        "aligned_end_count": 3,
        "dirty_end_count": 0,
        "runtime_status": "ready",
    }

    serialized = json.dumps(report, ensure_ascii=False)
    assert str(tmp_path) not in serialized
    assert "unsafe_absolute_path" not in serialized
    assert "unsafe-runtime-root" not in serialized
    assert "repo_path" not in serialized
    assert "unknown" not in serialized
    assert "https://afs.example.test" not in serialized
    assert "provider_raw_response" not in serialized


def test_http_preflight_marks_three_end_drift_as_needs_attention(tmp_path: Path, monkeypatch) -> None:
    _enable_auth_preflight_env(monkeypatch)
    client = RuntimeTestClientAdapter(TestClient(create_runtime_app(runtime_root=tmp_path / "runtime")))

    def fake_http_client(base_url: str):
        assert base_url == "https://afs.example.test"
        return client

    def fake_three_end_status(**_kwargs):
        return {
            "artifact_type": "afs_three_end_status_report",
            "schema_version": "0.1.0",
            "status": "needs_attention",
            "provider_calls_started": False,
            "writes_company_kb": False,
            "writes_long_term_memory": False,
            "summary": {
                "checked_end_count": 3,
                "aligned_end_count": 2,
                "dirty_end_count": 0,
                "runtime_status": "ready",
            },
            "ends": {},
            "runtime_health": {"status": "ready"},
        }

    monkeypatch.setattr("tools.afs_internal_beta_acceptance.HttpAcceptanceClient", fake_http_client)
    monkeypatch.setattr("tools.afs_internal_beta_preflight_three_end.run_three_end_status", fake_three_end_status)

    report = run_http_preflight(
        base_url="https://afs.example.test",
        include_three_end_status=True,
        three_end_repo_root=tmp_path / "repo",
    )

    checks = {item["check_id"]: item for item in report["checks"]}
    assert report["status"] == "needs_attention"
    assert report["summary"]["failed_check_count"] == 1
    assert checks["three_end_status"]["status"] == "failed"
    assert checks["three_end_status"]["provider_calls_started"] is False


def _enable_auth_preflight_env(monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "alpha-http-invite,beta-http-invite")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VISION", "true")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "false")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_ASR", "false")
    monkeypatch.setenv("AFS_ALLOW_EXTERNAL_DOWNLOAD", "false")


def _unsafe_repo_snapshot(tmp_path: Path) -> dict[str, object]:
    return {
        "label": "local",
        "branch_status": "## master...origin/master",
        "head": "abc1234",
        "origin_head": "abc1234",
        "dirty": False,
        "aligned_with_origin": True,
        "repo_path": str(tmp_path / "unsafe-local-path"),
    }
