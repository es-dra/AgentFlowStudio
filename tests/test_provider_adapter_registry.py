from __future__ import annotations

import json
import subprocess
import base64
from pathlib import Path

import pytest

from agentflow_studio.model_gateway.company_secrets import load_company_provider_secrets
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, ProviderRegistry
from agentflow_studio.model_gateway import openai_compatible
from tests.provider_smoke_helpers import provider_config as legacy_kling_provider_config


def _store(tmp_path, payload: dict):
    path = tmp_path / "providers.local.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return load_company_provider_secrets(path)


def _codex_image_provider_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "local_codex": {
                "auth_type": "none",
                "execution_backend": "codex_exec",
                "cli_command": "codex",
                "default_models": {"image": "image2"},
            }
        },
        "account_pools": {
            "codex_image_pool": {
                "accounts": [
                    {
                        "account_id": "local_codex",
                        "service_id": "codex_image",
                        "enabled_capabilities": ["image"],
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
            "codex_image": {
                "provider": "codex_handoff",
                "account_ref": "local_codex",
                "capability": "image",
                "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.1",
                    "modality": "image",
                    "execution_mode": "async",
                    "capabilities": ["image"],
                    "account_pool_id": "codex_image_pool",
                    "reference_image_slots": 4,
                    "supported_aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16"],
                    "prompt_char_limit": 4000,
                    "seed_supported": True,
                    "cost_hint": "test-only",
                    "rate_limit_hint": "test-only",
                    "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
                },
            }
        },
    }


def test_provider_registry_rejects_missing_descriptor(tmp_path) -> None:
    payload = _codex_image_provider_config()
    payload["services"]["codex_image"].pop("descriptor", None)
    store = _store(tmp_path, payload)

    with pytest.raises(ModelConfigError, match="descriptor"):
        ProviderRegistry.from_store(store)


@pytest.mark.parametrize(
        ("field", "value", "match"),
        [
        ("required_gate", "IMAGE_API_KEY", "required_gate"),
        ("reference_image_slots", -1, "reference_image_slots"),
        ("supported_aspect_ratios", ["wide"], "supported_aspect_ratios"),
    ],
)
def test_provider_registry_rejects_invalid_descriptor_fields(tmp_path, field, value, match) -> None:
    payload = _codex_image_provider_config()
    payload["services"]["codex_image"]["descriptor"][field] = value
    store = _store(tmp_path, payload)

    with pytest.raises(ModelConfigError, match=match):
        ProviderRegistry.from_store(store)


def test_provider_registry_exposes_codex_image_descriptor(tmp_path) -> None:
    store = _store(tmp_path, _codex_image_provider_config())
    registry = ProviderRegistry.from_store(store)

    descriptor = registry.descriptor("codex_image")

    assert descriptor.modality == "image"
    assert descriptor.capabilities == ["image"]
    assert descriptor.execution_mode == "async"
    assert descriptor.account_pool_id == "codex_image_pool"
    assert descriptor.reference_image_slots == 4
    assert descriptor.prompt_char_limit == 4000
    assert descriptor.rate_limit_hint == "test-only"
    assert descriptor.required_gate == "AFS_ALLOW_REMOTE_IMAGE"


def test_provider_registry_normalizes_legacy_narratocut_gate_prefix(tmp_path) -> None:
    payload = _codex_image_provider_config()
    payload["services"]["codex_image"]["descriptor"]["required_gate"] = "NARRATOCUT_ALLOW_REMOTE_IMAGE"
    store = _store(tmp_path, payload)

    registry = ProviderRegistry.from_store(store)

    assert registry.descriptor("codex_image").required_gate == "AFS_ALLOW_REMOTE_IMAGE"


def test_provider_registry_ignores_company_gateway_aggregate_service(tmp_path) -> None:
    payload = _codex_image_provider_config()
    payload["services"]["company_gateway"] = {
        "provider": "company_gateway",
        "capability": "llm/asr/image/video",
        "required_gate": "task_specific_capability_gate",
        "descriptor": {
            "schema_version": "provider_descriptor.v0.1",
            "modality": "llm/asr/image/video",
            "execution_mode": "sync",
            "capabilities": ["llm", "image", "video", "asr"],
            "reference_image_slots": 0,
            "supported_aspect_ratios": ["1:1"],
            "prompt_char_limit": 12000,
            "seed_supported": False,
            "required_gate": "task_specific_capability_gate",
        },
    }
    store = _store(tmp_path, payload)

    registry = ProviderRegistry.from_store(store)

    assert registry.descriptor("codex_image").modality == "image"
    with pytest.raises(ModelConfigError, match="Provider service not found: company_gateway"):
        registry.descriptor("company_gateway")


def test_provider_registry_rejects_disabled_account_pool_entry(tmp_path, monkeypatch) -> None:
    payload = _codex_image_provider_config()
    payload["account_pools"]["codex_image_pool"]["accounts"][0]["enabled"] = False
    store = _store(tmp_path, payload)
    registry = ProviderRegistry.from_store(store)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")

    with pytest.raises(ModelConfigError, match="No enabled provider account"):
        registry.dispatch(
            "image",
            "codex_image",
            ProviderDispatchRequest(prompt="hello", output_dir=tmp_path, aspect_ratio="9:16"),
        )


