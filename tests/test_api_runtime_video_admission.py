from __future__ import annotations

import base64
import hashlib
from contextlib import contextmanager
from copy import deepcopy
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from agentflow.harness.json_io import write_json
from apps.api.runtime_models import VideoGenerationRequest
from apps.api import runtime_video_direct_batch_routes as direct_batch_routes
from apps.api.runtime_film_production_graph import _approved_media_projection
from apps.api.runtime_production_graph import ProductionGraphStore, canonical_digest
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore, read_json
from apps.api.runtime_video_admission import (
    AUTO_RETRY,
    CREATE_ENDPOINT,
    DURATION_SEC,
    HARD_BUDGET_USD,
    MAX_ACTIVE_VIDEO_LANES,
    MAX_DISPATCHES,
    MODEL_ID,
    RESOLUTION,
    SERVICE_ID,
    QUERY_ENDPOINT,
    _video_manifest_consumes_lane,
    claim_video_admission_dispatch,
    enforce_video_admission_request,
    load_video_admission_manifest,
    mark_video_admission_network_started,
    mark_video_admission_task_recorded,
    video_admission_capability,
    video_admission_generation_request,
)
from apps.api.runtime_video_direct_batch_routes import OPERATOR_CONFIRMATION
from apps.api.runtime_video_dispatch_outbox import (
    mark_network_may_have_started,
    mark_reconcile_required,
    prepare_dispatch_outbox,
    record_provider_task,
)
from apps.api.runtime_video_staging import build_temporal_prompt
from tools import afs_video_direct_batch_runner as direct_batch_runner


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
VIDEO_CANDIDATE_BYTES = b"afs-deterministic-video-candidate-v1"
REQUESTED_AT = "2026-07-26T03:00:00Z"
TEMPORAL_STAGING = {
    "subject_action_arc": "值守人员从观察仪表转为拿起校准器完成校准",
    "spatial_displacement": "身体由操作台左侧前倾移向仪表中央",
    "interaction_object": "双手操作六角校准器与仪表旋钮",
    "camera_movement": "沿操作台缓慢向前推进",
    "environment_dynamics": "仪表指针轻微摆动，检修灯稳定闪烁",
    "pacing": "前缓后稳，在校准完成处停顿",
    "start_state": "值守人员坐在操作台前观察异常读数",
    "end_state": "校准器归位，仪表读数稳定",
    "narrative_purpose": "建立孤立环境中的检修任务并完成一次动作转折",
}


@pytest.fixture(autouse=True)
def _exact_seedance_capability(monkeypatch) -> None:
    descriptor = SimpleNamespace(
        reference_image_slots=4,
        supported_durations_sec=[6],
        supported_resolutions=["480p", "720p"],
        frame_modes=["first_frame", "reference_images"],
    )
    registry = SimpleNamespace(
        store=SimpleNamespace(
            service=lambda service_id: {
                "model": MODEL_ID,
                "endpoint": CREATE_ENDPOINT,
                "query_endpoint": QUERY_ENDPOINT,
                "allowed_artifact_hosts": ["media.crazyrouter.com"],
                "allowed_artifact_host_suffixes": [
                    "tos-cn-beijing.volces.com",
                ],
                "pricing_exposure_contract": {
                    "verification_state": "verified",
                    "billing_mode": "provider_output_tokens",
                    "output_token_usd": "0.01",
                    "worst_case_output_tokens": 100,
                    "worst_case_cost_usd": "1.00",
                    "source_checked_at": "2026-07-26T00:00:00Z",
                    "provider_enforced_cost_cap": False,
                },
            }
        ),
        descriptor=lambda service_id: descriptor,
    )
    monkeypatch.setattr(
        "apps.api.runtime_video_admission.load_provider_registry",
        lambda: registry,
    )


def _upload(client: TestClient, project_id: str, label: str) -> str:
    response = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": f"source-{label}",
            "filename": f"{label}.png",
            "mime_type": "image/png",
            "data_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            "role": "reference_image",
            "generated_at": REQUESTED_AT,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["asset"]["asset_id"]


def test_video_admission_capability_rejects_incomplete_reference_contract(monkeypatch) -> None:
    registry = SimpleNamespace(
        store=SimpleNamespace(
            service=lambda service_id: {
                "model": MODEL_ID,
                "endpoint": CREATE_ENDPOINT,
                "query_endpoint": QUERY_ENDPOINT,
                "allowed_artifact_hosts": [],
                "pricing_exposure_contract": {
                    "verification_state": "unverified",
                },
            }
        ),
        descriptor=lambda service_id: SimpleNamespace(
            reference_image_slots=2,
            supported_durations_sec=[6],
            supported_resolutions=["720p"],
            frame_modes=["first_frame"],
        ),
    )
    monkeypatch.setattr(
        "apps.api.runtime_video_admission.load_provider_registry",
        lambda: registry,
    )

    capability = video_admission_capability()

    assert capability["exact_model"] is True
    assert capability["exact_endpoint"] is True
    assert capability["configured"] is False
    assert capability["reference_image_slots"] == 2
    assert capability["reference_mode_supported"] is False


def test_video_admission_capability_requires_shared_tos_artifact_policy(
    monkeypatch,
) -> None:
    registry = SimpleNamespace(
        store=SimpleNamespace(
            service=lambda service_id: {
                "model": MODEL_ID,
                "endpoint": CREATE_ENDPOINT,
                "query_endpoint": QUERY_ENDPOINT,
                "input_upload_endpoint": "/v1/files/uploads/base64",
                "allowed_artifact_hosts": ["media.crazyrouter.com"],
                "allowed_input_hosts": ["media.crazyrouter.com"],
                "pricing_exposure_contract": {
                    "verification_state": "verified",
                    "billing_mode": "provider_output_tokens",
                    "output_token_usd": "0.01",
                    "worst_case_output_tokens": 100,
                    "worst_case_cost_usd": "1.00",
                    "source_checked_at": REQUESTED_AT,
                    "provider_enforced_cost_cap": False,
                },
            }
        ),
        descriptor=lambda service_id: SimpleNamespace(
            reference_image_slots=4,
            supported_durations_sec=[6],
            supported_resolutions=["720p"],
            frame_modes=["first_frame", "reference_images"],
        ),
    )
    monkeypatch.setattr(
        "apps.api.runtime_video_admission.load_provider_registry",
        lambda: registry,
    )

    capability = video_admission_capability()

    assert capability["artifact_hosts_configured"] is False
    assert capability["configured"] is False


def test_video_admission_capability_blocks_unverified_pricing_exposure(monkeypatch) -> None:
    registry = SimpleNamespace(
        store=SimpleNamespace(
            service=lambda service_id: {
                "model": MODEL_ID,
                "endpoint": CREATE_ENDPOINT,
                "query_endpoint": QUERY_ENDPOINT,
                "allowed_artifact_hosts": ["media.example.invalid"],
                "pricing_exposure_contract": {
                    "verification_state": "unverified",
                    "billing_mode": "provider_output_tokens",
                    "provider_enforced_cost_cap": False,
                },
            }
        ),
        descriptor=lambda service_id: SimpleNamespace(
            reference_image_slots=4,
            supported_durations_sec=[6],
            supported_resolutions=["720p"],
            frame_modes=["reference_images"],
        ),
    )
    monkeypatch.setattr(
        "apps.api.runtime_video_admission.load_provider_registry",
        lambda: registry,
    )

    capability = video_admission_capability()

    assert capability["exact_model"] is True
    assert capability["exact_endpoint"] is True
    assert capability["exact_query_endpoint"] is True
    assert capability["pricing_verified"] is False
    assert capability["provider_enforced_cost_cap"] is False
    assert capability["configured"] is False


def test_video_admission_capability_fails_closed_on_input_upload_config_drift(
    monkeypatch,
) -> None:
    registry = SimpleNamespace(
        store=SimpleNamespace(
            service=lambda service_id: {
                "model": MODEL_ID,
                "endpoint": CREATE_ENDPOINT,
                "query_endpoint": QUERY_ENDPOINT,
                "input_upload_endpoint": "/v1/files/uploads/url",
                "allowed_artifact_hosts": ["media.crazyrouter.com"],
                "allowed_input_hosts": [
                    "media.crazyrouter.com",
                    "similar.crazyrouter.com",
                ],
                "pricing_exposure_contract": {
                    "verification_state": "verified",
                    "billing_mode": "provider_output_tokens",
                    "output_token_usd": "0.01",
                    "worst_case_output_tokens": 100,
                    "worst_case_cost_usd": "1.00",
                    "source_checked_at": REQUESTED_AT,
                    "provider_enforced_cost_cap": False,
                },
            }
        ),
        descriptor=lambda service_id: SimpleNamespace(
            reference_image_slots=4,
            supported_durations_sec=[6],
            supported_resolutions=["720p"],
            frame_modes=["first_frame", "reference_images"],
        ),
    )
    monkeypatch.setattr(
        "apps.api.runtime_video_admission.load_provider_registry",
        lambda: registry,
    )

    capability = video_admission_capability()

    assert capability["exact_input_upload_endpoint"] is False
    assert capability["input_host_configured"] is False
    assert capability["configured"] is False


def _seed_ready_project(
    tmp_path,
    *,
    manifest_semantics: bool = True,
    graph_semantics: bool = True,
    manifest_status: str = "locked",
    strict_first_frame_required: bool = True,
    include_keyframe: bool = True,
) -> tuple[TestClient, RuntimeStore, str, dict[str, str]]:
    runtime_root = tmp_path / "runtime"
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    store = RuntimeStore(runtime_root)
    project_id = "seedance-readiness"
    response = client.post(
        "/projects",
        json={"project_id": project_id, "goal": "Reference-driven shot 01 video"},
    )
    assert response.status_code == 200
    media = {}
    if include_keyframe:
        media["keyframe"] = _upload(client, project_id, "shot-01-keyframe")
    media.update(
        {
            "character": _upload(client, project_id, "character-reference"),
            "scene": _upload(client, project_id, "scene-reference"),
            "prop": _upload(client, project_id, "prop-reference"),
        }
    )
    graph_store = ProductionGraphStore(store)
    graph = graph_store.ensure(project_id)
    events = [
        {
            "type": "node_upserted",
            "node": {
                "node_id": "character-a",
                "category": "entity",
                "metadata": {"display_name": "巡夜人甲"},
            },
        },
        {
            "type": "node_upserted",
            "node": {
                "node_id": "scene-container-a",
                "category": "location",
                "metadata": {"display_name": "第一场"},
            },
        },
        {
            "type": "node_upserted",
            "node": {
                "node_id": "scene-a",
                "category": "resource",
                "metadata": {"kind": "scene", "display_name": "北侧检修站"},
            },
        },
        {
            "type": "node_upserted",
            "node": {
                "node_id": "prop-a",
                "category": "resource",
                "metadata": {"kind": "prop", "display_name": "六角校准器"},
            },
        },
        {
            "type": "node_upserted",
            "node": {
                "node_id": "shot-01",
                "category": "unit",
                "metadata": {
                    "kind": "shot",
                    "display_name": "镜头 01",
                    "strict_first_frame_required": strict_first_frame_required,
                    **(
                        {
                            "intent": "建立检修任务",
                            "blocking": "巡夜人甲在操作台前校准六角校准器",
                            "shot_size": "中景",
                            "camera_angle": "平视",
                            "camera_movement": "沿操作台缓慢向前推进",
                            "narrative_purpose": "保持克制专注的检修压力",
                            "continuity_cues": ["服装、工具位置与北侧检修站照明保持连续"],
                        }
                        if graph_semantics
                        else {}
                    ),
                },
            },
        },
        {
            "type": "relation_upserted",
            "from_id": "character-a",
            "to_id": "shot-01",
            "relation_type": "required_by",
        },
        {
            "type": "relation_upserted",
            "from_id": "prop-a",
            "to_id": "shot-01",
            "relation_type": "required_by",
        },
        {
            "type": "relation_upserted",
            "from_id": "scene-a",
            "to_id": "shot-01",
            "relation_type": "required_by",
        },
        {
            "type": "relation_upserted",
            "from_id": "scene-container-a",
            "to_id": "shot-01",
            "relation_type": "contains",
        },
    ]
    for label, asset_id in media.items():
        target_id = {
            "keyframe": "shot-01",
            "character": "character-a",
            "scene": "scene-a",
            "prop": "prop-a",
        }[label]
        approved_node_id = f"approved-{label}"
        events.append(
            {
                "type": "node_upserted",
                "node": {
                    "node_id": approved_node_id,
                    "category": "artifact",
                    "metadata": {
                        "kind": "approved_image",
                        "image_asset_id": asset_id,
                    },
                },
            }
        )
        events.append(
            {
                "type": "relation_upserted",
                "from_id": target_id,
                "to_id": approved_node_id,
                "relation_type": "approved_image",
            }
        )
    graph = graph_store.append(
        project_id,
        expected_version=graph["version"],
        idempotency_key="seed-video-readiness",
        semantic_digest=canonical_digest({"media": media}),
        events=events,
    )
    if include_keyframe:
        image_manifest = {
            "schema_version": "afs.image_admission_manifest.v0.1",
            "project_id": project_id,
            "manifest_id": "image-manifest-for-video",
            "manifest_hash": "a" * 64,
            "status": manifest_status,
            "source": {
                "asset_bible_revision_id": "asset-bible-r9",
                "shot_candidate_id": "shots-r1",
                "shot_grounding": {
                    "shots": [
                        {
                            "shot_id": "shot-01",
                            "title": "镜头 01",
                            "number": 1,
                            "action": (
                                "巡夜人甲在操作台前校准六角校准器"
                                if manifest_semantics
                                else ""
                            ),
                            "composition": (
                                "中景"
                                if manifest_semantics
                                else ""
                            ),
                            "camera_angle": "平视" if manifest_semantics else "",
                            "movement": "沿操作台缓慢向前推进" if manifest_semantics else "",
                            "emotion": "保持克制专注的检修压力" if manifest_semantics else "",
                            "purpose": "保持克制专注的检修压力" if manifest_semantics else "",
                            "continuity_cues": (
                                ["服装、工具位置与北侧检修站照明保持连续"]
                                if manifest_semantics
                                else []
                            ),
                        }
                    ]
                },
            },
            "accepted_graph_snapshots": [
                {"version": graph["version"], "graph_digest": graph["graph_digest"]}
            ],
            "items": [
                {
                    "item_id": "keyframe-shot-01",
                    "item_type": "shot_keyframe",
                    "target_shot_id": "shot-01",
                    "label": "镜头 01 已批准关键帧",
                    "aspect_ratio": "16:9",
                    "state": "approved",
                    "candidate": {"image_asset_id": media["keyframe"]},
                    "reference_asset_ids": ["character-a", "scene-a", "prop-a"],
                    "reference_media_ids": [
                        media["character"],
                        media["scene"],
                        media["prop"],
                    ],
                }
            ],
        }
        image_manifest_path = (
            store.projects_dir / project_id / "image_admission" / "manifest.json"
        )
        image_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(image_manifest_path, image_manifest)
    return client, store, project_id, media


