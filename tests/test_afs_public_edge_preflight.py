from __future__ import annotations

from tools.afs_public_edge_preflight import EdgeResponse, nginx_basic_auth_disable_commands, run_public_edge_preflight


def test_public_edge_preflight_detects_nginx_basic_auth_block() -> None:
    report = run_public_edge_preflight(
        public_url="https://afstudio.art/studio/?preview=1",
        server="afs-bwg-ops",
        head_fetcher=lambda _url: EdgeResponse(
            status_code=401,
            headers={"www-authenticate": 'Basic realm="AFS Studio Internal Test"'},
        ),
        runtime_health_fetcher=lambda _server, _url: {
            "status": "ready",
            "auth_required": True,
            "studio_static": {"status": "ready"},
            "provider_gates": {"llm": True, "image": True, "vision": True, "video": False},
        },
    )

    assert report["status"] == "blocked_by_edge_basic_auth"
    assert report["provider_calls_started"] is False
    assert report["writes_company_kb"] is False
    assert report["writes_long_term_memory"] is False
    assert report["summary"]["edge_basic_auth"] is True
    assert report["checks"][0]["check_id"] == "public_edge_auth"
    assert report["checks"][0]["status"] == "failed"
    assert report["checks"][0]["evidence"]["public_url"] == "https://afstudio.art/studio/"
    assert report["checks"][0]["evidence"]["www_authenticate"] == "Basic"
    assert report["checks"][1]["status"] == "passed"
    assert report["checks"][2]["check_id"] == "runtime_auth_boundary"
    assert report["checks"][2]["status"] == "passed"
    assert report["readiness_boundary"]["acceptance_ready"] is False
    assert "not human creative acceptance" in report["non_claims"]
    assert report["recommended_action"]["action"] == "remove_nginx_basic_auth_or_intentionally_keep_it"
    assert "afs_public_edge_nginx_fix" in " ".join(report["recommended_action"]["commands"])


def test_public_edge_preflight_reports_ready_when_edge_and_runtime_are_ready() -> None:
    report = run_public_edge_preflight(
        public_url="https://afstudio.art/studio/",
        server="afs-bwg-ops",
        head_fetcher=lambda _url: EdgeResponse(status_code=200, headers={}),
        runtime_health_fetcher=lambda _server, _url: {
            "status": "ready",
            "auth_required": True,
            "studio_static": {"status": "ready", "mounted": True},
            "provider_gates": {"llm": True, "image": True, "video": False},
        },
    )

    assert report["status"] == "ready_for_public_auth"
    assert report["summary"]["auth_required"] is True
    assert report["summary"]["acceptance_ready"] is False
    assert report["summary"]["edge_basic_auth"] is False
    assert [item["status"] for item in report["checks"]] == ["passed", "passed", "passed"]
    assert report["runtime_health"]["provider_gates"] == {"llm": True, "image": True, "video": False}
    assert report["readiness_boundary"] == {
        "public_edge_auth_ready": True,
        "runtime_three_end_alignment_evidence": False,
        "runtime_loaded_code_freshness_claim": "not_claimed",
        "acceptance_ready": False,
        "human_acceptance_claim": "not_claimed",
        "product_readiness_claim": "not_claimed",
    }
    assert report["recommended_action"] == {"action": "none", "commands": []}


def test_public_edge_preflight_blocks_auth_disabled_runtime_from_public_auth_ready() -> None:
    report = run_public_edge_preflight(
        public_url="https://afstudio.art/studio/",
        server="afs-bwg-ops",
        head_fetcher=lambda _url: EdgeResponse(status_code=200, headers={}),
        runtime_health_fetcher=lambda _server, _url: {
            "status": "ready",
            "auth_required": False,
            "studio_static": {"status": "ready", "mounted": True},
            "readiness": {
                "service_ready": True,
                "auth_ready_for_public_edge": False,
                "runtime_three_end_alignment_evidence": False,
                "acceptance_ready": False,
            },
        },
    )

    checks = {item["check_id"]: item for item in report["checks"]}
    assert report["status"] == "public_edge_auth_not_ready"
    assert checks["public_edge_auth"]["status"] == "passed"
    assert checks["runtime_health"]["status"] == "passed"
    assert checks["runtime_auth_boundary"]["status"] == "failed"
    assert report["readiness_boundary"]["public_edge_auth_ready"] is False
    assert report["readiness_boundary"]["acceptance_ready"] is False


def test_public_edge_preflight_can_check_runtime_health_locally() -> None:
    report = run_public_edge_preflight(
        public_url="https://afstudio.art/studio/",
        check_runtime_health=True,
        head_fetcher=lambda _url: EdgeResponse(status_code=401, headers={"www-authenticate": "Basic realm=x"}),
        local_runtime_health_fetcher=lambda _url: {
            "status": "ready",
            "auth_required": True,
            "studio_static": {"status": "ready"},
        },
    )

    assert report["status"] == "blocked_by_edge_basic_auth"
    assert report["checks"][1]["evidence"]["runtime_checked"] is True
    assert report["checks"][1]["evidence"]["runtime_status"] == "ready"
    assert report["checks"][1]["status"] == "passed"
    assert report["checks"][2]["status"] == "passed"


def test_nginx_basic_auth_disable_commands_are_sudo_scoped() -> None:
    commands = nginx_basic_auth_disable_commands()

    assert commands[0].startswith("sudo ./.venv/bin/python -m tools.afs_public_edge_nginx_fix --apply")
    assert commands[-2:] == ["sudo nginx -t", "sudo systemctl reload nginx"]
    assert all("provider" not in command.lower() for command in commands)
    assert all("sed" not in command.lower() for command in commands)
