from __future__ import annotations

import base64
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

from apps.api import runtime_video_routes
from apps.api.runtime_models import VideoGenerationRequest, VideoRevisionRequest
from apps.api.runtime_service import create_runtime_app


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


def test_runtime_video_requests_default_to_seedance_provider() -> None:
    generation = VideoGenerationRequest(
        prompt_text="A controlled image-to-video move.",
        first_frame_image_asset_id="img_first_frame",
        generated_at="2026-06-25T20:00:00+08:00",
    )
    revision = VideoRevisionRequest(
        base_video_job_id="video_generation_base",
        revision_intent="Add a slow push-in while preserving identity.",
        prompt_text="A controlled image-to-video revision.",
        first_frame_image_asset_id="img_first_frame",
        generated_at="2026-06-25T20:00:00+08:00",
    )

    assert generation.provider_service_id == "seedance_i2v"
    assert revision.provider_service_id == "seedance_i2v"


def _upload_image(client: TestClient, project_id: str) -> str:
    upload = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": "image_1",
            "filename": "first-frame.png",
            "mime_type": "image/png",
            "data_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            "role": "first_frame",
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )
    assert upload.status_code == 200
    return upload.json()["asset"]["asset_id"]


def test_video_generation_requires_explicit_first_frame(tmp_path, monkeypatch) -> None:
    config = _fake_video_provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-no-first-frame"
    client.post("/projects", json={"project_id": project_id, "goal": "Video first frame guard"})

    response = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "prompt_text": "A slow camera push in.",
            "provider_service_id": "fake_video",
            "duration_sec": 5,
            "resolution": "720p",
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )

    assert response.status_code == 422
    assert "first_frame_image_asset_id" in response.text


def test_video_generation_rejects_candidate_count_not_one(tmp_path, monkeypatch) -> None:
    config = _fake_video_provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-count-guard"
    client.post("/projects", json={"project_id": project_id, "goal": "Video count guard"})
    asset_id = _upload_image(client, project_id)

    response = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "prompt_text": "A slow camera push in.",
            "provider_service_id": "fake_video",
            "first_frame_image_asset_id": asset_id,
            "duration_sec": 5,
            "resolution": "720p",
            "candidate_count": 2,
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )

    assert response.status_code == 422
    assert "candidate_count" in response.text


def test_video_generation_gate_closed_blocks_before_provider_submit(tmp_path, monkeypatch) -> None:
    config = _fake_video_provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config))
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-gate-closed"
    client.post("/projects", json={"project_id": project_id, "goal": "Video gate guard"})
    asset_id = _upload_image(client, project_id)

    response = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "prompt_text": "A slow camera push in.",
            "provider_service_id": "fake_video",
            "first_frame_image_asset_id": asset_id,
            "duration_sec": 5,
            "resolution": "720p",
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["status"] == "blocked"
    assert payload["safe_manifest"]["status"] == "blocked"
    assert payload["provider_calls_started"] is False
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert "secret" not in serialized
    assert "fake-video-key" not in serialized


def test_tiny_video_first_frame_blocks_before_provider_submit(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")

    class GuardedRegistry:
        def descriptor(self, service_id: str):
            assert service_id == "fake_video"
            return SimpleNamespace(required_gate="AFS_ALLOW_REMOTE_VIDEO", min_reference_image_edge_px=256)

        def submit(self, capability: str, service_id: str, request):
            raise AssertionError("tiny first frame should be blocked before provider submit")

    monkeypatch.setattr(runtime_video_routes, "load_provider_registry", lambda: GuardedRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-tiny-first-frame-guard"
    client.post("/projects", json={"project_id": project_id, "goal": "Video tiny first frame guard"})
    asset_id = _upload_image(client, project_id)

    response = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "prompt_text": "A slow camera push in.",
            "provider_service_id": "fake_video",
            "first_frame_image_asset_id": asset_id,
            "duration_sec": 5,
            "resolution": "720p",
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["status"] == "blocked"
    assert payload["safe_manifest"]["status"] == "blocked"
    assert payload["provider_calls_started"] is False
    assert payload["safe_manifest"]["provider_calls_started"] is False
    assert payload["safe_manifest"]["blocks"][0]["block_id"] == "remote_video_reference_image_too_small"


def test_video_generation_preflight_needs_no_video_gate_and_is_stable(tmp_path, monkeypatch) -> None:
    config = _fake_video_provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config))
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-preflight"
    client.post("/projects", json={"project_id": project_id, "goal": "Video preflight"})
    asset_id = _upload_image(client, project_id)
    request = {
        "prompt_text": "A slow camera push in.",
        "provider_service_id": "fake_video",
        "first_frame_image_asset_id": asset_id,
        "duration_sec": 5,
        "resolution": "720p",
        "generated_at": "2026-06-13T10:00:00+08:00",
    }

    first = client.post(f"/projects/{project_id}/video-generations/preflight", json=request)
    second = client.post(f"/projects/{project_id}/video-generations/preflight", json=request)
    changed = client.post(
        f"/projects/{project_id}/video-generations/preflight",
        json={**request, "prompt_text": "A fast tracking shot."},
    )

    assert first.status_code == 200
    assert first.json()["provider_calls_started"] is False
    assert first.json()["requires_provider_gate"] is False
    assert first.json()["preflight_token"] == second.json()["preflight_token"]
    assert first.json()["preflight_token"] != changed.json()["preflight_token"]