def _add_second_ready_shot(store: RuntimeStore, project_id: str) -> dict:
    return _add_ready_shot(store, project_id, "shot-02", 2)


def _add_ready_shot(
    store: RuntimeStore,
    project_id: str,
    shot_id: str,
    number: int,
    *,
    metadata: dict | None = None,
) -> dict:
    graph_store = ProductionGraphStore(store)
    graph = graph_store.load(project_id)
    display = f"镜头 {number:02d}"
    details = {
        "kind": "shot",
        "display_name": display,
        "number": number,
        "intent": f"完成第 {number:02d} 个动作段落",
        "blocking": "巡夜人甲离开操作台转向检修门",
        "shot_size": "中近景",
        "camera_angle": "平视",
        "camera_movement": "横移跟随",
        "narrative_purpose": "推进检修任务进入下一空间",
        "continuity_cues": ["延续北侧检修站照明与六角校准器位置"],
        **(metadata or {}),
    }
    return graph_store.append(
        project_id,
        expected_version=graph["version"],
        idempotency_key=f"seed-video-{shot_id}",
        semantic_digest=canonical_digest({"shot": shot_id, "metadata": details}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": shot_id,
                    "category": "unit",
                    "metadata": details,
                },
            },
            {
                "type": "relation_upserted",
                "from_id": "character-a",
                "to_id": shot_id,
                "relation_type": "required_by",
            },
            {
                "type": "relation_upserted",
                "from_id": "prop-a",
                "to_id": shot_id,
                "relation_type": "required_by",
            },
            {
                "type": "relation_upserted",
                "from_id": "scene-a",
                "to_id": shot_id,
                "relation_type": "required_by",
            },
            {
                "type": "relation_upserted",
                "from_id": "scene-container-a",
                "to_id": shot_id,
                "relation_type": "contains",
            },
        ],
    )


def test_video_readiness_normalizes_equivalent_production_graph_shot_fields(tmp_path) -> None:
    client, _, project_id, _ = _seed_ready_project(
        tmp_path,
        manifest_semantics=False,
    )

    response = client.get(f"/projects/{project_id}/m6/video-admission")

    assert response.status_code == 200
    assert response.json()["readiness"]["status"] == "ready"
    preview = _command(
        client,
        project_id,
        _reference_video_setup_command(
            {"type": "compile", "idempotency_key": "compile-normalized-shot"}
        ),
        confirm=False,
    )
    prompt_contract = preview["result"]["manifest"]["source"]["prompt_contract"]
    assert preview["result"]["manifest"]["source"]["shot_semantics"]["action"] == (
        "巡夜人甲在操作台前校准六角校准器"
    )
    assert prompt_contract["shot_action"] == TEMPORAL_STAGING["subject_action_arc"]
    assert prompt_contract["composition"] == "中景"
    assert prompt_contract["camera_movement"] == "沿操作台缓慢向前推进"
    assert prompt_contract["emotion"] == TEMPORAL_STAGING["narrative_purpose"]
    assert prompt_contract["keyword_rewrite"] is False
    assert prompt_contract["sample_fallback"] is False
    assert preview["provider_dispatch_count"] == 0


def test_reference_conditioned_manifest_sends_real_identity_references_without_first_frame(
    tmp_path,
) -> None:
    client, store, project_id, media = _seed_ready_project(tmp_path)
    readiness = client.get(f"/projects/{project_id}/m6/video-admission").json()[
        "readiness"
    ]
    assert readiness["suggested_generation_mode"] == "reference_conditioned"
    assert {
        item["mode"]: item["supported"]
        for item in readiness["generation_modes"]
    } == {
        "reference_conditioned": True,
        "first_frame": True,
        "text_to_video": False,
    }
    command = {
        "type": "compile",
        "idempotency_key": "compile-reference-conditioned",
        "generation_mode": "reference_conditioned",
        "selection_reason": "使用角色、场景和道具参考约束连续性，不锁定首帧。",
        "temporal_staging": TEMPORAL_STAGING,
    }
    body = {"command": command, "requested_at": REQUESTED_AT}
    preview = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json=body,
    )
    assert preview.status_code == 200, preview.text
    candidate = preview.json()["result"]["manifest"]
    input_contract = candidate["provider_input_contract"]
    assert input_contract["mode"] == "reference_conditioned"
    assert input_contract["first_frame"] is None
    assert input_contract["last_frame"] is None
    assert [item["role"] for item in input_contract["reference_images"]] == [
        "reference_image",
        "reference_image",
        "reference_image",
    ]
    assert {
        item["image_asset_id"] for item in input_contract["reference_images"]
    } == {media["character"], media["scene"], media["prop"]}
    assert input_contract["frame_role_cardinality"] == {
        "first_frame": 0,
        "last_frame": 0,
        "reference_image": 3,
    }
    assert candidate["source"]["temporal_staging"] == TEMPORAL_STAGING
    assert candidate["source"]["prompt_contract"]["generation_mode"] == (
        "reference_conditioned"
    )
    assert "Reference images" not in candidate["source"]["prompt_contract"][
        "provider_prompt"
    ]
    confirmed = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/confirm",
        json={**body, "preview_digest": preview.json()["preview_digest"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    reserved = _command(
        client,
        project_id,
        {"type": "reserve_dispatch", "idempotency_key": "reserve-reference"},
    )["result"]["manifest"]
    request = video_admission_generation_request(
        reserved,
        generated_at=REQUESTED_AT,
    )
    assert request["generation_path"] == "reference_images"
    assert request["first_frame_image_asset_id"] is None
    assert set(request["reference_image_asset_ids"]) == {
        media["character"],
        media["scene"],
        media["prop"],
    }
    assert load_video_admission_manifest(store, project_id) == reserved


def test_reference_targets_exclude_scene_container_and_include_scene_resource(
    tmp_path,
) -> None:
    client, store, project_id, media = _seed_ready_project(tmp_path)

    preview = _command(
        client,
        project_id,
        {
            "type": "compile",
            "idempotency_key": "compile-canonical-scene-resource",
            "generation_mode": "reference_conditioned",
            "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
        },
        confirm=False,
    )
    manifest = preview["result"]["manifest"]

    assert manifest["source"]["canonical_entities"] == {
        "characters": ["巡夜人甲"],
        "scenes": ["北侧检修站"],
        "props": ["六角校准器"],
    }
    assert {
        item["target_asset_id"]: item["image_asset_id"]
        for item in manifest["source"]["references"]
    } == {
        "character-a": media["character"],
        "scene-a": media["scene"],
        "prop-a": media["prop"],
    }
    assert "第一场" not in manifest["source"]["prompt_contract"]["provider_prompt"]
    assert preview["provider_dispatch_count"] == 0
    assert load_video_admission_manifest(store, project_id) == {}


def test_reference_conditioned_manifest_allows_four_provider_refs(tmp_path) -> None:
    client, store, project_id, media = _seed_ready_project(tmp_path)
    extra_prop = _upload(client, project_id, "second-prop-reference")
    graph_store = ProductionGraphStore(store)
    graph = graph_store.load(project_id)
    graph_store.append(
        project_id,
        expected_version=graph["version"],
        idempotency_key="seed-fourth-video-reference",
        semantic_digest=canonical_digest({"extra_ref": extra_prop}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "prop-b",
                    "category": "resource",
                    "metadata": {"kind": "prop", "display_name": "备用仪表盘"},
                },
            },
            {
                "type": "relation_upserted",
                "from_id": "prop-b",
                "to_id": "shot-01",
                "relation_type": "required_by",
            },
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "approved-extra-prop",
                    "category": "artifact",
                    "metadata": {
                        "kind": "approved_image",
                        "image_asset_id": extra_prop,
                    },
                },
            },
            {
                "type": "relation_upserted",
                "from_id": "prop-b",
                "to_id": "approved-extra-prop",
                "relation_type": "approved_image",
            },
        ],
    )

    manifest = _command(
        client,
        project_id,
        {
            "type": "compile",
            "idempotency_key": "compile-four-video-refs",
            "generation_mode": "reference_conditioned",
            "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
        },
    )["result"]["manifest"]
    request = video_admission_generation_request(
        manifest,
        generated_at=REQUESTED_AT,
    )

    assert len(request["reference_image_asset_ids"]) == 4
    assert set(request["reference_image_asset_ids"]) == {
        media["character"],
        media["scene"],
        media["prop"],
        extra_prop,
    }
    VideoGenerationRequest(**request)
    assert manifest["provider_input_contract"]["frame_role_cardinality"]["reference_image"] == 4


def test_partial_reference_compile_records_missing_scene_without_faking_input(
    tmp_path,
) -> None:
    client, store, project_id, media = _seed_ready_project(tmp_path)
    graph_store = ProductionGraphStore(store)
    graph = graph_store.load(project_id)
    graph_store.append(
        project_id,
        expected_version=graph["version"],
        idempotency_key="seed-partial-video-shot",
        semantic_digest=canonical_digest({"partial": "shot-02"}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "scene-missing",
                    "category": "resource",
                    "metadata": {"kind": "scene", "display_name": "未完成场景"},
                },
            },
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "shot-02",
                    "category": "unit",
                    "metadata": {
                        "kind": "shot",
                        "display_name": "镜头 02",
                        "number": 2,
                        "blocking": "巡夜人甲走向新空间",
                        "shot_size": "中景",
                        "camera_angle": "平视",
                        "camera_movement": "横移跟随",
                        "narrative_purpose": "进入下一段空间调度",
                    },
                },
            },
            {
                "type": "relation_upserted",
                "from_id": "scene-container-a",
                "to_id": "shot-02",
                "relation_type": "contains",
            },
            {
                "type": "relation_upserted",
                "from_id": "character-a",
                "to_id": "shot-02",
                "relation_type": "required_by",
            },
            {
                "type": "relation_upserted",
                "from_id": "prop-a",
                "to_id": "shot-02",
                "relation_type": "required_by",
            },
            {
                "type": "relation_upserted",
                "from_id": "scene-missing",
                "to_id": "shot-02",
                "relation_type": "required_by",
            },
        ],
    )

    strict = client.post(
        f"/projects/{project_id}/m6/video-admission/lanes/shot-02/commands/preview",
        json={
            "command": _reference_video_setup_command(
                {
                    "type": "compile",
                    "idempotency_key": "compile-partial-strict",
                    "shot_id": "shot-02",
                }
            ),
            "requested_at": REQUESTED_AT,
        },
    )
    assert strict.status_code == 422

    partial = client.post(
        f"/projects/{project_id}/m6/video-admission/lanes/shot-02/commands/preview",
        json={
            "command": _reference_video_setup_command(
                {
                    "type": "compile",
                    "idempotency_key": "compile-partial-allowed",
                    "shot_id": "shot-02",
                    "allow_partial_references": True,
                    "partial_reference_reason": "测试允许场景缺图时使用主体和道具参考继续。",
                }
            ),
            "requested_at": REQUESTED_AT,
        },
    )
    assert partial.status_code == 200, partial.text
    manifest = partial.json()["result"]["manifest"]
    resolution = manifest["source"]["reference_resolution"]
    assert resolution["partial_reference_pack"] is True
    assert resolution["partial_reason"] == "测试允许场景缺图时使用主体和道具参考继续。"
    assert resolution["missing_references"] == [
        {
            "target_asset_id": "scene-missing",
            "label": "未完成场景",
            "kind": "scene",
            "missing_scene_ref": True,
            "reason": "missing_approved_reference_image",
        }
    ]
    assert set(video_admission_generation_request(manifest, generated_at=REQUESTED_AT)["reference_image_asset_ids"]) == {
        media["character"],
        media["prop"],
    }
    assert any(
        item["role"] == "missing_reference_not_sent"
        and item["target_asset_id"] == "scene-missing"
        for item in manifest["provider_input_contract"]["excluded_grounding_references"]
    )
    assert load_video_admission_manifest(store, project_id, shot_id="shot-02") == {}


def test_temporal_prompt_uses_explicit_staging_narrative_for_emotion() -> None:
    contract = build_temporal_prompt(
        mode="reference_conditioned",
        selection_reason="使用已批准资产参考约束身份与连续性，不锁定首帧。",
        staging={
            **TEMPORAL_STAGING,
            "narrative_purpose": "用梦境隐喻表现创伤记忆和重生前奏，明确无伤害细节。",
        },
        shot={
            "composition": "水下大全景",
            "camera_angle": "轻微俯角",
            "emotion": "濒死感打开前世创伤和重生设定",
            "continuity_cues": [],
        },
        canonical_entities={
            "characters": ["叶安安"],
            "scenes": ["象征性深海"],
            "props": [],
        },
    )

    assert contract["emotion"] == "用梦境隐喻表现创伤记忆和重生前奏，明确无伤害细节。"
    assert "濒死" not in contract["provider_prompt"]
    assert "死亡" not in contract["provider_prompt"]
    assert "血腥" not in contract["provider_prompt"]


def test_direct_batch_targets_skip_post_only_and_unready_first_frame(tmp_path) -> None:
    _, store, project_id, _ = _seed_ready_project(tmp_path)
    for number in (2, 31, 33, 34, 35):
        _add_ready_shot(store, project_id, f"shot-{number:02d}", number)

    targets = direct_batch_runner.build_targets(store, project_id)
    by_number = {target.shot_number: target for target in targets}

    assert by_number[1].skip_reason == ""
    assert by_number[2].skip_reason == ""
    assert by_number[31].skip_reason == "post_only"
    assert by_number[33].skip_reason == "post_only"
    assert by_number[34].skip_reason == "post_only"
    assert by_number[35].skip_reason == "requires_approved_first_frame"


