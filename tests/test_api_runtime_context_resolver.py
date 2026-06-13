from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

from apps.api.runtime_context_resolver import provider_prompt_from_bundle, resolve_context_bundle
from apps.api.runtime_models import ContextSubgraph, DirectorSetup2D
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore
from agentflow.harness.json_io import write_json


PNG_B64 = base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
).decode("ascii")


def _upload(client: TestClient, project_id: str, node_id: str) -> str:
    response = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": node_id,
            "filename": f"{node_id}.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": "reference_image",
            "generated_at": "2026-06-12T10:00:00+08:00",
        },
    )
    assert response.status_code == 200
    return response.json()["asset"]["asset_id"]


def _promote(client: TestClient, project_id: str, image_id: str, label: str, asset_type: str = "character") -> dict:
    response = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json={
            "source_image_asset_refs": [image_id],
            "asset_type": asset_type,
            "label": label,
            "signature": f"{label} signature",
            "feature_card": {"identity": f"{label} identity", "palette": "black and red"},
            "negative_locks": [f"keep {label} identity", "keep black short hair"],
            "source_node_id": f"{label}-node",
            "review_decision": "fixed",
            "reviewed_at": "2026-06-12T10:05:00+08:00",
        },
    )
    assert response.status_code == 200
    return response.json()["asset"]


def _subgraph(target: str, upstream: str, asset_id: str, relation: str = "reference") -> dict:
    return {
        "target_node_id": target,
        "runtime_work_mode": "context_generate",
        "nodes": [
            {"id": target, "type": "image", "title": "Target", "prompt": "target prompt", "visual_asset_ids": []},
            {"id": upstream, "type": "image", "title": "Asset", "prompt": "asset prompt", "visual_asset_ids": [asset_id]},
        ],
        "edges": [{"id": "edge-1", "from": upstream, "to": target, "relation_type": relation}],
    }


def _chain_subgraph(target: str, asset_id: str, relation: str, depth: int) -> dict:
    nodes = [{"id": target, "type": "image", "title": "Target", "prompt": "target", "visual_asset_ids": []}]
    edges = []
    previous = target
    for index in range(1, depth + 1):
        node_id = f"chain-{relation}-{index}"
        nodes.append(
            {
                "id": node_id,
                "type": "image",
                "title": f"Chain {index}",
                "prompt": f"chain prompt {index}",
                "visual_asset_ids": [asset_id] if index == depth else [],
            }
        )
        edges.append({"id": f"edge-{index}", "from": node_id, "to": previous, "relation_type": relation})
        previous = node_id
    return {"target_node_id": target, "runtime_work_mode": "context_generate", "nodes": nodes, "edges": edges}


