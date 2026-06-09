from __future__ import annotations

import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app


def test_runtime_service_registers_safe_source_asset_summary(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_asset_library",
            "project_type": "short_video_campaign",
            "goal": "Register source assets through safe summaries.",
        },
    )

    registered = client.post(
        "/projects/proj_asset_library/source-assets",
        json={
            "asset_id": "brief-main",
            "asset_type": "brief",
            "label": "Main brief",
            "summary": "Short campaign brief summary for runtime planning.",
        },
    ).json()
    state = client.get("/projects/proj_asset_library/workbench-state").json()
    serialized = json.dumps({"registered": registered, "state": state}, ensure_ascii=False).lower()

    source_card = [card for card in state["cards"] if card["card_id"] == "source-assets"][0]
    assert registered["asset"]["ref_kind"] == "safe_summary"
    assert registered["summary"]["project_id"] == "proj_asset_library"
    assert state["asset_library"]["status"] == "ready"
    assert state["asset_library"]["counts"]["brief"] == 1
    assert state["asset_library"]["items"][0]["usage"] == "项目设置"
    assert state["project_readiness"]["status"] == "ready_to_draft"
    assert state["project_readiness"]["current_action"] == "draft_canvas"
    assert _step(state, "source_materials")["status"] == "succeeded"
    assert _step(state, "canvas_draft")["status"] == "ready_not_run"
    assert source_card["status"] == "succeeded"
    assert source_card["refs"] == [
        {
            "label": "Main brief",
            "artifact_id": "brief-main",
            "artifact_type": "brief",
            "summary": "Short campaign brief summary for runtime planning.",
        }
    ]
    assert "path" not in serialized
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    assert "api_key" not in serialized


def test_runtime_service_registers_content_card_for_creation_canvas(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_scene_cards",
            "project_type": "short_video_campaign",
            "goal": "Plan a content canvas through safe scene cards.",
        },
    )

    registered = client.post(
        "/projects/proj_scene_cards/content-cards",
        json={
            "card_id": "scene-001",
            "card_type": "scene",
            "title": "Opening scene",
            "summary": "A concise opening scene describing the product moment.",
            "target_platform": "short_video",
        },
    ).json()
    state = client.get("/projects/proj_scene_cards/workbench-state").json()
    serialized = json.dumps({"registered": registered, "state": state}, ensure_ascii=False).lower()

    scene_card = [card for card in state["cards"] if card["card_id"] == "scene-001"][0]
    assert registered["content_card"]["ref_kind"] == "content_card_summary"
    assert registered["summary"]["content_card_count"] == 1
    assert scene_card["kind"] == "scene_card"
    assert scene_card["title"] == "Opening scene"
    assert scene_card["status"] == "ready_not_run"
    assert state["filmstrip"] == [
        {
            "card_id": "scene-001",
            "title": "Opening scene",
            "status": "ready_not_run",
            "summary": "A concise opening scene describing the product moment.",
        }
    ]
    assert "path" not in serialized
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    assert "api_key" not in serialized


def test_runtime_service_drafts_canvas_from_safe_source_summaries(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_canvas_draft",
            "project_type": "short_video_campaign",
            "goal": "Turn a launch brief into a first reviewable content canvas.",
        },
    )
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
            "summary": "Quiet studio tabletop lighting with warm highlights and clean shadows.",
        },
        {
            "asset_id": "script-outline",
            "asset_type": "script",
            "label": "Script outline",
            "summary": "Hook with workspace pain, prove eye-comfort lighting, close with a calm upgrade CTA.",
        },
    ]:
        client.post("/projects/proj_canvas_draft/source-assets", json=payload)

    drafted = client.post(
        "/projects/proj_canvas_draft/canvas-draft",
        json={"generated_at": "2026-06-09T20:10:00+08:00"},
    ).json()
    state = client.get("/projects/proj_canvas_draft/workbench-state").json()
    serialized = json.dumps({"drafted": drafted, "state": state}, ensure_ascii=False).lower()

    assert drafted["job"]["action"] == "draft_canvas"
    assert drafted["job"]["status"] == "succeeded"
    assert drafted["draft"]["artifact_type"] == "agentflow_runtime_canvas_draft"
    assert drafted["draft"]["provider_calls_started"] is False
    assert drafted["draft"]["writes_long_term_memory"] is False
    assert [card["card_id"] for card in drafted["content_cards"]] == ["draft-hook", "draft-proof", "draft-cta"]
    assert [item["card_id"] for item in state["filmstrip"]] == ["draft-hook", "draft-proof", "draft-cta"]
    assert {card["title"] for card in state["cards"]} >= {"Hook", "Proof", "CTA"}
    assert state["project_readiness"]["status"] == "ready_for_first_check"
    assert state["project_readiness"]["current_action"] == "start_first_generation_check"
    assert _step(state, "canvas_draft")["status"] == "succeeded"
    assert _step(state, "first_generation_check")["status"] == "ready_not_run"
    assert any(event["action"] == "draft_canvas" and event["status"] == "succeeded" for event in state["events"])
    assert "path" not in serialized
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    assert "api_key" not in serialized