def test_provider_registry_ignores_removed_minimax_provider_services(tmp_path) -> None:
    payload = _codex_image_provider_config()
    payload["accounts"]["old_image"] = {
        "auth_type": "api_key",
        "base_url": "https://image-provider.example.invalid",
        "api_key_env": "OLD_IMAGE_API_KEY",
        "default_models": {"image": "retired"},
    }
    payload["account_pools"]["old_image_pool"] = {
        "accounts": [
            {
                "account_id": "old_image",
                "service_id": "old_image",
                "enabled_capabilities": ["image"],
                "enabled": True,
                "priority": 10,
                "weight": 1,
                "concurrency_limit": 1,
                "health_state": "healthy",
            }
        ]
    }
    payload["services"]["old_image"] = {
        "provider": "minimax",
        "account_ref": "old_image",
        "capability": "image",
        "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
        "descriptor": {
            "schema_version": "provider_descriptor.v0.1",
            "modality": "image",
            "execution_mode": "sync",
            "capabilities": ["image"],
            "account_pool_id": "old_image_pool",
            "reference_image_slots": 1,
            "supported_aspect_ratios": ["9:16"],
            "prompt_char_limit": 1500,
            "seed_supported": True,
            "cost_hint": "retired",
            "rate_limit_hint": "retired",
            "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
        },
    }
    store = _store(tmp_path, payload)
    registry = ProviderRegistry.from_store(store)

    with pytest.raises(ModelConfigError, match="Provider service not found: old_image"):
        registry.descriptor("old_image")



def test_provider_registry_dispatches_openai_compatible_llm(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_send(self, payload, api_key):
        captured["payload"] = payload
        captured["api_key"] = api_key
        return {"choices": [{"message": {"content": "enhanced text"}}]}

    monkeypatch.setattr(openai_compatible.OpenAICompatibleProvider, "_send_request", fake_send)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_TEST_LLM_KEY", "secret-value")
    store = _store(tmp_path, _provider_gateway_config())
    registry = ProviderRegistry.from_store(store)

    result = registry.dispatch(
        "llm",
        "openai_text",
        ProviderDispatchRequest(prompt="Improve this prompt", output_dir=tmp_path, task_type="prompt_enhancement"),
    )

    assert result["text"] == "enhanced text"
    assert result["provider_calls_started"] is True
    assert captured["payload"]["model"] == "gpt-test"
    assert captured["payload"]["messages"][0]["role"] == "system"
    assert "strict prompt formatter" in captured["payload"]["messages"][0]["content"]
    assert captured["payload"]["messages"][1] == {"role": "user", "content": "Improve this prompt"}
    assert captured["api_key"] == "secret-value"


def test_provider_registry_dispatches_codex_local_llm(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(args, **kwargs):
        work_dir = Path(kwargs["cwd"])
        captured["args"] = args
        captured["kwargs"] = kwargs
        captured["request"] = json.loads((work_dir / "request.json").read_text(encoding="utf-8"))
        captured["prompt"] = (work_dir / "prompt.md").read_text(encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="优化后的提示词", stderr="")

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_codex_local.subprocess.run", fake_run)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("AFS_CODEX_BOOTSTRAP", "false")
    registry = ProviderRegistry.from_store(_store(tmp_path, _codex_local_provider_config()))

    result = registry.dispatch(
        "llm",
        "prompt_optimizer",
        ProviderDispatchRequest(prompt="优化这个提示词", output_dir=tmp_path, task_type="prompt_enhancement"),
    )

    assert result == {"text": "优化后的提示词", "provider_calls_started": True}
    assert captured["args"][:2] == ["codex", "exec"]
    assert Path(captured["kwargs"]["env"]["CODEX_HOME"]) == tmp_path / "runtime" / "codex-home"
    assert captured["request"]["service_id"] == "prompt_optimizer"
    assert captured["request"]["capability"] == "llm"
    assert "AFS_MODEL_RELAY_API_KEY" not in json.dumps(captured, ensure_ascii=False)


def test_provider_registry_dispatches_codex_local_vision_with_safe_observation(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}
    reference = tmp_path / "reference.png"
    reference.write_bytes(_png_bytes())

    def fake_run(args, **kwargs):
        work_dir = Path(kwargs["cwd"])
        captured["kwargs"] = kwargs
        request = json.loads((work_dir / "request.json").read_text(encoding="utf-8"))
        copied = work_dir / request["reference_images"][0]["path"]
        captured["copied_reference_exists"] = copied.is_file()
        captured["request"] = request
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout=json.dumps(
                {
                    "observation": {
                        "description": "A rain rooftop character reference.",
                        "summary": "Rain rooftop character.",
                        "labels": ["character"],
                        "feature_card": {"identity": "Lin Wan"},
                    }
                }
            ),
            stderr="",
        )

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_codex_local.subprocess.run", fake_run)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VISION", "true")
    monkeypatch.setenv("AFS_RUNTIME_ROOT", str(tmp_path / "runtime"))
    monkeypatch.setenv("AFS_CODEX_BOOTSTRAP", "false")
    registry = ProviderRegistry.from_store(_store(tmp_path, _codex_local_provider_config()))

    result = registry.dispatch(
        "vision",
        "vision_image",
        ProviderDispatchRequest(prompt="Describe this image", output_dir=tmp_path, reference_image_paths=(reference,)),
    )

    assert captured["copied_reference_exists"] is True
    assert Path(captured["kwargs"]["env"]["CODEX_HOME"]) == tmp_path / "runtime" / "codex-home"
    assert captured["request"]["service_id"] == "vision_image"
    assert result["status"] == "succeeded"
    assert result["provider_calls_started"] is True
    assert result["provider_raw_response_stored"] is False
    assert result["provider_observation"]["description"] == "A rain rooftop character reference."
    assert result["provider_observation"]["feature_card"] == {"identity": "Lin Wan"}
    assert result["safe_manifest"]["local_paths_returned_by_api"] is False