def test_optimize_context_injects_only_connected_or_label_matched_signatures(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_optimize_context"
    assets = []
    for index, label in enumerate(["Lin Wan", "Desert Lab", "Rain Alley", "Unused Studio", "Extra Actor"]):
        image_id = _upload(client, project_id, f"node-{index}")
        assets.append(_promote(client, project_id, image_id, label, "scene" if index in {1, 2, 3} else "character"))

    response = client.post(
        f"/projects/{project_id}/prompt-optimizations",
        json={
            "node_id": "target-node",
            "node_type": "image",
            "prompt_text": "Lin Wan walks past Rain Alley at night.",
            "generation_target": "keyframe",
            "target_platform": "short_video",
            "style": "cinematic",
            "context_subgraph": _subgraph("target-node", "asset-node", assets[1]["asset_id"]),
            "generated_at": "2026-06-12T10:10:00+08:00",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    bundle = payload["context_bundle"]
    included_ids = [asset["asset_id"] for asset in bundle["included_assets"]]

    assert len(included_ids) <= 4
    assert assets[1]["asset_id"] in included_ids
    assert assets[0]["asset_id"] in included_ids
    assert assets[2]["asset_id"] in included_ids
    assert assets[3]["asset_id"] not in included_ids
    assert "Unused Studio signature" not in payload["optimized_prompt"]
    assert any(item["label"] == "Unused Studio" for item in bundle["available_project_assets"])


def test_generate_context_uses_connected_fixed_assets_and_lock_overrides(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_generate_context"
    image_id = _upload(client, project_id, "char-node")
    asset = _promote(client, project_id, image_id, "Lin Wan")
    retired_image = _upload(client, project_id, "retired-node")
    retired = _promote(client, project_id, retired_image, "Retired Actor")
    client.post(
        f"/projects/{project_id}/visual-assets/{retired['asset_id']}/retire",
        json={"reason": "not used", "retired_at": "2026-06-12T10:06:00+08:00"},
    )

    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "Draw Lin Wan with red long hair.",
            "optimized_prompt": "A rooftop keyframe with Lin Wan.",
            "target_platform": "short_video",
            "style": "cinematic",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "context_subgraph": _subgraph("target-node", "char-node", asset["asset_id"]),
            "temporary_lock_overrides": [
                {"asset_id": asset["asset_id"], "lock_text": "keep black short hair", "reason": "one-off variant test"}
            ],
            "generated_at": "2026-06-12T10:20:00+08:00",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    plan = client.get(f"/artifacts/{payload['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    bundle = plan["context_bundle"]
    provider_prompt = plan["provider_prompt"]

    assert payload["job"]["status"] == "blocked"
    assert plan["context_path"] == "context_subgraph_v0.1"
    assert bundle["subject_reference_asset_id"] == asset["asset_id"]
    assert bundle["reference_image_channel"][0]["asset_id"] == image_id
    assert "keep Lin Wan identity" in provider_prompt
    assert "keep black short hair" not in provider_prompt
    assert bundle["temporary_lock_overrides"][0]["lock_text"] == "keep black short hair"
    assert retired["asset_id"] not in {item["asset_id"] for item in bundle["included_assets"]}


def test_scene_asset_never_occupies_subject_reference_and_frontend_asset_text_is_rejected(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_scene_subject_ref"
    scene_image = _upload(client, project_id, "scene-node")
    scene = _promote(client, project_id, scene_image, "Desert Lab", "scene")
    graph = _subgraph("target-node", "scene-node", scene["asset_id"])

    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "A quiet desert laboratory.",
            "optimized_prompt": "A quiet desert laboratory.",
            "context_subgraph": graph,
            "generated_at": "2026-06-12T10:30:00+08:00",
        },
    )
    assert response.status_code == 200
    plan = client.get(f"/artifacts/{response.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    assert plan["subject_reference_asset_id"] is None
    assert plan["context_bundle"]["subject_reference_asset_id"] is None

    graph["nodes"][1]["feature_card"] = {"forged": "frontend must not supply this"}
    rejected = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "A quiet desert laboratory.",
            "optimized_prompt": "A quiet desert laboratory.",
            "context_subgraph": graph,
            "generated_at": "2026-06-12T10:31:00+08:00",
        },
    )
    assert rejected.status_code == 422


def test_reference_image_slots_allow_multiple_character_subject_refs(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_reference_slots"
    first_image = _upload(client, project_id, "first-char")
    first = _promote(client, project_id, first_image, "Lin Wan")
    second_image = _upload(client, project_id, "second-char")
    second = _promote(client, project_id, second_image, "Zhou Yu")
    graph = {
        "target_node_id": "target-node",
        "runtime_work_mode": "context_generate",
        "nodes": [
            {"id": "target-node", "type": "image", "title": "Target", "prompt": "target", "visual_asset_ids": []},
            {"id": "first-char", "type": "image", "title": "First", "prompt": "first", "visual_asset_ids": [first["asset_id"]]},
            {"id": "second-char", "type": "image", "title": "Second", "prompt": "second", "visual_asset_ids": [second["asset_id"]]},
        ],
        "edges": [
            {"id": "edge-1", "from": "first-char", "to": "target-node", "relation_type": "reference"},
            {"id": "edge-2", "from": "second-char", "to": "target-node", "relation_type": "reference"},
        ],
    }

    bundle = resolve_context_bundle(
        RuntimeStore(tmp_path),
        project_id,
        mode="generate",
        visible_prompt="two character keyframe",
        context_subgraph=ContextSubgraph.model_validate(graph),
        reference_image_slots=2,
    )

    expected = [image_id for _, image_id in sorted([(first["asset_id"], first_image), (second["asset_id"], second_image)])]
    assert [item["asset_id"] for item in bundle["reference_image_channel"]] == expected


def test_director_setup_asset_binding_reads_signature_from_backend_store(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_director_asset_binding"
    image_id = _upload(client, project_id, "char-node")
    asset = _promote(client, project_id, image_id, "Lin Wan")

    bundle = resolve_context_bundle(
        RuntimeStore(tmp_path),
        project_id,
        mode="generate",
        visible_prompt="director setup binding test",
        context_subgraph=ContextSubgraph.model_validate(_subgraph("target-node", "char-node", asset["asset_id"])),
        include_fixed_assets=False,
        director_setup=DirectorSetup2D.model_validate(
            {
                "subjects": [
                    {
                        "id": "sub_a",
                        "name": "主体A",
                        "visual_asset_id": asset["asset_id"],
                        "signature": "forged frontend signature",
                    }
                ],
                "cameras": [{"id": "cam_a", "name": "机位", "x": 20, "y": 80, "shot": "中景"}],
            }
        ),
    )
    prompt = provider_prompt_from_bundle(bundle)

    assert "Lin Wan signature" in prompt
    assert "forged frontend signature" not in prompt
    assert bundle["director_compile_result"]["asset_refs_used"] == [asset["asset_id"]]


def test_legacy_background_context_is_not_consumed_by_context_resolver(tmp_path) -> None:
    store = RuntimeStore(tmp_path)
    legacy_dir = tmp_path / "creative_memory" / "proj_legacy_context"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        legacy_dir / "creative_memory_state.json",
        {
            "artifact_type": "agentflow_creative_memory_state",
            "schema_version": "0.1.0",
            "project_id": "proj_legacy_context",
            "characters": [{"memory_type": "character", "label": "Legacy Character"}],
            "scenes": [{"memory_type": "scene", "label": "Legacy Scene"}],
            "style_preferences": [],
            "user_preferences": [],
            "extracted_context": [],
        },
    )
    client = TestClient(create_runtime_app(runtime_root=store.root))
    response = client.post(
        "/projects/proj_legacy_context/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "A new keyframe.",
            "optimized_prompt": "A new keyframe.",
            "context_subgraph": {
                "target_node_id": "target-node",
                "runtime_work_mode": "context_generate",
                "nodes": [{"id": "target-node", "type": "image", "title": "Target", "prompt": "A new keyframe."}],
                "edges": [],
            },
            "generated_at": "2026-06-12T10:40:00+08:00",
        },
    )
    assert response.status_code == 200
    plan = client.get(f"/artifacts/{response.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    serialized = json.dumps(plan, ensure_ascii=False)

    assert "Legacy Character" not in serialized
    assert "Legacy Scene" not in serialized
    assert plan["context_bundle"]["included_assets"] == []


def test_generate_budget_enforces_floor_and_never_truncates_locks(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_budget_enforce"
    image_id = _upload(client, project_id, "char-node")
    asset = _promote(client, project_id, image_id, "Lin Wan")

    long_visible = "Lin Wan crosses the rooftop in slow motion. " * 60
    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "Lin Wan rooftop keyframe.",
            "optimized_prompt": long_visible,
            "context_subgraph": _subgraph("target-node", "char-node", asset["asset_id"]),
            "generated_at": "2026-06-12T11:00:00+08:00",
        },
    )
    assert response.status_code == 200
    plan = client.get(f"/artifacts/{response.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    bundle = plan["context_bundle"]
    budget = bundle["budget"]

    assert budget["enforcement_applied"] is True
    assert budget["segments"]["lock_identity"]["truncated"] is False
    assert budget["segments"]["visible_prompt"]["truncated"] is True
    assert budget["segments"]["visible_prompt"]["used"] >= budget["visible_prompt_floor"]
    assert budget["total_used"] <= budget["total_limit"]
    assert "keep Lin Wan identity" in plan["provider_prompt"]
    assert "keep black short hair" in plan["provider_prompt"]


def test_generate_fills_upstream_summary_and_style_preference_segments(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_upstream_preference"
    image_id = _upload(client, project_id, "char-node")
    asset = _promote(client, project_id, image_id, "Lin Wan")

    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "Lin Wan night rooftop.",
            "optimized_prompt": "Lin Wan night rooftop.",
            "style": "noir film",
            "context_subgraph": _subgraph("target-node", "char-node", asset["asset_id"]),
            "generated_at": "2026-06-12T11:10:00+08:00",
        },
    )
    assert response.status_code == 200
    plan = client.get(f"/artifacts/{response.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    text_channel = plan["context_bundle"]["text_channel"]

    assert "asset prompt" in text_channel["upstream_summary_segment"]
    assert text_channel["preference_segment"] == "style preference: noir film"
    assert "asset prompt" in plan["provider_prompt"]
    assert "style preference: noir film" in plan["provider_prompt"]


def test_lock_conflict_warning_uses_attribute_vocabulary_and_enforcement_is_independent(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_vocab_conflict"
    image_id = _upload(client, project_id, "char-node")
    asset = _promote(client, project_id, image_id, "Lin Wan")

    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "Draw Lin Wan with red long hair.",
            "optimized_prompt": "Draw Lin Wan with red long hair.",
            "context_subgraph": _subgraph("target-node", "char-node", asset["asset_id"]),
            "generated_at": "2026-06-12T11:20:00+08:00",
        },
    )
    assert response.status_code == 200
    plan = client.get(f"/artifacts/{response.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    warnings = plan["context_bundle"]["warnings"]
    conflict_attrs = {
        (item["attribute"], item["lock_value"], item["prompt_value"])
        for item in warnings
        if item["warning_id"] == "best_effort_lock_conflict"
    }

    assert ("hair_color", "black", "red") in conflict_attrs
    assert ("hair_length", "short", "long") in conflict_attrs
    # enforcement is independent of detection: the lock still rides the prompt
    assert "keep black short hair" in plan["provider_prompt"]


def test_keyframe_preflight_is_gate_free_stable_and_reports_conflicts(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_keyframe_preflight"
    image_id = _upload(client, project_id, "char-node")
    asset = _promote(client, project_id, image_id, "Lin Wan")
    request = {
        "node_id": "target-node",
        "prompt_text": "Draw Lin Wan with red long hair.",
        "optimized_prompt": "Draw Lin Wan with red long hair.",
        "context_subgraph": _subgraph("target-node", "char-node", asset["asset_id"]),
        "generated_at": "2026-06-12T11:24:00+08:00",
    }

    first = client.post(f"/projects/{project_id}/keyframe-generations/preflight", json=request)
    second = client.post(f"/projects/{project_id}/keyframe-generations/preflight", json=request)
    changed_prompt = client.post(
        f"/projects/{project_id}/keyframe-generations/preflight",
        json={**request, "optimized_prompt": "Draw Lin Wan in a quiet classroom."},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert changed_prompt.status_code == 200
    payload = first.json()
    token = payload["preflight_token"]

    assert payload["provider_calls_started"] is False
    assert payload["requires_provider_gate"] is False
    assert payload["included_assets"][0]["asset_id"] == asset["asset_id"]
    assert payload["subject_reference_asset_id"] == asset["asset_id"]
    assert payload["reference_image_channel"][0]["asset_id"] == image_id
    assert payload["asset_conflicts"]
    assert payload["context_bundle"]["asset_conflicts"] == payload["asset_conflicts"]
    assert second.json()["preflight_token"] == token
    assert changed_prompt.json()["preflight_token"] != token


def test_keyframe_submit_rejects_stale_preflight_token(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_stale_preflight"
    image_id = _upload(client, project_id, "char-node")
    asset = _promote(client, project_id, image_id, "Lin Wan")
    request = {
        "node_id": "target-node",
        "prompt_text": "Draw Lin Wan.",
        "optimized_prompt": "Draw Lin Wan.",
        "context_subgraph": _subgraph("target-node", "char-node", asset["asset_id"]),
        "generated_at": "2026-06-12T11:25:00+08:00",
    }
    preflight = client.post(f"/projects/{project_id}/keyframe-generations/preflight", json=request)
    assert preflight.status_code == 200

    stale_submit = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={**request, "optimized_prompt": "Draw a different scene.", "preflight_token": preflight.json()["preflight_token"]},
    )

    assert stale_submit.status_code == 409
    assert "stale_preflight" in stale_submit.text


def test_temporary_asset_exclusion_removes_asset_from_prompt_reference_and_subject(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_temporary_asset_exclusion"
    image_id = _upload(client, project_id, "char-node")
    asset = _promote(client, project_id, image_id, "Excluded Actor")
    request = {
        "node_id": "target-node",
        "prompt_text": "A rainy portrait.",
        "optimized_prompt": "A rainy portrait.",
        "context_subgraph": _subgraph("target-node", "char-node", asset["asset_id"]),
        "temporary_asset_exclusions": [{"asset_id": asset["asset_id"], "reason": "one-off female variant"}],
        "generated_at": "2026-06-12T11:26:00+08:00",
    }

    preflight = client.post(f"/projects/{project_id}/keyframe-generations/preflight", json=request)
    response = client.post(f"/projects/{project_id}/keyframe-generations", json=request)

    assert preflight.status_code == 200
    assert response.status_code == 200
    plan = client.get(f"/artifacts/{response.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    bundle = plan["context_bundle"]

    assert bundle["included_assets"] == []
    assert bundle["reference_image_channel"] == []
    assert bundle["subject_reference_asset_id"] is None
    assert any(
        item["asset_id"] == asset["asset_id"] and item["reason"] == "temporary_asset_excluded_by_user"
        for item in bundle["excluded_assets"]
    )
    assert "Excluded Actor" not in plan["provider_prompt"]
    assert "keep Excluded Actor identity" not in plan["provider_prompt"]
    assert preflight.json()["included_assets"] == []
    assert preflight.json()["subject_reference_asset_id"] is None


def test_generate_degrades_assets_over_character_and_scene_limits(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_asset_limit"
    characters = []
    for index in range(5):
        image_id = _upload(client, project_id, f"char-{index}")
        characters.append(_promote(client, project_id, image_id, f"Character {index}"))
    scene_a = _promote(client, project_id, _upload(client, project_id, "scene-a"), "Scene A", "scene")
    scene_b = _promote(client, project_id, _upload(client, project_id, "scene-b"), "Scene B", "scene")
    graph = {
        "target_node_id": "target-node",
        "runtime_work_mode": "context_generate",
        "nodes": [
            {"id": "target-node", "type": "image", "title": "Target", "prompt": "target", "visual_asset_ids": []},
            *[
                {"id": f"asset-node-{asset['asset_id']}", "type": "image", "title": asset["label"], "prompt": "", "visual_asset_ids": [asset["asset_id"]]}
                for asset in [*characters, scene_a, scene_b]
            ],
        ],
        "edges": [
            {"id": f"edge-{asset['asset_id']}", "from": f"asset-node-{asset['asset_id']}", "to": "target-node", "relation_type": "reference"}
            for asset in [*characters, scene_a, scene_b]
        ],
    }

    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "group scene",
            "optimized_prompt": "group scene",
            "context_subgraph": graph,
            "generated_at": "2026-06-12T11:30:00+08:00",
        },
    )
    assert response.status_code == 200
    plan = client.get(f"/artifacts/{response.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    bundle = plan["context_bundle"]
    full = [asset for asset in bundle["included_assets"] if asset.get("detail_level") == "full_card"]
    signature_only = [asset for asset in bundle["included_assets"] if asset.get("detail_level") == "signature_only"]
    degraded = [asset for asset in bundle["excluded_assets"] if asset.get("reason") == "degraded_to_signature_over_limit"]

    assert len([asset for asset in full if asset["asset_type"] == "character"]) == 3
    assert len([asset for asset in full if asset["asset_type"] == "scene"]) == 1
    assert len([asset for asset in signature_only if asset["asset_type"] == "character"]) == 2
    assert len([asset for asset in signature_only if asset["asset_type"] == "scene"]) == 1
    assert len(degraded) == 3
    assert bundle["budget"]["overflow_beyond_total"] is False


def test_reference_edges_do_not_consume_normal_hop_budget_but_generation_edges_do(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_reference_hops"
    image_id = _upload(client, project_id, "asset-node")
    asset = _promote(client, project_id, image_id, "Long Hop Actor")

    reference = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "reference chain",
            "optimized_prompt": "reference chain",
            "context_subgraph": _chain_subgraph("target-node", asset["asset_id"], "reference", 4),
            "generated_at": "2026-06-12T11:40:00+08:00",
        },
    )
    generation = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "generation chain",
            "optimized_prompt": "generation chain",
            "context_subgraph": _chain_subgraph("target-node", asset["asset_id"], "generation", 4),
            "generated_at": "2026-06-12T11:41:00+08:00",
        },
    )
    assert reference.status_code == 200
    assert generation.status_code == 200
    ref_plan = client.get(f"/artifacts/{reference.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    gen_plan = client.get(f"/artifacts/{generation.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]

    assert asset["asset_id"] in {item["asset_id"] for item in ref_plan["context_bundle"]["included_assets"]}
    assert asset["asset_id"] not in {item["asset_id"] for item in gen_plan["context_bundle"]["included_assets"]}


def test_same_label_visual_assets_resolve_to_chain_terminal_or_newest(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_label_arbitration"
    old = _promote(client, project_id, _upload(client, project_id, "old"), "Lin Wan")
    new = client.post(
        f"/projects/{project_id}/visual-assets/promote",
        json={
            "source_image_asset_refs": [_upload(client, project_id, "new")],
            "asset_type": "character",
            "label": "Lin Wan",
            "signature": "Lin Wan v2 signature",
            "feature_card": {"identity": "Lin Wan v2 identity"},
            "negative_locks": ["keep Lin Wan v2 identity"],
            "source_node_id": "new-node",
            "review_decision": "fixed",
            "reviewed_at": "2026-06-12T11:45:00+08:00",
            "supersedes_asset_id": old["asset_id"],
        },
    ).json()["asset"]
    graph = {
        "target_node_id": "target-node",
        "runtime_work_mode": "context_generate",
        "nodes": [
            {"id": "target-node", "type": "image", "title": "Target", "prompt": "target", "visual_asset_ids": []},
            {"id": "old-node", "type": "image", "title": "Old", "prompt": "", "visual_asset_ids": [old["asset_id"]]},
            {"id": "new-node", "type": "image", "title": "New", "prompt": "", "visual_asset_ids": [new["asset_id"]]},
        ],
        "edges": [
            {"id": "old-edge", "from": "old-node", "to": "target-node", "relation_type": "reference"},
            {"id": "new-edge", "from": "new-node", "to": "target-node", "relation_type": "reference"},
        ],
    }

    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "Lin Wan",
            "optimized_prompt": "Lin Wan",
            "context_subgraph": graph,
            "generated_at": "2026-06-12T11:46:00+08:00",
        },
    )
    assert response.status_code == 200
    plan = client.get(f"/artifacts/{response.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    bundle = plan["context_bundle"]

    assert [item["asset_id"] for item in bundle["included_assets"]] == [new["asset_id"]]
    assert any(item["asset_id"] == old["asset_id"] and item["reason"] == "superseded_by_newer_label_version" for item in bundle["excluded_assets"])


def test_same_label_without_supersedes_uses_newest_server_recorded_asset(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_IMAGE", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_label_newest"
    first = _promote(client, project_id, _upload(client, project_id, "first"), "Lin Wan")
    second = _promote(client, project_id, _upload(client, project_id, "second"), "Lin Wan")
    graph = {
        "target_node_id": "target-node",
        "runtime_work_mode": "context_generate",
        "nodes": [
            {"id": "target-node", "type": "image", "title": "Target", "prompt": "target", "visual_asset_ids": []},
            {"id": "first-node", "type": "image", "title": "First", "prompt": "", "visual_asset_ids": [first["asset_id"]]},
            {"id": "second-node", "type": "image", "title": "Second", "prompt": "", "visual_asset_ids": [second["asset_id"]]},
        ],
        "edges": [
            {"id": "first-edge", "from": "first-node", "to": "target-node", "relation_type": "reference"},
            {"id": "second-edge", "from": "second-node", "to": "target-node", "relation_type": "reference"},
        ],
    }

    response = client.post(
        f"/projects/{project_id}/keyframe-generations",
        json={
            "node_id": "target-node",
            "prompt_text": "Lin Wan",
            "optimized_prompt": "Lin Wan",
            "context_subgraph": graph,
            "generated_at": "2026-06-12T11:47:00+08:00",
        },
    )
    assert response.status_code == 200
    plan = client.get(f"/artifacts/{response.json()['artifacts']['keyframe_request_plan']['artifact_id']}").json()["payload"]
    bundle = plan["context_bundle"]

    assert [item["asset_id"] for item in bundle["included_assets"]] == [second["asset_id"]]
    assert any(item["asset_id"] == first["asset_id"] and item["reason"] == "superseded_by_newer_label_version" for item in bundle["excluded_assets"])


def test_context_bundle_reproducibility_metadata_is_deterministic(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_bundle_metadata"
    image_id = _upload(client, project_id, "char-node")
    asset = _promote(client, project_id, image_id, "Lin Wan")

    first = resolve_context_bundle(
        RuntimeStore(tmp_path),
        project_id,
        mode="generate",
        visible_prompt="metadata",
        context_subgraph=ContextSubgraph.model_validate(_subgraph("target-node", "char-node", asset["asset_id"])),
    )
    second = resolve_context_bundle(
        RuntimeStore(tmp_path),
        project_id,
        mode="generate",
        visible_prompt="metadata",
        context_subgraph=ContextSubgraph.model_validate(_subgraph("target-node", "char-node", asset["asset_id"])),
    )

    assert first["resolver_version"].startswith("context_resolver_")
    assert first["vocabulary_hash"] == second["vocabulary_hash"]
    assert first["included_assets"][0]["feature_card_hash"] == second["included_assets"][0]["feature_card_hash"]
