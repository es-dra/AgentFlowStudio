from __future__ import annotations

import base64
import io
import json
from types import SimpleNamespace
import urllib.error
import socket

import pytest
from fastapi.testclient import TestClient

from agentflow_studio.model_gateway.company_secrets import load_company_provider_secrets
from agentflow_studio.model_gateway.errors import (
    ModelConfigError,
    ModelGatewayError,
    ModelProviderError,
)
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, ProviderRegistry
from agentflow_studio.model_gateway import volc_seedance_video
from apps.api import runtime_video_routes
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import reject_unsafe_payload
from apps.api.runtime_video_task_state import provider_task_for_state


PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


@pytest.fixture(autouse=True)
def _public_test_dns(monkeypatch) -> None:
    monkeypatch.setattr(
        "agentflow_studio.model_gateway.volc_seedance_video.socket.getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 443))
        ],
    )


def test_provider_registry_builds_seedance_example_descriptor() -> None:
    store = load_company_provider_secrets("configs/providers.example.json")
    registry = ProviderRegistry.from_store(store)

    descriptor = registry.descriptor("seedance_i2v")

    assert descriptor.modality == "video"
    assert descriptor.required_gate == "AFS_ALLOW_REMOTE_VIDEO"
    assert descriptor.frame_slots == {"first_frame": "required", "last_frame": "optional"}
    assert descriptor.reference_image_slots == 4
    assert descriptor.frame_modes == ["first_frame", "first_last_frame", "reference_images"]
    assert descriptor.supported_durations_sec == list(range(4, 16))
    assert descriptor.supported_resolutions == ["480p", "720p"]
    assert store.services["seedance_i2v"]["provider"] == "volc_seedance"


def test_seedance_video_dispatch_builds_task_payload_and_downloads_safe_output(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}
    first = tmp_path / "first.png"
    last = tmp_path / "last.png"
    first.write_bytes(PNG_BYTES)
    last.write_bytes(PNG_BYTES)

    def fake_urlopen(request, timeout):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if url == "https://relay.test/v1/files/uploads/base64":
            return _upload_response()
        if url == "https://relay.test/volc/v1/contents/generations/tasks":
            captured["create_auth"] = request.get_header("Authorization")
            captured["create_payload"] = json.loads(request.data.decode("utf-8"))
            captured["create_timeout"] = timeout
            return _JsonResponse({"id": "cgt-seedance-123", "status": "queued"})
        if url == "https://relay.test/volc/v1/contents/generations/tasks/cgt-seedance-123":
            captured["poll_auth"] = request.get_header("Authorization")
            return _JsonResponse(
                    {
                        "id": "cgt-seedance-123",
                        "status": "succeeded",
                        "content": {"video_url": "https://media.seedance.test/result.mp4"},
                        "usage": {"output_tokens": 4321, "total_tokens": 5000},
                        }
                )
        if url == "https://media.seedance.test/result.mp4":
            captured["download_timeout"] = timeout
            return _BytesResponse(b"fake-seedance-video", "video/mp4")
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("agentflow_studio.model_gateway.volc_seedance_video.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(
        volc_seedance_video,
        "_PinnedHTTPSConnection",
        lambda host, port, *, addresses, timeout: _FakePinnedConnection(
            _PinnedResponse(b"fake-seedance-video", "video/mp4"),
            on_request=lambda: captured.update(download_timeout=timeout),
        ),
    )
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "secret-video-key")
    registry = ProviderRegistry.from_store(load_company_provider_secrets(_seedance_provider_config(tmp_path)))

    result = registry.dispatch(
        "video",
        "seedance_i2v",
        ProviderDispatchRequest(
            prompt="A controlled cinematic move from first to last frame.",
            output_dir=tmp_path / "run",
            aspect_ratio="16:9",
            reference_image_paths=(first, last),
            subject_reference_image_path=first,
            duration_sec=5,
            resolution="720p",
        ),
    )

    payload = captured["create_payload"]
    assert captured["create_auth"] == "Bearer secret-video-key"
    assert captured["poll_auth"] == "Bearer secret-video-key"
    assert captured["create_timeout"] == 900.0
    assert captured["download_timeout"] == 180.0
    assert payload["model"] == "doubao-seedance-2-0"
    assert payload["ratio"] == "16:9"
    assert payload["duration"] == 5
    assert payload["resolution"] == "720p"
    assert payload["watermark"] is False
    assert "max_output_tokens" not in payload
    assert payload["content"][0] == {"type": "text", "text": "A controlled cinematic move from first to last frame."}
    assert payload["content"][1]["role"] == "first_frame"
    assert payload["content"][2]["role"] == "last_frame"
    assert payload["content"][1]["image_url"]["url"].startswith(
        "https://media.seedance.test/task-artifacts/tmp-inputs/"
    )
    assert result["status"] == "succeeded"
    assert result["usage"]["output_tokens"] == 4321
    assert result["billing"] == {
        "provider_reported_cost": False,
        "billing_mode": "output_tokens",
        "model": "doubao-seedance-2-0",
        "duration_sec": 5,
        "resolution": "720p",
        "output_tokens": 4321,
    }
    assert result["outputs"][0]["video_path"] == "video_candidates/candidate_001.mp4"
    assert (tmp_path / "run" / "video_candidates" / "candidate_001.mp4").read_bytes() == b"fake-seedance-video"
    assert "secret-video-key" not in json.dumps(result, ensure_ascii=False)
    assert "media.seedance.test" not in json.dumps(result, ensure_ascii=False)