def test_direct_batch_dry_run_keeps_shot1_safe_and_provider_free(
    tmp_path,
    monkeypatch,
) -> None:
    _, store, project_id, _ = _seed_ready_project(tmp_path)
    graph_store = ProductionGraphStore(store)
    graph = graph_store.load(project_id)
    metadata = deepcopy(graph["nodes"]["shot-01"]["metadata"])
    metadata.update(
        {
            "display_name": "深海坠落",
            "action": "叶安安在象征性深海缓慢下沉",
            "emotion": "濒死感打开前世创伤和重生设定",
            "narrative_purpose": "濒死感打开前世创伤和重生设定",
        }
    )
    graph_store.append(
        project_id,
        expected_version=graph["version"],
        idempotency_key="seed-shot1-policy-sensitive-source",
        semantic_digest=canonical_digest({"shot": "shot-01", "metadata": metadata}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "shot-01",
                    "category": "unit",
                    "metadata": metadata,
                },
            }
        ],
    )
    monkeypatch.setattr(
        direct_batch_runner,
        "provider_pool_summary",
        lambda: {
            "dispatch_ready": True,
            "service_id": SERVICE_ID,
            "model": MODEL_ID,
            "enabled_video_accounts": 4,
            "concurrency_capacity": 4,
        },
    )

    summary = direct_batch_runner.dry_run(store, project_id)

    assert summary["eligible"] == 1
    assert summary["skipped"] == 0
    assert summary["provider_dispatch_count"] == 0
    compiled = summary["compiled"][0]
    assert compiled["shot_number"] == 1
    assert compiled["generation_mode"] == "reference_conditioned"
    assert compiled["reference_count"] == 3
    assert compiled["shot1_policy_safe"] is True
    assert load_video_admission_manifest(store, project_id, shot_id="shot-01") == {}


def test_direct_batch_operator_proof_records_service_process_task_identity(
    tmp_path,
    monkeypatch,
) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _add_second_ready_shot(store, project_id)

    def _fake_dispatch_once(
        store: RuntimeStore,
        project_id: str,
        run_id: str,
        manifest: dict,
        *,
        job_id: str | None = None,
    ) -> dict:
        request = VideoGenerationRequest(
            **{
                **video_admission_generation_request(
                    manifest,
                    generated_at=REQUESTED_AT,
                ),
                "quota_override_confirmed": True,
            }
        )
        job_id = job_id or store.new_job_id("video_generation", project_id)
        claim_video_admission_dispatch(store, project_id, request, job_id=job_id)
        mark_video_admission_network_started(store, project_id, job_id=job_id)
        mark_video_admission_task_recorded(
            store,
            project_id,
            job_id=job_id,
            provider_task_fingerprint="proof-task-fingerprint",
        )
        return {
            "status": "submitted",
            "job": {"job_id": job_id, "status": "submitted"},
            "provider_calls_started": True,
            "safe_manifest": {"blocks": []},
            "candidate_previews": [],
        }

    monkeypatch.setattr(direct_batch_runner, "dispatch_once", _fake_dispatch_once)

    response = client.post(
        f"/studio/operator/projects/{project_id}/video-direct-batch/proof",
        json={
            "operator_confirmation": OPERATOR_CONFIRMATION,
            "run_id": "video-direct-proof-test",
            "shot_number": 2,
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "proof_passed"
    assert payload["result"]["connectivity_proof_passed"] is True
    assert payload["result"]["has_provider_task_fingerprint"] is True
    manifest = load_video_admission_manifest(store, project_id, shot_id="shot-02")
    assert manifest["item"]["state"] == "processing"
    assert manifest["item"]["network_disposition"] == "dispatched_with_task_identity"
    assert manifest["provider_dispatch_count"] == 1


def test_direct_batch_operator_diagnostic_runs_text_and_single_ref_without_graph_mutation(
    tmp_path,
    monkeypatch,
) -> None:
    client, store, project_id, media = _seed_ready_project(tmp_path)
    graph_store = ProductionGraphStore(store)
    graph = graph_store.load(project_id)
    graph = graph_store.append(
        project_id,
        expected_version=graph["version"],
        idempotency_key="seed-diagnostic-gold-piece-ref",
        semantic_digest=canonical_digest({"diagnostic_ref": "A-PROP-01"}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "A-PROP-01",
                    "category": "resource",
                    "metadata": {"kind": "prop", "display_name": "金色棋子"},
                },
            },
            {
                "type": "relation_upserted",
                "from_id": "A-PROP-01",
                "to_id": "approved-prop",
                "relation_type": "approved_image",
            },
        ],
    )

    class _FakeRegistry:
        def submit(self, capability: str, service_id: str, request) -> dict:
            assert capability == "video"
            assert service_id == SERVICE_ID
            assert request.duration_sec == 6
            assert request.resolution == "720p"
            assert request.aspect_ratio == "16:9"
            return {
                "task": {
                    "task_id": f"diag-{request.input_mode}",
                    "status": "submitted",
                }
            }

    monkeypatch.setattr(
        "apps.api.runtime_video_direct_batch_routes.load_provider_registry",
        lambda: _FakeRegistry(),
    )

    text = client.post(
        f"/studio/operator/projects/{project_id}/video-direct-batch/diagnostic",
        json={
            "operator_confirmation": OPERATOR_CONFIRMATION,
            "run_id": "video-direct-diagnostic-text-test",
            "step": "text_only",
        },
    )
    ref = client.post(
        f"/studio/operator/projects/{project_id}/video-direct-batch/diagnostic",
        json={
            "operator_confirmation": OPERATOR_CONFIRMATION,
            "run_id": "video-direct-diagnostic-ref-test",
            "step": "single_reference",
        },
    )

    assert text.status_code == 200, text.text
    assert ref.status_code == 200, ref.text
    assert text.json()["result"]["has_provider_task_fingerprint"] is True
    assert text.json()["result"]["input_mode"] == "text_only"
    assert ref.json()["result"]["has_provider_task_fingerprint"] is True
    assert ref.json()["result"]["input_mode"] == "reference_images"
    assert ref.json()["result"]["reference_asset_id"] == media["prop"]
    current = graph_store.load(project_id)
    assert current["version"] == graph["version"]
    assert current["graph_digest"] == graph["graph_digest"]


def test_direct_batch_operator_diagnostic_provider_block_returns_safe_packet(
    tmp_path,
    monkeypatch,
) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    graph_before = ProductionGraphStore(store).load(project_id)

    class _BlockedRegistry:
        def submit(self, capability: str, service_id: str, request) -> dict:
            raise ValueError("unsupported input mode for seedance_i2v: text_only")

    monkeypatch.setattr(
        "apps.api.runtime_video_direct_batch_routes.load_provider_registry",
        lambda: _BlockedRegistry(),
    )

    response = client.post(
        f"/studio/operator/projects/{project_id}/video-direct-batch/diagnostic",
        json={
            "operator_confirmation": OPERATOR_CONFIRMATION,
            "run_id": "video-direct-diagnostic-blocked-test",
            "step": "text_only",
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "diagnostic_text_only_blocked"
    assert payload["result"]["connectivity_proof_passed"] is False
    assert payload["result"]["input_mode"] == "text_only"
    assert payload["result"]["block"]["reason"] == (
        "unsupported input mode for seedance_i2v: text_only"
    )
    graph_after = ProductionGraphStore(store).load(project_id)
    assert graph_after["version"] == graph_before["version"]
    assert graph_after["graph_digest"] == graph_before["graph_digest"]


def test_direct_batch_operator_diagnostic_candidate_summary_is_ledger_safe(
    tmp_path,
    monkeypatch,
) -> None:
    client, store, project_id, media = _seed_ready_project(tmp_path)
    graph_store = ProductionGraphStore(store)
    graph_before = graph_store.load(project_id)
    graph_store.append(
        project_id,
        expected_version=graph_before["version"],
        idempotency_key="seed-ledger-safe-diagnostic-ref",
        semantic_digest=canonical_digest({"diagnostic_ref": "A-PROP-01", "safe_ledger": True}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "A-PROP-01",
                    "category": "resource",
                    "metadata": {"kind": "prop", "display_name": "金色棋子"},
                },
            },
            {
                "type": "relation_upserted",
                "from_id": "A-PROP-01",
                "to_id": "approved-prop",
                "relation_type": "approved_image",
            },
        ],
    )

    class _FakeRegistry:
        def submit(self, capability: str, service_id: str, request) -> dict:
            assert capability == "video"
            assert service_id == SERVICE_ID
            return {"task": {"task_id": "diag-ledger-safe", "status": "submitted"}}

    def _unsafe_poll_summary(*args, **kwargs) -> dict:
        return {
            "status": "succeeded",
            "job_id": "job-ledger-safe",
            "candidate_count": 1,
            "candidates": [
                {
                    "candidate_id": "candidate_001",
                    "preview_url": f"/projects/{project_id}/video-generations/job-ledger-safe/candidates/candidate_001/preview",
                    "path": "/var/lib/afs-runtime/runs/project/job/video_candidates/candidate_001.mp4",
                    "sha256": "a" * 64,
                    "byte_count": 123,
                    "technical_qa": {"file_present": True, "nonzero_bytes": True, "suffix": ".mp4"},
                }
            ],
            "provider_calls_started": True,
            "blocks": [],
            "terminal": True,
        }

    monkeypatch.setattr(
        "apps.api.runtime_video_direct_batch_routes.load_provider_registry",
        lambda: _FakeRegistry(),
    )
    monkeypatch.setattr(
        direct_batch_routes,
        "_poll_diagnostic_job_to_terminal",
        _unsafe_poll_summary,
    )

    response = client.post(
        f"/studio/operator/projects/{project_id}/video-direct-batch/diagnostic",
        json={
            "operator_confirmation": OPERATOR_CONFIRMATION,
            "run_id": "video-direct-diagnostic-safe-ledger-test",
            "step": "single_reference",
            "max_poll_sec": 30,
        },
    )

    assert response.status_code == 200, response.text
    payload_text = response.text
    assert "/var/lib/" not in payload_text
    assert "/projects/" not in payload_text
    payload = response.json()
    assert payload["status"] == "diagnostic_single_reference_accepted"
    assert payload["result"]["poll"]["candidate_count"] == 1
    ledger = read_json(
        direct_batch_runner.batch_path(
            store,
            project_id,
            "video-direct-diagnostic-safe-ledger-test",
        )
    )
    ledger_text = str(ledger)
    assert "/var/lib/" not in ledger_text
    assert "/projects/" not in ledger_text
    assert ledger["status"] == "diagnostic_single_reference_accepted"
    assert ledger["results"][0]["poll"]["candidates"][0]["candidate_id"] == "candidate_001"


def test_direct_batch_safety_rewrite_staging_is_positive_and_provider_free(
    tmp_path,
    monkeypatch,
) -> None:
    _, store, project_id, _ = _seed_ready_project(tmp_path)
    for number in (10, 21, 22, 23):
        _add_ready_shot(
            store,
            project_id,
            f"shot-{number:02d}",
            number,
            metadata={
                "display_name": f"敏感源镜头 {number:02d}",
                "blocking": "旧源文本包含冲突和危险词但不应进入新轮主体动作",
                "narrative_purpose": "旧源文本包含伤害和威胁但不应进入新轮情绪",
            },
        )
    monkeypatch.setattr(
        direct_batch_runner,
        "provider_pool_summary",
        lambda: {
            "dispatch_ready": True,
            "service_id": SERVICE_ID,
            "model": MODEL_ID,
            "enabled_video_accounts": 2,
            "concurrency_capacity": 2,
        },
    )

    summary = direct_batch_runner.dry_run(store, project_id)
    by_number = {item["shot_number"]: item for item in summary["compiled"]}

    for number in (10, 21, 22, 23):
        assert by_number[number]["reference_count"] == 3
        manifest = direct_batch_runner.admission_command(
            store,
            project_id,
            f"shot-{number:02d}",
            {
                "type": "compile",
                "shot_id": f"shot-{number:02d}",
                "generation_mode": "reference_conditioned",
                "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
                "temporal_staging": direct_batch_runner.temporal_staging_for_target(
                    store,
                    project_id,
                    direct_batch_runner.BatchTarget(
                        f"shot-{number:02d}",
                        number,
                        f"镜头 {number:02d}",
                        "reference_conditioned",
                        3,
                    ),
                ),
                "idempotency_key": f"safety-rewrite-preview-{number}",
            },
            confirm=False,
        )["result"]["manifest"]
        prompt = manifest["source"]["prompt_contract"]["provider_prompt"]
        assert "旧源文本" not in prompt
        assert "伤害" not in prompt
        assert "威胁" not in prompt
        assert "危险" not in prompt
    assert summary["provider_dispatch_count"] == 0


def test_video_compile_selects_explicit_non_first_active_unit_shot(tmp_path) -> None:
    client, store, project_id, media = _seed_ready_project(tmp_path)
    _add_second_ready_shot(store, project_id)

    implicit = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": _reference_video_setup_command(
                {"type": "compile", "idempotency_key": "compile-ambiguous"}
            ),
            "requested_at": REQUESTED_AT,
        },
    )
    assert implicit.status_code == 422
    assert "explicit shot_id" in implicit.text

    preview = _command(
        client,
        project_id,
        {
            "type": "compile",
            "idempotency_key": "compile-shot-02",
            "shot_id": "shot-02",
            "generation_mode": "reference_conditioned",
            "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
        },
        confirm=False,
    )
    manifest = preview["result"]["manifest"]

    assert manifest["source"]["shot"]["shot_id"] == "shot-02"
    assert manifest["source"]["shot"]["number"] == 2
    assert manifest["item"]["item_id"] == "video-shot-02"
    assert {item["image_asset_id"] for item in manifest["source"]["references"]} == {
        media["character"],
        media["scene"],
        media["prop"],
    }
    assert manifest["provider_dispatch_count"] == 0
    assert load_video_admission_manifest(store, project_id) == {}


def test_unstarted_reserved_video_failure_releases_lane_without_dispatch(tmp_path) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _command(
        client,
        project_id,
        {
            "type": "compile",
            "idempotency_key": "compile-unstarted-reserved-failure",
            "generation_mode": "reference_conditioned",
            "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
        },
    )
    reserved = _command(
        client,
        project_id,
        {
            "type": "reserve_dispatch",
            "idempotency_key": "reserve-unstarted-reserved-failure",
        },
    )["result"]["manifest"]

    assert reserved["item"]["state"] == "reserved"
    assert reserved["item"]["network_disposition"] == "never_started"
    assert reserved["provider_dispatch_count"] == 0

    failed = _command(
        client,
        project_id,
        {
            "type": "record_failure",
            "idempotency_key": "fail-unstarted-reserved",
            "error_category": "provider_gate_closed",
        },
    )["result"]["manifest"]

    assert failed["item"]["state"] == "failed"
    assert failed["item"]["error_category"] == "provider_gate_closed"
    assert failed["provider_dispatch_count"] == 0
    assert failed["budget"]["dispatches_reserved"] == 1
    assert failed["budget"]["remaining_dispatches"] == 0
    assert failed["item"]["provider_job_id"] == ""
    assert load_video_admission_manifest(store, project_id) == failed
    assert _video_manifest_consumes_lane(store, project_id, failed) is False