def _step(state: dict, step_id: str) -> dict:
    matches = [step for step in state["project_readiness"]["steps"] if step["step_id"] == step_id]
    assert len(matches) == 1
    return matches[0]
    assert "provider_config" not in serialized
    assert "signed_url" not in serialized


def test_runtime_service_updates_scene_inspector_for_selected_content_card(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_scene_inspector",
            "project_type": "short_video_campaign",
            "goal": "Edit scene prompt and style through a safe inspector.",
        },
    )
    client.post(
        "/projects/proj_scene_inspector/content-cards",
        json={
            "card_id": "scene-001",
            "card_type": "scene",
            "title": "Opening scene",
            "summary": "Opening scene summary.",
            "target_platform": "short_video",
        },
    )

    updated = client.post(
        "/projects/proj_scene_inspector/scene-inspector",
        json={
            "card_id": "scene-001",
            "prompt": "Product opening shot with a clean studio setup.",
            "reference_summary": "Use the approved brief and main product reference summary.",
            "style_direction": "Quiet premium commercial style.",
            "retry_intent": "If weak, revise composition before provider smoke.",
        },
    ).json()
    state = client.get("/projects/proj_scene_inspector/workbench-state").json()
    serialized = json.dumps({"updated": updated, "state": state}, ensure_ascii=False).lower()

    scene_card = [card for card in state["cards"] if card["card_id"] == "scene-001"][0]
    assert updated["scene_inspector"]["ref_kind"] == "scene_inspector_summary"
    assert scene_card["inspector"] == {
        "prompt": "Product opening shot with a clean studio setup.",
        "reference_summary": "Use the approved brief and main product reference summary.",
        "style_direction": "Quiet premium commercial style.",
        "retry_intent": "If weak, revise composition before provider smoke.",
    }
    assert "path" not in serialized
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    assert "api_key" not in serialized


def test_runtime_service_records_scene_review_decision_as_evidence(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post(
        "/projects",
        json={
            "project_id": "proj_review_room",
            "project_type": "short_video_campaign",
            "goal": "Review scene decisions without promoting memory.",
        },
    )
    client.post(
        "/projects/proj_review_room/content-cards",
        json={
            "card_id": "scene-001",
            "card_type": "scene",
            "title": "Opening scene",
            "summary": "Opening scene summary.",
            "target_platform": "short_video",
        },
    )

    recorded = client.post(
        "/projects/proj_review_room/review-decisions",
        json={
            "card_id": "scene-001",
            "candidate_id": "scene-001:planned",
            "artifact_id": "safe-review-artifact",
            "decision": "keep",
            "note": "Keep this direction for the next pass.",
            "generated_at": "2026-06-09T18:20:00+08:00",
        },
    ).json()
    state = client.get("/projects/proj_review_room/workbench-state").json()
    artifact = client.get(f"/artifacts/{recorded['artifact']['artifact_id']}").json()
    serialized = json.dumps({"recorded": recorded, "state": state, "artifact": artifact}, ensure_ascii=False).lower()

    review_card = [card for card in state["cards"] if card["card_id"] == "review"][0]
    assert recorded["job"]["action"] == "record_review_decision"
    assert recorded["review_decision"]["decision"] == "keep"
    assert recorded["review_decision"]["candidate_id"] == "scene-001:planned"
    assert recorded["review_decision"]["artifact_id"] == "safe-review-artifact"
    assert recorded["review_decision"]["feedback_is_memory"] is False
    assert recorded["review_decision"]["writes_long_term_memory"] is False
    assert artifact["artifact_type"] == "agentflow_runtime_review_decision"
    assert review_card["status"] == "succeeded"
    assert state["review_room"]["decision_counts"]["keep"] == 1
    assert state["review_room"]["candidates"][0]["latest_decision"] == "keep"
    assert any(event["action"] == "record_review_decision" for event in state["events"])
    assert "path" not in serialized
    assert "d:\\" not in serialized
    assert "c:\\" not in serialized
    assert "api_key" not in serialized
