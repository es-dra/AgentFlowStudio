from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agentflow_studio.model_gateway.company_secrets import SERVER_CODEX_SERVICE_ID, load_company_provider_secrets
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import ProviderDispatchRequest, ProviderRegistry


def test_codex_local_missing_cli_is_reported_as_model_gateway_error(tmp_path, monkeypatch) -> None:
    def missing_codex(*args, **kwargs):  # noqa: ANN001, ANN202
        raise FileNotFoundError("codex")

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_codex_local.subprocess.run", missing_codex)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_CODEX_HOME", str(tmp_path / "codex-home"))
    monkeypatch.setenv("AFS_CODEX_BOOTSTRAP", "false")
    registry = ProviderRegistry.from_store(_store(tmp_path, _codex_local_provider_config()))

    with pytest.raises(ModelGatewayError, match="Codex local provider command is not available"):
        registry.dispatch(
            "llm",
            "prompt_optimizer",
            ProviderDispatchRequest(prompt="hello", output_dir=tmp_path, task_type="sprite_chat"),
        )


def test_server_codex_is_injected_without_rewriting_prompt_optimizer(tmp_path: Path) -> None:
    store = _store(tmp_path, _codex_local_provider_config())
    assert store.service(SERVER_CODEX_SERVICE_ID)["provider"] == "codex_local"
    assert store.service(SERVER_CODEX_SERVICE_ID)["capability"] == "llm"
    assert store.service("prompt_optimizer")["provider"] == "codex_local"
    assert store.service("prompt_optimizer")["account_ref"] == "local_codex"


def test_server_codex_conflicting_relay_route_is_rejected(tmp_path: Path) -> None:
    payload = _codex_local_provider_config()
    payload["services"][SERVER_CODEX_SERVICE_ID] = {"provider": "api_relay", "capability": "llm"}
    with pytest.raises(ModelConfigError, match="server_codex must remain a codex_local llm service"):
        _store(tmp_path, payload)


def test_server_codex_dispatch_uses_managed_codex_cli(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def completed(args, **kwargs):  # noqa: ANN001, ANN202
        captured["args"] = args
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_codex_local.subprocess.run", completed)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_CODEX_HOME", str(tmp_path / "codex-home"))
    monkeypatch.setenv("AFS_CODEX_BOOTSTRAP", "false")
    registry = ProviderRegistry.from_store(_store(tmp_path, _codex_local_provider_config()))
    result = registry.dispatch(
        "llm",
        SERVER_CODEX_SERVICE_ID,
        ProviderDispatchRequest(prompt="hello", output_dir=tmp_path, task_type="script"),
    )

    assert result["text"] == "ok"
    args = captured["args"]
    assert Path(args[0]).name == "codex"
    assert args[1] == "exec"


def _store(tmp_path: Path, payload: dict) -> object:
    path = tmp_path / "providers.local.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return load_company_provider_secrets(path)


def _codex_local_provider_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "local_codex": {
                "auth_type": "none",
                "execution_backend": "codex_exec",
                "default_models": {"llm": "codex-local"},
            }
        },
        "account_pools": {
            "prompt_optimizer_pool": {
                "accounts": [
                    {
                        "account_id": "local_codex",
                        "service_id": "prompt_optimizer",
                        "enabled_capabilities": ["llm"],
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
            "prompt_optimizer": {
                "provider": "codex_local",
                "account_ref": "local_codex",
                "capability": "llm",
                "required_gate": "AFS_ALLOW_REMOTE_LLM",
                "descriptor": {
                    "schema_version": "provider_descriptor.v0.1",
                    "modality": "llm",
                    "execution_mode": "sync",
                    "capabilities": ["llm"],
                    "account_pool_id": "prompt_optimizer_pool",
                    "reference_image_slots": 0,
                    "supported_aspect_ratios": ["1:1"],
                    "prompt_char_limit": 5000,
                    "seed_supported": False,
                    "cost_hint": "local-codex",
                    "rate_limit_hint": "local-codex",
                    "required_gate": "AFS_ALLOW_REMOTE_LLM",
                },
            }
        },
    }