def test_video_compile_rejects_invalid_non_active_or_non_unit_shot_id(tmp_path) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    graph_store = ProductionGraphStore(store)
    graph = graph_store.load(project_id)
    graph_store.append(
        project_id,
        expected_version=graph["version"],
        idempotency_key="seed-invalid-shot-targets",
        semantic_digest=canonical_digest({"invalid": "shot-targets"}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "inactive-shot",
                    "category": "unit",
                    "state": "inactive",
                    "metadata": {"kind": "shot", "display_name": "停用镜头"},
                },
            },
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "scene-asset-not-shot",
                    "category": "resource",
                    "metadata": {"kind": "scene", "display_name": "非镜头资产"},
                },
            },
        ],
    )

    for shot_id, reason in (
        ("missing-shot", "not present"),
        ("inactive-shot", "active unit shot"),
        ("scene-asset-not-shot", "active unit shot"),
    ):
        response = client.post(
            f"/projects/{project_id}/m6/video-admission/commands/preview",
            json={
                "command": _reference_video_setup_command(
                    {
                        "type": "compile",
                        "idempotency_key": f"compile-{shot_id}",
                        "shot_id": shot_id,
                    }
                ),
                "requested_at": REQUESTED_AT,
            },
        )
        assert response.status_code == 422
        assert reason in response.text


def test_reference_conditioned_manifest_does_not_require_approved_shot_keyframe(
    tmp_path,
) -> None:
    client, store, project_id, media = _seed_ready_project(
        tmp_path,
        strict_first_frame_required=False,
        include_keyframe=False,
    )

    readiness = client.get(f"/projects/{project_id}/m6/video-admission").json()[
        "readiness"
    ]
    assert readiness["status"] == "ready"
    assert readiness["suggested_generation_mode"] == "reference_conditioned"
    assert {
        item["mode"]: item["supported"]
        for item in readiness["generation_modes"]
    } == {
        "reference_conditioned": True,
        "first_frame": False,
        "text_to_video": False,
    }

    preview = _command(
        client,
        project_id,
        {
            "type": "compile",
            "idempotency_key": "compile-reference-no-keyframe",
            "generation_mode": "reference_conditioned",
            "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
        },
        confirm=False,
    )
    manifest = preview["result"]["manifest"]
    assert manifest["source"]["keyframe"] == {}
    assert manifest["provider_input_contract"]["first_frame"] is None
    assert {
        item["image_asset_id"]
        for item in manifest["provider_input_contract"]["reference_images"]
    } == {media["character"], media["scene"], media["prop"]}
    request = video_admission_generation_request(
        {
            **manifest,
            "item": {
                **manifest["item"],
                "state": "reserved",
                "reservation_token": "test-reservation",
            },
        },
        generated_at=REQUESTED_AT,
    )
    assert request["generation_path"] == "reference_images"
    assert request["first_frame_image_asset_id"] is None
    assert request["aspect_ratio"] == "16:9"
    assert load_video_admission_manifest(store, project_id) == {}


def test_first_frame_mode_requires_explicit_opening_frame_semantics(tmp_path) -> None:
    client, store, project_id, _ = _seed_ready_project(
        tmp_path,
        strict_first_frame_required=False,
    )
    response = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": _video_setup_command(
                {
                    "type": "compile",
                    "idempotency_key": "compile-first-frame-without-semantics",
                }
            ),
            "requested_at": REQUESTED_AT,
        },
    )

    assert response.status_code == 422
    assert "只在镜头明确要求" in response.json()["detail"]["details"]["raw_detail"]
    assert load_video_admission_manifest(store, project_id) == {}


@pytest.mark.parametrize(
    "mutation",
    [
        {"temporal_staging": {**TEMPORAL_STAGING, "end_state": ""}},
        {"generation_mode": "text_to_video"},
        {"generation_mode": ""},
    ],
)
def test_video_setup_fails_closed_before_manifest_or_provider(
    tmp_path,
    mutation,
) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    command = {
        "type": "compile",
        "idempotency_key": "invalid-video-setup",
        "generation_mode": "reference_conditioned",
        "selection_reason": "使用资产参考约束连续性。",
        "temporal_staging": TEMPORAL_STAGING,
        **mutation,
    }
    response = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={"command": command, "requested_at": REQUESTED_AT},
    )
    assert response.status_code == 422
    assert load_video_admission_manifest(store, project_id) == {}
    assert response.json()["detail"]["details"]["raw_detail"]


def test_video_readiness_still_fails_closed_when_creative_semantics_are_absent(tmp_path) -> None:
    client, _, project_id, _ = _seed_ready_project(
        tmp_path,
        manifest_semantics=False,
        graph_semantics=False,
    )

    readiness = client.get(f"/projects/{project_id}/m6/video-admission")
    preview = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": {
                "type": "compile",
                "idempotency_key": "compile-missing-semantics",
            },
            "requested_at": REQUESTED_AT,
        },
    )

    assert readiness.status_code == 200
    assert readiness.json()["readiness"]["status"] == "blocked"
    assert preview.status_code == 422
    assert load_video_admission_manifest(
        RuntimeStore(tmp_path / "runtime"),
        project_id,
    ) == {}


@pytest.mark.parametrize("manifest_status", ["draft", "cancelled"])
def test_first_frame_readiness_requires_locked_image_manifest(
    tmp_path,
    manifest_status: str,
) -> None:
    client, store, project_id, _ = _seed_ready_project(
        tmp_path,
        manifest_status=manifest_status,
    )

    readiness = client.get(f"/projects/{project_id}/m6/video-admission")
    preview = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": _video_setup_command(
                {
                    "type": "compile",
                    "idempotency_key": f"compile-{manifest_status}-manifest",
                }
            ),
            "requested_at": REQUESTED_AT,
        },
    )

    assert readiness.status_code == 200
    assert readiness.json()["readiness"]["status"] == "ready"
    assert readiness.json()["readiness"]["suggested_generation_mode"] == "reference_conditioned"
    assert preview.status_code == 422
    assert "首帧图生视频需要明确选择" in preview.json()["detail"]["details"]["raw_detail"]
    assert load_video_admission_manifest(store, project_id) == {}
    assert ProductionGraphStore(store).load(project_id)["version"] == 1


def _video_setup_command(command: dict) -> dict:
    return {
        "generation_mode": "first_frame",
        "selection_reason": "测试明确要求从批准关键帧开始。",
        "temporal_staging": TEMPORAL_STAGING,
        **command,
    }


def _reference_video_setup_command(command: dict) -> dict:
    return {
        "generation_mode": "reference_conditioned",
        "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
        "temporal_staging": TEMPORAL_STAGING,
        **command,
    }


def _command(
    client: TestClient,
    project_id: str,
    command: dict,
    *,
    confirm: bool = True,
) -> dict:
    if command.get("type") in {
        "compile",
        "recompile_current",
        "create_new_round",
        "create_next_shot",
    }:
        command = _video_setup_command(command)
    body = {
        "command": command,
        "requested_at": REQUESTED_AT,
    }
    preview = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json=body,
    )
    assert preview.status_code == 200, preview.text
    if not confirm:
        return preview.json()
    response = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/confirm",
        json={**body, "preview_digest": preview.json()["preview_digest"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _lane_command(
    client: TestClient,
    project_id: str,
    shot_id: str,
    command: dict,
    *,
    confirm: bool = True,
) -> dict:
    if command.get("type") in {"compile", "recompile_current", "create_new_round"}:
        command = _reference_video_setup_command(command)
    body = {"command": command, "requested_at": REQUESTED_AT}
    preview = client.post(
        f"/projects/{project_id}/m6/video-admission/lanes/{shot_id}/commands/preview",
        json=body,
    )
    assert preview.status_code == 200, preview.text
    if not confirm:
        return preview.json()
    response = client.post(
        f"/projects/{project_id}/m6/video-admission/lanes/{shot_id}/commands/confirm",
        json={**body, "preview_digest": preview.json()["preview_digest"]},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _rotate_image_manifest_after_graph_update(
    store: RuntimeStore,
    project_id: str,
) -> tuple[dict, dict]:
    image_path = store.projects_dir / project_id / "image_admission" / "manifest.json"
    historical = read_json(image_path)
    history_path = (
        image_path.parent
        / "history"
        / f"{historical['manifest_id']}.json"
    )
    write_json(history_path, historical)
    graph_store = ProductionGraphStore(store)
    graph = graph_store.load(project_id)
    graph = graph_store.append(
        project_id,
        expected_version=graph["version"],
        idempotency_key="approve-other-shot-keyframe",
        semantic_digest=canonical_digest({"other_shot_keyframe": "approved"}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "approved-other-shot-keyframe",
                    "category": "artifact",
                    "metadata": {
                        "kind": "approved_image",
                        "image_asset_id": "other-shot-image",
                    },
                },
            }
        ],
    )
    current = deepcopy(historical)
    current["manifest_id"] = "image-manifest-current-batch"
    current["manifest_hash"] = "b" * 64
    current["items"] = [
        {
            "item_id": "other-shot-processing",
            "item_type": "shot_keyframe",
            "target_shot_id": "shot-03",
            "state": "processing",
        }
    ]
    current["accepted_graph_snapshots"] = [
        {"version": graph["version"], "graph_digest": graph["graph_digest"]}
    ]
    write_json(image_path, current)
    return historical, graph


def test_stale_video_manifest_rebuilds_from_historical_approved_keyframe_without_dispatch(
    tmp_path,
) -> None:
    client, store, project_id, media = _seed_ready_project(tmp_path)
    _command(client, project_id, {"type": "compile", "idempotency_key": "compile-v1"})
    old_video = deepcopy(load_video_admission_manifest(store, project_id))
    _, graph = _rotate_image_manifest_after_graph_update(store, project_id)
    image_path = store.projects_dir / project_id / "image_admission" / "manifest.json"
    image_before = read_json(image_path)

    state = client.get(f"/projects/{project_id}/m6/video-admission").json()

    assert state["readiness"]["status"] == "stale"
    assert state["readiness"]["prepared_graph_version"] == old_video["source"]["production_graph"]["version"]
    assert state["readiness"]["current_graph_version"] == graph["version"]
    assert state["lineage"]["keyframe_reuse"] == "updated_approved_source"
    assert state["lineage"]["rebuild_allowed"] is True
    assert state["lineage"]["affected_objects"] == ["镜头 01 已批准关键帧"]
    assert state["provider_dispatch_count"] == 0

    body = {
        "command": _reference_video_setup_command({
            "type": "recompile_current",
            "idempotency_key": "recompile-current-v2",
        }),
        "requested_at": REQUESTED_AT,
    }
    preview = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json=body,
    )

    assert preview.status_code == 200, preview.text
    candidate = preview.json()["result"]["manifest"]
    assert candidate["version"] == old_video["version"] + 1
    assert candidate["source"]["production_graph"] == {
        "version": graph["version"],
        "graph_digest": graph["graph_digest"],
    }
    assert candidate["source"]["keyframe"] == {}
    assert [item["image_asset_id"] for item in candidate["source"]["references"]] == [
        media["character"],
        media["scene"],
        media["prop"],
    ]
    assert candidate["item"]["state"] == "planned"
    assert candidate["budget"]["dispatches_reserved"] == 0
    assert candidate["provider_dispatch_count"] == 0
    assert load_video_admission_manifest(store, project_id) == old_video
    assert read_json(image_path) == image_before

    confirmed = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/confirm",
        json={**body, "preview_digest": preview.json()["preview_digest"]},
    )

    assert confirmed.status_code == 200, confirmed.text
    rebuilt = load_video_admission_manifest(store, project_id)
    assert rebuilt == confirmed.json()["result"]["manifest"]
    assert rebuilt["source"]["production_graph"]["version"] == graph["version"]
    assert rebuilt["item"]["state"] == "planned"
    assert rebuilt["budget"] == {
        "dispatches_reserved": 0,
        "remaining_dispatches": 1,
        "hard_ceiling_usd": "2.00",
        "actual_charge_usd": None,
        "actual_charge_verification": "unverified",
    }
    assert rebuilt["provider_dispatch_count"] == 0
    archived = read_json(
        store.projects_dir
        / project_id
        / "video_admission"
        / "history"
        / f"{old_video['manifest_id']}.json"
    )
    assert archived == old_video
    assert read_json(image_path) == image_before

    replay = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/confirm",
        json={**body, "preview_digest": preview.json()["preview_digest"]},
    )
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert load_video_admission_manifest(store, project_id) == rebuilt
    assert read_json(image_path) == image_before


def test_stale_video_rebuild_fails_closed_when_graph_advances_during_confirmation(
    tmp_path,
    monkeypatch,
) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _command(client, project_id, {"type": "compile", "idempotency_key": "compile-v1"})
    old_video = deepcopy(load_video_admission_manifest(store, project_id))
    _rotate_image_manifest_after_graph_update(store, project_id)
    body = {
        "command": _reference_video_setup_command({
            "type": "recompile_current",
            "idempotency_key": "recompile-racing-graph",
        }),
        "requested_at": REQUESTED_AT,
    }
    preview = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json=body,
    )
    assert preview.status_code == 200, preview.text

    from apps.api import runtime_video_admission as module

    original_lock = module._verified_graph_snapshot_lock

    @contextmanager
    def advance_graph_before_snapshot_lock(*args, **kwargs):
        graph_store = ProductionGraphStore(store)
        graph = graph_store.load(project_id)
        graph_store.append(
            project_id,
            expected_version=graph["version"],
            idempotency_key="concurrent-shot-03-approval",
            semantic_digest=canonical_digest({"shot_03": "approved"}),
            events=[
                {
                    "type": "node_upserted",
                    "node": {
                        "node_id": "concurrent-shot-03-artifact",
                        "category": "artifact",
                        "metadata": {
                            "kind": "approved_image",
                            "image_asset_id": "shot-03-approved-image",
                        },
                    },
                }
            ],
        )
        with original_lock(*args, **kwargs):
            yield

    monkeypatch.setattr(
        module,
        "_verified_graph_snapshot_lock",
        advance_graph_before_snapshot_lock,
    )
    confirmed = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/confirm",
        json={**body, "preview_digest": preview.json()["preview_digest"]},
    )

    assert confirmed.status_code == 409
    assert "ProductionGraph changed" in confirmed.text
    assert load_video_admission_manifest(store, project_id) == old_video
    assert not (
        store.projects_dir / project_id / "video_admission" / "history"
    ).exists()
    assert old_video["provider_dispatch_count"] == 0


