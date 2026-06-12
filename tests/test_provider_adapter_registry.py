from __future__ import annotations

import json

import pytest

from agentflow_studio.model_gateway.company_secrets import load_company_provider_secrets
from agentflow_studio.model_gateway.errors import ModelConfigError
from agentflow_studio.model_gateway.provider_adapter import ProviderRegistry
from tests.minimax_image_test_helpers import provider_config


def _store(tmp_path, payload: dict):
    path = tmp_path / "providers.local.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return load_company_provider_secrets(path)


def test_provider_registry_rejects_missing_descriptor(tmp_path) -> None:
    payload = provider_config()
    payload["services"]["minimax_image"].pop("descriptor", None)
    store = _store(tmp_path, payload)

    with pytest.raises(ModelConfigError, match="descriptor"):
        ProviderRegistry.from_store(store)


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("required_gate", "MINIMAX_API_KEY", "required_gate"),
        ("reference_image_slots", -1, "reference_image_slots"),
        ("supported_aspect_ratios", ["wide"], "supported_aspect_ratios"),
    ],
)
def test_provider_registry_rejects_invalid_descriptor_fields(tmp_path, field, value, match) -> None:
    payload = provider_config()
    payload["services"]["minimax_image"]["descriptor"][field] = value
    store = _store(tmp_path, payload)

    with pytest.raises(ModelConfigError, match=match):
        ProviderRegistry.from_store(store)


def test_provider_registry_exposes_minimax_descriptor(tmp_path) -> None:
    store = _store(tmp_path, provider_config())
    registry = ProviderRegistry.from_store(store)

    descriptor = registry.descriptor("minimax_image")

    assert descriptor.modality == "image"
    assert descriptor.execution_mode == "sync"
    assert descriptor.reference_image_slots == 1
    assert descriptor.prompt_char_limit == 1500
    assert descriptor.required_gate == "AFS_ALLOW_REMOTE_IMAGE"
