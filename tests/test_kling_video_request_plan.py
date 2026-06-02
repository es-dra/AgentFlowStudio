from __future__ import annotations

import json

import pytest

from agentflow_studio.model_gateway import ModelConfigError, ModelProviderError
from agentflow_studio.model_gateway.company_secrets import (
    COMPANY_PROVIDER_CONFIG_ENV,
    load_company_provider_secrets,
)
from agentflow_studio.model_gateway.kling_plan import build_kling_request_plan
from tests.kling_video_smoke_helpers import provider_config, store


def test_load_company_provider_secrets_handles_utf8_bom(tmp_path) -> None:
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(provider_config()), encoding="utf-8-sig")

    store = load_company_provider_secrets(config_path)

    assert store.schema_version == "company_provider_secrets.local.v2"
    assert store.account("kling")["auth_type"] == "jwt_hs256_from_ak_sk"


def test_load_company_provider_secrets_requires_explicit_path_or_env(monkeypatch) -> None:
    monkeypatch.delenv(COMPANY_PROVIDER_CONFIG_ENV, raising=False)

    with pytest.raises(ModelConfigError, match=COMPANY_PROVIDER_CONFIG_ENV):
        load_company_provider_secrets()


def test_load_company_provider_secrets_uses_env_path(monkeypatch, tmp_path) -> None:
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(provider_config()), encoding="utf-8")
    monkeypatch.setenv(COMPANY_PROVIDER_CONFIG_ENV, str(config_path))

    store = load_company_provider_secrets()

    assert store.schema_version == "company_provider_secrets.local.v2"
    assert store.service("kling_i2v")["provider"] == "kling"


def test_kling_i2v_plan_requires_image_reference(tmp_path) -> None:
    provider_store = store(tmp_path)

    with pytest.raises(ModelConfigError, match="image_ref"):
        build_kling_request_plan(
            provider_store,
            service_id="kling_i2v",
            prompt="slow push-in camera movement",
        )


def test_kling_i2v_dry_run_plan_uses_video_gate_and_local_image_ref(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")
    provider_store = store(tmp_path)

    plan = build_kling_request_plan(
        provider_store,
        service_id="kling_i2v",
        prompt="slow push-in camera movement",
        image_ref="image_candidates/candidate_001.png",
        duration="5",
        mode="pro",
    )

    assert plan["service_id"] == "kling_i2v"
    assert plan["capability"] == "video"
    assert plan["required_gate"] == "AFS_ALLOW_REMOTE_VIDEO"
    assert plan["gate_status"] == "enabled"
    assert plan["live_call_authorized"] is True
    assert plan["create_request"]["url"] == "https://api-beijing.klingai.com/v1/videos/image2video"
    assert plan["query_request"]["url_template"] == "https://api-beijing.klingai.com/v1/videos/image2video/{id}"
    assert plan["create_request"]["json"]["model_name"] == "kling-v3"
    assert plan["create_request"]["json"]["image"] == {
        "source": "local_path",
        "path": "image_candidates/candidate_001.png",
        "send_as": "base64_without_data_uri",
    }
    assert plan["create_request"]["json"]["duration"] == "5"
    assert plan["create_request"]["json"]["mode"] == "pro"
    assert plan["create_request"]["json"]["sound"] == "off"

    serialized = json.dumps(plan, ensure_ascii=False)
    assert "fake-access-key" not in serialized
    assert "fake-secret-key" not in serialized
    assert "Bearer " not in serialized


def test_kling_t2v_plan_can_require_live_gate(tmp_path) -> None:
    provider_store = store(tmp_path)

    with pytest.raises(ModelProviderError, match="AFS_ALLOW_REMOTE_VIDEO"):
        build_kling_request_plan(
            provider_store,
            service_id="kling_t2v",
            prompt="vertical workstation video",
            require_live_gate=True,
        )


def test_kling_plan_rejects_removed_image_family(tmp_path) -> None:
    provider_store = _store_with_removed_image_service(tmp_path)

    with pytest.raises(ModelConfigError, match="Unsupported Kling api_family"):
        build_kling_request_plan(
            provider_store,
            service_id="kling_t2i",
            prompt="image generation is intentionally handled by MiniMax",
        )


def _store_with_removed_image_service(tmp_path):
    config = provider_config()
    config["accounts"]["kling"]["default_models"]["image"] = "kling-v3"
    config["accounts"]["kling"]["endpoints"]["image_create"] = "/v1/images/generations"
    config["accounts"]["kling"]["endpoints"]["image_query"] = "/v1/images/generations/{id}"
    config["services"]["kling_t2i"] = {
        "provider": "kling",
        "account_ref": "kling",
        "capability": "image",
        "api_family": "t2i",
        "default_model_ref": "accounts.kling.default_models.image",
        "create_endpoint_ref": "accounts.kling.endpoints.image_create",
        "query_endpoint_ref": "accounts.kling.endpoints.image_query",
        "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
    }
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return load_company_provider_secrets(config_path)