def test_stale_video_manifest_can_rebuild_reference_conditioned_when_keyframe_lineage_changes(
    tmp_path,
) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _command(client, project_id, {"type": "compile", "idempotency_key": "compile-before-change"})
    old_video = deepcopy(load_video_admission_manifest(store, project_id))
    _, _ = _rotate_image_manifest_after_graph_update(store, project_id)

    state = client.get(f"/projects/{project_id}/m6/video-admission").json()

    assert state["readiness"]["status"] == "stale"
    assert state["lineage"]["status"] == "stale"
    assert state["lineage"]["keyframe_reuse"] == "updated_approved_source"
    assert state["lineage"]["rebuild_allowed"] is True
    assert state["readiness"]["suggested_generation_mode"] == "reference_conditioned"
    response = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": _reference_video_setup_command({
                "type": "recompile_current",
                "idempotency_key": "safe-reference-recompile",
            }),
            "requested_at": REQUESTED_AT,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["result"]["manifest"]["provider_input_contract"]["first_frame"] is None
    assert load_video_admission_manifest(store, project_id) == old_video
    assert not (
        store.projects_dir / project_id / "video_admission" / "history"
    ).exists()


def test_stale_keyframe_does_not_reenable_first_frame_when_graph_shot_changes(
    tmp_path,
) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _command(client, project_id, {"type": "compile", "idempotency_key": "compile-before-graph-shot-change"})
    old_video = deepcopy(load_video_admission_manifest(store, project_id))
    _rotate_image_manifest_after_graph_update(store, project_id)
    graph_store = ProductionGraphStore(store)
    graph = graph_store.load(project_id)
    graph_store.append(
        project_id,
        expected_version=graph["version"],
        idempotency_key="change-canonical-shot-semantics",
        semantic_digest=canonical_digest({"shot": "changed"}),
        events=[
            {
                "type": "node_metadata_updated",
                "node_id": "shot-01",
                "patch": {
                    "blocking": "巡夜人甲离开操作台并走向站台另一端",
                    "camera_movement": "横移跟随人物远离操作台",
                    "narrative_purpose": "转入新的空间调度",
                },
            }
        ],
    )

    state = client.get(f"/projects/{project_id}/m6/video-admission").json()
    assert state["readiness"]["status"] == "stale"
    assert state["readiness"]["suggested_generation_mode"] == "reference_conditioned"
    assert {
        item["mode"]: item["supported"]
        for item in state["readiness"]["generation_modes"]
    } == {
        "reference_conditioned": True,
        "first_frame": False,
        "text_to_video": False,
    }

    first_frame_preview = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": _video_setup_command(
                {
                    "type": "recompile_current",
                    "idempotency_key": "unsafe-first-frame-after-graph-shot-change",
                }
            ),
            "requested_at": REQUESTED_AT,
        },
    )
    assert first_frame_preview.status_code == 422
    assert "首帧图生视频需要明确选择" in first_frame_preview.json()["detail"]["details"]["raw_detail"]

    reference_preview = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": _reference_video_setup_command(
                {
                    "type": "recompile_current",
                    "idempotency_key": "reference-after-graph-shot-change",
                }
            ),
            "requested_at": REQUESTED_AT,
        },
    )
    assert reference_preview.status_code == 200, reference_preview.text
    manifest = reference_preview.json()["result"]["manifest"]
    assert manifest["source"]["keyframe"] == {}
    assert manifest["provider_input_contract"]["first_frame"] is None
    assert manifest["provider_input_contract"]["mode"] == "reference_conditioned"
    assert load_video_admission_manifest(store, project_id) == old_video


def _claim_for_test(
    store: RuntimeStore,
    project_id: str,
    request: VideoGenerationRequest,
    *,
    job_id: str,
) -> dict:
    claim_video_admission_dispatch(store, project_id, request, job_id=job_id)
    mark_video_admission_network_started(store, project_id, job_id=job_id)
    return mark_video_admission_task_recorded(
        store,
        project_id,
        job_id=job_id,
        provider_task_fingerprint="fixture-task-fingerprint",
    )


def _record_candidate_for_test(
    client: TestClient,
    store: RuntimeStore,
    project_id: str,
    *,
    job_id: str,
) -> dict:
    _command(
        client,
        project_id,
        {
            "type": "record_job",
            "idempotency_key": f"record-{job_id}",
            "provider_job_id": job_id,
        },
    )
    candidate_path = store.run_dir(project_id, job_id) / "video_candidates" / "candidate_001.mp4"
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(VIDEO_CANDIDATE_BYTES)
    data = candidate_path.read_bytes()
    candidate = {
        "job_id": job_id,
        "candidate_id": "candidate_001",
        "preview_url": (
            f"/projects/{project_id}/video-generations/"
            f"{job_id}/candidates/candidate_001/preview"
        ),
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_count": len(data),
        "usage_evidence": {
            "provider_reported_usage": True,
            "output_tokens": 1234,
            "provider_reported_cost": False,
            "actual_charge_verification": "unverified",
        },
    }
    return _command(
        client,
        project_id,
        {
            "type": "record_candidate",
            "idempotency_key": f"candidate-{job_id}",
            "candidate": candidate,
        },
    )["result"]["manifest"]


def test_video_admission_locks_exact_non_fast_single_dispatch_contract(tmp_path) -> None:
    client, store, project_id, media = _seed_ready_project(tmp_path)

    readiness = client.get(f"/projects/{project_id}/m6/video-admission")
    assert readiness.status_code == 200
    assert readiness.json()["readiness"]["status"] == "ready"
    assert readiness.json()["readiness"]["shot_id"] == "shot-01"
    assert readiness.json()["provider_dispatch_count"] == 0

    preview = _command(
        client,
        project_id,
        {"type": "compile", "idempotency_key": "compile-video"},
        confirm=False,
    )
    assert load_video_admission_manifest(store, project_id) == {}
    manifest = preview["result"]["manifest"]
    assert manifest["provider_contract"] == {
        "service_id": SERVICE_ID,
        "model": MODEL_ID,
        "model_variant": "non_fast",
        "create_endpoint": CREATE_ENDPOINT,
        "query_endpoint": QUERY_ENDPOINT,
        "resolution": RESOLUTION,
        "duration_sec": DURATION_SEC,
        "candidate_count": 1,
        "max_dispatches": MAX_DISPATCHES,
        "auto_retry": AUTO_RETRY,
    }
    assert manifest["budget_contract"] == {
        "currency": "USD",
        "hard_ceiling_usd": f"{HARD_BUDGET_USD:.2f}",
        "classification": "program_stop_ceiling_not_provider_enforced_estimate_or_actual",
        "billing_mode": "provider_output_tokens",
        "provider_enforced_cost_cap": False,
        "program_stop_ceiling_only": True,
        "pricing_verification_state": "verified",
        "worst_case_output_tokens": 100,
        "worst_case_cost_usd": "1.00",
        "actual_charge_usd": None,
        "actual_charge_verification": "unverified",
    }
    assert manifest["source"]["keyframe"]["image_asset_id"] == media["keyframe"]
    assert {item["image_asset_id"] for item in manifest["source"]["references"]} == {
        media["character"],
        media["scene"],
        media["prop"],
    }
    prompt = manifest["source"]["prompt_contract"]["provider_prompt"]
    for value in (
        "巡夜人甲",
        "北侧检修站",
        "六角校准器",
        "缓慢向前推进",
        TEMPORAL_STAGING["narrative_purpose"],
    ):
        assert value in prompt
    assert manifest["source"]["prompt_contract"]["keyword_rewrite"] is False
    assert manifest["source"]["prompt_contract"]["sample_fallback"] is False
    assert manifest["provider_dispatch_count"] == 0

    confirmed = _command(
        client,
        project_id,
        {"type": "compile", "idempotency_key": "compile-video"},
    )
    assert confirmed["result"]["manifest"]["manifest_hash"] == manifest["manifest_hash"]
    assert confirmed["provider_dispatch_count"] == 0


def test_video_admission_reservation_is_idempotent_and_dispatch_claim_is_exactly_once(tmp_path) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _command(client, project_id, {"type": "compile", "idempotency_key": "compile"})
    reserved = _command(
        client,
        project_id,
        {"type": "reserve_dispatch", "idempotency_key": "reserve-once"},
    )["result"]["manifest"]
    replay = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/confirm",
        json={
            "command": {
                "type": "reserve_dispatch",
                "idempotency_key": "reserve-once",
            },
            "requested_at": REQUESTED_AT,
            "preview_digest": "",
        },
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent_replay"] is True
    assert (
        replay.json()["result"]["manifest"]["item"]["reservation_token"]
        == reserved["item"]["reservation_token"]
    )
    assert reserved["budget"]["dispatches_reserved"] == 1
    assert reserved["budget"]["remaining_dispatches"] == 0
    assert reserved["provider_dispatch_count"] == 0

    conflicting = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": {
                "type": "reserve_dispatch",
                "idempotency_key": "reserve-different",
            },
            "requested_at": REQUESTED_AT,
        },
    )
    assert conflicting.status_code == 422

    request = VideoGenerationRequest(
        **video_admission_generation_request(reserved, generated_at=REQUESTED_AT)
    )
    assert enforce_video_admission_request(store, project_id, request)["manifest_hash"] == reserved["manifest_hash"]
    claimed = claim_video_admission_dispatch(
        store,
        project_id,
        request,
        job_id="video-job-001",
    )
    replayed_claim = claim_video_admission_dispatch(
        store,
        project_id,
        request,
        job_id="video-job-001",
    )
    assert claimed["provider_dispatch_count"] == replayed_claim["provider_dispatch_count"] == 0
    assert claimed["item"]["network_disposition"] == "never_started"
    ambiguous = mark_video_admission_network_started(
        store,
        project_id,
        job_id="video-job-001",
    )
    assert ambiguous["provider_dispatch_count"] == 1
    assert ambiguous["item"]["state"] == "reconcile_required"
    assert ambiguous["item"]["network_disposition"] == "may_have_dispatched"
    submitted = mark_video_admission_task_recorded(
        store,
        project_id,
        job_id="video-job-001",
        provider_task_fingerprint="safe-fingerprint",
    )
    assert submitted["provider_dispatch_count"] == 1
    assert submitted["item"]["state"] == "processing"
    assert submitted["item"]["network_disposition"] == "dispatched_with_task_identity"
    with pytest.raises(ValueError, match="already claimed"):
        claim_video_admission_dispatch(
            store,
            project_id,
            request,
            job_id="video-job-002",
        )


def test_video_admission_supports_two_explicit_shot_lanes_without_overwrite(tmp_path) -> None:
    client, store, project_id, _ = _seed_ready_project(
        tmp_path,
        strict_first_frame_required=False,
    )
    _add_second_ready_shot(store, project_id)

    lane_1 = _lane_command(
        client,
        project_id,
        "shot-01",
        {
            "type": "compile",
            "idempotency_key": "lane-shot-01",
            "shot_id": "shot-01",
        },
    )["result"]["manifest"]
    lane_2 = _lane_command(
        client,
        project_id,
        "shot-02",
        {
            "type": "compile",
            "idempotency_key": "lane-shot-02",
            "shot_id": "shot-02",
        },
    )["result"]["manifest"]
    assert lane_1["source"]["shot"]["shot_id"] == "shot-01"
    assert lane_2["source"]["shot"]["shot_id"] == "shot-02"
    assert lane_1["manifest_id"] != lane_2["manifest_id"]
    assert load_video_admission_manifest(store, project_id) == {}

    reserved_1 = _lane_command(
        client,
        project_id,
        "shot-01",
        {"type": "reserve_dispatch", "idempotency_key": "reserve-lane-01"},
    )["result"]["manifest"]
    reserved_2 = _lane_command(
        client,
        project_id,
        "shot-02",
        {"type": "reserve_dispatch", "idempotency_key": "reserve-lane-02"},
    )["result"]["manifest"]
    lanes = client.get(f"/projects/{project_id}/m6/video-admission/lanes").json()
    assert lanes["capacity"] == {
        "max_active_lanes": MAX_ACTIVE_VIDEO_LANES,
        "active_lanes": 2,
        "available_lanes": MAX_ACTIVE_VIDEO_LANES - 2,
    }
    assert {
        (lane["shot_id"], lane["item_state"], lane["lane_active"])
        for lane in lanes["lanes"]
    } == {
        ("shot-01", "reserved", True),
        ("shot-02", "reserved", True),
    }

    request_1 = VideoGenerationRequest(
        **video_admission_generation_request(reserved_1, generated_at=REQUESTED_AT)
    )
    request_2 = VideoGenerationRequest(
        **video_admission_generation_request(reserved_2, generated_at=REQUESTED_AT)
    )
    assert enforce_video_admission_request(store, project_id, request_1)["manifest_id"] == reserved_1["manifest_id"]
    assert enforce_video_admission_request(store, project_id, request_2)["manifest_id"] == reserved_2["manifest_id"]
    claim_video_admission_dispatch(store, project_id, request_1, job_id="video-job-lane-01")
    claim_video_admission_dispatch(store, project_id, request_2, job_id="video-job-lane-02")
    mark_video_admission_network_started(store, project_id, job_id="video-job-lane-01")
    mark_video_admission_network_started(store, project_id, job_id="video-job-lane-02")

    updated_1 = load_video_admission_manifest(store, project_id, shot_id="shot-01")
    updated_2 = load_video_admission_manifest(store, project_id, shot_id="shot-02")
    assert updated_1["item"]["provider_job_id"] == "video-job-lane-01"
    assert updated_1["item"]["state"] == "reconcile_required"
    assert updated_2["item"]["provider_job_id"] == "video-job-lane-02"
    assert updated_2["item"]["state"] == "reconcile_required"


