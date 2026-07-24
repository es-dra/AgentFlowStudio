from __future__ import annotations

import base64
import json

from fastapi.testclient import TestClient

from apps.api.runtime_service import create_runtime_app

PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def test_studio_state_prunes_runtime_bundle_details_before_safety_scan(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-state-runtime-result"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio failed result persistence"})

    state = {
        "nodes": {
            "image_1": {
                "type": "image",
                "title": "generated candidate",
                "prompt": "A character walks through a desert.",
                "result": "Gate blocked\nReason: image provider gate is closed.",
                "params": {
                    "model": "image2-keyframe",
                    "temporaryLockOverrides": [{"asset_id": "va_1", "lock_text": "keep black hair"}],
                    "lastKeyframeSourceEvidenceTrace": {
                        "trace_type": "studio_keyframe_layer_source_evidence",
                        "production_graph_review": {"artifact_id": "artifact_pg_1"},
                    },
                    "lastContextBundle": {
                        "trace_summary": "not persisted in studio state",
                        "included_assets": [{"asset_id": "va_1"}],
                    },
                    "visualAssets": [{"asset_id": "va_fixed_1", "label": "Zhou Tong"}],
                },
            }
        },
        "order": ["image_1"],
    }

    response = client.put(f"/projects/{project_id}/studio-state", json={"state": state})

    assert response.status_code == 200
    params = response.json()["state"]["nodes"]["image_1"]["params"]
    assert params["lastContextBundle"]["included_assets"] == [{"asset_id": "va_1"}]
    assert "trace_summary" not in params["lastContextBundle"]
    assert "temporaryLockOverrides" not in params
    assert "lastKeyframeSourceEvidenceTrace" not in params
    assert params["visualAssets"][0]["asset_id"] == "va_fixed_1"


