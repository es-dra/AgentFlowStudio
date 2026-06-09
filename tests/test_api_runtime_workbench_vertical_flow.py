from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def test_workbench_vertical_flow_reaches_ready_for_next_round(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_vertical_flow"

    created = client.post(
        "/projects",
        json={
            "project_id": project_id,
            "project_type": "short_video_campaign",
            "goal": "Complete a deterministic workbench production flow.",
        },
    ).json()
    assert created["flow"]["current_action"] == "add_reference"
    _assert_state(client, project_id, project_status="in_progress", readiness="needs_assets", action="add_reference")

    for payload in [
        {
            "asset_id": "brief-main",
            "asset_type": "brief",
            "label": "Launch brief",
            "summary": "Launch a premium desk lamp for remote creative teams.",
        },
        {
            "asset_id": "reference-main",
            "asset_type": "reference",
            "label": "Visual reference",
            "summary": "Warm tabletop studio lighting with clean shadows.",
        },
        {
            "asset_id": "script-outline",
            "asset_type": "script",
            "label": "Script outline",
            "summary": "Hook pain, prove comfort, close with a calm upgrade CTA.",
        },
    ]:
        source_result = client.post(f"/projects/{project_id}/source-assets", json=payload).json()
    assert source_result["flow"]["current_action"] == "draft_canvas"
    _assert_state(client, project_id, project_status="in_progress", readiness="ready_to_draft", action="draft_canvas")

    drafted = client.post(f"/projects/{project_id}/canvas-draft", json={"generated_at": "2026-06-09T21:00:00+08:00"}).json()
    assert drafted["flow"]["current_action"] == "start_first_generation_check"
    draft_state = _assert_state(
        client,
        project_id,
        project_status="in_progress",
        readiness="ready_for_first_check",
        action="start_first_generation_check",
    )
    first_card = draft_state["creation_workspace"]["canvas_cards"][0]["card_id"]
    inspector = client.post(
        f"/projects/{project_id}/scene-inspector",
        json={
            "card_id": first_card,
            "prompt": "Open on a clean desk setup with warm premium lighting.",
            "reference_summary": "Use the approved brief and visual reference summaries.",
            "style_direction": "Quiet premium content-tool commercial style.",
            "retry_intent": "If weak, revise the composition before provider smoke.",
        },
    ).json()
    assert inspector["flow"]["current_action"] == "start_first_generation_check"

    round_1 = client.post(
        "/runs/asset-test",
        json={
            "project_id": project_id,
            "asset_profile_seed": "examples/agentflow/production_memory_asset_profile_seed.example.json",
            "promotion_decision": "promoted",
            "promotion_rationale": "Workbench deterministic vertical flow.",
            "generated_at": "2026-06-09T21:10:00+08:00",
            "decided_at": "2026-06-09T21:11:00+08:00",
            "reviewed_at": "2026-06-09T21:12:00+08:00",
        },
    ).json()
    assert round_1["flow"]["current_action"] == "start_next_round"
    review_state = _assert_state(
        client,
        project_id,
        project_status="blocked",
        readiness="ready_for_next_round",
        action="start_next_round",
    )
    assert review_state["style_memory"]["status"] == "ready"
    assert review_state["memory_workspace"]["counts"]["profile_versions"] == 1
    assert review_state["memory_workspace"]["counts"]["feedback_refs"] == 1

    recorded = client.post(
        f"/projects/{project_id}/review-decisions",
        json={
            "card_id": first_card,
            "candidate_id": review_state["review_room"]["candidates"][0]["candidate_id"],
            "artifact_id": round_1["artifacts"]["real_asset_test_report"]["artifact_id"],
            "decision": "keep",
            "note": "Keep this direction for the next deterministic pass.",
            "generated_at": "2026-06-09T21:20:00+08:00",
        },
    ).json()
    assert recorded["flow"]["current_action"] == "start_next_round"
    decision_state = _assert_state(
        client,
        project_id,
        project_status="in_progress",
        readiness="ready_for_next_round",
        action="start_next_round",
    )
    assert decision_state["review_room"]["decision_counts"]["keep"] == 1

    round_2 = client.post(
        "/runs/two-round-validate",
        json={
            "project_id": project_id,
            "round_1_job_id": round_1["job"]["job_id"],
            "generated_at": "2026-06-09T21:30:00+08:00",
            "reviewed_at": "2026-06-09T21:31:00+08:00",
        },
    ).json()
    assert round_2["flow"]["current_action"] == "run_provider_preflight"
    final_state = _assert_state(
        client,
        project_id,
        project_status="ready_for_next_round",
        readiness="ready_for_provider_preflight",
        action="run_provider_preflight",
    )
    serialized = json.dumps(final_state, ensure_ascii=False).lower()
    assert final_state["production_board"]["lanes"][-1]["action"] == "run_provider_preflight"
    assert final_state["project_hub"]["counts"]["runs"] >= 2
    assert final_state["project_hub"]["counts"]["profile_versions"] == 1
    assert final_state["studio_workspace"]["primary_command"]["ui_action"] == "run-provider-preflight"
    assert final_state["studio_workspace"]["provider_status"] == "ready_not_run"
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    assert "signed_url" not in serialized
    assert "api_key" not in serialized


def _assert_state(client: TestClient, project_id: str, *, project_status: str, readiness: str, action: str) -> dict:
    state = client.get(f"/projects/{project_id}/workbench-state").json()
    assert state["project"]["status"] == project_status
    assert state["project_readiness"]["status"] == readiness
    assert state["project_readiness"]["current_action"] == action
    assert state["command_hub"]["primary_command"]["backend_action"] == action
    assert state["studio_workspace"]["primary_command"]["backend_action"] == action
    return state
