from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def test_runtime_service_reports_health_and_capabilities_without_secrets(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    health = client.get("/health").json()
    capabilities = client.get("/capabilities").json()
    serialized = json.dumps({"health": health, "capabilities": capabilities}, ensure_ascii=False).lower()

    assert health["service"] == "agentflow_runtime_service"
    assert health["status"] == "ready"
    assert health["runtime_root_persisted"] is False
    assert "asset_test_run" in capabilities["actions"]
    assert "two_round_validate" in capabilities["actions"]
    assert "provider_validation_plan" in capabilities["actions"]
    assert "api_key" not in serialized
    assert "token" not in serialized
    assert "d:\\" not in serialized


def test_runtime_service_creates_project_manifest_and_reads_safe_artifact(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    created = client.post(
        "/projects",
        json={
            "project_id": "proj_runtime_demo",
            "project_type": "short_video_campaign",
            "goal": "Validate local AFS runtime service contract.",
            "status": "in_progress",
        },
    ).json()

    assert created["project_id"] == "proj_runtime_demo"
    assert created["manifest"]["artifact_type"] == "agentflow_project_manifest"
    assert created["artifact"]["artifact_id"]
    assert "path" not in created["artifact"]

    fetched = client.get("/projects/proj_runtime_demo/manifest").json()
    artifact = client.get(f"/artifacts/{created['artifact']['artifact_id']}").json()

    assert fetched["manifest"]["project_id"] == "proj_runtime_demo"
    assert artifact["artifact_type"] == "agentflow_project_manifest"
    assert artifact["payload"]["does_not_store_secrets"] is True
    assert "path" not in json.dumps(artifact, ensure_ascii=False).lower()


def test_runtime_service_runs_round_1_asset_harness_with_safe_job_artifacts(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/runs/asset-test",
        json={
            "project_id": "proj_runtime_demo",
            "asset_profile_seed": "examples/agentflow/production_memory_asset_profile_seed.example.json",
            "promotion_decision": "promoted",
            "promotion_rationale": "Runtime service fixture smoke; not durable memory.",
            "generated_at": "2026-06-04T08:00:00+08:00",
            "decided_at": "2026-06-04T08:20:00+08:00",
            "reviewed_at": "2026-06-04T08:30:00+08:00",
        },
    ).json()

    assert result["job"]["action"] == "asset_test_run"
    assert result["job"]["status"] == "blocked"
    assert result["report"]["run_status"] == "completed_with_blocks"
    assert result["report"]["provider_calls_started"] is False
    assert result["report"]["writes_long_term_memory"] is False
    assert result["artifacts"]["real_asset_test_report"]["artifact_id"]
    assert result["artifacts"]["agentflow_run_trace"]["artifact_type"] == "agentflow_run_trace"
    trace = client.get(f"/artifacts/{result['artifacts']['agentflow_run_trace']['artifact_id']}").json()["payload"]
    assert trace["tool_gate_state"]["remote_image"] == "blocked_by_default"
    assert trace["non_claims"] == ["not human acceptance", "not business validation", "not durable memory"]
    serialized = json.dumps(result, ensure_ascii=False).lower()
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized
    assert "data/processed/runs" not in serialized


def test_runtime_service_runs_two_round_validation_from_round_1_job(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    round_1 = client.post(
        "/runs/asset-test",
        json={
            "project_id": "proj_runtime_demo",
            "asset_profile_seed": "examples/agentflow/production_memory_asset_profile_seed.example.json",
            "promotion_decision": "promoted",
            "promotion_rationale": "Runtime service fixture smoke; not durable memory.",
            "generated_at": "2026-06-04T08:00:00+08:00",
            "decided_at": "2026-06-04T08:20:00+08:00",
            "reviewed_at": "2026-06-04T08:30:00+08:00",
        },
    ).json()

    result = client.post(
        "/runs/two-round-validate",
        json={
            "project_id": "proj_runtime_demo",
            "round_1_job_id": round_1["job"]["job_id"],
            "generated_at": "2026-06-04T08:40:00+08:00",
            "reviewed_at": "2026-06-04T08:50:00+08:00",
        },
    ).json()

    assert result["job"]["action"] == "two_round_validate"
    assert result["job"]["status"] == "succeeded"
    assert result["report"]["runtime_verification_status"] == "verified"
    assert result["report"]["improvement_assessment"] == "no_clear_improvement"
    assert result["artifacts"]["two_round_context_runtime_report"]["artifact_id"]
    assert result["artifacts"]["agentflow_run_trace"]["artifact_type"] == "agentflow_run_trace"


def test_runtime_service_provider_validation_plan_is_blocked_without_live_calls(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    result = client.post(
        "/provider/validation-plan",
        json={
            "project_id": "proj_runtime_demo",
            "asset_profile_seed": "examples/agentflow/production_memory_asset_profile_seed.example.json",
            "generated_at": "2026-06-04T09:00:00+08:00",
        },
    ).json()

    assert result["job"]["action"] == "provider_validation_plan"
    assert result["job"]["status"] == "blocked"
    assert result["safe_manifest"]["status"] == "blocked"
    assert result["safe_manifest"]["provider_calls_started"] is False
    assert result["safe_manifest"]["request_summary"]["private_paths_persisted"] is False
    assert result["artifacts"]["agentflow_run_trace"]["artifact_type"] == "agentflow_run_trace"
    serialized = json.dumps(result, ensure_ascii=False).lower()
    assert "providers.local.json" not in serialized
    assert "api_key" not in serialized
    assert "d:\\" not in serialized


def test_frontend_runtime_service_request_examples_match_api_contract(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    fixture_dir = Path("examples/frontend_runtime_service")

    project_request = _load_fixture(fixture_dir / "create_project.request.example.json")
    project = client.post("/projects", json=project_request).json()
    assert project["manifest"]["project_id"] == project_request["project_id"]

    round_1_request = _load_fixture(fixture_dir / "asset_test_run.request.example.json")
    round_1 = client.post("/runs/asset-test", json=round_1_request).json()
    assert round_1["job"]["job_id"]

    feedback_request = _load_fixture(fixture_dir / "feedback_record.request.example.json")
    feedback = client.post("/feedback", json=feedback_request).json()
    assert feedback["feedback_event"]["feedback_is_memory"] is False

    round_2_request = _load_fixture(fixture_dir / "two_round_validate.request.example.json")
    round_2_request["round_1_job_id"] = round_1["job"]["job_id"]
    round_2 = client.post("/runs/two-round-validate", json=round_2_request).json()
    assert round_2["report"]["runtime_verification_status"] == "verified"

    provider_request = _load_fixture(fixture_dir / "provider_validation_plan.request.example.json")
    provider = client.post("/provider/validation-plan", json=provider_request).json()
    assert provider["safe_manifest"]["provider_calls_started"] is False


def _load_fixture(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert "api_key" not in serialized
    assert "token" not in serialized
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    return payload
