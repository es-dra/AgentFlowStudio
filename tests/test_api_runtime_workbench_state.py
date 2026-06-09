from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def test_runtime_service_workbench_state_starts_from_user_facing_project_state(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    created = client.post(
        "/projects",
        json={
            "project_id": "proj_workbench_demo",
            "project_type": "short_video_campaign",
            "goal": "Create a provider-gated content memory workbench.",
        },
    ).json()

    state = client.get("/projects/proj_workbench_demo/workbench-state").json()
    serialized = json.dumps(state, ensure_ascii=False).lower()

    assert state["artifact_type"] == "agentflow_runtime_workbench_state"
    assert state["project"]["project_id"] == "proj_workbench_demo"
    assert state["project"]["artifact_id"] == created["artifact"]["artifact_id"]
    assert state["navigation"] == ["Projects", "Create", "Assets", "Review", "Style Memory", "Jobs", "Settings"]
    assert state["safe_ref_policy"] == "frontend stores ids and summaries only; content is read through safe artifact refs"
    assert state["advanced_evidence"]["visible_by_default"] is False
    assert state["advanced_evidence"]["non_claims"] == [
        "not human acceptance",
        "not business validation",
        "not durable memory",
    ]
    assert state["style_memory"]["status"] == "not_started"
    assert state["style_memory"]["profile_version_count"] == 0
    assert state["asset_library"]["status"] == "needs_assets"
    assert state["asset_library"]["counts"]["total"] == 0
    assert state["asset_library"]["next_actions"]
    assert state["review_room"]["status"] == "not_started"
    assert state["review_room"]["candidates"] == []
    assert state["job_center"]["status"] == "not_started"
    assert state["job_center"]["counts"]["total"] == 0
    assert state["job_center"]["polling"]["enabled"] is True
    assert state["job_center"]["polling"]["scope"] == "current_project_jobs"
    assert state["activity_timeline"]["status"] == "not_started"
    assert state["activity_timeline"]["counts"]["total"] == 0
    assert state["activity_timeline"]["items"] == []
    assert state["production_board"]["status"] == "needs_assets"
    assert [lane["lane_id"] for lane in state["production_board"]["lanes"]] == [
        "source",
        "draft",
        "first_check",
        "review",
        "style_memory",
        "next_round",
        "provider_gate",
    ]
    assert _lane(state, "source")["status"] == "blocked"
    assert _lane(state, "draft")["status"] == "not_started"
    assert _lane(state, "first_check")["action"] == "start_first_generation_check"
    assert state["command_hub"]["status"] == "needs_assets"
    assert state["command_hub"]["title"] == "操作指令"
    assert state["command_hub"]["primary_command"]["backend_action"] == "add_reference"
    assert state["command_hub"]["primary_command"]["ui_action"] == "register-source-asset"
    assert state["command_hub"]["primary_command"]["view"] == "Assets"
    assert state["command_hub"]["primary_command"]["enabled"] is True
    assert state["command_hub"]["primary_command"]["requires_input"] == [
        "source_asset_id",
        "source_asset_label",
        "source_asset_summary",
    ]
    assert _command(state, "draft_canvas")["ui_action"] == "draft-canvas"
    assert _command(state, "start_first_generation_check")["ui_action"] == "run-asset-test"
    assert _command(state, "record_review_note")["ui_action"] == "record-review-decision"
    assert state["project_hub"]["status"] == "needs_assets"
    assert state["project_hub"]["title"] == "项目中心"
    assert state["project_hub"]["active_project"]["project_id"] == "proj_workbench_demo"
    assert state["project_hub"]["active_project"]["artifact_id"] == created["artifact"]["artifact_id"]
    assert state["project_hub"]["counts"] == {
        "source_assets": 0,
        "content_cards": 0,
        "runs": 0,
        "jobs": 0,
        "feedback_refs": 0,
        "profile_versions": 0,
    }
    assert state["project_hub"]["next_command"]["ui_action"] == "register-source-asset"
    assert state["project_hub"]["recent_jobs"] == []
    assert state["creation_workspace"]["status"] == "needs_assets"
    assert state["creation_workspace"]["title"] == "Creation workspace"
    assert state["creation_workspace"]["selected_card_id"] == "content-cards"
    assert state["creation_workspace"]["counts"] == {
        "canvas_cards": 2,
        "filmstrip_items": 0,
        "editable_scene_cards": 0,
        "artifact_refs": 0,
    }
    assert state["creation_workspace"]["run_controls"]["primary_action"] == "add_reference"
    assert state["creation_workspace"]["run_controls"]["enabled"] is False
    assert state["creation_workspace"]["run_controls"]["handoff_view"] == "Assets"
    assert state["creation_workspace"]["inspector"]["card_id"] == "content-cards"
    assert state["creation_workspace"]["inspector"]["mode"] == "setup"
    assert state["creation_workspace"]["filmstrip"] == []
    assert state["memory_workspace"]["status"] == "not_started"
    assert state["memory_workspace"]["title"] == "Memory workspace"
    assert state["memory_workspace"]["selected_candidate_id"] == ""
    assert state["memory_workspace"]["counts"] == {
        "candidates": 0,
        "decisions": 0,
        "feedback_refs": 0,
        "profile_versions": 0,
        "reusable_preferences": 0,
    }
    assert state["memory_workspace"]["feedback_controls"]["primary_action"] == "record_review_note"
    assert state["memory_workspace"]["feedback_controls"]["enabled"] is False
    assert state["memory_workspace"]["feedback_controls"]["requires_input"] == [
        "selected_review_candidate",
        "review_decision",
        "review_decision_note",
    ]
    assert state["memory_workspace"]["style_profile"]["status"] == "not_started"
    assert state["project_readiness"]["status"] == "needs_assets"
    assert state["project_readiness"]["current_action"] == "add_reference"
    assert state["project_readiness"]["current_action_label"] == "添加素材摘要"
    assert _step(state, "source_materials")["status"] == "blocked"
    assert _step(state, "canvas_draft")["status"] == "not_started"
    assert _step(state, "first_generation_check")["status"] == "not_started"
    assert state["workspace"]["primary_action"] == state["project_readiness"]["current_action"]
    assert _card(state, "project")["status"] == "succeeded"
    assert _card(state, "source-assets")["status"] == "blocked"
    assert _card(state, "source-assets")["blockers"][0]["blocker_id"] == "source_assets_missing"
    assert _card(state, "first-generation-check")["status"] == "ready_not_run"
    assert _card(state, "style-memory")["status"] == "not_started"
    assert state["provider_gate"]["status"] == "ready_not_run"
    assert "job_id" not in _card(state, "project")
    assert "artifact_id" not in _card(state, "project")
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    assert "data/processed/runs" not in serialized
    assert "provider_config" not in serialized


def test_runtime_service_workbench_state_summarizes_full_deterministic_flow(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    fixture_dir = Path("examples/frontend_runtime_service")

    client.post("/projects", json=_load_fixture(fixture_dir / "create_project.request.example.json")).json()
    round_1 = client.post("/runs/asset-test", json=_load_fixture(fixture_dir / "asset_test_run.request.example.json")).json()
    client.post("/feedback", json=_load_fixture(fixture_dir / "feedback_record.request.example.json")).json()
    round_2_request = _load_fixture(fixture_dir / "two_round_validate.request.example.json")
    round_2_request["round_1_job_id"] = round_1["job"]["job_id"]
    round_2 = client.post("/runs/two-round-validate", json=round_2_request).json()
    provider = client.post("/provider/validation-plan", json=_load_fixture(fixture_dir / "provider_validation_plan.request.example.json")).json()

    state = client.get("/projects/proj_runtime_demo/workbench-state").json()
    serialized = json.dumps(state, ensure_ascii=False).lower()

    assert state["project"]["status"] == "ready_for_next_round"
    assert state["project_readiness"]["status"] == "provider_blocked"
    assert state["project_readiness"]["current_action"] == "resolve_provider_preflight"
    assert _step(state, "source_materials")["status"] == "succeeded"
    assert _step(state, "first_generation_check")["status"] == "blocked"
    assert _step(state, "review_feedback")["status"] == "succeeded"
    assert _step(state, "next_round")["status"] == "succeeded"
    assert _step(state, "provider_preflight")["status"] == "blocked"
    assert state["workspace"]["primary_action"] == state["project_readiness"]["current_action"]
    assert _card(state, "first-generation-check")["status"] == "blocked"
    assert _card(state, "first-generation-check")["primary_artifact_id"] == round_1["artifacts"]["real_asset_test_report"]["artifact_id"]
    assert _card(state, "review")["status"] == "succeeded"
    assert _card(state, "style-memory")["status"] == "succeeded"
    assert state["style_memory"]["status"] == "ready"
    assert state["style_memory"]["profile_version_count"] == 1
    assert state["style_memory"]["feedback_count"] >= 1
    assert state["style_memory"]["latest_profile_artifact_id"]
    assert state["style_memory"]["non_claims"] == ["not durable company memory", "not human acceptance", "not business validation"]
    assert state["review_room"]["status"] == "ready"
    assert {candidate["stage"] for candidate in state["review_room"]["candidates"]} == {
        "first_generation_check",
        "next_round",
    }
    assert state["job_center"]["status"] == "blocked"
    assert state["job_center"]["counts"]["total"] == 4
    assert state["job_center"]["counts"]["blocked"] == 2
    assert any(item["action"] == "provider_validation_plan" and item["guidance"] for item in state["job_center"]["items"])
    assert state["activity_timeline"]["status"] == "blocked"
    assert state["activity_timeline"]["counts"]["total"] == 4
    assert state["activity_timeline"]["counts"]["blocked"] == 2
    assert state["activity_timeline"]["items"][0]["action"] == "provider_validation_plan"
    assert state["activity_timeline"]["items"][0]["primary_artifact_id"] == provider["artifacts"]["provider_safe_manifest"]["artifact_id"]
    assert state["production_board"]["status"] == "blocked"
    assert state["production_board"]["current_action"] == "resolve_provider_preflight"
    assert state["command_hub"]["status"] == "blocked"
    assert state["command_hub"]["primary_command"]["backend_action"] == "resolve_provider_preflight"
    assert state["command_hub"]["primary_command"]["ui_action"] == ""
    assert state["command_hub"]["primary_command"]["enabled"] is False
    assert state["command_hub"]["primary_command"]["blocked_reason"] == "Provider 能力闸门仍处于阻塞状态。"
    assert _command(state, "start_next_round")["ui_action"] == "run-two-round"
    assert _command(state, "run_provider_preflight")["ui_action"] == "run-provider-preflight"
    assert state["project_hub"]["status"] == "blocked"
    assert state["project_hub"]["active_project"]["project_id"] == "proj_runtime_demo"
    assert state["project_hub"]["counts"]["jobs"] == 4
    assert state["project_hub"]["counts"]["runs"] >= 1
    assert state["project_hub"]["counts"]["feedback_refs"] >= 1
    assert state["project_hub"]["counts"]["profile_versions"] == 1
    assert state["project_hub"]["next_command"]["backend_action"] == "resolve_provider_preflight"
    assert state["project_hub"]["next_command"]["enabled"] is False
    assert state["project_hub"]["recent_jobs"][0]["action"] == "provider_validation_plan"
    assert state["project_hub"]["recent_jobs"][0]["primary_artifact_id"] == provider["artifacts"]["provider_safe_manifest"]["artifact_id"]
    assert state["creation_workspace"]["status"] == "blocked"
    assert state["creation_workspace"]["selected_card_id"] == "first-generation-check"
    assert state["creation_workspace"]["counts"]["canvas_cards"] == 2
    assert state["creation_workspace"]["counts"]["artifact_refs"] >= 1
    assert state["creation_workspace"]["run_controls"]["primary_action"] == "resolve_provider_preflight"
    assert state["creation_workspace"]["run_controls"]["enabled"] is False
    assert state["creation_workspace"]["run_controls"]["handoff_view"] == "Jobs"
    assert state["creation_workspace"]["inspector"]["card_id"] == "first-generation-check"
    assert state["creation_workspace"]["inspector"]["primary_artifact_id"] == round_1["artifacts"]["real_asset_test_report"]["artifact_id"]
    assert state["memory_workspace"]["status"] == "ready"
    assert state["memory_workspace"]["selected_candidate_id"] == state["review_room"]["candidates"][0]["candidate_id"]
    assert state["memory_workspace"]["counts"]["candidates"] == 2
    assert state["memory_workspace"]["counts"]["feedback_refs"] >= 1
    assert state["memory_workspace"]["counts"]["profile_versions"] == 1
    assert state["memory_workspace"]["style_profile"]["latest_profile_artifact_id"] == state["style_memory"]["latest_profile_artifact_id"]
    assert state["memory_workspace"]["style_profile"]["next_pass_usage"] == state["style_memory"]["next_pass_usage"]
    assert state["memory_workspace"]["feedback_controls"]["primary_action"] == "record_review_note"
    assert state["memory_workspace"]["feedback_controls"]["enabled"] is True
    assert state["memory_workspace"]["next_round_controls"]["primary_action"] == "start_next_round"
    assert _lane(state, "source")["status"] == "succeeded"
    assert _lane(state, "first_check")["status"] == "blocked"
    assert _lane(state, "review")["status"] == "succeeded"
    assert _lane(state, "style_memory")["status"] == "succeeded"
    assert _lane(state, "next_round")["status"] == "succeeded"
    assert _lane(state, "provider_gate")["status"] == "blocked"
    assert _lane(state, "provider_gate")["primary_artifact_id"] == provider["artifacts"]["provider_safe_manifest"]["artifact_id"]
    assert _card(state, "next-round")["status"] == "succeeded"
    assert _card(state, "next-round")["primary_artifact_id"] == round_2["artifacts"]["two_round_context_runtime_report"]["artifact_id"]
    assert state["provider_gate"]["status"] == "blocked"
    assert state["provider_gate"]["primary_artifact_id"] == provider["artifacts"]["provider_safe_manifest"]["artifact_id"]
    assert {blocker["blocker_id"] for blocker in state["provider_gate"]["blockers"]} == {
        "image_gate_unset",
        "video_gate_unset",
        "provider_config_missing",
        "character_reference_image_missing",
    }
    assert any(event["action"] == "asset_test_run" and event["status"] == "blocked" for event in state["events"])
    assert any(event["action"] == "record_feedback" and event["status"] == "succeeded" for event in state["events"])
    assert any(event["action"] == "two_round_validate" and event["status"] == "succeeded" for event in state["events"])
    assert any(event["action"] == "provider_validation_plan" and event["status"] == "blocked" for event in state["events"])
    assert "path" not in json.dumps(state["cards"], ensure_ascii=False).lower()
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    assert "data/processed/runs" not in serialized


def _card(state: dict, card_id: str) -> dict:
    matches = [card for card in state["cards"] if card["card_id"] == card_id]
    assert len(matches) == 1
    return matches[0]


def _step(state: dict, step_id: str) -> dict:
    matches = [step for step in state["project_readiness"]["steps"] if step["step_id"] == step_id]
    assert len(matches) == 1
    return matches[0]


def _lane(state: dict, lane_id: str) -> dict:
    matches = [lane for lane in state["production_board"]["lanes"] if lane["lane_id"] == lane_id]
    assert len(matches) == 1
    return matches[0]


def _command(state: dict, backend_action: str) -> dict:
    matches = [command for command in state["command_hub"]["commands"] if command["backend_action"] == backend_action]
    assert len(matches) == 1
    return matches[0]


def _load_fixture(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload
