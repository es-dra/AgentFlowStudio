from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def test_studio_workspace_starts_from_empty_project(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    created = client.post(
        "/projects",
        json={
            "project_id": "proj_studio_empty",
            "project_type": "short_video_campaign",
            "goal": "Build an industrial content memory workspace.",
        },
    ).json()

    state = client.get("/projects/proj_studio_empty/workbench-state").json()
    studio = state["studio_workspace"]

    assert studio["status"] == "needs_assets"
    assert studio["title"] == "Studio workspace"
    assert studio["active_project"]["project_id"] == "proj_studio_empty"
    assert studio["active_project"]["artifact_id"] == created["artifact"]["artifact_id"]
    assert studio["primary_command"]["backend_action"] == "add_reference"
    assert studio["primary_command"]["ui_action"] == "register-source-asset"
    assert studio["provider_status"] == "ready_not_run"
    assert studio["counts"] == {
        "assets": 0,
        "canvas_cards": 2,
        "filmstrip_items": 0,
        "review_candidates": 0,
        "runtime_jobs": 0,
        "provider_blockers": 0,
        "reusable_preferences": 0,
    }
    assert studio["canvas"]["selected_card_id"] == "content-cards"
    assert len(studio["canvas"]["cards"]) == 2
    assert studio["inspector"]["card_id"] == "content-cards"
    assert studio["run_controls"]["primary_action"] == "add_reference"
    assert studio["side_rail"]["assets"] == []
    assert studio["side_rail"]["style_profile"]["status"] == "not_started"
    assert studio["operations_summary"]["selected_job_id"] == ""
    assert studio["non_claims"] == state["non_claims"]


def test_studio_workspace_summarizes_blocked_production_flow(tmp_path) -> None:
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
    studio = state["studio_workspace"]
    serialized = json.dumps(studio, ensure_ascii=False).lower()

    assert studio["status"] == "blocked"
    assert studio["active_project"]["status"] == "ready_for_next_round"
    assert studio["primary_command"]["backend_action"] == "resolve_provider_preflight"
    assert studio["primary_command"]["enabled"] is False
    assert studio["provider_status"] == "blocked"
    assert studio["counts"]["canvas_cards"] == 2
    assert studio["counts"]["review_candidates"] == 2
    assert studio["counts"]["runtime_jobs"] == 4
    assert studio["counts"]["provider_blockers"] == 4
    assert studio["counts"]["reusable_preferences"] == 1
    assert studio["canvas"]["selected_card_id"] == "first-generation-check"
    assert studio["inspector"]["primary_artifact_id"] == round_1["artifacts"]["real_asset_test_report"]["artifact_id"]
    assert studio["run_controls"]["handoff_view"] == "Jobs"
    assert studio["filmstrip"] == state["creation_workspace"]["filmstrip"]
    assert studio["side_rail"]["style_profile"]["latest_profile_artifact_id"] == state["style_memory"]["latest_profile_artifact_id"]
    assert studio["side_rail"]["review_candidates"][0]["candidate_id"] == state["review_room"]["candidates"][0]["candidate_id"]
    assert studio["operations_summary"]["selected_job_id"] == provider["job"]["job_id"]
    assert studio["operations_summary"]["primary_artifact_id"] == provider["artifacts"]["provider_safe_manifest"]["artifact_id"]
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    assert "data/processed/runs" not in serialized


def _load_fixture(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload
