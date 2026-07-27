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
from apps.api.runtime_production_graph import ProductionGraphStore, canonical_digest
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore, read_json
from apps.api.runtime_video_admission import (
    AUTO_RETRY,
    CREATE_ENDPOINT,
    DURATION_SEC,
    HARD_BUDGET_USD,
    MAX_DISPATCHES,
    MODEL_ID,
    RESOLUTION,
    SERVICE_ID,
    QUERY_ENDPOINT,
    claim_video_admission_dispatch,
    enforce_video_admission_request,
    load_video_admission_manifest,
    mark_video_admission_network_started,
    mark_video_admission_task_recorded,
    video_admission_capability,
    video_admission_generation_request,
)


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
VIDEO_CANDIDATE_BYTES = b"afs-deterministic-video-candidate-v1"
REQUESTED_AT = "2026-07-26T03:00:00Z"


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
    media = {
        "keyframe": _upload(client, project_id, "shot-01-keyframe"),
        "character": _upload(client, project_id, "character-reference"),
        "scene": _upload(client, project_id, "scene-reference"),
        "prop": _upload(client, project_id, "prop-reference"),
    }
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
                "node_id": "scene-a",
                "category": "location",
                "metadata": {"display_name": "北侧检修站"},
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
                    **(
                        {
                            "intent": "建立检修任务",
                            "blocking": "巡夜人甲在操作台前校准六角校准器",
                            "shot_size": "中景",
                            "camera_angle": "平视",
                            "camera_movement": "沿操作台缓慢向前推进",
                            "narrative_purpose": "保持克制专注的检修压力",
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
                            "巡夜人甲用六角校准器完成一次精确校准"
                            if manifest_semantics
                            else ""
                        ),
                        "composition": (
                            "中景，人物与操作台保持清晰层次"
                            if manifest_semantics
                            else ""
                        ),
                        "camera_angle": "平视" if manifest_semantics else "",
                        "movement": "缓慢向前推进" if manifest_semantics else "",
                        "emotion": "克制而专注" if manifest_semantics else "",
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
        {"type": "compile", "idempotency_key": "compile-normalized-shot"},
        confirm=False,
    )
    prompt_contract = preview["result"]["manifest"]["source"]["prompt_contract"]
    assert prompt_contract["shot_action"] == "巡夜人甲在操作台前校准六角校准器"
    assert prompt_contract["composition"] == "中景"
    assert prompt_contract["camera_movement"] == "沿操作台缓慢向前推进"
    assert prompt_contract["emotion"] == "保持克制专注的检修压力"
    assert prompt_contract["keyword_rewrite"] is False
    assert prompt_contract["sample_fallback"] is False
    assert preview["provider_dispatch_count"] == 0


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
def test_video_readiness_requires_locked_image_manifest(
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
            "command": {
                "type": "compile",
                "idempotency_key": f"compile-{manifest_status}-manifest",
            },
            "requested_at": REQUESTED_AT,
        },
    )

    assert readiness.status_code == 200
    assert readiness.json()["readiness"]["status"] == "blocked"
    assert preview.status_code == 422
    assert load_video_admission_manifest(store, project_id) == {}
    assert ProductionGraphStore(store).load(project_id)["version"] == 1


def _command(
    client: TestClient,
    project_id: str,
    command: dict,
    *,
    confirm: bool = True,
) -> dict:
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
    assert state["lineage"]["keyframe_reuse"] == "verified_current"
    assert state["lineage"]["rebuild_allowed"] is True
    assert state["lineage"]["affected_objects"] == ["镜头 01 视频来源未受此次更新影响"]
    assert state["provider_dispatch_count"] == 0

    body = {
        "command": {
            "type": "recompile_current",
            "idempotency_key": "recompile-current-v2",
        },
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
    assert candidate["source"]["keyframe"]["image_asset_id"] == media["keyframe"]
    assert [item["image_asset_id"] for item in candidate["source"]["references"]] == [
        media["character"],
        media["prop"],
        media["scene"],
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
        "command": {
            "type": "recompile_current",
            "idempotency_key": "recompile-racing-graph",
        },
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


def test_stale_video_manifest_requires_new_keyframe_when_shot_visual_semantics_change(
    tmp_path,
) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _command(client, project_id, {"type": "compile", "idempotency_key": "compile-before-change"})
    old_video = deepcopy(load_video_admission_manifest(store, project_id))
    _, _ = _rotate_image_manifest_after_graph_update(store, project_id)
    image_path = store.projects_dir / project_id / "image_admission" / "manifest.json"
    current_image = read_json(image_path)
    current_image["source"]["shot_grounding"]["shots"][0]["action"] = (
        "巡夜人甲离开操作台并走向站台另一端"
    )
    write_json(image_path, current_image)

    state = client.get(f"/projects/{project_id}/m6/video-admission").json()

    assert state["readiness"]["status"] == "blocked"
    assert state["lineage"]["status"] == "stale"
    assert state["lineage"]["keyframe_reuse"] == "requires_new_keyframe"
    assert state["lineage"]["rebuild_allowed"] is False
    assert "新的镜头 01 关键帧" in state["lineage"]["next_action"]
    response = client.post(
        f"/projects/{project_id}/m6/video-admission/commands/preview",
        json={
            "command": {
                "type": "recompile_current",
                "idempotency_key": "unsafe-recompile",
            },
            "requested_at": REQUESTED_AT,
        },
    )
    assert response.status_code == 422
    assert load_video_admission_manifest(store, project_id) == old_video
    assert not (
        store.projects_dir / project_id / "video_admission" / "history"
    ).exists()


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
        "克制而专注",
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
    assert approved_videos[0]["metadata"]["actual_usd"] is None


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
        "command": {
            "type": "create_new_round",
            "idempotency_key": "new-independent-round",
        },
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


def test_video_readiness_requires_literal_shot_one_and_exact_reference_pack(tmp_path) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    path = store.projects_dir / project_id / "image_admission" / "manifest.json"
    manifest = read_json(path)
    manifest["source"]["shot_grounding"]["shots"][0]["number"] = 2
    write_json(path, manifest)

    response = client.get(f"/projects/{project_id}/m6/video-admission")
    assert response.status_code == 200
    assert response.json()["readiness"]["status"] == "blocked"
    assert "numbered 1" in response.json()["readiness"]["reason"]

    manifest["source"]["shot_grounding"]["shots"][0]["number"] = 1
    manifest["items"][0]["reference_asset_ids"] = ["character-a", "scene-a"]
    write_json(path, manifest)
    response = client.get(f"/projects/{project_id}/m6/video-admission")
    assert response.json()["readiness"]["status"] == "blocked"
    assert "every canonical shot asset" in response.json()["readiness"]["reason"]


def test_video_readiness_rejects_keyframe_bound_to_another_shot(tmp_path) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    path = store.projects_dir / project_id / "image_admission" / "manifest.json"
    manifest = read_json(path)
    manifest["items"][0]["target_shot_id"] = "shot-other"
    write_json(path, manifest)

    response = client.get(f"/projects/{project_id}/m6/video-admission")
    assert response.json()["readiness"]["status"] == "blocked"
    assert "bound exactly to shot 01" in response.json()["readiness"]["reason"]


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
