from __future__ import annotations

import base64


PNG_B64 = base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
).decode("ascii")


def _upload_image(client, project_id: str, *, node_id: str, role: str, generated_at: str) -> str:
    uploaded = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": node_id,
            "filename": "model-context-reference.png",
            "mime_type": "image/png",
            "data_base64": PNG_B64,
            "role": role,
            "generated_at": generated_at,
        },
    )
    assert uploaded.status_code == 200
    return uploaded.json()["asset"]["asset_id"]


def test_runtime_video_generation_registers_model_call_context_and_request_plan(tmp_path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from apps.api.runtime_service import create_runtime_app

    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    image_asset_id = _upload_image(
        client,
        "proj_video_model_context",
        node_id="first-frame-node",
        role="first_frame",
        generated_at="2026-06-18T10:19:00+08:00",
    )

    result = client.post(
        "/projects/proj_video_model_context/video-generations",
        json={
            "node_id": "video-node-001",
            "prompt_text": "Animate the keyframe into a short establishing shot.",
            "optimized_prompt": "Animate the keyframe into a short establishing shot.",
            "first_frame_image_asset_id": image_asset_id,
            "duration_sec": 5,
            "motion": "slow dolly in",
            "generated_at": "2026-06-18T10:20:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    context = client.get(f"/artifacts/{payload['artifacts']['model_call_context']['artifact_id']}").json()["payload"]
    projection = client.get(f"/artifacts/{payload['artifacts']['model_request_plan']['artifact_id']}").json()["payload"]

    assert payload["model_call_context_id"] == context["context_id"]
    assert context["operation_intent"] == "video_generate"
    assert context["generation_target"] == "video"
    assert context["reference_context"]["reference_image_refs"] == [image_asset_id]
    assert projection["context_id"] == context["context_id"]
    assert projection["request_mode"] == "i2v"
    assert projection["provider_request"]["reference_image_refs"] == [image_asset_id]
    assert payload["safe_manifest"]["model_call_context_id"] == context["context_id"]


def test_runtime_video_generation_immediate_completion_keeps_model_call_artifacts(tmp_path, monkeypatch) -> None:
    from types import SimpleNamespace

    from fastapi.testclient import TestClient

    from apps.api import runtime_video_routes
    from apps.api.runtime_service import create_runtime_app

    class ImmediateRegistry:
        def descriptor(self, service_id: str):
            assert service_id == "immediate_video"
            return SimpleNamespace(required_gate="AFS_ALLOW_REMOTE_VIDEO", min_reference_image_edge_px=0)

        def submit(self, capability: str, service_id: str, dispatch_request):
            assert capability == "video"
            assert service_id == "immediate_video"
            candidate_dir = dispatch_request.output_dir / "video_candidates"
            candidate_dir.mkdir(parents=True, exist_ok=True)
            (candidate_dir / "candidate_001.mp4").write_bytes(b"fake-video")
            return {
                "task": {
                    "status": "already_complete",
                    "raw": {
                        "outputs": [
                            {
                                "candidate_id": "candidate_001",
                                "video_path": "video_candidates/candidate_001.mp4",
                            }
                        ]
                    },
                }
            }

    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setattr(runtime_video_routes, "load_provider_registry", lambda: ImmediateRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    project_id = "proj_video_immediate_model_context"
    image_asset_id = _upload_image(
        client,
        project_id,
        node_id="first-frame-node",
        role="first_frame",
        generated_at="2026-06-18T10:19:00+08:00",
    )

    result = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "node_id": "video-node-002",
            "prompt_text": "Animate the keyframe into an immediate completed shot.",
            "optimized_prompt": "Animate the keyframe into an immediate completed shot.",
            "first_frame_image_asset_id": image_asset_id,
            "provider_service_id": "immediate_video",
            "duration_sec": 5,
            "generated_at": "2026-06-18T10:20:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    context = client.get(f"/artifacts/{payload['artifacts']['model_call_context']['artifact_id']}").json()["payload"]
    projection = client.get(f"/artifacts/{payload['artifacts']['model_request_plan']['artifact_id']}").json()["payload"]

    assert payload["job"]["status"] == "succeeded"
    assert payload["model_call_context_id"] == context["context_id"]
    assert payload["safe_manifest"]["model_call_context_id"] == context["context_id"]
    assert projection["context_id"] == context["context_id"]


def test_asset_card_draft_registers_visual_inspect_context_and_observation(tmp_path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from apps.api.runtime_service import create_runtime_app

    monkeypatch.setenv("AFS_ALLOW_REMOTE_VISION", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    image_asset_id = _upload_image(
        client,
        "proj_asset_card_model_context",
        node_id="character-source-node",
        role="reference",
        generated_at="2026-06-18T10:21:00+08:00",
    )

    result = client.post(
        "/projects/proj_asset_card_model_context/asset-card-drafts",
        json={
            "asset_type": "character",
            "prompt_text": "a steady heroine wearing a red scarf",
            "source_image_asset_refs": [image_asset_id],
            "provider_service_id": "fake-vision",
            "generated_at": "2026-06-18T10:22:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    context = client.get(f"/artifacts/{payload['artifacts']['model_call_context']['artifact_id']}").json()["payload"]
    projection = client.get(f"/artifacts/{payload['artifacts']['model_request_plan']['artifact_id']}").json()["payload"]
    observation = client.get(
        f"/artifacts/{payload['artifacts']['visual_understanding_observation']['artifact_id']}"
    ).json()["payload"]

    assert payload["model_call_context_id"] == context["context_id"]
    assert context["operation_intent"] == "visual_inspect"
    assert context["generation_target"] == "asset_card"
    assert context["reference_context"]["reference_image_refs"] == [image_asset_id]
    assert context["safety_boundary"]["no_provider_raw"] is True
    assert context["safety_boundary"]["no_local_path"] is True
    assert projection["context_id"] == context["context_id"]
    assert projection["request_mode"] == "visual_inspect"
    assert observation["artifact_type"] == "agentflow_visual_understanding_observation"
    assert observation["asset_card_policy"]["default_status"] == "draft"
    assert payload["draft"]["status"] == "draft"
    assert payload["draft"]["visual_observation_ref"] == "visual_understanding_observation.json"


def test_video_revision_registers_feedback_context_and_revision_request_plan(tmp_path, monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from apps.api.runtime_service import create_runtime_app

    monkeypatch.delenv("AFS_ENABLE_EXPERIMENTAL_VIDEO_REVISION", raising=False)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    image_asset_id = _upload_image(
        client,
        "proj_revision_model_context",
        node_id="revision-first-frame-node",
        role="first_frame",
        generated_at="2026-06-18T10:23:00+08:00",
    )

    result = client.post(
        "/projects/proj_revision_model_context/video-revisions",
        json={
            "node_id": "video-revision-node-001",
            "base_video_job_id": "video_generation_base_001",
            "revision_intent": "Adjust the light on frame 34 while preserving character identity and camera path.",
            "editable_targets": ["lighting"],
            "locked_aspects": ["character_identity", "camera_path"],
            "temporal_scope": {"kind": "frame_range", "start_frame": 34, "end_frame": 34},
            "provider_service_id": "fake-video",
            "first_frame_image_asset_id": image_asset_id,
            "duration_sec": 5,
            "resolution": "720p",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "generated_at": "2026-06-18T10:24:00+08:00",
        },
    )

    assert result.status_code == 200
    payload = result.json()
    context = client.get(f"/artifacts/{payload['artifacts']['model_call_context']['artifact_id']}").json()["payload"]
    projection = client.get(f"/artifacts/{payload['artifacts']['model_request_plan']['artifact_id']}").json()["payload"]
    revision = client.get(f"/artifacts/{payload['artifacts']['revision_plan']['artifact_id']}").json()["payload"]

    assert payload["model_call_context_id"] == context["context_id"]
    assert context["operation_intent"] == "revision"
    assert context["generation_target"] == "revision"
    assert context["reference_context"]["reference_image_refs"] == [image_asset_id]
    assert context["feedback_context"]["revision_control"]["revision_intent"].startswith("Adjust the light")
    assert context["feedback_context"]["revision_control"]["drift_risks"]
    assert projection["context_id"] == context["context_id"]
    assert projection["request_mode"] == "revision"
    assert revision["algorithm_id"] == "afs.revision_drift_control.v0.1"
    assert payload["safe_manifest"]["model_call_context_id"] == context["context_id"]
    assert payload["safe_manifest"]["revision_plan_ref"] == "revision_plan.json"
