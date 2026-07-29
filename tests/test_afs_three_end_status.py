from __future__ import annotations

import json

from tools.afs_three_end_status import (
    RepoSnapshot,
    build_three_end_report,
    parse_repo_snapshot,
    run_three_end_status,
    safe_runtime_health,
)


def test_parse_repo_snapshot_marks_clean_origin_alignment() -> None:
    snapshot = parse_repo_snapshot(
        label="local",
        status_text="## master...origin/master\n",
        head="abc1234",
        origin_head="abc1234",
    )

    assert snapshot == RepoSnapshot(
        label="local",
        branch_status="## master...origin/master",
        head="abc1234",
        origin_head="abc1234",
        dirty=False,
        aligned_with_origin=True,
    )


def test_three_end_report_marks_drift_without_leaking_server_details() -> None:
    local = parse_repo_snapshot("local", "## master...origin/master\n", "abc1234", "abc1234")
    home = parse_repo_snapshot("server_home", "## master...origin/master\n", "abc1234", "abc1234")
    opt = parse_repo_snapshot("server_opt", "## master...origin/master [behind 1]\n", "old9999", "abc1234")
    unsafe_health = {
        "service": "agentflow_runtime_service",
        "status": "ready",
        "service_version": "0.2.0",
        "schema_version": "0.1.0",
        "runtime_root_persisted": True,
        "auth_required": True,
        "provider_gates": {"llm": True, "image": True, "vision": True, "video": False, "asr": False},
        "provider_config": "/etc/afs/providers.local.json",
        "runtime_root": "/opt/afs/AgentFlowStudio",
        "session_token": "secret-session",
    }

    report = build_three_end_report(local=local, server_home=home, server_opt=opt, runtime_health=unsafe_health)

    assert report["artifact_type"] == "afs_three_end_status_report"
    assert report["status"] == "needs_attention"
    assert report["provider_calls_started"] is False
    assert report["summary"]["aligned_end_count"] == 2
    assert report["summary"]["checked_end_count"] == 3
    assert report["ends"]["server_opt"]["aligned_with_origin"] is False
    assert report["runtime_health"]["status"] == "ready"
    assert report["runtime_health"]["provider_gates"]["video"] is False
    assert report["readiness_claims"]["runtime_three_end_alignment_evidence"] is False
    assert report["readiness_claims"]["runtime_loaded_code_freshness_claim"] == "not_claimed"
    assert report["readiness_claims"]["acceptance_ready"] is False
    assert report["readiness_claims"]["product_readiness"] is False
    assert "not human creative acceptance" in report["non_claims"]

    serialized = json.dumps(report, ensure_ascii=False)
    assert "/etc/afs" not in serialized
    assert "/opt/afs" not in serialized
    assert "secret-session" not in serialized
    assert "provider_config" not in serialized
    assert "session_token" not in serialized


def test_safe_runtime_health_keeps_only_public_readiness_fields() -> None:
    safe = safe_runtime_health(
        {
            "service": "agentflow_runtime_service",
            "status": "ready",
            "runtime_root_persisted": True,
            "auth_required": True,
            "studio_static": {"status": "ready", "mounted": True, "root_exists": True},
            "provider_gates": {"llm": 1, "video": 0, "unknown": "/private"},
            "readiness": {"service_ready": True, "runtime_three_end_alignment_evidence": False, "acceptance_ready": False},
            "signed_url": "https://example.test/signed",
        }
    )

    assert safe == {
        "service": "agentflow_runtime_service",
        "status": "ready",
        "service_version": "",
        "schema_version": "",
        "runtime_root_persisted": True,
        "auth_required": True,
        "studio_static": {
            "mounted": True,
            "root_exists": True,
            "index_exists": False,
            "assets_dir_exists": False,
            "entry_js_exists": False,
            "status": "ready",
            "route": "",
            "role": "",
        },
        "provider_gates": {"llm": True, "video": False},
        "readiness": {
            "service_ready": True,
            "auth_ready_for_public_edge": False,
            "public_edge_verified": False,
            "runtime_three_end_alignment_evidence": False,
            "acceptance_ready": False,
            "product_readiness": False,
            "runtime_loaded_code_freshness_claim": "not_claimed",
        },
    }


def test_three_end_alignment_does_not_claim_acceptance_or_product_readiness() -> None:
    local = parse_repo_snapshot("local", "## master...origin/master\n", "abc1234", "abc1234")
    home = parse_repo_snapshot("server_home", "## master...origin/master\n", "abc1234", "abc1234")
    opt = parse_repo_snapshot("server_opt", "## master...origin/master\n", "abc1234", "abc1234")

    report = build_three_end_report(
        local=local,
        server_home=home,
        server_opt=opt,
        runtime_health={"status": "ready", "auth_required": True},
    )

    assert report["status"] == "aligned"
    assert report["readiness_claims"] == {
        "repo_ends_aligned": True,
        "runtime_service_ready": True,
        "runtime_three_end_alignment_evidence": True,
        "runtime_loaded_code_freshness_claim": "not_claimed",
        "acceptance_ready": False,
        "human_creative_acceptance": False,
        "product_readiness": False,
    }


def test_report_treats_empty_checked_health_as_attention_needed() -> None:
    local = parse_repo_snapshot("local", "## master...origin/master\n", "abc1234", "abc1234")

    report = build_three_end_report(local=local, runtime_health={})

    assert report["summary"]["aligned_end_count"] == 1
    assert report["status"] == "needs_attention"
    assert report["summary"]["runtime_status"] == ""


def test_run_three_end_status_handles_remote_health_failure_without_leaking_error(tmp_path, monkeypatch) -> None:
    clean = parse_repo_snapshot("local", "## master...origin/master\n", "abc1234", "abc1234")

    monkeypatch.setattr("tools.afs_three_end_status.collect_local_repo_snapshot", lambda *args, **kwargs: clean)
    monkeypatch.setattr(
        "tools.afs_three_end_status.collect_remote_repo_snapshot",
        lambda _server, _path, label, **_kwargs: parse_repo_snapshot(label, "## master...origin/master\n", "abc1234", "abc1234"),
    )

    def fail_health(_server: str, _url: str) -> dict[str, object]:
        raise RuntimeError("curl failed against /opt/afs/AgentFlowStudio with private-marker")

    monkeypatch.setattr("tools.afs_three_end_status.collect_remote_runtime_health", fail_health)

    report = run_three_end_status(repo_root=tmp_path, server="afs-bwg-ops")

    assert report["status"] == "needs_attention"
    assert report["summary"]["checked_end_count"] == 3
    assert report["summary"]["aligned_end_count"] == 3
    serialized = json.dumps(report, ensure_ascii=False)
    assert "/opt/afs" not in serialized
    assert "private-marker" not in serialized