def test_video_generation_rejects_stale_preflight_token(tmp_path, monkeypatch) -> None:
    config = _fake_video_provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config))
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-stale-preflight"
    client.post("/projects", json={"project_id": project_id, "goal": "Video stale preflight"})
    asset_id = _upload_image(client, project_id)
    request = {
        "prompt_text": "A slow camera push in.",
        "provider_service_id": "fake_video",
        "first_frame_image_asset_id": asset_id,
        "duration_sec": 5,
        "resolution": "720p",
        "generated_at": "2026-06-13T10:00:00+08:00",
    }
    preflight = client.post(f"/projects/{project_id}/video-generations/preflight", json=request)
    assert preflight.status_code == 200

    stale = client.post(
        f"/projects/{project_id}/video-generations",
        json={**request, "prompt_text": "A different motion.", "preflight_token": preflight.json()["preflight_token"]},
    )

    assert stale.status_code == 409
    assert "stale_preflight" in stale.text


def test_fake_async_video_submit_poll_and_preview(tmp_path, monkeypatch) -> None:
    config = _fake_video_provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-fake-async"
    client.post("/projects", json={"project_id": project_id, "goal": "Video async flow"})
    asset_id = _upload_image(client, project_id)

    submitted = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "node_id": "video_1",
            "prompt_text": "A slow camera push in.",
            "provider_service_id": "fake_video",
            "first_frame_image_asset_id": asset_id,
            "duration_sec": 5,
            "resolution": "720p",
            "aspect_ratio": "9:16",
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )
    assert submitted.status_code == 200
    job = submitted.json()["job"]
    assert job["status"] == "submitted"
    assert job["progress"]["provider_phase"] == "submitted"
    assert "elapsed_sec" in job["progress"]
    assert "queued_sec" in job["progress"]

    polled = client.post(f"/projects/{project_id}/video-generations/{job['job_id']}/poll")
    assert polled.status_code == 200
    payload = polled.json()
    assert payload["job"]["status"] == "succeeded"
    assert payload["job"]["progress"]["provider_phase"] == "succeeded"
    assert "elapsed_sec" in payload["job"]["progress"]
    assert "running_sec" in payload["job"]["progress"]
    assert payload["candidate_previews"][0]["preview_url"].startswith(
        f"/projects/{project_id}/video-generations/{job['job_id']}/candidates/"
    )
    preview = client.get(payload["candidate_previews"][0]["preview_url"])
    assert preview.status_code == 200
    assert preview.headers["content-type"].startswith("video/")
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert "data/processed/runs" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized


def test_video_provider_prompt_removes_image_edit_language() -> None:
    request = runtime_video_routes.VideoGenerationRequest(
        prompt_text="基于当前关键帧生成视频",
        optimized_prompt=(
            "意图：本次只做这一项图生图编辑。\n"
            "动作/情节：人物保持参考图原有静态姿态和身体朝向。\n"
            "运动/时间推进：单帧图像编辑，不制造多阶段动作或剧情。"
        ),
        provider_service_id="fake_video",
        first_frame_image_asset_id="img_first_frame",
        duration_sec=5,
        motion="角色在沙漠中行走",
        generated_at="2026-06-13T10:00:00+08:00",
    )

    prompt = runtime_video_routes._video_provider_prompt(
        request,
        {
            "text_channel": {
                "visible_prompt": "旧关键帧提示词不应被直接拼入",
                "asset_signature_segment": "周彤: 蓝白校服，体态比例稳定",
                "asset_identity_segment": "保持周彤身份",
                "scene_director_segment": "镜头轻微跟随",
                "preference_segment": "cinematic",
            }
        },
    )

    assert "图生图编辑" not in prompt
    assert "单帧图像编辑" not in prompt
    assert "静态姿态" not in prompt
    assert "旧关键帧提示词不应被直接拼入" not in prompt
    assert "first frame as a strict visual anchor" in prompt
    assert "角色在沙漠中行走" in prompt
    assert "周彤" in prompt