def test_seedance_video_rejects_fast_or_alias_model_before_network(tmp_path, monkeypatch) -> None:
    first = tmp_path / "first.png"
    first.write_bytes(PNG_BYTES)
    network_calls = 0

    def forbidden_urlopen(*args, **kwargs):
        nonlocal network_calls
        network_calls += 1
        raise AssertionError("wrong Seedance model must fail before network")

    monkeypatch.setattr("agentflow_studio.model_gateway.volc_seedance_video.urllib.request.urlopen", forbidden_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "secret-video-key")
    registry = ProviderRegistry.from_store(
        load_company_provider_secrets(
            _seedance_provider_config(tmp_path, model="doubao-seedance-2-0-fast")
        )
    )

    with pytest.raises(ModelGatewayError, match="exact non-fast model"):
        registry.dispatch(
            "video",
            "seedance_i2v",
            ProviderDispatchRequest(
                prompt="A controlled cinematic move.",
                output_dir=tmp_path / "run",
                aspect_ratio="16:9",
                reference_image_paths=(first,),
                duration_sec=5,
                resolution="720p",
            ),
        )
    assert network_calls == 0


def test_seedance_video_rejects_extra_body_model_override_before_network(tmp_path, monkeypatch) -> None:
    first = tmp_path / "first.png"
    first.write_bytes(PNG_BYTES)
    network_calls = 0

    def forbidden_urlopen(*args, **kwargs):
        nonlocal network_calls
        network_calls += 1
        raise AssertionError("extra_body model override must fail before network")

    monkeypatch.setattr("agentflow_studio.model_gateway.volc_seedance_video.urllib.request.urlopen", forbidden_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "secret-video-key")
    registry = ProviderRegistry.from_store(
        load_company_provider_secrets(
            _seedance_provider_config(
                tmp_path,
                extra_body={"model": "doubao-seedance-2-0-fast"},
            )
        )
    )

    with pytest.raises(ModelGatewayError, match="extra_body cannot override request field: model"):
        registry.dispatch(
            "video",
            "seedance_i2v",
            ProviderDispatchRequest(
                prompt="A controlled cinematic move.",
                output_dir=tmp_path / "run",
                aspect_ratio="16:9",
                reference_image_paths=(first,),
                duration_sec=5,
                resolution="720p",
            ),
        )
    assert network_calls == 0


def test_seedance_video_rejects_unsupported_output_limit_field_before_network(
    tmp_path,
    monkeypatch,
) -> None:
    first = tmp_path / "first.png"
    first.write_bytes(PNG_BYTES)
    called = 0

    def forbidden(*_args, **_kwargs):
        nonlocal called
        called += 1
        raise AssertionError("unsupported request field must fail before network")

    monkeypatch.setattr(volc_seedance_video.urllib.request, "urlopen", forbidden)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "test-only")
    registry = ProviderRegistry.from_store(
        load_company_provider_secrets(
            _seedance_provider_config(
                tmp_path,
                extra_body={"max_output_tokens": 100},
            )
        )
    )
    with pytest.raises(ModelGatewayError, match="public request contract"):
        registry.submit(
            "video",
            "seedance_i2v",
            ProviderDispatchRequest(
                prompt="public contract only",
                output_dir=tmp_path / "run",
                aspect_ratio="16:9",
                reference_image_paths=(first,),
                duration_sec=5,
                resolution="720p",
            ),
        )
    assert called == 0


def test_seedance_video_rejects_non_native_create_endpoint_before_network(tmp_path, monkeypatch) -> None:
    first = tmp_path / "first.png"
    first.write_bytes(PNG_BYTES)
    config_path = _seedance_provider_config(tmp_path)
    config = json.loads((tmp_path / "providers.local.json").read_text(encoding="utf-8"))
    config["services"]["seedance_i2v"]["endpoint"] = "/v1/videos"
    (tmp_path / "providers.local.json").write_text(json.dumps(config), encoding="utf-8")
    network_calls = 0

    def forbidden_urlopen(*args, **kwargs):
        nonlocal network_calls
        network_calls += 1
        raise AssertionError("non-native endpoint must fail before network")

    monkeypatch.setattr(
        "agentflow_studio.model_gateway.volc_seedance_video.urllib.request.urlopen",
        forbidden_urlopen,
    )
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "secret-video-key")
    registry = ProviderRegistry.from_store(load_company_provider_secrets(config_path))

    with pytest.raises(ModelGatewayError, match="native task endpoint"):
        registry.dispatch(
            "video",
            "seedance_i2v",
            ProviderDispatchRequest(
                prompt="A controlled cinematic move.",
                output_dir=tmp_path / "run",
                aspect_ratio="16:9",
                reference_image_paths=(first,),
                duration_sec=5,
                resolution="720p",
            ),
        )
    assert network_calls == 0


def test_seedance_readiness_payload_uses_six_seconds_and_reference_group(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}
    images = []
    for index in range(4):
        path = tmp_path / f"reference-{index}.png"
        path.write_bytes(PNG_BYTES)
        images.append(path)
    config_path = _seedance_provider_config(tmp_path)
    config = json.loads((tmp_path / "providers.local.json").read_text(encoding="utf-8"))
    service = config["services"]["seedance_i2v"]
    service["reference_roles"] = [
        "first_frame",
        "reference_image",
        "reference_image",
        "reference_image",
    ]
    descriptor = service["descriptor"]
    descriptor["reference_image_slots"] = 4
    descriptor["frame_modes"] = ["first_frame", "first_last_frame", "reference_images"]
    descriptor["supported_durations_sec"] = [6]
    (tmp_path / "providers.local.json").write_text(json.dumps(config), encoding="utf-8")

    def fake_urlopen(request, timeout):
        if request.full_url == "https://relay.test/v1/files/uploads/base64":
            return _upload_response()
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _JsonResponse({"id": "seedance-readiness-task", "status": "queued"})

    monkeypatch.setattr(
        "agentflow_studio.model_gateway.volc_seedance_video.urllib.request.urlopen",
        fake_urlopen,
    )
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "secret-video-key")
    registry = ProviderRegistry.from_store(load_company_provider_secrets(config_path))
    result = registry.submit(
        "video",
        "seedance_i2v",
        ProviderDispatchRequest(
            prompt="Preserve the approved canonical shot and references.",
            output_dir=tmp_path / "run",
            aspect_ratio="16:9",
            reference_image_paths=tuple(images),
            subject_reference_image_path=images[0],
            duration_sec=6,
            resolution="720p",
            input_mode="reference_images",
            model_name_override="doubao-seedance-2-0",
        ),
    )

    payload = captured["payload"]
    assert captured["url"] == "https://relay.test/volc/v1/contents/generations/tasks"
    assert payload["model"] == "doubao-seedance-2-0"
    assert payload["duration"] == 6
    assert payload["resolution"] == "720p"
    assert [item["role"] for item in payload["content"][1:]] == [
        "reference_image",
        "reference_image",
        "reference_image",
        "reference_image",
    ]
    assert result["task"]["input_upload_count"] == 4
    assert result["task"]["status"] == "submitted"


def test_seedance_first_frame_mode_rejects_mixed_image_cardinality_before_network(
    tmp_path,
    monkeypatch,
) -> None:
    first = tmp_path / "first.png"
    other = tmp_path / "other.png"
    first.write_bytes(PNG_BYTES)
    other.write_bytes(PNG_BYTES)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "secret-video-key")
    called = 0

    def forbidden(*_args, **_kwargs):
        nonlocal called
        called += 1
        raise AssertionError("mixed first-frame request must fail before upload or submit")

    monkeypatch.setattr(volc_seedance_video.urllib.request, "urlopen", forbidden)
    registry = ProviderRegistry.from_store(
        load_company_provider_secrets(_seedance_provider_config(tmp_path))
    )

    with pytest.raises(ModelGatewayError, match="requires exactly one image"):
        registry.submit(
            "video",
            "seedance_i2v",
            ProviderDispatchRequest(
                prompt="Animate only the approved first frame.",
                output_dir=tmp_path / "run",
                aspect_ratio="16:9",
                reference_image_paths=(first, other),
                duration_sec=5,
                resolution="720p",
                input_mode="first_frame",
            ),
        )
    assert called == 0


def test_seedance_text_only_role_contract_has_zero_images() -> None:
    assert volc_seedance_video._frame_roles("text_only", 0) == ()
    with pytest.raises(
        ModelConfigError,
        match="text_only mode cannot include images",
    ):
        volc_seedance_video._frame_roles("text_only", 1)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("mime_type", "", "MIME type"),
        ("size", len(PNG_BYTES) - 1, "byte count"),
        ("expires_at", "2026-07-27T00:00:00Z", "expiry"),
    ],
)
def test_seedance_input_upload_receipt_fails_closed_on_invalid_metadata(
    field,
    value,
    message,
) -> None:
    response = dict(_upload_response().payload)
    response[field] = value
    with pytest.raises(ModelGatewayError, match=message):
        volc_seedance_video._validated_input_url(
            response,
            ("media.seedance.test",),
            expected_mime_type="image/png",
            expected_byte_count=len(PNG_BYTES),
        )


def test_seedance_input_upload_receipt_rejects_similar_host() -> None:
    response = dict(_upload_response().payload)
    response["url"] = (
        "https://media.seedance.test.attacker.invalid/"
        "task-artifacts/tmp-inputs/2026/07/27/test/reference.png"
    )
    with pytest.raises(ModelGatewayError, match="unapproved URL"):
        volc_seedance_video._validated_input_url(
            response,
            ("media.seedance.test",),
            expected_mime_type="image/png",
            expected_byte_count=len(PNG_BYTES),
        )


def test_seedance_poll_treats_not_start_as_running(tmp_path, monkeypatch) -> None:
    first = tmp_path / "first.png"
    first.write_bytes(PNG_BYTES)

    def fake_urlopen(request, timeout):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if url == "https://relay.test/v1/files/uploads/base64":
            return _upload_response()
        if url == "https://relay.test/volc/v1/contents/generations/tasks":
            return _JsonResponse({"id": "cgt-seedance-not-start", "status": "queued"})
        if url == "https://relay.test/volc/v1/contents/generations/tasks/cgt-seedance-not-start":
            return _JsonResponse({"id": "cgt-seedance-not-start", "status": "not_start"})
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("agentflow_studio.model_gateway.volc_seedance_video.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(
        volc_seedance_video,
        "_PinnedHTTPSConnection",
        lambda *_args, **_kwargs: _FakePinnedConnection(
            _PinnedResponse(b"fake-seedance-video", "video/mp4")
        ),
    )
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "secret-video-key")
    registry = ProviderRegistry.from_store(load_company_provider_secrets(_seedance_provider_config(tmp_path)))

    task = registry.submit(
        "video",
        "seedance_i2v",
        ProviderDispatchRequest(
            prompt="A controlled cinematic move from the first frame.",
            output_dir=tmp_path / "run",
            aspect_ratio="16:9",
            reference_image_paths=(first,),
            subject_reference_image_path=first,
            duration_sec=5,
            resolution="720p",
        ),
    )

    result = registry.poll("video", "seedance_i2v", task)

    assert result == {"status": "running", "task": {"task_id": "cgt-seedance-not-start"}}


def test_seedance_submit_task_state_is_safe_and_poll_rehydrates_credential(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}
    first = tmp_path / "first.png"
    first.write_bytes(PNG_BYTES)

    def fake_urlopen(request, timeout):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if url == "https://relay.test/v1/files/uploads/base64":
            return _upload_response()
        if url == "https://relay.test/volc/v1/contents/generations/tasks":
            captured["create_auth"] = request.get_header("Authorization")
            return _JsonResponse({"id": "cgt-seedance-safe-task", "status": "queued"})
        if url == "https://relay.test/volc/v1/contents/generations/tasks/cgt-seedance-safe-task":
            captured["poll_auth"] = request.get_header("Authorization")
            return _JsonResponse(
                {
                    "id": "cgt-seedance-safe-task",
                    "status": "succeeded",
                    "content": {"video_url": "https://media.seedance.test/result.mp4"},
                }
            )
        if url == "https://media.seedance.test/result.mp4":
            return _BytesResponse(b"fake-seedance-video", "video/mp4")
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("agentflow_studio.model_gateway.volc_seedance_video.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr(
        volc_seedance_video,
        "_PinnedHTTPSConnection",
        lambda *_args, **_kwargs: _FakePinnedConnection(
            _PinnedResponse(b"fake-seedance-video", "video/mp4")
        ),
    )
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "secret-video-key")
    registry = ProviderRegistry.from_store(load_company_provider_secrets(_seedance_provider_config(tmp_path)))

    task = registry.submit(
        "video",
        "seedance_i2v",
        ProviderDispatchRequest(
            prompt="A controlled cinematic move from the first frame.",
            output_dir=tmp_path / "run",
            aspect_ratio="16:9",
            reference_image_paths=(first,),
            subject_reference_image_path=first,
            duration_sec=5,
            resolution="720p",
        ),
    )

    persisted_task = provider_task_for_state(task)
    serialized_persisted_task = json.dumps(persisted_task, ensure_ascii=False).lower()
    assert "secret-video-key" not in serialized_persisted_task
    assert "api_key" not in serialized_persisted_task
    reject_unsafe_payload({"task": persisted_task})

    result = registry.poll("video", "seedance_i2v", task)

    assert captured["create_auth"] == "Bearer secret-video-key"
    assert captured["poll_auth"] == "Bearer secret-video-key"
    assert result["status"] == "succeeded"


def test_seedance_poll_reports_policy_failure_safely(tmp_path, monkeypatch) -> None:
    first = tmp_path / "first.png"
    first.write_bytes(PNG_BYTES)

    def fake_urlopen(request, timeout):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        if url == "https://relay.test/v1/files/uploads/base64":
            return _upload_response()
        if url == "https://relay.test/volc/v1/contents/generations/tasks":
            return _JsonResponse({"id": "cgt-seedance-policy-task", "status": "queued"})
        if url == "https://relay.test/volc/v1/contents/generations/tasks/cgt-seedance-policy-task":
            return _JsonResponse(
                {
                    "code": "success",
                    "data": {
                        "status": "FAILURE",
                        "fail_reason": "task failed",
                        "data": {
                            "error": {
                                "code": "OutputVideoSensitiveContentDetected.PolicyViolation",
                                "message": (
                                    "The request failed because the output video may be related "
                                    "to copyright restrictions. Request id: raw-provider-id"
                                ),
                            }
                        },
                    },
                }
            )
        raise AssertionError(f"unexpected URL: {url}")

    monkeypatch.setattr("agentflow_studio.model_gateway.volc_seedance_video.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "secret-video-key")
    registry = ProviderRegistry.from_store(load_company_provider_secrets(_seedance_provider_config(tmp_path)))

    task = registry.submit(
        "video",
        "seedance_i2v",
        ProviderDispatchRequest(
            prompt="A controlled cinematic move from the first frame.",
            output_dir=tmp_path / "run",
            aspect_ratio="16:9",
            reference_image_paths=(first,),
            subject_reference_image_path=first,
            duration_sec=5,
            resolution="720p",
        ),
    )

    with pytest.raises(ModelProviderError) as exc_info:
        registry.poll("video", "seedance_i2v", task)

    message = str(exc_info.value)
    assert "copyright restrictions" in message
    assert "raw-provider-id" not in message
    assert "secret-video-key" not in message


def test_seedance_submit_http_error_attaches_safe_provider_summary(tmp_path, monkeypatch) -> None:
    first = tmp_path / "first.png"
    first.write_bytes(PNG_BYTES)

    def fake_urlopen(request, timeout):
        body = json.dumps(
            {
                "error": {
                    "code": "InvalidParameter",
                    "message": "reference image format is unsupported. Request id: raw-provider-id",
                },
                "request_id": "raw-provider-id",
            }
        ).encode("utf-8")
        raise urllib.error.HTTPError(
            request.full_url,
            400,
            "Bad Request",
            hdrs=None,
            fp=io.BytesIO(body),
        )

    monkeypatch.setattr("agentflow_studio.model_gateway.volc_seedance_video.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "secret-video-key")
    registry = ProviderRegistry.from_store(load_company_provider_secrets(_seedance_provider_config(tmp_path)))

    with pytest.raises(ModelGatewayError) as exc_info:
        registry.submit(
            "video",
            "seedance_i2v",
            ProviderDispatchRequest(
                prompt="A controlled cinematic move from the first frame.",
                output_dir=tmp_path / "run",
                aspect_ratio="16:9",
                reference_image_paths=(first,),
                subject_reference_image_path=first,
                duration_sec=5,
                resolution="720p",
            ),
        )

    message = str(exc_info.value)
    summary = exc_info.value.provider_error_summary
    assert "Seedance video HTTP error 400" in message
    assert "reference image format is unsupported" in message
    assert summary["provider_http_status"] == 400
    assert summary["provider_error_code"] == "InvalidParameter"
    assert summary["provider_error_message"] == "reference image format is unsupported."
    assert summary["provider_raw_response_stored"] is False
    serialized = json.dumps({"message": message, "summary": summary}, ensure_ascii=False)
    assert "raw-provider-id" not in serialized
    assert "secret-video-key" not in serialized


def test_seedance_video_gate_blocks_before_network(tmp_path, monkeypatch) -> None:
    called = {"count": 0}

    def fake_urlopen(*_args, **_kwargs):
        called["count"] += 1
        raise AssertionError("network must not be called while video gate is closed")

    monkeypatch.setattr("agentflow_studio.model_gateway.volc_seedance_video.urllib.request.urlopen", fake_urlopen)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "secret-video-key")
    registry = ProviderRegistry.from_store(load_company_provider_secrets(_seedance_provider_config(tmp_path)))

    with pytest.raises(ModelGatewayError, match="AFS_ALLOW_REMOTE_VIDEO"):
        registry.dispatch(
            "video",
            "seedance_i2v",
            ProviderDispatchRequest(prompt="blocked", output_dir=tmp_path, aspect_ratio="16:9"),
        )

    assert called["count"] == 0


@pytest.mark.parametrize(
    ("url", "allowlist"),
    [
        ("http://media.seedance.test/result.mp4", ("media.seedance.test",)),
        ("file:///tmp/result.mp4", ("media.seedance.test",)),
        ("https://127.0.0.1/result.mp4", ("127.0.0.1",)),
        ("https://media.seedance.test.evil.test/result.mp4", ("media.seedance.test",)),
        ("https://media.seedance.test/result.mp4", ()),
    ],
)
def test_seedance_artifact_download_rejects_unsafe_urls_before_network(
    url,
    allowlist,
    monkeypatch,
) -> None:
    called = 0

    def forbidden(*_args, **_kwargs):
        nonlocal called
        called += 1
        raise AssertionError("unsafe artifact URL must fail before network")

    monkeypatch.setattr(volc_seedance_video, "_PinnedHTTPSConnection", forbidden)
    with pytest.raises(ModelProviderError):
        volc_seedance_video._download_video(
            url,
            timeout_sec=5,
            allowed_url_hosts=allowlist,
        )
    assert called == 0


@pytest.mark.parametrize(
    "url",
    [
        "http://bucket.tos-cn-beijing.volces.com/result.mp4",
        "https://tos-cn-beijing.volces.com/result.mp4",
        "https://bucket.tos-cn-beijing.volces.com.evil.test/result.mp4",
        "https://bucket.evil-tos-cn-beijing.volces.com/result.mp4",
        "https://user@bucket.tos-cn-beijing.volces.com/result.mp4",
        "https://@bucket.tos-cn-beijing.volces.com/result.mp4",
        "https://user:@bucket.tos-cn-beijing.volces.com/result.mp4",
        "https://:password@bucket.tos-cn-beijing.volces.com/result.mp4",
        "https://bucket.tos-cn-beijing.volces.com.:443/result.mp4",
        "https://bucket.tos-cn-beijing.volces.com:444/result.mp4",
        "https://xn--bcher-kva.tos-cn-beijing.volces.com/result.mp4",
        "https://bücher.tos-cn-beijing.volces.com/result.mp4",
        "https://nested.bucket.tos-cn-beijing.volces.com/result.mp4",
    ],
)
def test_seedance_tos_artifact_policy_rejects_bypass_urls_before_network(
    url,
    monkeypatch,
) -> None:
    called = 0

    def forbidden(*_args, **_kwargs):
        nonlocal called
        called += 1
        raise AssertionError("unsafe TOS artifact URL must fail before network")

    monkeypatch.setattr(volc_seedance_video, "_PinnedHTTPSConnection", forbidden)
    with pytest.raises(ModelProviderError):
        volc_seedance_video._download_video(
            url,
            timeout_sec=5,
            allowed_url_host_suffixes=("tos-cn-beijing.volces.com",),
        )
    assert called == 0


def test_seedance_tos_artifact_policy_accepts_one_valid_bucket_label(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        volc_seedance_video,
        "_PinnedHTTPSConnection",
        lambda *_args, **_kwargs: _FakePinnedConnection(
            _PinnedResponse(b"valid-video", "video/mp4")
        ),
    )

    body, content_type = volc_seedance_video._download_video(
        "https://ark-acg-cn-beijing.tos-cn-beijing.volces.com/result.mp4?signature=redacted",
        timeout_sec=5,
        allowed_url_host_suffixes=("tos-cn-beijing.volces.com",),
    )

    assert body == b"valid-video"
    assert content_type == "video/mp4"


def test_seedance_poll_recovers_existing_task_with_current_artifact_policy(
    tmp_path,
    monkeypatch,
) -> None:
    output_dir = tmp_path / "existing-run"
    output_dir.mkdir()
    config = _seedance_provider_config(tmp_path)
    registry = ProviderRegistry.from_store(load_company_provider_secrets(config))
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "secret-video-key")
    monkeypatch.setattr(
        volc_seedance_video,
        "_request_json",
        lambda *_args, **_kwargs: {
            "id": "existing-task",
            "status": "succeeded",
            "content": {
                "video_url": (
                    "https://ark-acg-cn-beijing.tos-cn-beijing.volces.com/"
                    "existing.mp4?signature=redacted"
                )
            },
        },
    )
    monkeypatch.setattr(
        volc_seedance_video,
        "_PinnedHTTPSConnection",
        lambda *_args, **_kwargs: _FakePinnedConnection(
            _PinnedResponse(b"existing-task-video", "video/mp4")
        ),
    )
    legacy_task = {
        "service_id": "seedance_i2v",
        "capability": "video",
        "task": {
            "task_id": "existing-task",
            "query_url_template": (
                "https://relay.test/volc/v1/contents/generations/tasks/{id}"
            ),
            "allowed_url_hosts": ("media.seedance.test",),
            "output_dir": str(output_dir),
        },
    }

    result = registry.poll("video", "seedance_i2v", legacy_task)

    assert result["status"] == "succeeded"
    assert result["provider_raw_response_stored"] is False
    assert result["outputs"][0]["byte_count"] == len(b"existing-task-video")
    assert (output_dir / result["outputs"][0]["video_path"]).read_bytes() == (
        b"existing-task-video"
    )


def test_seedance_artifact_download_revalidates_each_allowed_redirect(
    monkeypatch,
) -> None:
    connections = iter(
        [
            _FakePinnedConnection(
                _PinnedResponse(
                    b"",
                    "text/plain",
                    status=302,
                    location="https://ark-acg-cn-beijing.tos-cn-beijing.volces.com/result.mp4",
                )
            ),
            _FakePinnedConnection(_PinnedResponse(b"redirected-video", "video/mp4")),
        ]
    )
    hosts: list[str] = []

    def connection(host, *_args, **_kwargs):
        hosts.append(host)
        return next(connections)

    monkeypatch.setattr(
        volc_seedance_video,
        "_PinnedHTTPSConnection",
        connection,
    )
    body, content_type = volc_seedance_video._download_video(
        "https://media.crazyrouter.com/result.mp4",
        timeout_sec=5,
        allowed_url_hosts=("media.crazyrouter.com",),
        allowed_url_host_suffixes=("tos-cn-beijing.volces.com",),
    )

    assert hosts == [
        "media.crazyrouter.com",
        "ark-acg-cn-beijing.tos-cn-beijing.volces.com",
    ]
    assert body == b"redirected-video"
    assert content_type == "video/mp4"


def test_seedance_artifact_download_rejects_redirect_outside_policy(
    monkeypatch,
) -> None:
    followed = 0

    def connection(*_args, **_kwargs):
        nonlocal followed
        followed += 1
        return _FakePinnedConnection(
            _PinnedResponse(
                b"",
                "text/plain",
                status=302,
                location="https://bucket.tos-cn-beijing.volces.com.evil.test/result.mp4",
            )
        )

    monkeypatch.setattr(volc_seedance_video, "_PinnedHTTPSConnection", connection)
    with pytest.raises(ModelProviderError, match="URL is not allowed"):
        volc_seedance_video._download_video(
            "https://media.crazyrouter.com/result.mp4",
            timeout_sec=5,
            allowed_url_hosts=("media.crazyrouter.com",),
            allowed_url_host_suffixes=("tos-cn-beijing.volces.com",),
        )
    assert followed == 1


def test_seedance_artifact_download_rejects_private_dns_resolution(monkeypatch) -> None:
    called = 0

    def forbidden(*_args, **_kwargs):
        nonlocal called
        called += 1
        raise AssertionError("private DNS result must fail before download")

    monkeypatch.setattr(
        volc_seedance_video.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("169.254.10.20", 443))
        ],
    )
    monkeypatch.setattr(volc_seedance_video, "_PinnedHTTPSConnection", forbidden)
    with pytest.raises(ModelProviderError, match="public network"):
        volc_seedance_video._download_video(
            "https://media.seedance.test/result.mp4",
            timeout_sec=5,
            allowed_url_hosts=("media.seedance.test",),
        )
    assert called == 0


def test_seedance_pinned_connection_uses_validated_socket_without_dns_reresolution(
    monkeypatch,
) -> None:
    connected: list[tuple[str, int]] = []

    class RawSocket:
        def settimeout(self, _timeout):
            return None

        def connect(self, sockaddr):
            connected.append(sockaddr)

        def close(self):
            return None

    class Context:
        def wrap_socket(self, raw, *, server_hostname):
            assert server_hostname == "media.seedance.test"
            return raw

    monkeypatch.setattr(
        volc_seedance_video.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("pinned connect must not resolve DNS again")
        ),
    )
    monkeypatch.setattr(
        volc_seedance_video.socket,
        "socket",
        lambda family, kind: RawSocket(),
    )
    connection = volc_seedance_video._PinnedHTTPSConnection(
        "media.seedance.test",
        443,
        addresses=((socket.AF_INET, ("8.8.8.8", 443)),),
        timeout=5,
    )
    connection._context = Context()
    connection.connect()

    assert connected == [("8.8.8.8", 443)]


def test_seedance_poll_rejects_unencoded_provider_task_path_before_network(
    tmp_path,
    monkeypatch,
) -> None:
    registry = ProviderRegistry.from_store(
        load_company_provider_secrets(_seedance_provider_config(tmp_path))
    )
    called = 0

    def forbidden(*_args, **_kwargs):
        nonlocal called
        called += 1
        raise AssertionError("invalid provider task identity must fail before network")

    monkeypatch.setattr(volc_seedance_video.urllib.request, "urlopen", forbidden)
    with pytest.raises(ModelGatewayError, match="task id is invalid"):
        registry.poll(
            "video",
            "seedance_i2v",
            {
                "task": {
                    "task_id": "../other-task?x=1",
                    "query_url_template": (
                        "https://relay.test/volc/v1/contents/generations/tasks/{id}"
                    ),
                }
            },
        )
    assert called == 0


def test_seedance_rejects_non_native_poll_endpoint_before_network(
    tmp_path,
    monkeypatch,
) -> None:
    config_path = _seedance_provider_config(tmp_path)
    config = json.loads((tmp_path / "providers.local.json").read_text(encoding="utf-8"))
    config["services"]["seedance_i2v"]["query_endpoint"] = "/v1/tasks/{id}"
    (tmp_path / "providers.local.json").write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "test-only")
    called = 0

    def forbidden(*_args, **_kwargs):
        nonlocal called
        called += 1
        raise AssertionError("non-native poll endpoint must fail before network")

    monkeypatch.setattr(volc_seedance_video.urllib.request, "urlopen", forbidden)
    registry = ProviderRegistry.from_store(load_company_provider_secrets(config_path))
    with pytest.raises(ModelGatewayError, match="native task poll endpoint"):
        registry.submit(
            "video",
            "seedance_i2v",
            ProviderDispatchRequest(
                prompt="native poll contract",
                output_dir=tmp_path / "run",
                aspect_ratio="16:9",
            ),
        )
    assert called == 0


def test_seedance_fails_closed_without_verified_pricing_exposure(
    tmp_path,
    monkeypatch,
) -> None:
    config_path = _seedance_provider_config(tmp_path)
    config = json.loads((tmp_path / "providers.local.json").read_text(encoding="utf-8"))
    config["services"]["seedance_i2v"]["pricing_exposure_contract"] = {
        "verification_state": "unverified",
        "billing_mode": "provider_output_tokens",
        "output_token_usd": None,
        "worst_case_output_tokens": None,
        "worst_case_cost_usd": None,
        "source_checked_at": None,
        "provider_enforced_cost_cap": False,
    }
    (tmp_path / "providers.local.json").write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setenv("AFS_VIDEO_RELAY_API_KEY", "test-only")
    registry = ProviderRegistry.from_store(load_company_provider_secrets(config_path))
    called = 0

    def forbidden(*_args, **_kwargs):
        nonlocal called
        called += 1
        raise AssertionError("unverified exposure must block before network")

    monkeypatch.setattr(volc_seedance_video.urllib.request, "urlopen", forbidden)
    with pytest.raises(ModelGatewayError, match="verified pricing"):
        registry.submit(
            "video",
            "seedance_i2v",
            ProviderDispatchRequest(
                prompt="budget contract",
                output_dir=tmp_path / "run",
                aspect_ratio="16:9",
            ),
        )
    assert called == 0