def test_provider_registry_blocks_llm_before_network_when_gate_closed(tmp_path, monkeypatch) -> None:
    called = {"count": 0}

    def fake_send(self, payload, api_key):
        called["count"] += 1
        return {"choices": [{"message": {"content": "should not happen"}}]}

    monkeypatch.setattr(openai_compatible.OpenAICompatibleProvider, "_send_request", fake_send)
    monkeypatch.delenv("AFS_ALLOW_REMOTE_LLM", raising=False)
    monkeypatch.setenv("AFS_TEST_LLM_KEY", "secret-value")
    store = _store(tmp_path, _provider_gateway_config())
    registry = ProviderRegistry.from_store(store)

    with pytest.raises(ModelGatewayError, match="AFS_ALLOW_REMOTE_LLM"):
        registry.dispatch(
            "llm",
            "openai_text",
            ProviderDispatchRequest(prompt="hello", output_dir=tmp_path),
        )

    assert called["count"] == 0


def test_provider_registry_supports_fake_vision_descriptor_and_gate(tmp_path, monkeypatch) -> None:
    payload = _provider_gateway_config()
    payload["accounts"]["fake_vision_account"] = {
        "auth_type": "none",
        "base_url": "https://vision.example.test",
        "default_models": {"vision": "fake-vision"},
    }
    payload["account_pools"]["vision_pool"] = {
        "accounts": [
            {
                "account_id": "fake_vision_account",
                "service_id": "fake_vision",
                "enabled_capabilities": ["vision"],
                "enabled": True,
                "priority": 10,
                "weight": 1,
                "concurrency_limit": 1,
                "health_state": "healthy",
            }
        ]
    }
    payload["services"]["fake_vision"] = {
        "provider": "fake",
        "account_ref": "fake_vision_account",
        "capability": "vision",
        "descriptor": {
            "schema_version": "provider_descriptor.v0.1",
            "modality": "vision",
            "execution_mode": "sync",
            "capabilities": ["vision"],
            "account_pool_id": "vision_pool",
            "reference_image_slots": 8,
            "supported_aspect_ratios": ["1:1"],
            "prompt_char_limit": 3000,
            "seed_supported": False,
            "cost_hint": "fake-only",
            "rate_limit_hint": "fake-only",
        },
    }
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VISION", raising=False)
    registry = ProviderRegistry.from_store(_store(tmp_path, payload))

    descriptor = registry.descriptor("fake_vision")
    assert descriptor.modality == "vision"
    assert descriptor.required_gate == "AFS_ALLOW_REMOTE_VISION"
    with pytest.raises(ModelGatewayError, match="AFS_ALLOW_REMOTE_VISION"):
        registry.dispatch(
            "vision",
            "fake_vision",
            ProviderDispatchRequest(prompt="Describe this image", output_dir=tmp_path, reference_image_paths=("img_1",)),
        )

    monkeypatch.setenv("AFS_ALLOW_REMOTE_VISION", "true")
    result = registry.dispatch(
        "vision",
        "fake_vision",
        ProviderDispatchRequest(prompt="Describe this image", output_dir=tmp_path, reference_image_paths=("img_1",)),
    )
    assert result["status"] == "succeeded"
    assert result["provider_calls_started"] is True
    assert result["safe_manifest"]["provider_raw_response_stored"] is False


def test_provider_registry_supports_fake_async_video_lifecycle(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    store = _store(tmp_path, _provider_gateway_config())
    registry = ProviderRegistry.from_store(store)

    result = registry.dispatch(
        "video",
        "fake_video",
        ProviderDispatchRequest(prompt="A calm camera move", output_dir=tmp_path, aspect_ratio="9:16"),
    )

    assert result["status"] == "succeeded"
    assert result["execution_mode"] == "async"
    assert result["task_id"].startswith("fake_video_")
    assert result["provider_calls_started"] is False


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("frame_slots", {"first_frame": "maybe"}, "frame_slots"),
        ("supported_durations_sec", [0], "supported_durations_sec"),
        ("supported_resolutions", ["wide"], "supported_resolutions"),
    ],
)
def test_provider_registry_rejects_invalid_video_descriptor_v02_fields(tmp_path, field, value, match) -> None:
    payload = _kling_provider_config()
    payload["services"]["kling_i2v"]["descriptor"][field] = value
    store = _store(tmp_path, payload)

    with pytest.raises(ModelConfigError, match=match):
        ProviderRegistry.from_store(store)


def test_provider_registry_builds_kling_i2v_adapter_descriptor_v02(tmp_path) -> None:
    store = _store(tmp_path, _kling_provider_config())
    registry = ProviderRegistry.from_store(store)

    descriptor = registry.descriptor("kling_i2v")

    assert descriptor.schema_version == "provider_descriptor.v0.2"
    assert descriptor.modality == "video"
    assert descriptor.execution_mode == "async"
    assert descriptor.frame_slots == {"first_frame": "required", "last_frame": "optional"}
    assert descriptor.frame_modes == ["first_frame", "first_last_frame"]
    assert descriptor.supported_durations_sec == [5, 10]
    assert descriptor.supported_resolutions == ["720p", "1080p"]
    assert descriptor.prompt_profile == "video_i2v_v1"


def test_provider_registry_derives_legacy_kling_i2v_descriptor(tmp_path) -> None:
    store = _store(tmp_path, legacy_kling_provider_config())
    registry = ProviderRegistry.from_store(store)

    descriptor = registry.descriptor("kling_i2v")

    assert descriptor.schema_version == "provider_descriptor.v0.2"
    assert descriptor.modality == "video"
    assert descriptor.execution_mode == "async"
    assert descriptor.frame_slots["first_frame"] == "required"
    assert descriptor.prompt_profile == "video_i2v_v1"


def test_provider_registry_uses_deepseek_default_model_when_ref_blank(tmp_path, monkeypatch) -> None:
    payload = legacy_kling_provider_config()
    payload["accounts"]["deepseek"] = {
        "auth_type": "bearer",
        "base_url": "https://api.deepseek.com",
        "api_key": "fake-deepseek-key",
        "default_models": {"llm": ""},
    }
    payload["services"]["deepseek_llm"] = {
        "provider": "deepseek",
        "account_ref": "deepseek",
        "capability": "llm",
        "default_model_ref": "accounts.deepseek.default_models.llm",
        "required_gate": "AFS_ALLOW_REMOTE_LLM",
    }
    captured: dict[str, object] = {}

    def fake_send(self, payload, api_key):
        captured["payload"] = payload
        captured["api_key"] = api_key
        return {"choices": [{"message": {"content": "legacy deepseek llm ok"}}]}

    monkeypatch.setattr(openai_compatible.OpenAICompatibleProvider, "_send_request", fake_send)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    store = _store(tmp_path, payload)
    registry = ProviderRegistry.from_store(store)

    result = registry.dispatch(
        "llm",
        "deepseek_llm",
        ProviderDispatchRequest(prompt="Improve this prompt", output_dir=tmp_path, task_type="prompt_enhancement"),
    )

    assert registry.descriptor("deepseek_llm").required_gate == "AFS_ALLOW_REMOTE_LLM"
    assert result["text"] == "legacy deepseek llm ok"
    assert captured["payload"]["model"] == "deepseek-chat"
    assert captured["api_key"] == "fake-deepseek-key"


def test_provider_registry_ignores_legacy_minimax_image_service(tmp_path) -> None:
    payload = legacy_kling_provider_config()
    payload["services"]["minimax_image"] = {
        "provider": "minimax",
        "account_ref": "minimax",
        "capability": "image",
        "required_gate": "NARRATO" + "CUT_ALLOW_REMOTE_IMAGE",
    }
    store = _store(tmp_path, payload)
    registry = ProviderRegistry.from_store(store)

    with pytest.raises(ModelConfigError, match="Provider service not found: minimax_image"):
        registry.descriptor("minimax_image")


def test_provider_registry_blocks_kling_before_network_when_gate_closed(tmp_path, monkeypatch) -> None:
    called = {"count": 0}

    def fake_submit_kling_i2v_task(*args, **kwargs):
        called["count"] += 1
        return {"status": "submitted"}

    first_frame = tmp_path / "first.png"
    first_frame.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    monkeypatch.setattr(
        "agentflow_studio.model_gateway.provider_adapter_impl.submit_kling_i2v_task",
        fake_submit_kling_i2v_task,
    )
    store = _store(tmp_path, _kling_provider_config())
    registry = ProviderRegistry.from_store(store)

    with pytest.raises(ModelGatewayError, match="AFS_ALLOW_REMOTE_VIDEO"):
        registry.dispatch(
            "video",
            "kling_i2v",
            ProviderDispatchRequest(
                prompt="A slow camera push in.",
                output_dir=tmp_path / "run",
                aspect_ratio="9:16",
                subject_reference_image_path=first_frame,
                duration_sec=5,
                resolution="720p",
            ),
        )

    assert called["count"] == 0