def test_studio_state_preserves_storyboard_asset_and_keyframe_contract_params(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-state-storyboard-contract"
    client.post("/projects", json={"project_id": project_id, "goal": "Storyboard state contract persistence"})

    preview_url = f"/projects/{project_id}/image-assets/img_ref_001/preview"
    structured_shot = {
        "shot_id": "shot_01",
        "index": 1,
        "duration": "6s",
        "description": "@主角 在 @主要场景 中仰望星空。",
        "shot_size": "远景",
        "light_atmosphere": "冷蓝月光",
        "camera_motion": "固定机位",
        "dialogue": "无明确对白",
        "sound": "城市环境底噪",
        "asset_refs": [
            {"label": "主角", "asset_type": "character", "asset_id": "candidate:character:hero"},
            {"label": "主要场景", "asset_type": "scene", "asset_id": "candidate:scene:rooftop"},
        ],
    }
    asset_card = {
        "card_id": "asset_card:shot_01:character:hero",
        "asset_type": "character",
        "label": "主角",
        "status": "draft",
        "source_script_node_id": "script_1",
        "source_shot_id": "shot_01",
        "signature": "未来机器人主角",
        "feature_card": {"identity": "未来机器人", "appearance": "金属机身和青蓝发光纹路"},
        "negative_locks": ["保持金属机身", "保持青蓝发光纹路"],
        "memory_policy": {
            "writes_fixed_asset": False,
            "included_in_context_before_confirmation": False,
            "requires_human_confirmation": True,
        },
        "updated_by_user": True,
    }
    asset_auto_binding_graph = {
        "artifact_type": "agentflow_asset_auto_binding_graph",
        "schema_version": "0.1.0",
        "algorithm_id": "afs.asset_auto_binding.v0.1",
        "summary": {"suggested_binding_count": 1, "established_binding_count": 1, "blocked_candidate_count": 0},
        "binding_suggestions": [
            {
                "binding_id": "binding:graph_character_hero:vas_fixed_001",
                "binding_state": "bound",
                "graph_asset_id": "graph:character:主角",
                "fixed_visual_asset_id": "vas_fixed_001",
                "asset_type": "character",
                "label": "主角",
                "confidence": 0.91,
                "lineage_refs": {
                    "candidate_graph_asset_id": "graph:character:主角",
                    "fixed_visual_asset_id": "vas_fixed_001",
                    "fixed_source_node_id": "asset_1",
                    "source_human_gate_id": "gate_hero",
                    "source_asset_card_candidate_id": "asset_card_candidate_hero",
                },
                "reversal_plan": {"reversible": True, "action": "unbind", "preserve_lineage": True},
            }
        ],
        "relationships": [
            {
                "relationship_type": "asset_auto_binding_established",
                "from_node_id": "asset:graph:character:主角",
                "to_node_id": "fixed_asset:vas_fixed_001",
                "binding_id": "binding:graph_character_hero:vas_fixed_001",
                "binding_state": "bound",
                "confidence": 0.91,
                "source": "afs.asset_auto_binding.v0.1",
            }
        ],
    }
    node_reference_stack = {
        "artifact_type": "studio_node_reference_stack",
        "node_id": "script_1",
        "summary": {"asset_auto_binding_reference_count": 1, "selected_reference_count": 1},
        "references": [
            {
                "reference_id": "binding:graph_character_hero:vas_fixed_001",
                "reference_type": "binding",
                "studio_entity_id": "binding",
                "scope": "node",
                "target_slot": "asset_binding:graph:character:主角",
                "target_ref": "vas_fixed_001",
                "status": "bound",
                "priority": 91,
                "source": "asset_auto_binding_graph",
                "source_algorithm_id": "afs.asset_auto_binding.v0.1",
                "source_relationship_type": "asset_auto_binding_established",
                "selected": True,
                "conflict_state": "selected",
            }
        ],
    }
    state = {
        "nodes": {
            "script_1": {
                "type": "script",
                "title": "分镜 01",
                "content": "镜号：01",
                "params": {
                    "nodeRole": "storyboard_shot",
                    "sourceTextNodeId": "text_1",
                    "scriptSegmentIndex": 1,
                    "structuredShot": structured_shot,
                    "shotAssetRefs": structured_shot["asset_refs"],
                    "assetAutoBindingGraph": asset_auto_binding_graph,
                    "nodeReferenceStack": node_reference_stack,
                    "assetPrepState": {"status": "pending_user_review", "downstream_node_ids": ["asset_1"]},
                    "storyboardBreakdown": {
                        "assetAutoBindingGraph": asset_auto_binding_graph,
                        "assetAutoBindingGraphArtifactId": "artifact_binding_graph",
                    },
                },
            },
            "asset_1": {
                "type": "image",
                "title": "角色资产 · @主角",
                "previewUrl": preview_url,
                "params": {
                    "nodeRole": "asset_card_draft",
                    "assetCardDraft": asset_card,
                    "assetCardRevision": {
                        "mode": "image_guided_partial_revision",
                        "asset_type": "character",
                        "asset_label": "主角",
                        "reference_assets": [
                            {"asset_id": "img_ref_001", "role": "identity_layout_anchor", "priority": 1},
                        ],
                        "changed_fields": [
                            {"field": "appearance", "label": "外形辨识", "from": "金属机身", "to": "毛绒机身"},
                        ],
                        "preserve_locks": ["保持体态比例", "保持正侧背视图一致"],
                    },
                    "asset_prep": {"status": "card_ready", "source_script_node_id": "script_1"},
                    "uploads": [{"asset_id": "img_ref_001", "preview_url": preview_url}],
                    "visualAssets": [
                        {
                            "asset_id": "vas_fixed_001",
                            "asset_type": "character",
                            "label": "主角",
                            "status": "fixed",
                            "signature": "固定后的机器人主角",
                            "preview_url": preview_url,
                            "feature_card": {"identity": "未来机器人"},
                            "negative_locks": ["保持机器人身份"],
                        }
                    ],
                    "lastVisualAssetWarnings": [{"warning_id": "duplicate_visual_asset_label"}],
                },
            },
            "keyframe_1": {
                "type": "image",
                "title": "关键帧 · 分镜 01",
                "params": {
                    "nodeRole": "keyframe_generation",
                    "structuredShot": structured_shot,
                    "visualAssets": [{"asset_id": "vas_fixed_001", "label": "主角", "status": "fixed"}],
                    "keyframeLayer": {
                        "status": "ready",
                        "source_script_node_id": "script_1",
                        "source_asset_card_node_ids": ["asset_1"],
                        "fixed_visual_asset_ids": ["vas_fixed_001"],
                        "missing_asset_card_node_ids": [],
                    },
                    "lastKeyframeJobId": "keyframe_generation-abc123",
                    "lastKeyframeCompletedJobId": "keyframe_generation-abc123",
                    "lastOptimizedPromptPlain": "根据固定机器人资产生成屋顶关键帧。",
                    "temporaryAssetExclusions": [{"asset_id": "vas_old", "reason": "one_run_asset_exclusion"}],
                    "keyframeConstraints": {
                        "schema_version": "afs_keyframe_constraints.v0.1",
                        "updated_at": "2026-07-06T10:00:00+08:00",
                        "rows": [
                            {
                                "id": "row_character",
                                "section": "character",
                                "text": "keep the hero red scarf",
                                "enabled": True,
                                "order": 1,
                                "projection": "provider",
                                "unknown_key": "drop me",
                            },
                            {
                                "id": "row_local",
                                "section": "local_reference",
                                "text": "operator-only local reference label",
                                "enabled": True,
                                "order": 2,
                                "projection": "provider",
                                "asset_id": "local_ref_1",
                                "label": "Private Concept Board",
                                "note": "audit only",
                            },
                            {
                                "id": "row_unknown",
                                "section": "unrecognized",
                                "text": "unknown section stays audit only",
                                "enabled": False,
                                "order": 3,
                                "projection": "provider",
                            },
                        ],
                    },
                },
            },
        },
        "order": ["script_1", "asset_1", "keyframe_1"],
    }

    response = client.put(f"/projects/{project_id}/studio-state", json={"state": state})

    assert response.status_code == 200
    saved = response.json()["state"]["nodes"]
    script_params = saved["script_1"]["params"]
    asset_params = saved["asset_1"]["params"]
    keyframe_params = saved["keyframe_1"]["params"]
    assert script_params["structuredShot"]["asset_refs"][1]["asset_type"] == "scene"
    assert script_params["assetAutoBindingGraph"]["summary"]["established_binding_count"] == 1
    assert script_params["nodeReferenceStack"]["references"][0]["target_ref"] == "vas_fixed_001"
    assert script_params["storyboardBreakdown"]["assetAutoBindingGraphArtifactId"] == "artifact_binding_graph"
    assert script_params["assetPrepState"]["status"] == "pending_user_review"
    assert asset_params["assetCardDraft"]["feature_card"]["appearance"] == "金属机身和青蓝发光纹路"
    assert asset_params["assetCardRevision"]["reference_assets"][0]["asset_id"] == "img_ref_001"
    assert asset_params["assetCardRevision"]["changed_fields"][0]["to"] == "毛绒机身"
    assert asset_params["visualAssets"][0]["preview_url"] == preview_url
    assert asset_params["lastVisualAssetWarnings"][0]["warning_id"] == "duplicate_visual_asset_label"
    assert keyframe_params["keyframeLayer"]["fixed_visual_asset_ids"] == ["vas_fixed_001"]
    assert keyframe_params["lastKeyframeJobId"] == "keyframe_generation-abc123"
    assert keyframe_params["lastOptimizedPromptPlain"] == "根据固定机器人资产生成屋顶关键帧。"
    assert keyframe_params["temporaryAssetExclusions"][0]["asset_id"] == "vas_old"
    assert keyframe_params["keyframeConstraints"]["rows"][0]["text"] == "keep the hero red scarf"
    assert "unknown_key" not in keyframe_params["keyframeConstraints"]["rows"][0]
    assert keyframe_params["keyframeConstraints"]["rows"][1]["projection"] == "audit_only"
    assert keyframe_params["keyframeConstraints"]["rows"][1]["label"] == "Private Concept Board"
    assert keyframe_params["keyframeConstraints"]["rows"][2]["section"] == "local_reference"
    assert keyframe_params["keyframeConstraints"]["rows"][2]["enabled"] is False


def test_studio_state_sanitizes_keyframe_constraints_editor_state(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-state-keyframe-constraints"
    client.post("/projects", json={"project_id": project_id, "goal": "Keyframe constraints persistence"})

    state = {
        "nodes": {
            "keyframe_1": {
                "type": "image",
                "title": "Keyframe 1",
                "prompt": "Base prompt",
                "params": {
                    "nodeRole": "keyframe_generation",
                    "keyframeConstraints": {
                        "schema_version": "afs_keyframe_constraints.v0.1",
                        "updated_at": "2026-07-06T00:00:00Z",
                        "rows": [
                            {
                                "id": "provider_1",
                                "section": "lighting",
                                "text": "cool moonlight from camera left",
                                "enabled": True,
                                "order": 1,
                                "projection": "provider",
                                "signed_url": "https://signed.example/private.png?token=secret",
                            },
                            {
                                "id": "disabled_1",
                                "section": "camera",
                                "text": "disabled row persists locally",
                                "enabled": False,
                                "order": 2,
                                "projection": "provider",
                            },
                            {
                                "id": "local_1",
                                "section": "local_reference",
                                "text": "operator-only board label",
                                "enabled": True,
                                "order": 3,
                                "projection": "provider",
                                "asset_id": "local_board_1",
                                "label": "Local board",
                            },
                            {
                                "id": "unsafe_path",
                                "section": "scene",
                                "text": "use D:\\private\\scene.png",
                                "enabled": True,
                                "order": 4,
                                "projection": "provider",
                            },
                        ],
                    },
                },
            }
        },
        "order": ["keyframe_1"],
    }

    response = client.put(f"/projects/{project_id}/studio-state", json={"state": state})

    assert response.status_code == 200
    params = response.json()["state"]["nodes"]["keyframe_1"]["params"]
    constraints = params["keyframeConstraints"]
    rows = constraints["rows"]
    serialized = json.dumps(constraints, ensure_ascii=False)
    assert constraints["schema_version"] == "afs_keyframe_constraints.v0.1"
    assert [row["id"] for row in rows] == ["provider_1", "disabled_1", "local_1"]
    assert rows[0]["projection"] == "provider"
    assert rows[1]["enabled"] is False
    assert rows[2]["projection"] == "audit_only"
    assert rows[2]["asset_id"] == "local_board_1"
    assert "signed_url" not in serialized
    assert "signed.example" not in serialized
    assert "D:\\private" not in serialized
    assert "unsafe_path" not in serialized


def test_projects_list_includes_studio_state_meta_and_preview_url_persists(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-project-persist"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio project persistence"})

    preview_url = f"/projects/{project_id}/image-assets/img_abc123/preview"
    state = {
        "meta": {
            "projectName": "Seedance Test Project",
            "canvasName": "Video Board",
            "seq": 7,
            "updated_at": "2026-06-13T10:00:00+08:00",
        },
        "nodes": {
            "image_1": {
                "type": "image",
                "title": "first frame",
                "previewUrl": preview_url,
                "params": {
                    "uploads": [{"asset_id": "img_abc123", "preview_url": preview_url}],
                    "previewAspectRatio": "9:16",
                },
            }
        },
        "order": ["image_1"],
    }

    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": state})
    assert saved.status_code == 200

    loaded = client.get(f"/projects/{project_id}/studio-state").json()["state"]
    assert loaded["nodes"]["image_1"]["previewUrl"] == preview_url
    assert loaded["nodes"]["image_1"]["params"]["uploads"][0]["preview_url"] == preview_url

    projects = client.get("/projects").json()["projects"]
    item = next(project for project in projects if project["project_id"] == project_id)
    assert item["studio_state_meta"]["projectName"] == "Seedance Test Project"
    assert item["studio_state_meta"]["canvasName"] == "Video Board"
    assert item["studio_state_meta"]["seq"] == 7
    assert item["studio_state_meta"]["updated_at"] == "2026-06-13T10:00:00+08:00"
    assert item["studio_state_meta"]["state_version"]
    assert item["studio_state_meta"]["saved_at"]
    assert item["production_graph_authoritative"] is False


def test_projects_list_marks_nonempty_canonical_graph_authoritative(tmp_path) -> None:
    from apps.api.runtime_production_graph import ProductionGraphStore, canonical_digest
    from apps.api.runtime_store import RuntimeStore

    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-project-canonical-graph"
    client.post("/projects", json={"project_id": project_id, "goal": "Canonical graph startup"})
    graph_store = ProductionGraphStore(RuntimeStore(tmp_path))
    graph = graph_store.ensure(project_id)
    graph_store.append(
        project_id,
        expected_version=graph["version"],
        idempotency_key="seed-canonical-startup",
        semantic_digest=canonical_digest({"project_id": project_id, "seed": True}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "asset-001",
                    "category": "asset",
                    "metadata": {"label": "Test asset"},
                },
            }
        ],
    )

    projects = client.get("/projects").json()["projects"]
    item = next(project for project in projects if project["project_id"] == project_id)
    assert item["production_graph_authoritative"] is True


