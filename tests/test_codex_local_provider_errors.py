from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from agentflow_studio.model_gateway.company_secrets import SERVER_CODEX_SERVICE_ID, load_company_provider_secrets
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.provider_adapter import (
    ProviderDispatchRequest,
    ProviderRegistry,
    structured_output_schema_digest,
)


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


def _structured_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["title"],
        "properties": {"title": {"type": "string", "minLength": 1}},
    }


def _structured_request(tmp_path: Path, *, digest: str | None = None) -> ProviderDispatchRequest:
    schema = _structured_schema()
    return ProviderDispatchRequest(
        prompt="write title",
        output_dir=tmp_path,
        task_type="adaptive_canvas_script_v3",
        structured_output_contract_id="adaptive_canvas_script_v3",
        structured_output_schema=schema,
        structured_output_schema_digest=digest or structured_output_schema_digest(schema),
    )


def _enable_codex_test_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_LLM", "true")
    monkeypatch.setenv("AFS_CODEX_HOME", str(tmp_path / "codex-home"))
    monkeypatch.setenv("AFS_CODEX_BOOTSTRAP", "false")


def test_server_codex_structured_output_reads_only_last_message(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    def completed(args, **kwargs):  # noqa: ANN001, ANN202
        captured["args"] = args
        final_path = Path(args[args.index("--output-last-message") + 1])
        final_path.write_text('{"title":"final"}', encoding="utf-8")
        schema_path = Path(args[args.index("--output-schema") + 1])
        captured["schema"] = json.loads(schema_path.read_text(encoding="utf-8"))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout='reasoning {"title":"wrong"}', stderr="")

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_codex_local.subprocess.run", completed)
    _enable_codex_test_env(tmp_path, monkeypatch)
    registry = ProviderRegistry.from_store(_store(tmp_path, _codex_local_provider_config()))
    result = registry.dispatch("llm", SERVER_CODEX_SERVICE_ID, _structured_request(tmp_path))

    assert result["structured_output"] == {"title": "final"}
    assert result["text"] == '{"title":"final"}'
    assert captured["schema"] == _structured_schema()
    assert "--ephemeral" in captured["args"]
    assert "--output-schema" in captured["args"]
    assert "--output-last-message" in captured["args"]


@pytest.mark.parametrize(
    ("final_text", "message"),
    [
        ('```json\n{"title":"x"}\n```', "not valid JSON"),
        ('before {"title":"x"} after', "not valid JSON"),
        ("", "response is empty"),
        ('{"wrong":"x"}', "does not match schema"),
    ],
)
def test_server_codex_structured_output_rejects_non_contract_final(
    tmp_path: Path,
    monkeypatch,
    final_text: str,
    message: str,
) -> None:
    def completed(args, **kwargs):  # noqa: ANN001, ANN202
        final_path = Path(args[args.index("--output-last-message") + 1])
        final_path.write_text(final_text, encoding="utf-8")
        return subprocess.CompletedProcess(args=args, returncode=0, stdout='{"title":"stdout-must-be-ignored"}', stderr="")

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_codex_local.subprocess.run", completed)
    _enable_codex_test_env(tmp_path, monkeypatch)
    registry = ProviderRegistry.from_store(_store(tmp_path, _codex_local_provider_config()))

    with pytest.raises(ModelGatewayError, match=message):
        registry.dispatch("llm", SERVER_CODEX_SERVICE_ID, _structured_request(tmp_path))


def test_server_codex_structured_output_cli_nonzero_is_failure(tmp_path: Path, monkeypatch) -> None:
    def completed(args, **kwargs):  # noqa: ANN001, ANN202
        return subprocess.CompletedProcess(args=args, returncode=7, stdout="", stderr="structured execution failed")

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_codex_local.subprocess.run", completed)
    _enable_codex_test_env(tmp_path, monkeypatch)
    registry = ProviderRegistry.from_store(_store(tmp_path, _codex_local_provider_config()))

    with pytest.raises(ModelGatewayError, match="structured execution failed"):
        registry.dispatch("llm", SERVER_CODEX_SERVICE_ID, _structured_request(tmp_path))


def test_server_codex_structured_output_rejects_schema_digest_mismatch(tmp_path: Path, monkeypatch) -> None:
    def should_not_run(*args, **kwargs):  # noqa: ANN001, ANN202
        raise AssertionError("subprocess must not run")

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_codex_local.subprocess.run", should_not_run)
    _enable_codex_test_env(tmp_path, monkeypatch)
    registry = ProviderRegistry.from_store(_store(tmp_path, _codex_local_provider_config()))

    with pytest.raises(ModelConfigError, match="schema digest mismatch"):
        registry.dispatch("llm", SERVER_CODEX_SERVICE_ID, _structured_request(tmp_path, digest="0" * 64))


def test_server_codex_structured_output_incomplete_contract_fails_closed(tmp_path: Path, monkeypatch) -> None:
    def should_not_run(*args, **kwargs):  # noqa: ANN001, ANN202
        raise AssertionError("subprocess must not run")

    monkeypatch.setattr("agentflow_studio.model_gateway.provider_codex_local.subprocess.run", should_not_run)
    _enable_codex_test_env(tmp_path, monkeypatch)
    registry = ProviderRegistry.from_store(_store(tmp_path, _codex_local_provider_config()))
    request = ProviderDispatchRequest(
        prompt="write title",
        output_dir=tmp_path,
        structured_output_contract_id="adaptive_canvas_script_v3",
    )

    with pytest.raises(ModelConfigError, match="contract id, schema, and schema digest are required"):
        registry.dispatch("llm", SERVER_CODEX_SERVICE_ID, request)


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