def test_provider_registry_dispatches_kling_i2v_through_adapter(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_submit_kling_i2v_task(
        store,
        *,
        service_id,
        prompt,
        image_path,
        output_dir,
        duration,
        mode,
        timeout_sec,
        transport,
        model_name_override=None,
    ):
        kwargs = {
            "service_id": service_id,
            "prompt": prompt,
            "image_path": image_path,
            "output_dir": output_dir,
            "duration": duration,
            "mode": mode,
            "timeout_sec": timeout_sec,
            "transport": transport,
            "model_name_override": model_name_override,
        }
        captured["kwargs"] = kwargs
        return {
            "status": "submitted",
            "service_id": service_id,
            "api_family": "i2v",
            "task": {"task_id": "task_123", "task_status": "submitted"},
        }

    def fake_poll_kling_i2v_task_once(store, *, output_dir, state, timeout_sec, transport):
        captured["poll"] = {"output_dir": output_dir, "state": state, "timeout_sec": timeout_sec, "transport": transport}
        return {
            "status": "succeeded",
            "service_id": state["service_id"],
            "provider": "kling",
            "outputs": [{"video_path": "video_candidates/candidate_001.mp4"}],
        }

    first_frame = tmp_path / "first.png"
    first_frame.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setattr(
        "agentflow_studio.model_gateway.provider_adapter_impl.submit_kling_i2v_task",
        fake_submit_kling_i2v_task,
    )
    monkeypatch.setattr(
        "agentflow_studio.model_gateway.provider_adapter_impl.poll_kling_i2v_task_once",
        fake_poll_kling_i2v_task_once,
    )
    store = _store(tmp_path, _kling_provider_config())
    registry = ProviderRegistry.from_store(store)

    result = registry.dispatch(
        "video",
        "kling_i2v",
        ProviderDispatchRequest(
            prompt="A slow camera push in.",
            output_dir=tmp_path / "run",
            aspect_ratio="9:16",
            subject_reference_image_path=first_frame,
            duration_sec=5,
            resolution="720p",
            motion="slow push in",
        ),
    )

    assert result["status"] == "succeeded"
    assert result["service_id"] == "kling_i2v"
    assert captured["kwargs"]["service_id"] == "kling_i2v"
    assert captured["kwargs"]["prompt"] == "A slow camera push in."
    assert captured["kwargs"]["image_path"] == first_frame
    assert captured["kwargs"]["duration"] == "5"
    assert captured["kwargs"]["model_name_override"] is None
    assert captured["poll"]["state"]["task"]["task_id"] == "task_123"
    assert "secret" not in json.dumps(result, ensure_ascii=False).lower()


def test_provider_registry_submit_kling_i2v_returns_submitted_without_polling(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_submit_kling_i2v_task(store, *, service_id, prompt, image_path, output_dir, duration, mode, timeout_sec, transport, model_name_override=None):
        captured["submit"] = {
            "service_id": service_id,
            "prompt": prompt,
            "image_path": image_path,
            "output_dir": output_dir,
            "duration": duration,
            "mode": mode,
            "timeout_sec": timeout_sec,
            "transport": transport,
            "model_name_override": model_name_override,
        }
        return {
            "status": "submitted",
            "service_id": service_id,
            "api_family": "i2v",
            "task": {"task_id": "task_async", "task_status": "submitted"},
        }

    def fail_if_polled(*args, **kwargs):
        raise AssertionError("Kling submit must not poll synchronously")

    first_frame = tmp_path / "first.png"
    first_frame.write_bytes(b"\x89PNG\r\n\x1a\nfake")
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    monkeypatch.setattr(
        "agentflow_studio.model_gateway.provider_adapter_impl.submit_kling_i2v_task",
        fake_submit_kling_i2v_task,
    )
    monkeypatch.setattr(
        "agentflow_studio.model_gateway.provider_adapter_impl.poll_kling_i2v_task_once",
        fail_if_polled,
    )
    registry = ProviderRegistry.from_store(_store(tmp_path, _kling_provider_config()))

    task = registry.submit(
        "video",
        "kling_i2v",
        ProviderDispatchRequest(
            prompt="A slow camera push in.",
            output_dir=tmp_path / "run",
            aspect_ratio="9:16",
            subject_reference_image_path=first_frame,
            duration_sec=5,
            resolution="720p",
        ),
    )

    assert task["task"]["status"] == "submitted"
    assert task["task"]["state"]["task"]["task_id"] == "task_async"
    assert captured["submit"]["image_path"] == first_frame


def test_provider_registry_dispatches_api_relay_llm(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["authorization"] = request.get_header("Authorization")
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _JsonResponse({"text": "relay enhanced text"})

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_MODEL_RELAY_BASE_URL", "https://relay.example.test")
    monkeypatch.setenv("AFS_MODEL_RELAY_API_KEY", "secret-relay-key")
    registry = ProviderRegistry.from_store(_store(tmp_path, _api_relay_provider_config()))

    result = registry.dispatch(
        "llm",
        "prompt_optimizer",
        ProviderDispatchRequest(prompt="Improve this prompt", output_dir=tmp_path, task_type="prompt_enhancement"),
    )

    assert result == {"text": "relay enhanced text", "provider_calls_started": True}
    assert captured["url"] == "https://relay.example.test/v1/afs/llm"
    assert captured["authorization"] == "Bearer secret-relay-key"
    assert captured["payload"]["service_id"] == "prompt_optimizer"
    assert captured["payload"]["capability"] == "llm"
    assert captured["payload"]["prompt"] == "Improve this prompt"


def test_provider_registry_dispatches_api_relay_vision_with_safe_evidence(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return _JsonResponse(
            {
                "observation": {
                    "description": "A rain rooftop character reference.",
                    "summary": "Rain rooftop character.",
                    "labels": ["character"],
                    "feature_card": {"identity": "Lin Wan"},
                },
                "safe_evidence": {"relay_trace_id": "trace_001"},
            }
        )

    reference = tmp_path / "reference.png"
    reference.write_bytes(_png_bytes())
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VISION", "true")
    monkeypatch.setenv("AFS_MODEL_RELAY_BASE_URL", "https://relay.example.test")
    monkeypatch.setenv("AFS_MODEL_RELAY_API_KEY", "secret-relay-key")
    registry = ProviderRegistry.from_store(_store(tmp_path, _api_relay_provider_config()))

    result = registry.dispatch(
        "vision",
        "vision_image",
        ProviderDispatchRequest(prompt="Describe this image", output_dir=tmp_path, reference_image_paths=(reference,)),
    )

    assert result["status"] == "succeeded"
    assert result["provider_calls_started"] is True
    assert result["provider_raw_response_stored"] is False
    assert result["provider_observation"]["description"] == "A rain rooftop character reference."
    assert result["provider_observation"]["feature_card"] == {"identity": "Lin Wan"}
    assert captured["payload"]["reference_images"][0]["mime_type"] == "image/png"
    assert "data_base64" in captured["payload"]["reference_images"][0]
    assert "secret-relay-key" not in json.dumps(result, ensure_ascii=False)


def test_provider_registry_dispatches_api_relay_image_and_writes_candidates(tmp_path, monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        assert payload["capability"] == "image"
        assert payload["aspect_ratio"] == "9:16"
        return _JsonResponse({"images": [{"data_base64": base64.b64encode(_png_bytes()).decode("ascii")} ]})

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("AFS_MODEL_RELAY_BASE_URL", "https://relay.example.test")
    monkeypatch.setenv("AFS_MODEL_RELAY_API_KEY", "secret-relay-key")
    registry = ProviderRegistry.from_store(_store(tmp_path, _api_relay_provider_config(include_image=True)))

    result = registry.dispatch(
        "image",
        "relay_image",
        ProviderDispatchRequest(prompt="Generate a clean keyframe", output_dir=tmp_path / "run", aspect_ratio="9:16"),
    )

    assert result["status"] == "succeeded"
    assert result["provider_calls_started"] is True
    assert result["outputs"][0]["candidate_id"] == "candidate_001"
    assert result["outputs"][0]["image_path"] == "image_candidates/candidate_001.png"
    assert (tmp_path / "run" / "image_candidates" / "candidate_001.png").is_file()
    assert "secret-relay-key" not in json.dumps(result, ensure_ascii=False)


def test_provider_registry_dispatches_api_relay_openai_images_url_response(tmp_path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):
        if request.full_url == "https://api.crazyrouter.com/v1/images/generations":
            captured["authorization"] = request.get_header("Authorization")
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            captured["timeout"] = timeout
            return _JsonResponse({"data": [{"url": "https://media.crazyrouter.com/task-artifacts/result.png"}]})
        if request.full_url == "https://media.crazyrouter.com/task-artifacts/result.png":
            captured["downloaded"] = True
            return _BytesResponse(_png_bytes())
        raise AssertionError(f"unexpected URL: {request.full_url}")

    config = _api_relay_provider_config(include_image=True)
    account = config["accounts"]["model_relay"]
    account["base_url"] = "https://api.crazyrouter.com/v1"
    account["default_models"]["image"] = "gpt-image-2"
    service = config["services"]["relay_image"]
    service["endpoint"] = "/images/generations"
    service["model"] = "gpt-image-2"
    service["request_format"] = "openai_images"
    service["quality"] = "low"
    service["output_format"] = "png"
    service["descriptor"]["reference_image_slots"] = 16
    service["allowed_artifact_hosts"] = [".crazyrouter.com"]
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay_images.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("AFS_MODEL_RELAY_API_KEY", "secret-relay-key")
    registry = ProviderRegistry.from_store(_store(tmp_path, config))

    assert registry.descriptor("relay_image").reference_image_slots == 16
    result = registry.dispatch(
        "image",
        "relay_image",
        ProviderDispatchRequest(prompt="Generate a clean asset sheet", output_dir=tmp_path / "run", aspect_ratio="9:16"),
    )

    assert captured["authorization"] == "Bearer secret-relay-key"
    assert captured["payload"] == {
        "model": "gpt-image-2",
        "prompt": "Generate a clean asset sheet",
        "n": 1,
        "size": "720x1280",
        "quality": "low",
        "output_format": "png",
    }
    assert captured["downloaded"] is True
    assert captured["timeout"] == 120.0
    assert result["outputs"][0]["image_path"] == "image_candidates/candidate_001.png"
    assert result["outputs"][0]["provider_url_persisted"] is False
    assert (tmp_path / "run" / "image_candidates" / "candidate_001.png").is_file()
    assert "media.crazyrouter.com" not in json.dumps(result, ensure_ascii=False)
    assert "secret-relay-key" not in json.dumps(result, ensure_ascii=False)


def test_provider_registry_dispatches_api_relay_openai_images_edit_with_high_fidelity(
    tmp_path,
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}
    source_image = tmp_path / "robot-source.png"
    source_image.write_bytes(_png_bytes())

    def fake_urlopen(request, timeout):
        if request.full_url == "https://api.crazyrouter.com/v1/images/edits":
            captured["authorization"] = request.get_header("Authorization")
            captured["content_type"] = request.get_header("Content-type")
            captured["body"] = request.data.decode("latin1")
            captured["timeout"] = timeout
            return _JsonResponse({"data": [{"b64_json": base64.b64encode(_png_bytes()).decode("ascii")}]})
        raise AssertionError(f"unexpected URL: {request.full_url}")

    config = _api_relay_provider_config(include_image=True)
    account = config["accounts"]["model_relay"]
    account["base_url"] = "https://api.crazyrouter.com/v1"
    account["default_models"]["image"] = "gpt-image-2"
    service = config["services"]["relay_image"]
    service["endpoint"] = "/images/generations"
    service["model"] = "gpt-image-2"
    service["request_format"] = "openai_images"
    service["quality"] = "low"
    service["output_format"] = "png"
    monkeypatch.setattr("agentflow_studio.model_gateway.provider_api_relay_http.urllib.request.urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("AFS_MODEL_RELAY_API_KEY", "secret-relay-key")
    registry = ProviderRegistry.from_store(_store(tmp_path, config))

    result = registry.dispatch(
        "image",
        "relay_image",
        ProviderDispatchRequest(
            prompt="Change only the metal body surface into plush fabric while preserving the same robot.",
            output_dir=tmp_path / "run",
            aspect_ratio="16:9",
            image_operation="edit",
            reference_image_paths=(source_image,),
            edit_source_image_path=source_image,
            edit_reference_image_paths=(source_image,),
            image_input_fidelity="high",
        ),
    )

    body = str(captured["body"])
    assert captured["authorization"] == "Bearer secret-relay-key"
    assert "multipart/form-data" in str(captured["content_type"])
    assert 'name="model"' in body and "gpt-image-2" in body
    assert 'name="prompt"' in body and "Change only the metal body surface into plush fabric" in body
    assert 'name="input_fidelity"' in body and "high" in body
    assert 'name="image[]"; filename="robot-source.png"' in body
    assert captured["timeout"] == 120.0
    assert result["outputs"][0]["image_path"] == "image_candidates/candidate_001.png"
    assert "secret-relay-key" not in json.dumps(result, ensure_ascii=False)


def test_provider_example_config_builds_registry_without_secret_values() -> None:
    store = load_company_provider_secrets("configs/providers.example.json")
    registry = ProviderRegistry.from_store(store)
    serialized = json.dumps(store.model_dump(mode="json"), ensure_ascii=False).lower()

    assert registry.descriptor("prompt_optimizer").modality == "llm"
    assert registry.descriptor("prompt_optimizer").account_pool_id == "prompt_optimizer_pool"
    assert store.services["prompt_optimizer"]["provider"] == "codex_local"
    assert registry.descriptor("codex_image").execution_mode == "async"
    assert registry.descriptor("codex_image").account_pool_id == "codex_image_pool"
    assert registry.descriptor("vision_image").modality == "vision"
    assert store.services["vision_image"]["provider"] == "codex_local"
    assert registry.descriptor("vision_video").reference_image_slots == 8
    assert registry.descriptor("fake_video").execution_mode == "async"
    assert registry.descriptor("kling_i2v").prompt_profile == "video_i2v_v1"
    assert "model_relay" not in serialized
    assert "afs_model_relay" not in serialized
    assert "api_relay" not in serialized
    assert "minimax_image" not in serialized
    assert "minimax_m3" not in serialized
    assert "image-01" not in serialized
    assert "bearer " not in serialized
    assert "sk-" not in serialized
    assert "fk-" not in serialized


class _JsonResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class _BytesResponse:
    def __init__(self, payload: bytes):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, *_args) -> bytes:
        return self.payload


def _png_bytes() -> bytes:
    return base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )


def _api_relay_provider_config(*, include_image: bool = False) -> dict:
    services = {
        "prompt_optimizer": _api_relay_service("llm", "prompt_optimizer", "llm_pool", "/v1/afs/llm"),
        "vision_image": _api_relay_service("vision", "vision_image", "vision_pool", "/v1/afs/vision"),
    }
    pools = {
        "llm_pool": {"accounts": [_api_relay_pool_entry("prompt_optimizer", "llm")]},
        "vision_pool": {"accounts": [_api_relay_pool_entry("vision_image", "vision")]},
    }
    if include_image:
        services["relay_image"] = _api_relay_service("image", "relay_image", "image_pool", "/v1/afs/image")
        pools["image_pool"] = {"accounts": [_api_relay_pool_entry("relay_image", "image")]}
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "model_relay": {
                "auth_type": "api_key",
                "base_url": "https://relay.invalid",
                "base_url_env": "AFS_MODEL_RELAY_BASE_URL",
                "api_key_env": "AFS_MODEL_RELAY_API_KEY",
                "default_models": {"llm": "relay-llm", "vision": "relay-vision", "image": "relay-image"},
            }
        },
        "account_pools": pools,
        "services": services,
    }


def _api_relay_pool_entry(service_id: str, capability: str) -> dict:
    return {
        "account_id": "model_relay",
        "service_id": service_id,
        "credential_env": "AFS_MODEL_RELAY_API_KEY",
        "enabled_capabilities": [capability],
        "enabled": True,
        "priority": 10,
        "weight": 1,
        "concurrency_limit": 1,
        "health_state": "healthy",
    }


def _api_relay_service(capability: str, service_id: str, pool_id: str, endpoint: str) -> dict:
    return {
        "provider": "api_relay",
        "account_ref": "model_relay",
        "capability": capability,
        "model": "server-configured",
        "endpoint": endpoint,
        "required_gate": f"AFS_ALLOW_REMOTE_{capability.upper()}",
        "descriptor": {
            "schema_version": "provider_descriptor.v0.1",
            "modality": capability,
            "execution_mode": "sync",
            "capabilities": [capability],
            "account_pool_id": pool_id,
            "reference_image_slots": 8 if capability == "vision" else 4 if capability == "image" else 0,
            "supported_aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16"],
            "prompt_char_limit": 5000,
            "seed_supported": capability == "image",
            "cost_hint": "test-only",
            "rate_limit_hint": "test-only",
            "required_gate": f"AFS_ALLOW_REMOTE_{capability.upper()}",
        },
    }


def _codex_local_provider_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "local_codex": {
                "auth_type": "none",
                "execution_backend": "codex_exec",
                "cli_command": "codex",
                "default_models": {"llm": "codex-local", "vision": "codex-local", "image": "image2"},
            }
        },
        "account_pools": {
            "prompt_optimizer_pool": {"accounts": [_codex_pool_entry("prompt_optimizer", "llm")]},
            "vision_pool": {"accounts": [_codex_pool_entry("vision_image", "vision")]},
        },
        "services": {
            "prompt_optimizer": _codex_local_service("llm", "prompt_optimizer", "prompt_optimizer_pool", ["1:1"], 0),
            "vision_image": _codex_local_service("vision", "vision_image", "vision_pool", ["1:1"], 8),
        },
    }