def test_studio_state_rejects_unsafe_preview_url(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-preview-safety"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio preview safety"})

    response = client.put(
        f"/projects/{project_id}/studio-state",
        json={
            "state": {
                "nodes": {
                    "image_1": {
                        "type": "image",
                        "title": "unsafe preview",
                        "previewUrl": "https://signed.example/private.png?token=secret",
                    }
                },
                "order": ["image_1"],
            }
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["action"] == "studio_state"
    assert "preview" in detail["details"]["raw_detail"]


def test_image_asset_list_returns_public_metadata_only(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "studio-image-list"
    client.post("/projects", json={"project_id": project_id, "goal": "Studio image asset list"})

    upload = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": "image_1",
            "filename": "first-frame.png",
            "mime_type": "image/png",
            "data_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            "role": "reference_image",
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )
    assert upload.status_code == 200

    listed = client.get(f"/projects/{project_id}/image-assets").json()
    serialized = str(listed).lower()
    assert listed["project_id"] == project_id
    assert len(listed["assets"]) == 1
    assert listed["assets"][0]["asset_id"] == upload.json()["asset"]["asset_id"]
    assert listed["assets"][0]["preview_url"].startswith(f"/projects/{project_id}/image-assets/")
    assert "source.png" not in serialized
    assert "data/processed/runs" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized
