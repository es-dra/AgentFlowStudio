from __future__ import annotations

from agentflow_studio.model_gateway import ModelProviderError
from agentflow_studio.model_gateway.kling_video_runtime import poll_video_task


def test_kling_poll_retries_transient_transport_error() -> None:
    calls = 0

    def request_json(url, *, method, authorization, timeout_sec, payload=None):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ModelProviderError(
                "GET request failed: CurlError(35): schannel: failed to receive handshake"
            )
        return {
            "code": 0,
            "data": {
                "task_id": "recoverable_i2v_task_789",
                "task_status": "succeed",
                "task_result": {"videos": [{"url": "https://signed.example/video.mp4"}]},
            },
        }

    result = poll_video_task(
        "https://safe.example/tasks/{id}",
        task_id="recoverable_i2v_task_789",
        authorization="Bearer fake-token",
        request_json=request_json,
        poll_interval_sec=0,
        max_polls=2,
        timeout_sec=1,
    )

    assert calls == 2
    assert result["task_status"] == "succeed"