def _codex_pool_entry(service_id: str, capability: str) -> dict:
    return {
        "account_id": "local_codex",
        "service_id": service_id,
        "enabled_capabilities": [capability],
        "enabled": True,
        "priority": 10,
        "weight": 1,
        "concurrency_limit": 1,
        "health_state": "healthy",
    }


def _codex_local_service(
    capability: str,
    service_id: str,
    pool_id: str,
    aspect_ratios: list[str],
    reference_image_slots: int,
) -> dict:
    return {
        "provider": "codex_local",
        "account_ref": "local_codex",
        "capability": capability,
        "required_gate": f"AFS_ALLOW_REMOTE_{capability.upper()}",
        "descriptor": {
            "schema_version": "provider_descriptor.v0.1",
            "modality": capability,
            "execution_mode": "sync",
            "capabilities": [capability],
            "account_pool_id": pool_id,
            "reference_image_slots": reference_image_slots,
            "supported_aspect_ratios": aspect_ratios,
            "prompt_char_limit": 5000,
            "seed_supported": False,
            "cost_hint": "local-codex",
            "rate_limit_hint": "local-codex",
            "required_gate": f"AFS_ALLOW_REMOTE_{capability.upper()}",
        },
    }


def _provider_gateway_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "openai_account": {
                "auth_type": "api_key",
                "base_url": "https://example.test/v1",
                "api_key_env": "AFS_TEST_LLM_KEY",
                "default_models": {"llm": "gpt-test"},
            },
            "fake_video_account": {
                "auth_type": "none",
                "base_url": "https://video.example.test",
                "default_models": {"video": "fake-video"},
            },
        },
        "account_pools": {
            "llm_pool": {
                "accounts": [
                    {
                        "account_id": "openai_account",
                        "service_id": "openai_text",
                        "credential_env": "AFS_TEST_LLM_KEY",
                        "enabled_capabilities": ["llm"],
                        "enabled": True,
                        "priority": 10,
                        "weight": 1,
                        "concurrency_limit": 1,
                        "health_state": "healthy",
                    }
                ]
            },
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
            },
        },
        "services": {
            "openai_text": {
                "provider": "openai_compatible",
                "account_ref": "openai_account",
                "capability": "llm",
                "model": "gpt-test",
                "required_gate": "AFS_ALLOW_REMOTE_LLM",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.1",
                    "modality": "llm",
                    "execution_mode": "sync",
                    "capabilities": ["llm"],
                    "account_pool_id": "llm_pool",
                    "reference_image_slots": 0,
                    "supported_aspect_ratios": ["1:1"],
                    "prompt_char_limit": 5000,
                    "seed_supported": False,
                    "cost_hint": "test-only",
                    "rate_limit_hint": "test-only",
                    "required_gate": "AFS_ALLOW_REMOTE_LLM",
                },
            },
            "fake_video": {
                "provider": "fake",
                "account_ref": "fake_video_account",
                "capability": "video",
                "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.1",
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
                },
            },
        },
    }