def test_runtime_seedance_generation_cannot_bypass_video_admission(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    class CaptureRegistry:
        def descriptor(self, service_id: str):
            assert service_id == "seedance_i2v"
            return SimpleNamespace(required_gate="AFS_ALLOW_REMOTE_VIDEO", min_reference_image_edge_px=0)

        def submit(self, capability: str, service_id: str, request):
            captured["capability"] = capability
            captured["service_id"] = service_id
            captured["reference_image_paths"] = tuple(request.reference_image_paths)
            return {"task": {"status": "already_complete", "raw": {"status": "succeeded", "outputs": []}}}

    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setattr(runtime_video_routes, "load_provider_registry", lambda: CaptureRegistry())
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "seedance-first-last-frame"
    client.post("/projects", json={"project_id": project_id, "goal": "Seedance first last frame"})
    first_id = _upload_image(client, project_id, "first_frame")
    last_id = _upload_image(client, project_id, "last_frame")
    request = {
        "prompt_text": "Move from first frame to last frame.",
        "provider_service_id": "seedance_i2v",
        "first_frame_image_asset_id": first_id,
        "last_frame_image_asset_id": last_id,
        "duration_sec": 5,
        "resolution": "720p",
        "aspect_ratio": "16:9",
        "generated_at": "2026-06-24T20:00:00+08:00",
    }
    preflight = client.post(f"/projects/{project_id}/video-generations/preflight", json=request)
    assert preflight.status_code == 200

    response = client.post(
        f"/projects/{project_id}/video-generations",
        json={**request, "preflight_token": preflight.json()["preflight_token"]},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["error"] == "video_admission_rejected"
    assert captured == {}


def _upload_image(client: TestClient, project_id: str, role: str) -> str:
    response = client.post(
        f"/projects/{project_id}/image-assets",
        json={
            "node_id": role,
            "filename": f"{role}.png",
            "mime_type": "image/png",
            "data_base64": base64.b64encode(PNG_BYTES).decode("ascii"),
            "role": role,
            "generated_at": "2026-06-24T20:00:00+08:00",
        },
    )
    assert response.status_code == 200
    return response.json()["asset"]["asset_id"]


def _seedance_provider_config(
    tmp_path,
    *,
    model: str = "doubao-seedance-2-0",
    extra_body: dict[str, object] | None = None,
) -> str:
    payload = {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "volc_seedance_relay": {
                "auth_type": "api_key",
                "base_url": "https://relay.test/v1",
                "api_key_env": "AFS_VIDEO_RELAY_API_KEY",
                "default_models": {"video": model},
            }
        },
        "account_pools": {
            "seedance_video_pool": {
                "accounts": [
                    {
                        "account_id": "volc_seedance_relay",
                        "service_id": "seedance_i2v",
                        "credential_env": "AFS_VIDEO_RELAY_API_KEY",
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
            "seedance_i2v": {
                "provider": "volc_seedance",
                "account_ref": "volc_seedance_relay",
                "capability": "video",
                "base_url": "https://relay.test",
                "endpoint": "/volc/v1/contents/generations/tasks",
                "query_endpoint": "/volc/v1/contents/generations/tasks/{id}",
                "model": model,
                "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                "reference_roles": ["first_frame", "last_frame"],
                "watermark": False,
                "allowed_artifact_hosts": ["media.seedance.test"],
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
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.2",
                    "modality": "video",
                    "execution_mode": "async",
                    "capabilities": ["video"],
                    "account_pool_id": "seedance_video_pool",
                    "reference_image_slots": 2,
                    "supported_aspect_ratios": ["16:9", "9:16"],
                    "prompt_char_limit": 5000,
                    "seed_supported": True,
                    "cost_hint": "test-only",
                    "rate_limit_hint": "test-only",
                    "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                    "frame_slots": {"first_frame": "required", "last_frame": "optional"},
                    "frame_modes": ["first_frame", "first_last_frame"],
                    "supported_durations_sec": [5, 10],
                    "supported_resolutions": ["480p", "720p"],
                    "async_poll_interval_sec": 5,
                    "async_timeout_sec": 900,
                    "async_max_polls": 180,
                    "prompt_profile": "video_i2v_v1",
                },
            }
        },
    }
    if extra_body is not None:
        payload["services"]["seedance_i2v"]["extra_body"] = extra_body
    path = tmp_path / "providers.local.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


class _JsonResponse:
    def __init__(self, payload: dict):
        self.payload = payload
        self.headers = {"Content-Type": "application/json"}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def geturl(self) -> str:
        return ""


def _upload_response() -> _JsonResponse:
    return _JsonResponse(
        {
            "id": "file_test_input",
            "url": (
                "https://media.seedance.test/task-artifacts/tmp-inputs/"
                "2026/07/27/test/reference.png"
            ),
            "mime_type": "image/png",
            "size": len(PNG_BYTES),
            "expires_at": "2099-07-29T00:00:00Z",
        }
    )


class _BytesResponse:
    def __init__(self, payload: bytes, content_type: str):
        self.payload = payload
        self.headers = {"Content-Type": content_type}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, *_args) -> bytes:
        return self.payload

    def geturl(self) -> str:
        return "https://media.seedance.test/result.mp4"


class _PinnedResponse:
    def __init__(
        self,
        payload: bytes,
        content_type: str,
        *,
        status: int = 200,
        location: str = "",
    ):
        self.payload = payload
        self.content_type = content_type
        self.status = status
        self.location = location

    def read(self) -> bytes:
        return self.payload

    def getheader(self, name: str) -> str:
        if name.lower() == "content-type":
            return self.content_type
        if name.lower() == "location":
            return self.location
        return ""


class _FakePinnedConnection:
    def __init__(self, response: _PinnedResponse, *, on_request=None):
        self.response = response
        self.on_request = on_request

    def request(self, *_args, **_kwargs) -> None:
        if self.on_request:
            self.on_request()

    def getresponse(self) -> _PinnedResponse:
        return self.response

    def close(self) -> None:
        return None