def test_video_admission_blocks_third_active_lane_before_dispatch(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_VIDEO_ADMISSION_MAX_ACTIVE_LANES", "2")
    client, store, project_id, _ = _seed_ready_project(
        tmp_path,
        strict_first_frame_required=False,
    )
    _add_second_ready_shot(store, project_id)
    _add_ready_shot(store, project_id, "shot-03", 3)

    for shot_id in ("shot-01", "shot-02"):
        _lane_command(
            client,
            project_id,
            shot_id,
            {
                "type": "compile",
                "idempotency_key": f"compile-{shot_id}",
                "shot_id": shot_id,
            },
        )
        _lane_command(
            client,
            project_id,
            shot_id,
            {"type": "reserve_dispatch", "idempotency_key": f"reserve-{shot_id}"},
        )

    _lane_command(
        client,
        project_id,
        "shot-03",
        {
            "type": "compile",
            "idempotency_key": "compile-shot-03",
            "shot_id": "shot-03",
        },
    )
    blocked = client.post(
        f"/projects/{project_id}/m6/video-admission/lanes/shot-03/commands/preview",
        json={
            "command": {
                "type": "reserve_dispatch",
                "idempotency_key": "reserve-shot-03",
            },
            "requested_at": REQUESTED_AT,
        },
    )
    assert blocked.status_code == 422
    assert "2-lane active dispatch limit" in blocked.json()["detail"]["details"]["raw_detail"]
    assert load_video_admission_manifest(store, project_id, shot_id="shot-03")[
        "provider_dispatch_count"
    ] == 0


def test_video_admission_rejects_structured_post_only_shot(tmp_path) -> None:
    client, store, project_id, _ = _seed_ready_project(
        tmp_path,
        strict_first_frame_required=False,
    )
    _add_ready_shot(
        store,
        project_id,
        "shot-post-only",
        31,
        metadata={"video_dispatch_policy": "post_only"},
    )

    response = client.post(
        f"/projects/{project_id}/m6/video-admission/lanes/shot-post-only/commands/preview",
        json={
            "command": _reference_video_setup_command(
                {
                    "type": "compile",
                    "idempotency_key": "compile-post-only",
                    "shot_id": "shot-post-only",
                }
            ),
            "requested_at": REQUESTED_AT,
        },
    )
    assert response.status_code == 422
    assert "post-only" in response.json()["detail"]["details"]["raw_detail"]


def _stub_video_probe(monkeypatch) -> None:
    monkeypatch.setattr(
        "apps.api.runtime_video_admission.probe_video_metadata",
        lambda _path: SimpleNamespace(
            probe_status="succeeded",
            width=1280,
            height=720,
            duration_sec=6.0,
            codec="mpeg4",
        ),
    )


def test_video_candidate_requires_human_approval_before_graph_writeback(
    tmp_path,
    monkeypatch,
) -> None:
    _stub_video_probe(monkeypatch)
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    graph_store = ProductionGraphStore(store)
    initial_graph = graph_store.load(project_id)
    _command(client, project_id, {"type": "compile", "idempotency_key": "compile"})
    reserved = _command(
        client,
        project_id,
        {"type": "reserve_dispatch", "idempotency_key": "reserve"},
    )["result"]["manifest"]
    request = VideoGenerationRequest(
        **video_admission_generation_request(reserved, generated_at=REQUESTED_AT)
    )
    _claim_for_test(store, project_id, request, job_id="video-job-001")
    _command(
        client,
        project_id,
        {
            "type": "record_job",
            "idempotency_key": "record-job",
            "provider_job_id": "video-job-001",
        },
    )
    candidate_path = (
        store.run_dir(project_id, "video-job-001")
        / "video_candidates"
        / "candidate_001.mp4"
    )
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(VIDEO_CANDIDATE_BYTES)
    candidate_bytes = candidate_path.read_bytes()
    candidate = {
        "job_id": "video-job-001",
        "candidate_id": "candidate_001",
        "preview_url": (
            f"/projects/{project_id}/video-generations/"
            "video-job-001/candidates/candidate_001/preview"
        ),
        "sha256": hashlib.sha256(candidate_bytes).hexdigest(),
        "byte_count": len(candidate_bytes),
    }
    recorded = _command(
        client,
        project_id,
        {
            "type": "record_candidate",
            "idempotency_key": "record-candidate",
            "candidate": candidate,
        },
    )["result"]["manifest"]
    assert recorded["item"]["state"] == "candidate"
    assert recorded["item"]["candidate"]["technical_qa"] == {
        "status": "pass",
        "container": "video/mp4",
        "width": 1280,
        "height": 720,
        "duration_sec": 6.0,
        "codec": "mpeg4",
        "decode_probe": "passed",
    }
    assert graph_store.load(project_id)["version"] == initial_graph["version"]

    preview = _command(
        client,
        project_id,
        {"type": "approve", "idempotency_key": "approve-video"},
        confirm=False,
    )
    assert preview["result"]["graph_mutation"] == 0
    assert graph_store.load(project_id)["version"] == initial_graph["version"]
    approved = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/confirm",
        json={
            "command": {"type": "approve", "idempotency_key": "approve-video"},
            "requested_at": REQUESTED_AT,
            "preview_digest": preview["preview_digest"],
        },
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["result"]["graph_mutation"] == 1
    graph = graph_store.load(project_id)
    approved_videos = [
        item
        for item in graph["nodes"].values()
        if item.get("metadata", {}).get("kind") == "approved_video"
    ]
    assert len(approved_videos) == 1
    assert approved_videos[0]["metadata"]["model"] == MODEL_ID
    assert approved_videos[0]["metadata"]["source_shot_id"] == approved.json()[
        "result"
    ]["manifest"]["source"]["shot"]["shot_id"]
    assert approved_videos[0]["metadata"]["actual_usd"] is None
    assert approved_videos[0]["metadata"]["mime_type"] == "video/mp4"
    assert approved_videos[0]["metadata"]["width"] == 1280
    assert approved_videos[0]["metadata"]["height"] == 720
    assert approved_videos[0]["metadata"]["codec"] == "mpeg4"
    assert approved_videos[0]["metadata"]["generation_mode"] == "first_frame"
    assert approved_videos[0]["metadata"]["first_frame_count"] == 1
    assert approved_videos[0]["metadata"]["reference_image_count"] == 0
    assert approved_videos[0]["metadata"]["temporal_staging"] == TEMPORAL_STAGING
    approved_manifest = approved.json()["result"]["manifest"]
    readiness = client.get(f"/projects/{project_id}/m6/video-admission").json()
    assert readiness["readiness"]["comparison_round_allowed"] is True
    assert readiness["manifest"] == approved_manifest

    comparison_command = {
        "type": "create_comparison_round",
        "idempotency_key": "reference-comparison",
        "generation_mode": "reference_conditioned",
        "selection_reason": "让批准资产约束身份与连续性，不将关键帧锁为首帧。",
        "temporal_staging": TEMPORAL_STAGING,
    }
    comparison_body = {
        "command": comparison_command,
        "requested_at": REQUESTED_AT,
    }
    comparison = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json=comparison_body,
    )
    assert comparison.status_code == 200, comparison.text
    comparison_manifest = comparison.json()["result"]["manifest"]
    assert comparison_manifest["round_contract"] == {
        "kind": "independent_comparison",
        "prior_manifest_id": approved_manifest["manifest_id"],
        "prior_manifest_hash": approved_manifest["manifest_hash"],
        "prior_round_preserved": True,
        "prior_round_replay_allowed": False,
        "prior_approved_result_immutable": True,
    }
    assert comparison_manifest["provider_input_contract"]["mode"] == (
        "reference_conditioned"
    )
    assert comparison_manifest["provider_input_contract"]["first_frame"] is None
    assert len(comparison_manifest["provider_input_contract"]["reference_images"]) == 3
    assert comparison_manifest["provider_dispatch_count"] == 0
    assert load_video_admission_manifest(store, project_id) == approved_manifest
    graph_before_comparison = graph_store.load(project_id)

    comparison_confirmed = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/confirm",
        json={
            **comparison_body,
            "preview_digest": comparison.json()["preview_digest"],
        },
    )
    assert comparison_confirmed.status_code == 200, comparison_confirmed.text
    assert graph_store.load(project_id) == graph_before_comparison
    assert comparison_confirmed.json()["provider_dispatch_count"] == 0
    archived_approved = read_json(
        store.projects_dir
        / project_id
        / "video_admission"
        / "history"
        / f"{approved_manifest['manifest_id']}.json"
    )
    assert archived_approved == approved_manifest

    workspace = client.get(
        f"/projects/{project_id}/m5/sequence-workspace"
    ).json()
    approved_media = workspace["sequence"]["approved_media"]
    approved_video = next(
        item for item in approved_media if item["media_kind"] == "video"
    )
    assert approved_video == {
        "media_node_id": approved.json()["result"]["manifest"]["item"]["promotion"][
            "production_graph_node_id"
        ],
        "media_kind": "video",
        "preview_url": (
            f"/projects/{project_id}/approved-video-assets/"
            f"{approved.json()['result']['manifest']['item']['promotion']['production_graph_node_id']}/preview"
        ),
        "mime_type": "video/mp4",
        "container": "video/mp4",
        "width": 1280,
        "height": 720,
        "duration_sec": 6.0,
        "codec": "mpeg4",
        "model": MODEL_ID,
        "resolution": RESOLUTION,
        "generation_mode": "first_frame",
        "approval_graph_version": graph["version"],
        "lineage": {
            "source_kind": "approved_video_receipt",
            "target_relation": "approved_video",
        },
        "target_node_ids": [approved.json()["result"]["manifest"]["source"]["shot"]["shot_id"]],
    }
    assert workspace["provider_dispatch_count"] == 0
    assert workspace["cost_usd"] == 0
    assert client.get(approved_video["preview_url"]).status_code == 200

    candidate_path.write_bytes(b"tampered-after-approval")
    assert client.get(approved_video["preview_url"]).status_code == 404
    tampered_workspace = client.get(
        f"/projects/{project_id}/m5/sequence-workspace"
    ).json()
    assert not any(
        item["media_kind"] == "video"
        for item in tampered_workspace["sequence"]["approved_media"]
    )
    assert graph_store.load(project_id)["version"] == graph["version"]


def test_typed_media_projection_keeps_images_and_multiple_approved_videos_separate(
    tmp_path,
) -> None:
    store = RuntimeStore(tmp_path / "runtime")
    project_id = "typed-media-projection"
    nodes: dict[str, dict] = {
        "shot-a": {"category": "unit", "state": "active", "metadata": {}},
        "shot-b": {"category": "unit", "state": "active", "metadata": {}},
        "image-node": {
            "category": "artifact",
            "state": "active",
            "metadata": {
                "kind": "approved_image",
                "image_asset_id": "image-safe",
                "width": 960,
                "height": 1280,
                "approval_graph_version": 4,
            },
        },
    }
    relations = [
        {
            "from_id": "shot-a",
            "to_id": "image-node",
            "relation_type": "approved_image",
        },
    ]
    admission_dir = store.projects_dir / project_id / "video_admission"
    history_dir = admission_dir / "history"
    for index, shot_id in enumerate(("shot-a", "shot-b"), start=1):
        manifest_id = f"video-manifest-{index}"
        manifest_hash = str(index) * 64
        job_id = f"video-job-{index}"
        candidate_id = f"candidate_{index:03d}"
        node_id = f"video-node-{index}"
        video_path = (
            store.run_dir(project_id, job_id)
            / "video_candidates"
            / f"{candidate_id}.mp4"
        )
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(f"video-{index}".encode())
        manifest = {
            "manifest_id": manifest_id,
            "manifest_hash": manifest_hash,
            "status": "locked",
            "source": {
                "shot": {
                    "shot_id": shot_id,
                    "label": f"Shot {index}",
                },
            },
            "item": {
                "state": "approved",
                "candidate": {
                    "job_id": job_id,
                    "candidate_id": candidate_id,
                    "sha256": hashlib.sha256(video_path.read_bytes()).hexdigest(),
                    "byte_count": video_path.stat().st_size,
                    "technical_qa": {
                        "status": "pass",
                        "container": "video/mp4",
                        "width": 1280,
                        "height": 720,
                        "duration_sec": 5.0 + index,
                        "codec": "h264",
                    },
                },
                "promotion": {
                    "production_graph_node_id": node_id,
                    "graph_version": 4 + index,
                },
            },
        }
        manifest_path = (
            admission_dir / "manifest.json"
            if index == 2
            else history_dir / f"{manifest_id}.json"
        )
        write_json(manifest_path, manifest)
        nodes[node_id] = {
            "category": "artifact",
            "state": "active",
            "metadata": {
                "kind": "approved_video",
                "manifest_id": manifest_id,
                "manifest_hash": manifest_hash,
                "job_id": job_id,
                "candidate_id": candidate_id,
                "sha256": manifest["item"]["candidate"]["sha256"],
                "byte_count": video_path.stat().st_size,
                "model": MODEL_ID,
                "resolution": RESOLUTION,
                "duration_sec": 5 + index,
            },
        }
        relations.append(
            {
                "from_id": shot_id,
                "to_id": node_id,
                "relation_type": "approved_video",
            }
        )

    projection = _approved_media_projection(
        nodes,
        relations,
        project_id=project_id,
        store=store,
    )
    assert [(item["media_kind"], item["target_node_ids"]) for item in projection] == [
        ("image", ["shot-a"]),
        ("video", ["shot-a"]),
        ("video", ["shot-b"]),
    ]
    assert [item["duration_sec"] for item in projection if item["media_kind"] == "video"] == [
        6.0,
        7.0,
    ]
    assert all(
        item["preview_url"].startswith(
            f"/projects/{project_id}/approved-video-assets/"
        )
        for item in projection
        if item["media_kind"] == "video"
    )

    first_video = next(
        item
        for item in projection
        if item["media_kind"] == "video"
        and item["target_node_ids"] == ["shot-a"]
    )
    first_relation = next(
        relation
        for relation in relations
        if relation["to_id"] == "video-node-1"
    )
    first_relation["from_id"] = "shot-b"
    wrong_shot_projection = _approved_media_projection(
        nodes,
        relations,
        project_id=project_id,
        store=store,
    )
    assert [
        (item["media_kind"], item["target_node_ids"])
        for item in wrong_shot_projection
    ] == [
        ("image", ["shot-a"]),
        ("video", ["shot-b"]),
    ]
    first_relation["from_id"] = "shot-a"

    tampered_path = (
        store.run_dir(project_id, "video-job-1")
        / "video_candidates"
        / "candidate_001.mp4"
    )
    tampered_path.write_bytes(b"tampered-approved-video")
    tampered_projection = _approved_media_projection(
        nodes,
        relations,
        project_id=project_id,
        store=store,
    )
    assert first_video not in tampered_projection
    assert [
        (item["media_kind"], item["target_node_ids"])
        for item in tampered_projection
    ] == [
        ("image", ["shot-a"]),
        ("video", ["shot-b"]),
    ]

    legacy_projection = _approved_media_projection(
        nodes,
        relations,
        project_id=project_id,
    )
    assert [item["media_kind"] for item in legacy_projection] == ["image"]