def _kling_provider_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "kling": {
                "auth_type": "jwt_hs256_from_ak_sk",
                "base_url": "https://api-beijing.klingai.com",
                "access_key": "fake-access-key",
                "secret_key": "fake-secret-key",
                "jwt": {"ttl_seconds": 1800, "nbf_skew_seconds": -5},
                "default_models": {"i2v": "kling-v3"},
                "endpoints": {
                    "i2v_create": "/v1/videos/image2video",
                    "i2v_query": "/v1/videos/image2video/{id}",
                },
            }
        },
        "account_pools": {
            "kling_video_pool": {
                "accounts": [
                    {
                        "account_id": "kling",
                        "service_id": "kling_i2v",
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
            "kling_i2v": {
                "provider": "kling",
                "account_ref": "kling",
                "capability": "video",
                "api_family": "i2v",
                "default_model_ref": "accounts.kling.default_models.i2v",
                "create_endpoint_ref": "accounts.kling.endpoints.i2v_create",
                "query_endpoint_ref": "accounts.kling.endpoints.i2v_query",
                "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.2",
                    "modality": "video",
                    "execution_mode": "async",
                    "capabilities": ["video"],
                    "account_pool_id": "kling_video_pool",
                    "reference_image_slots": 2,
                    "supported_aspect_ratios": ["16:9", "9:16"],
                    "prompt_char_limit": 2500,
                    "seed_supported": False,
                    "cost_hint": "Kling I2V live usage is billed by selected duration and mode.",
                    "rate_limit_hint": "Use one live Kling video task at a time during MVP validation.",
                    "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
                    "frame_slots": {"first_frame": "required", "last_frame": "optional"},
                    "frame_modes": ["first_frame", "first_last_frame"],
                    "supported_durations_sec": [5, 10],
                    "supported_resolutions": ["720p", "1080p"],
                    "async_poll_interval_sec": 5,
                    "async_timeout_sec": 600,
                    "async_max_polls": 120,
                    "prompt_profile": "video_i2v_v1",
                    "cost_estimate": {"unit": "task", "currency": "CNY", "disclaimer": "local estimate only"},
                },
            }
        },
    }
