from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def test_operations_workspace_starts_from_empty_project(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_operations_empty",
            "project_type": "short_video_campaign",
            "goal": "Create a provider-gated content memory workbench.",
        },
    )

    state = client.get("/projects/proj_operations_empty/workbench-state").json()
    operations = state["operations_workspace"]

    assert operations["status"] == "not_started"
    assert operations["title"] == "任务与 Provider"
    assert operations["selected_job_id"] == ""
    assert operations["counts"] == {
        "jobs": 0,
        "running": 0,
        "blocked": 0,
        "failed": 0,
        "succeeded": 0,
        "activities": 0,
        "artifact_refs": 0,
        "provider_blockers": 0,
    }
    assert operations["provider_gate"]["status"] == "ready_not_run"
    assert operations["provider_controls"]["primary_action"] == "run_provider_preflight"
    assert operations["provider_controls"]["enabled"] is False
    assert operations["polling"]["enabled"] is True


def test_operations_workspace_summarizes_provider_blocked_flow(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    fixture_dir = Path("examples/frontend_runtime_service")

    client.post("/projects", json=_load_fixture(fixture_dir / "create_project.request.example.json"))
    round_1 = client.post("/runs/asset-test", json=_load_fixture(fixture_dir / "asset_test_run.request.example.json")).json()
    client.post("/feedback", json=_load_fixture(fixture_dir / "feedback_record.request.example.json"))
    round_2_request = _load_fixture(fixture_dir / "two_round_validate.request.example.json")
    round_2_request["round_1_job_id"] = round_1["job"]["job_id"]
    client.post("/runs/two-round-validate", json=round_2_request)
    provider = client.post("/provider/validation-plan", json=_load_fixture(fixture_dir / "provider_validation_plan.request.example.json")).json()

    state = client.get("/projects/proj_runtime_demo/workbench-state").json()
    operations = state["operations_workspace"]

    assert operations["status"] == "blocked"
    assert operations["selected_job_id"] == provider["job"]["job_id"]
    assert operations["counts"]["jobs"] == 4
    assert operations["counts"]["blocked"] == 2
    assert operations["counts"]["artifact_refs"] >= 4
    assert operations["counts"]["provider_blockers"] == 4
    assert operations["latest_activity"][0]["action"] == "provider_validation_plan"
    assert operations["provider_gate"]["primary_artifact_id"] == provider["artifacts"]["provider_safe_manifest"]["artifact_id"]
    assert operations["provider_controls"]["primary_action"] == "resolve_provider_preflight"
    assert operations["provider_controls"]["enabled"] is False
    assert operations["provider_controls"]["blocked_reason"] == "Provider 能力闸门仍处于阻塞状态。"


def _load_fixture(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
