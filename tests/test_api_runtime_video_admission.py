from __future__ import annotations

import base64
import hashlib
import subprocess
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from agentflow.harness.json_io import write_json
from apps.api.runtime_models import VideoGenerationRequest
from apps.api.runtime_production_graph import ProductionGraphStore, canonical_digest
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_video_admission import (
    AUTO_RETRY,
    CREATE_ENDPOINT,
    DURATION_SEC,
    HARD_BUDGET_USD,
    MAX_DISPATCHES,
    MODEL_ID,
    RESOLUTION,
    SERVICE_ID,
    claim_video_admission_dispatch,
    enforce_video_admission_request,
    load_video_admission_manifest,
    video_admission_capability,
    video_admission_generation_request,
)


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)
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


def _seed_ready_project(tmp_path) -> tuple[TestClient, RuntimeStore, str, dict[str, str]]:
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
                "metadata": {"kind": "shot", "display_name": "镜头 01"},
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
        events.append(
            {
                "type": "node_upserted",
                "node": {
                    "node_id": f"approved-{label}",
                    "category": "artifact",
                    "metadata": {
                        "kind": "approved_image",
                        "image_asset_id": asset_id,
                    },
                },
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
        "status": "locked",
        "source": {
            "asset_bible_revision_id": "asset-bible-r9",
            "shot_candidate_id": "shots-r1",
            "shot_grounding": {
                "shots": [
                    {
                        "shot_id": "shot-01",
                        "title": "镜头 01",
                        "number": 1,
                        "action": "巡夜人甲用六角校准器完成一次精确校准",
                        "composition": "中景，人物与操作台保持清晰层次",
                        "camera_angle": "平视",
                        "movement": "缓慢向前推进",
                        "emotion": "克制而专注",
                        "continuity_cues": ["服装、工具位置与北侧检修站照明保持连续"],
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


def test_video_admission_locks_exact_non_fast_single_dispatch_contract(tmp_path) -> None:
    client, store, project_id, media = _seed_ready_project(tmp_path)

    readiness = client.get(f"/projects/{project_id}/m6/video-admission")
    assert readiness.status_code == 200
    assert readiness.json()["readiness"]["status"] == "ready"
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
        "resolution": RESOLUTION,
        "duration_sec": DURATION_SEC,
        "candidate_count": 1,
        "max_dispatches": MAX_DISPATCHES,
        "auto_retry": AUTO_RETRY,
    }
    assert manifest["budget_contract"] == {
        "currency": "USD",
        "hard_ceiling_usd": f"{HARD_BUDGET_USD:.2f}",
        "classification": "hard_ceiling_not_estimate_or_actual_charge",
        "billing_mode": "provider_output_tokens",
        "actual_charge_usd": None,
        "actual_charge_verification": "unverified",
    }
    assert manifest["source"]["keyframe"]["image_asset_id"] == media["keyframe"]
    assert [item["image_asset_id"] for item in manifest["source"]["references"]] == [
        media["character"],
        media["scene"],
        media["prop"],
    ]
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
    assert claimed["provider_dispatch_count"] == replayed_claim["provider_dispatch_count"] == 1
    with pytest.raises(ValueError, match="already claimed"):
        claim_video_admission_dispatch(
            store,
            project_id,
            request,
            job_id="video-job-002",
        )


def test_video_candidate_requires_human_approval_before_graph_writeback(tmp_path) -> None:
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
    claim_video_admission_dispatch(store, project_id, request, job_id="video-job-001")
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
    subprocess.run(
        [
            "ffmpeg",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=1280x720:d=6",
            "-c:v",
            "mpeg4",
            "-pix_fmt",
            "yuv420p",
            candidate_path,
        ],
        check=True,
    )
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


def test_video_admission_fails_closed_on_reference_and_graph_drift(tmp_path) -> None:
    client, store, project_id, _ = _seed_ready_project(tmp_path)
    _command(client, project_id, {"type": "compile", "idempotency_key": "compile"})
    manifest = load_video_admission_manifest(store, project_id)
    request_payload = video_admission_generation_request(manifest, generated_at=REQUESTED_AT)
    request_payload["reference_image_asset_ids"] = []
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
    claim_video_admission_dispatch(store, project_id, request, job_id="video-job-001")
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
    claim_video_admission_dispatch(store, project_id, request, job_id="video-job-001")
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