def test_video_generation_strips_adapter_output_dir_from_persisted_task_state(tmp_path, monkeypatch) -> None:
    config = _fake_video_provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")

    class PathReturningRegistry:
        def descriptor(self, service_id: str):
            assert service_id == "fake_video"
            return SimpleNamespace(required_gate="AFS_ALLOW_REMOTE_VIDEO")

        def submit(self, capability: str, service_id: str, request):
            assert capability == "video"
            assert service_id == "fake_video"
            return {
                "service_id": service_id,
                "capability": capability,
                "task": {
                    "status": "submitted",
                    "task_id": "path-returning-task",
                    "output_dir": str(request.output_dir),
                    "timeout_sec": 120.0,
                },
            }

        def poll(self, capability: str, service_id: str, task):
            assert capability == "video"
            assert service_id == "fake_video"
            assert task["task"]["output_dir"]
            return {"status": "running", "task": {"task_id": "path-returning-task"}}

    monkeypatch.setattr(runtime_video_routes, "load_provider_registry", lambda: PathReturningRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-path-safe-task-state"
    client.post("/projects", json={"project_id": project_id, "goal": "Video task state path hygiene"})
    asset_id = _upload_image(client, project_id)

    submitted = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "node_id": "video_1",
            "prompt_text": "A slow camera push in.",
            "provider_service_id": "fake_video",
            "first_frame_image_asset_id": asset_id,
            "duration_sec": 5,
            "resolution": "720p",
            "aspect_ratio": "9:16",
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )

    assert submitted.status_code == 200
    payload = submitted.json()
    assert payload["job"]["status"] == "submitted"
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert "output_dir" not in serialized
    assert "c:\\" not in serialized
    assert "d:\\" not in serialized

    job_id = payload["job"]["job_id"]
    state_path = tmp_path / "runtime" / "runs" / project_id / job_id / "video_task_state.json"
    state_text = state_path.read_text(encoding="utf-8").lower()
    assert "output_dir" not in state_text
    assert "c:\\" not in state_text
    assert "d:\\" not in state_text

    polled = client.post(f"/projects/{project_id}/video-generations/{job_id}/poll")

    assert polled.status_code == 200
    assert polled.json()["job"]["status"] == "running"
    assert polled.json()["job"]["progress"]["provider_phase"] == "running"
    assert "elapsed_sec" in polled.json()["job"]["progress"]
    assert "queued_sec" in polled.json()["job"]["progress"]
    assert "running_sec" in polled.json()["job"]["progress"]