def test_video_approval_reconciles_graph_append_after_ledger_write_crash(
    tmp_path,
    monkeypatch,
) -> None:
    _stub_video_probe(monkeypatch)
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    graph_store = ProductionGraphStore(store)
    _command(client, project_id, {"type": "compile", "idempotency_key": "compile-crash"})
    reserved = _command(
        client,
        project_id,
        {"type": "reserve_dispatch", "idempotency_key": "reserve-crash"},
    )["result"]["manifest"]
    request = VideoGenerationRequest(
        **video_admission_generation_request(reserved, generated_at=REQUESTED_AT)
    )
    _claim_for_test(store, project_id, request, job_id="video-job-crash")
    _record_candidate_for_test(
        client,
        store,
        project_id,
        job_id="video-job-crash",
    )
    preview = _command(
        client,
        project_id,
        {"type": "approve", "idempotency_key": "approve-crash"},
        confirm=False,
    )
    body = {
        "command": {"type": "approve", "idempotency_key": "approve-crash"},
        "requested_at": REQUESTED_AT,
        "preview_digest": preview["preview_digest"],
    }
    real_write_json = write_json
    failed = False

    def fail_manifest_once(path, payload):
        nonlocal failed
        if (
            path.name == "manifest.json"
            and path.parent.name == "video_admission"
            and not failed
        ):
            failed = True
            raise OSError("simulated manifest write failure")
        return real_write_json(path, payload)

    monkeypatch.setattr(
        "apps.api.runtime_video_admission.write_json",
        fail_manifest_once,
    )
    with pytest.raises(OSError, match="simulated manifest"):
        client.post(
            f"/projects/{project_id}/m6/video-admission/commands/confirm",
            json=body,
        )
    graph_after_append = graph_store.load(project_id)
    assert len([
        node for node in graph_after_append["nodes"].values()
        if node.get("metadata", {}).get("kind") == "approved_video"
    ]) == 1
    assert load_video_admission_manifest(store, project_id)["item"]["state"] == "candidate"

    refreshed_preview = _command(
        client,
        project_id,
        {"type": "approve", "idempotency_key": "approve-after-refresh"},
        confirm=False,
    )
    assert refreshed_preview["result"]["manifest"]["item"]["state"] == "approved"
    replay = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/confirm",
        json={
            "command": {
                "type": "approve",
                "idempotency_key": "approve-after-refresh",
            },
            "requested_at": REQUESTED_AT,
            "preview_digest": refreshed_preview["preview_digest"],
        },
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent_replay"] is True
    assert replay.json()["result"]["graph_mutation"] == 0
    repaired = load_video_admission_manifest(store, project_id)
    assert repaired["item"]["state"] == "approved"
    assert repaired["item"]["candidate"]["usage_evidence"]["output_tokens"] == 1234
    assert graph_store.load(project_id)["version"] == graph_after_append["version"]


def test_video_admission_fails_closed_on_reference_and_graph_drift(tmp_path) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _command(client, project_id, {"type": "compile", "idempotency_key": "compile"})
    manifest = load_video_admission_manifest(store, project_id)
    request_payload = video_admission_generation_request(manifest, generated_at=REQUESTED_AT)
    request_payload["reference_image_asset_ids"] = ["unapproved-reference"]
    with pytest.raises(ValueError, match="reference_image_asset_ids"):
        enforce_video_admission_request(
            store,
            project_id,
            VideoGenerationRequest(**request_payload),
        )

    graph_store = ProductionGraphStore(store)
    graph = graph_store.load(project_id)
    graph_store.append(
        project_id,
        expected_version=graph["version"],
        idempotency_key="concurrent-graph-change",
        semantic_digest=canonical_digest({"change": "concurrent"}),
        events=[
            {
                "type": "node_upserted",
                "node": {
                    "node_id": "concurrent-node",
                    "category": "artifact",
                    "metadata": {"kind": "diagnostic"},
                },
            }
        ],
    )
    response = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": {
                "type": "reserve_dispatch",
                "idempotency_key": "reserve-after-drift",
            },
            "requested_at": REQUESTED_AT,
        },
    )
    assert response.status_code == 422
    assert "ProductionGraph source is stale" in response.text


def test_rejected_video_round_creates_one_independent_first_frame_round_without_provider(
    tmp_path,
) -> None:
    client, store, project_id, media = _seed_ready_project(tmp_path)
    _command(client, project_id, {"type": "compile", "idempotency_key": "compile-old"})
    _command(client, project_id, {"type": "reserve_dispatch", "idempotency_key": "reserve-old"})
    old_request = VideoGenerationRequest(
        **video_admission_generation_request(
            load_video_admission_manifest(store, project_id),
            generated_at=REQUESTED_AT,
        )
    )
    claim_video_admission_dispatch(
        store,
        project_id,
        old_request,
        job_id="provider-job-rejected",
    )
    mark_video_admission_network_started(
        store,
        project_id,
        job_id="provider-job-rejected",
    )
    old_manifest = deepcopy(load_video_admission_manifest(store, project_id))
    safe_path = (
        store.run_dir(project_id, "provider-job-rejected")
        / "video_generation_safe_manifest.json"
    )
    write_json(
        safe_path,
        {
            "schema_version": "afs_video_generation_safe_manifest.v0.1",
            "status": "reconcile_required",
            "project_id": project_id,
            "provider_calls_started": True,
            "outputs": [],
            "blocks": [
                {
                    "block_id": "remote_video_provider_not_ready",
                    "provider_http_status": 400,
                    "provider_error_code": "fail_to_fetch_task",
                    "provider_error_message": "InvalidParameter",
                    "provider_error_stage": "submit_http_error",
                    "provider_raw_response_stored": False,
                }
            ],
        },
    )

    readiness = client.get(f"/projects/{project_id}/m6/video-admission").json()
    assert readiness["readiness"]["new_round_allowed"] is True
    assert readiness["manifest"] == old_manifest

    body = {
        "command": _video_setup_command({
            "type": "create_new_round",
            "idempotency_key": "new-independent-round",
        }),
        "requested_at": REQUESTED_AT,
    }
    preview = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json=body,
    )
    assert preview.status_code == 200, preview.text
    candidate = preview.json()["result"]["manifest"]
    assert candidate["version"] == old_manifest["version"] + 1
    assert candidate["round_contract"]["kind"] == "independent_after_provider_rejection"
    assert candidate["round_contract"]["prior_round_preserved"] is True
    assert candidate["round_contract"]["prior_round_replay_allowed"] is False
    assert candidate["provider_input_contract"]["mode"] == "first_frame"
    assert candidate["provider_input_contract"]["first_frame"]["image_asset_id"] == media["keyframe"]
    assert candidate["provider_input_contract"]["last_frame"] is None
    assert candidate["provider_input_contract"]["reference_images"] == []
    assert candidate["provider_input_contract"]["excluded_grounding_reference_count"] == 3
    assert candidate["budget"]["remaining_dispatches"] == 1
    assert candidate["provider_dispatch_count"] == 0
    assert load_video_admission_manifest(store, project_id) == old_manifest

    confirmed = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/confirm",
        json={**body, "preview_digest": preview.json()["preview_digest"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    active = load_video_admission_manifest(store, project_id)
    assert active == confirmed.json()["result"]["manifest"]
    assert active["item"]["state"] == "planned"
    assert active["provider_dispatch_count"] == 0
    request = video_admission_generation_request(
        {
            **active,
            "item": {**active["item"], "state": "reserved"},
        },
        generated_at=REQUESTED_AT,
    )
    assert request["reference_image_asset_ids"] == []
    archived = read_json(
        store.projects_dir
        / project_id
        / "video_admission"
        / "history"
        / f"{old_manifest['manifest_id']}.json"
    )
    assert archived == old_manifest
    assert read_json(safe_path)["provider_calls_started"] is True

    replay = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/confirm",
        json={**body, "preview_digest": preview.json()["preview_digest"]},
    )
    assert replay.status_code == 200
    assert replay.json()["idempotent_replay"] is True
    assert load_video_admission_manifest(store, project_id) == active

    duplicate = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": {
                "type": "create_new_round",
                "idempotency_key": "different-new-round",
            },
            "requested_at": REQUESTED_AT,
        },
    )
    assert duplicate.status_code == 422
    assert load_video_admission_manifest(store, project_id) == active


