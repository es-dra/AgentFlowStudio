from __future__ import annotations

import json

from agentflow_studio.model_gateway import ModelProviderError
from agentflow_studio.model_gateway import kling_video_completion


def test_kling_completion_falls_back_from_httpx_to_curl_without_resubmitting(monkeypatch, tmp_path) -> None:
    output_dir = tmp_path / "run"
    output_dir.mkdir()
    state = {
        "schema_version": "kling_video_task_state.v1",
        "status": "submitted",
        "provider": "kling",
        "service_id": "kling_i2v",
        "api_family": "i2v",
        "capability": "video",
        "model": "kling-v3",
        "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
        "gate_status": "enabled",
        "input_image": {
            "path_persisted": False,
            "byte_count": 11,
            "sha256": "safe-source-image-hash",
        },
        "task": {
            "task_id": "recoverable_i2v_task_456",
            "task_status": "submitted",
            "task_status_msg_present": False,
        },
        "artifact_policy": {
            "provider_urls_persisted": False,
            "authorization_header_persisted": False,
            "jwt_persisted": False,
            "source_image_path_persisted": False,
            "writes_long_term_memory": False,
        },
        "claim_boundary": "provider_task_recovery_state_only_not_creative_quality",
    }
    calls: list[str] = []

    def fake_request_json_with_transport(transport: str):
        def request_json(url, *, method, authorization, payload=None, timeout_sec):
            calls.append(f"{transport}:{method}:{url}")
            if transport == "httpx":
                raise ModelProviderError("Kling video request failed: ConnectError")
            return {
                "code": 0,
                "data": {
                    "task_id": "recoverable_i2v_task_456",
                    "task_status": "succeed",
                    "task_result": {"videos": [{"url": "https://signed.example/i2v.mp4?token=secret"}]},
                },
            }

        return request_json

    def fake_download_with_transport(transport: str):
        def download(url, *, timeout_sec):
            calls.append(f"{transport}:GET:{url}")
            return b"fake-video-bytes", "video/mp4"

        return download

    monkeypatch.setattr(kling_video_completion, "request_json_with_transport", fake_request_json_with_transport)
    monkeypatch.setattr(kling_video_completion, "download_with_transport", fake_download_with_transport)

    manifest = kling_video_completion.complete_video_task_with_transport_fallback(
        output_dir,
        state=state,
        query_url_template="https://safe.example/tasks/{id}",
        authorization="Bearer fake-token",
        transport="httpx",
        poll_interval_sec=0,
        max_polls=1,
        timeout_sec=1,
        started=0,
        resumed_from_task_state=False,
    )

    assert manifest["status"] == "succeeded"
    assert calls[0] == "httpx:GET:https://safe.example/tasks/recoverable_i2v_task_456"
    assert calls[1] == "curl:GET:https://safe.example/tasks/recoverable_i2v_task_456"
    assert calls[2] == "curl:GET:https://signed.example/i2v.mp4?token=secret"
    assert (output_dir / "video_candidates" / "candidate_001.mp4").read_bytes() == b"fake-video-bytes"

    updated_state = json.loads((output_dir / "kling_i2v_task_state.json").read_text(encoding="utf-8"))
    assert updated_state["status"] == "succeeded"
    assert "last_error" not in updated_state
    serialized = json.dumps(
        json.loads((output_dir / "kling_i2v_smoke_manifest.json").read_text(encoding="utf-8")),
        ensure_ascii=False,
    )
    assert "Bearer " not in serialized
    assert "fake-token" not in serialized
    assert "signed.example" not in serialized
    assert "secret" not in serialized