def test_video_generation_provider_internal_error_writes_safe_manifest(tmp_path, monkeypatch) -> None:
    config = _fake_video_provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config))
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")

    class FailingRegistry:
        def descriptor(self, service_id: str):
            assert service_id == "fake_video"
            return SimpleNamespace(required_gate="AFS_ALLOW_REMOTE_VIDEO")

        def submit(self, capability: str, service_id: str, request):
            assert capability == "video"
            assert service_id == "fake_video"
            raise TypeError("unexpected adapter kwarg: model_name_override")

    monkeypatch.setattr(runtime_video_routes, "load_provider_registry", lambda: FailingRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-provider-internal-error"
    client.post("/projects", json={"project_id": project_id, "goal": "Video safe error guard"})
    asset_id = _upload_image(client, project_id)

    response = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "prompt_text": "A slow camera push in.",
            "provider_service_id": "fake_video",
            "first_frame_image_asset_id": asset_id,
            "duration_sec": 5,
            "resolution": "720p",
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["status"] == "poll_failed"
    assert payload["safe_manifest"]["status"] == "poll_failed"
    assert payload["provider_calls_started"] is True
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    assert "secret" not in serialized
    assert "token" not in serialized


def test_video_generation_policy_failure_writes_policy_block(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")

    class PolicyFailingRegistry:
        def descriptor(self, service_id: str):
            assert service_id == "fake_video"
            return SimpleNamespace(required_gate="AFS_ALLOW_REMOTE_VIDEO")

        def submit(self, capability: str, service_id: str, request):
            assert capability == "video"
            assert service_id == "fake_video"
            return {"task": {"status": "submitted", "task_id": "policy-task"}}

        def poll(self, capability: str, service_id: str, task):
            raise RuntimeError(
                "Seedance video policy block: output video may be related to copyright restrictions. "
                "Request id: raw-provider-id"
            )

    monkeypatch.setattr(runtime_video_routes, "load_provider_registry", lambda: PolicyFailingRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-policy-block"
    client.post("/projects", json={"project_id": project_id, "goal": "Video policy block"})
    asset_id = _upload_image(client, project_id)

    submitted = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "prompt_text": "A slow camera push in.",
            "provider_service_id": "fake_video",
            "first_frame_image_asset_id": asset_id,
            "duration_sec": 5,
            "resolution": "720p",
            "generated_at": "2026-06-13T10:00:00+08:00",
        },
    )
    job_id = submitted.json()["job"]["job_id"]
    polled = client.post(f"/projects/{project_id}/video-generations/{job_id}/poll")

    assert polled.status_code == 200
    payload = polled.json()
    block = payload["safe_manifest"]["blocks"][0]
    assert block["block_id"] == "remote_video_policy_block"
    assert "copyright restrictions" in block["reason"]
    assert "raw-provider-id" not in json.dumps(payload, ensure_ascii=False)


def _fake_video_provider_config(tmp_path) -> str:
    payload = {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "fake_video_account": {
                "auth_type": "none",
                "base_url": "https://video.example.test",
                "default_models": {"video": "fake-video"},
            }
        },
        "account_pools": {
            "video_pool": {
                "accounts": [
                    {
                        "account_id": "fake_video_account",
                        "service_id": "fake_video",
                        "enabled_capabilities": ["video"],
                        "enabled": True,
                        "priority": 10,
                        "weight": 1,
                        "concurrency_limit": 1,
                        "health_state": "healthy",
                    }
                ]
            }
        },
        "services": {
            "fake_video": {
                "provider": "fake",
                "account_ref": "fake_video_account",
                "capability": "video",
                "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.2",
                    "modality": "video",
                    "execution_mode": "async",
                    "capabilities": ["video"],
                    "account_pool_id": "video_pool",
                    "reference_image_slots": 1,
                    "supported_aspect_ratios": ["16:9", "9:16"],
                    "prompt_char_limit": 2000,
                    "seed_supported": False,
                    "cost_hint": "fake-only",
                    "rate_limit_hint": "fake-only",
                    "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                    "frame_slots": {"first_frame": "required"},
                    "frame_modes": ["first_frame"],
                    "supported_durations_sec": [5],
                    "supported_resolutions": ["720p"],
                    "async_poll_interval_sec": 0.1,
                    "async_timeout_sec": 10,
                    "async_max_polls": 1,
                    "prompt_profile": "video_i2v_v1",
                    "cost_estimate": {"unit": "task"},
                },
            }
        },
    }
    path = tmp_path / "providers.local.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_video_generation_response_exposes_structured_generation_plan_when_gate_closed(tmp_path, monkeypatch) -> None:
    config = _fake_video_provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config))
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-generation-plan-gate-closed"
    client.post("/projects", json={"project_id": project_id, "goal": "Video plan without provider"})
    asset_id = _upload_image(client, project_id)

    response = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "node_id": "video_plan_1",
            "prompt_text": "A future robot watches stars on a rural rooftop.",
            "optimized_prompt": "Generate a continuous 5s video from the keyframe.",
            "provider_service_id": "fake_video",
            "first_frame_image_asset_id": asset_id,
            "duration_sec": 5,
            "resolution": "720p",
            "motion": "The robot slowly raises its glowing face toward the sky.",
            "generated_at": "2026-06-27T10:15:00+08:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job"]["status"] == "blocked"
    plan = payload["video_generation_plan"]
    assert plan["motion_plan"]["time_beats"][1]["time"] == "1.0s-3.5s"
    assert "unrequested eaves" in plan["editing_plan"]["forbidden_changes"]

    request_plan = client.get(f"/artifacts/{payload['artifacts']['model_request_plan']['artifact_id']}").json()["payload"]
    assert request_plan["generation_plan"] == plan


def test_video_generation_response_exposes_professional_reference(tmp_path, monkeypatch) -> None:
    config = _fake_video_provider_config(tmp_path)
    monkeypatch.setenv("AFS_PROVIDER_CONFIG", str(config))
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "video-generation-prof-ref"
    client.post("/projects", json={"project_id": project_id, "goal": "Video professional reference"})
    asset_id = _upload_image(client, project_id)

    response = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "node_id": "video_prof_ref_1",
            "prompt_text": "A future robot watches stars on a rural rooftop.",
            "optimized_prompt": "Generate a continuous 5s video from the keyframe.",
            "provider_service_id": "fake_video",
            "first_frame_image_asset_id": asset_id,
            "duration_sec": 5,
            "resolution": "720p",
            "motion": "The robot slowly raises its glowing face toward the sky.",
            "generated_at": "2026-06-27T10:30:00+08:00",
        },
    )

    assert response.status_code == 200
    plan = response.json()["video_generation_plan"]
    reference = plan["professional_reference"]
    assert {"night", "rooftop", "video"} <= set(reference["tags"])
    assert "moderate-to-deep" in reference["depth_of_field"]["decision"]
    assert reference["writes_company_kb"] is False