def test_terminal_video_round_creates_explicit_next_shot_without_provider(
    tmp_path,
) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _add_second_ready_shot(store, project_id)
    _command(
        client,
        project_id,
        {
            "type": "compile",
            "idempotency_key": "compile-shot-01",
            "shot_id": "shot-01",
            "generation_mode": "reference_conditioned",
            "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
        },
    )
    planned = load_video_admission_manifest(store, project_id)
    premature = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": _reference_video_setup_command(
                {
                    "type": "create_next_shot",
                    "idempotency_key": "premature-next-shot",
                    "shot_id": "shot-02",
                }
            ),
            "requested_at": REQUESTED_AT,
        },
    )
    assert premature.status_code == 422
    assert load_video_admission_manifest(store, project_id) == planned

    reserved = _command(
        client,
        project_id,
        {"type": "reserve_dispatch", "idempotency_key": "reserve-shot-01"},
    )["result"]["manifest"]
    request = VideoGenerationRequest(
        **video_admission_generation_request(reserved, generated_at=REQUESTED_AT)
    )
    _claim_for_test(store, project_id, request, job_id="video-job-shot-01")
    failed = _command(
        client,
        project_id,
        {
            "type": "record_failure",
            "idempotency_key": "fail-shot-01",
            "error_category": "provider_failed",
        },
    )["result"]["manifest"]
    same_shot = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": _reference_video_setup_command(
                {
                    "type": "create_next_shot",
                    "idempotency_key": "next-same-shot",
                    "shot_id": "shot-01",
                }
            ),
            "requested_at": REQUESTED_AT,
        },
    )
    assert same_shot.status_code == 422
    assert load_video_admission_manifest(store, project_id) == failed

    body = {
        "command": _reference_video_setup_command(
            {
                "type": "create_next_shot",
                "idempotency_key": "next-shot-02",
                "shot_id": "shot-02",
            }
        ),
        "requested_at": REQUESTED_AT,
    }
    preview = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json=body,
    )
    assert preview.status_code == 200, preview.text
    candidate = preview.json()["result"]["manifest"]
    assert candidate["source"]["shot"]["shot_id"] == "shot-02"
    assert candidate["round_contract"] == {
        "kind": "next_shot",
        "prior_manifest_id": failed["manifest_id"],
        "prior_manifest_hash": failed["manifest_hash"],
        "prior_shot_id": "shot-01",
        "next_shot_id": "shot-02",
        "prior_round_preserved": True,
        "prior_round_replay_allowed": False,
    }
    assert candidate["provider_contract"]["max_dispatches"] == MAX_DISPATCHES
    assert candidate["provider_contract"]["auto_retry"] == AUTO_RETRY
    assert candidate["provider_dispatch_count"] == 0
    assert load_video_admission_manifest(store, project_id) == failed

    confirmed = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/confirm",
        json={**body, "preview_digest": preview.json()["preview_digest"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    active = load_video_admission_manifest(store, project_id)
    assert active == confirmed.json()["result"]["manifest"]
    assert active["source"]["shot"]["shot_id"] == "shot-02"
    assert active["provider_dispatch_count"] == 0
    readiness = client.get(f"/projects/{project_id}/m6/video-admission")
    assert readiness.status_code == 200
    assert readiness.json()["readiness"]["status"] == "ready"
    assert readiness.json()["readiness"]["shot_id"] == "shot-02"
    archived = read_json(
        store.projects_dir
        / project_id
        / "video_admission"
        / "history"
        / f"{failed['manifest_id']}.json"
    )
    assert archived == failed


def test_same_shot_new_round_preserves_non_first_shot_without_provider(
    tmp_path,
) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _add_second_ready_shot(store, project_id)
    _command(
        client,
        project_id,
        {
            "type": "compile",
            "idempotency_key": "compile-shot-02",
            "shot_id": "shot-02",
            "generation_mode": "reference_conditioned",
            "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
        },
    )
    reserved = _command(
        client,
        project_id,
        {"type": "reserve_dispatch", "idempotency_key": "reserve-shot-02"},
    )["result"]["manifest"]
    request = VideoGenerationRequest(
        **video_admission_generation_request(reserved, generated_at=REQUESTED_AT)
    )
    claim_video_admission_dispatch(
        store,
        project_id,
        request,
        job_id="provider-job-rejected-shot-02",
    )
    mark_video_admission_network_started(
        store,
        project_id,
        job_id="provider-job-rejected-shot-02",
    )
    old_manifest = deepcopy(load_video_admission_manifest(store, project_id))
    safe_path = (
        store.run_dir(project_id, "provider-job-rejected-shot-02")
        / "video_generation_safe_manifest.json"
    )
    write_json(
        safe_path,
        {
            "schema_version": "afs_video_generation_safe_manifest.v0.1",
            "status": "reconcile_required",
            "project_id": project_id,
            "provider_calls_started": True,
            "outputs": [],
            "blocks": [
                {
                    "block_id": "remote_video_provider_not_ready",
                    "provider_http_status": 400,
                    "provider_error_code": "InvalidParameter",
                    "provider_error_message": "InvalidParameter",
                    "provider_raw_response_stored": False,
                }
            ],
        },
    )

    preview = _command(
        client,
        project_id,
        {
            "type": "create_new_round",
            "idempotency_key": "same-shot-new-round",
            "generation_mode": "reference_conditioned",
            "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
        },
        confirm=False,
    )
    candidate = preview["result"]["manifest"]
    assert candidate["source"]["shot"]["shot_id"] == "shot-02"
    assert candidate["round_contract"]["prior_manifest_id"] == old_manifest["manifest_id"]
    assert candidate["provider_dispatch_count"] == 0
    assert load_video_admission_manifest(store, project_id) == old_manifest


def test_provider_not_ready_reconcile_round_creates_same_shot_recovery_without_provider(
    tmp_path,
) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _command(
        client,
        project_id,
        {
            "type": "compile",
            "idempotency_key": "compile-before-provider-not-ready",
            "generation_mode": "reference_conditioned",
            "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
        },
    )
    reserved = _command(
        client,
        project_id,
        {"type": "reserve_dispatch", "idempotency_key": "reserve-before-provider-not-ready"},
    )["result"]["manifest"]
    request = VideoGenerationRequest(
        **video_admission_generation_request(reserved, generated_at=REQUESTED_AT)
    )
    claim_video_admission_dispatch(
        store,
        project_id,
        request,
        job_id="provider-not-ready-job",
    )
    mark_video_admission_network_started(
        store,
        project_id,
        job_id="provider-not-ready-job",
    )
    old_manifest = deepcopy(load_video_admission_manifest(store, project_id))
    safe_path = (
        store.run_dir(project_id, "provider-not-ready-job")
        / "video_generation_safe_manifest.json"
    )
    write_json(
        safe_path,
        {
            "schema_version": "afs_video_generation_safe_manifest.v0.1",
            "status": "reconcile_required",
            "project_id": project_id,
            "provider_calls_started": False,
            "outputs": [],
            "blocks": [
                {
                    "block_id": "remote_video_provider_not_ready",
                    "failure_class": "provider_not_ready",
                    "reason": "Video provider configuration is not ready.",
                    "provider_raw_response_stored": False,
                }
            ],
        },
    )

    preview = _command(
        client,
        project_id,
        {
            "type": "create_new_round",
            "idempotency_key": "recover-provider-not-ready",
            "generation_mode": "reference_conditioned",
            "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
        },
        confirm=False,
    )
    candidate = preview["result"]["manifest"]
    assert candidate["source"]["shot"]["shot_id"] == "shot-01"
    assert candidate["round_contract"]["kind"] == "independent_after_provider_rejection"
    assert candidate["round_contract"]["prior_round_preserved"] is True
    assert candidate["provider_dispatch_count"] == 0
    assert load_video_admission_manifest(store, project_id) == old_manifest


def test_conservative_provider_not_ready_reconcile_round_uses_outbox_no_task_boundary(
    tmp_path,
) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _command(
        client,
        project_id,
        {
            "type": "compile",
            "idempotency_key": "compile-conservative-provider-not-ready",
            "generation_mode": "reference_conditioned",
            "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
        },
    )
    reserved = _command(
        client,
        project_id,
        {
            "type": "reserve_dispatch",
            "idempotency_key": "reserve-conservative-provider-not-ready",
        },
    )["result"]["manifest"]
    job_id = "provider-not-ready-conservative-job"
    output_dir = store.run_dir(project_id, job_id)
    prepare_dispatch_outbox(
        output_dir,
        project_id=project_id,
        job_id=job_id,
        manifest_id=reserved["manifest_id"],
        manifest_hash=reserved["manifest_hash"],
        item_id=reserved["item"]["item_id"],
    )
    request = VideoGenerationRequest(
        **video_admission_generation_request(reserved, generated_at=REQUESTED_AT)
    )
    claim_video_admission_dispatch(store, project_id, request, job_id=job_id)
    mark_video_admission_network_started(store, project_id, job_id=job_id)
    mark_network_may_have_started(output_dir)
    mark_reconcile_required(output_dir, "provider_submit_outcome_unknown")
    old_manifest = deepcopy(load_video_admission_manifest(store, project_id))
    assert old_manifest["item"]["state"] == "reconcile_required"
    assert old_manifest["item"]["network_disposition"] == "may_have_dispatched"
    assert old_manifest["item"].get("provider_task_fingerprint") in (None, "")
    assert old_manifest["item"]["candidate"] is None
    safe_path = output_dir / "video_generation_safe_manifest.json"
    write_json(
        safe_path,
        {
            "schema_version": "afs_video_generation_safe_manifest.v0.1",
            "status": "reconcile_required",
            "project_id": project_id,
            "provider_calls_started": True,
            "failure_class": "provider_not_ready",
            "stage": "reconcile_required",
            "outputs": [],
            "blocks": [
                {
                    "block_id": "remote_video_provider_not_ready",
                    "failure_class": "provider_not_ready",
                    "reason": "Video provider configuration is not ready.",
                    "provider_raw_response_stored": False,
                }
            ],
        },
    )

    body = {
        "command": _reference_video_setup_command(
            {
                "type": "create_new_round",
                "idempotency_key": "recover-conservative-provider-not-ready",
            }
        ),
        "requested_at": REQUESTED_AT,
    }
    preview = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json=body,
    )
    assert preview.status_code == 200, preview.text
    candidate = preview.json()["result"]["manifest"]
    assert candidate["source"]["shot"]["shot_id"] == old_manifest["source"]["shot"]["shot_id"]
    assert candidate["round_contract"]["prior_manifest_id"] == old_manifest["manifest_id"]
    assert candidate["provider_dispatch_count"] == 0
    assert load_video_admission_manifest(store, project_id) == old_manifest

    confirmed = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/confirm",
        json={**body, "preview_digest": preview.json()["preview_digest"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    active = load_video_admission_manifest(store, project_id)
    assert active == confirmed.json()["result"]["manifest"]
    assert active["provider_dispatch_count"] == 0
    archived = read_json(
        store.projects_dir
        / project_id
        / "video_admission"
        / "history"
        / f"{old_manifest['manifest_id']}.json"
    )
    assert archived == old_manifest


def test_conservative_provider_not_ready_recovery_rejects_outbox_task_identity(
    tmp_path,
) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _command(
        client,
        project_id,
        {
            "type": "compile",
            "idempotency_key": "compile-provider-task-boundary",
            "generation_mode": "reference_conditioned",
            "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
        },
    )
    reserved = _command(
        client,
        project_id,
        {"type": "reserve_dispatch", "idempotency_key": "reserve-provider-task-boundary"},
    )["result"]["manifest"]
    job_id = "provider-not-ready-with-task-job"
    output_dir = store.run_dir(project_id, job_id)
    prepare_dispatch_outbox(
        output_dir,
        project_id=project_id,
        job_id=job_id,
        manifest_id=reserved["manifest_id"],
        manifest_hash=reserved["manifest_hash"],
        item_id=reserved["item"]["item_id"],
    )
    request = VideoGenerationRequest(
        **video_admission_generation_request(reserved, generated_at=REQUESTED_AT)
    )
    claim_video_admission_dispatch(store, project_id, request, job_id=job_id)
    mark_video_admission_network_started(store, project_id, job_id=job_id)
    mark_network_may_have_started(output_dir)
    record_provider_task(output_dir, {"task": {"task_id": "remote-task-001"}})
    mark_reconcile_required(output_dir, "provider_submit_outcome_unknown")
    safe_path = output_dir / "video_generation_safe_manifest.json"
    write_json(
        safe_path,
        {
            "schema_version": "afs_video_generation_safe_manifest.v0.1",
            "status": "reconcile_required",
            "project_id": project_id,
            "provider_calls_started": True,
            "failure_class": "provider_not_ready",
            "outputs": [],
            "blocks": [
                {
                    "block_id": "remote_video_provider_not_ready",
                    "failure_class": "provider_not_ready",
                    "reason": "Video provider configuration is not ready.",
                    "provider_raw_response_stored": False,
                }
            ],
        },
    )

    response = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": _reference_video_setup_command(
                {
                    "type": "create_new_round",
                    "idempotency_key": "recover-provider-task-boundary",
                }
            ),
            "requested_at": REQUESTED_AT,
        },
    )
    assert response.status_code == 422
    assert load_video_admission_manifest(store, project_id)["item"]["state"] == "reconcile_required"


@pytest.mark.parametrize("mutation", ["fingerprint", "candidate", "outputs", "started_not_ready"])
def test_provider_not_ready_new_round_rejects_uncertain_network_identity(
    tmp_path,
    mutation: str,
) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _command(
        client,
        project_id,
        {
            "type": "compile",
            "idempotency_key": f"compile-boundary-{mutation}",
            "generation_mode": "reference_conditioned",
            "selection_reason": "使用已批准资产参考约束身份与连续性，不锁定首帧。",
        },
    )
    reserved = _command(
        client,
        project_id,
        {"type": "reserve_dispatch", "idempotency_key": f"reserve-boundary-{mutation}"},
    )["result"]["manifest"]
    request = VideoGenerationRequest(
        **video_admission_generation_request(reserved, generated_at=REQUESTED_AT)
    )
    claim_video_admission_dispatch(
        store,
        project_id,
        request,
        job_id=f"provider-not-ready-{mutation}",
    )
    mark_video_admission_network_started(
        store,
        project_id,
        job_id=f"provider-not-ready-{mutation}",
    )
    manifest = load_video_admission_manifest(store, project_id)
    safe_manifest = {
        "schema_version": "afs_video_generation_safe_manifest.v0.1",
        "status": "reconcile_required",
        "project_id": project_id,
        "provider_calls_started": False,
        "outputs": [],
        "blocks": [
            {
                "block_id": "remote_video_provider_not_ready",
                "failure_class": "provider_not_ready",
                "reason": "Video provider configuration is not ready.",
                "provider_raw_response_stored": False,
            }
        ],
    }
    if mutation == "fingerprint":
        manifest["item"]["provider_task_fingerprint"] = "remote-task-fingerprint"
    elif mutation == "candidate":
        manifest["item"]["candidate"] = {}
    elif mutation == "outputs":
        safe_manifest["outputs"] = [{"candidate_id": "candidate_001"}]
    elif mutation == "started_not_ready":
        safe_manifest["provider_calls_started"] = True
    write_json(store.projects_dir / project_id / "video_admission" / "manifest.json", manifest)
    write_json(
        store.run_dir(project_id, f"provider-not-ready-{mutation}")
        / "video_generation_safe_manifest.json",
        safe_manifest,
    )

    response = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": _reference_video_setup_command(
                {
                    "type": "create_new_round",
                    "idempotency_key": f"recover-boundary-{mutation}",
                }
            ),
            "requested_at": REQUESTED_AT,
        },
    )
    assert response.status_code == 422


def test_video_readiness_uses_shot_id_and_requires_exact_reference_pack(tmp_path) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    path = store.projects_dir / project_id / "image_admission" / "manifest.json"
    manifest = read_json(path)
    manifest["source"]["shot_grounding"]["shots"][0]["number"] = 2
    write_json(path, manifest)

    response = client.get(f"/projects/{project_id}/m6/video-admission")
    assert response.status_code == 200
    assert response.json()["readiness"]["status"] == "ready"
    preview = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": _video_setup_command(
                {"type": "compile", "idempotency_key": "compile-bad-shot-number"}
            ),
            "requested_at": REQUESTED_AT,
        },
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["result"]["manifest"]["source"]["shot"]["shot_id"] == "shot-01"
    assert load_video_admission_manifest(store, project_id) == {}

    manifest["source"]["shot_grounding"]["shots"][0]["number"] = 1
    manifest["items"][0]["reference_asset_ids"] = ["character-a", "scene-a"]
    write_json(path, manifest)
    response = client.get(f"/projects/{project_id}/m6/video-admission")
    assert response.json()["readiness"]["status"] == "ready"
    preview = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": _video_setup_command(
                {"type": "compile", "idempotency_key": "compile-bad-reference-pack"}
            ),
            "requested_at": REQUESTED_AT,
        },
    )
    assert preview.status_code == 422
    assert "首帧图生视频需要明确选择" in preview.json()["detail"]["details"]["raw_detail"]


def test_video_readiness_rejects_keyframe_bound_to_another_shot(tmp_path) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    path = store.projects_dir / project_id / "image_admission" / "manifest.json"
    manifest = read_json(path)
    manifest["items"][0]["target_shot_id"] = "shot-other"
    write_json(path, manifest)

    response = client.get(f"/projects/{project_id}/m6/video-admission")
    assert response.json()["readiness"]["status"] == "ready"
    preview = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": _video_setup_command(
                {"type": "compile", "idempotency_key": "compile-wrong-keyframe-shot"}
            ),
            "requested_at": REQUESTED_AT,
        },
    )
    assert preview.status_code == 422
    assert "首帧图生视频需要明确选择" in preview.json()["detail"]["details"]["raw_detail"]


def test_video_candidate_preview_is_bound_to_current_project_and_job(tmp_path) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _command(client, project_id, {"type": "compile", "idempotency_key": "compile"})
    reserved = _command(
        client,
        project_id,
        {"type": "reserve_dispatch", "idempotency_key": "reserve"},
    )["result"]["manifest"]
    request = VideoGenerationRequest(
        **video_admission_generation_request(reserved, generated_at=REQUESTED_AT)
    )
    _claim_for_test(store, project_id, request, job_id="video-job-001")
    _command(
        client,
        project_id,
        {
            "type": "record_job",
            "idempotency_key": "record-job",
            "provider_job_id": "video-job-001",
        },
    )
    response = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": {
                "type": "record_candidate",
                "idempotency_key": "cross-project-candidate",
                "candidate": {
                    "job_id": "video-job-001",
                    "candidate_id": "candidate_001",
                    "preview_url": (
                        "/projects/other-project/video-generations/"
                        "video-job-001/candidates/candidate_001/preview"
                    ),
                    "sha256": "a" * 64,
                    "byte_count": 10,
                },
            },
            "requested_at": REQUESTED_AT,
        },
    )

    assert response.status_code == 422
    assert "current project and job" in response.text
    assert load_video_admission_manifest(store, project_id)["item"]["state"] == "processing"


def test_video_candidate_fails_closed_before_review_when_media_is_corrupt(tmp_path) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _command(client, project_id, {"type": "compile", "idempotency_key": "compile"})
    reserved = _command(
        client,
        project_id,
        {"type": "reserve_dispatch", "idempotency_key": "reserve"},
    )["result"]["manifest"]
    request = VideoGenerationRequest(
        **video_admission_generation_request(reserved, generated_at=REQUESTED_AT)
    )
    _claim_for_test(store, project_id, request, job_id="video-job-001")
    _command(
        client,
        project_id,
        {
            "type": "record_job",
            "idempotency_key": "record-job",
            "provider_job_id": "video-job-001",
        },
    )
    candidate_path = (
        store.run_dir(project_id, "video-job-001")
        / "video_candidates"
        / "candidate_001.mp4"
    )
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_bytes(b"\x00\x00\x00\x18ftypmp42corrupt")
    data = candidate_path.read_bytes()
    response = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": {
                "type": "record_candidate",
                "idempotency_key": "record-corrupt",
                "candidate": {
                    "job_id": "video-job-001",
                    "candidate_id": "candidate_001",
                    "preview_url": (
                        f"/projects/{project_id}/video-generations/"
                        "video-job-001/candidates/candidate_001/preview"
                    ),
                    "sha256": hashlib.sha256(data).hexdigest(),
                    "byte_count": len(data),
                },
            },
            "requested_at": REQUESTED_AT,
        },
    )

    assert response.status_code == 422
    assert "failed technical validation" in response.text
    assert load_video_admission_manifest(store, project_id)["item"]["state"] == "processing"
