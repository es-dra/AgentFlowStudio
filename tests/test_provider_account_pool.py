from __future__ import annotations

import pytest

from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.provider_account_pool import (
    reserve_provider_account,
    select_provider_account,
)


def _store() -> CompanyProviderSecrets:
    return CompanyProviderSecrets.model_validate(
        {
            "schema_version": "company_provider_secrets.local.v2",
            "accounts": {
                "crazyrouter": {"auth_type": "api_key", "api_key_env": "AFS_POOL_A"},
                "crazyrouter_image_a": {"auth_type": "api_key", "api_key_env": "AFS_POOL_B"},
                "crazyrouter_image_b": {"auth_type": "api_key", "api_key_env": "AFS_POOL_C"},
            },
            "account_pools": {
                "image_relay_pool": {
                    "accounts": [
                        _entry("crazyrouter", "AFS_POOL_A"),
                        _entry("crazyrouter_image_a", "AFS_POOL_B"),
                        _entry("crazyrouter_image_b", "AFS_POOL_C"),
                    ]
                }
            },
            "services": {
                "image_relay": {
                    "provider": "api_relay",
                    "account_ref": "crazyrouter",
                    "capability": "image",
                    "descriptor": {
                        "schema_version": "provider_descriptor.v0.1",
                        "modality": "image",
                        "execution_mode": "sync",
                        "capabilities": ["image"],
                        "account_pool_id": "image_relay_pool",
                        "reference_image_slots": 4,
                        "supported_aspect_ratios": ["3:4", "16:9"],
                        "prompt_char_limit": 4000,
                        "seed_supported": False,
                        "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
                    },
                }
            },
        }
    )


def _entry(account_id: str, env_name: str) -> dict:
    return {
        "account_id": account_id,
        "service_id": "image_relay",
        "credential_env": env_name,
        "enabled_capabilities": ["image"],
        "enabled": True,
        "priority": 10,
        "weight": 1,
        "concurrency_limit": 1,
        "health_state": "healthy",
    }


def test_provider_account_pool_routes_deterministically_across_weighted_entries(monkeypatch) -> None:
    for name in ("AFS_POOL_A", "AFS_POOL_B", "AFS_POOL_C"):
        monkeypatch.setenv(name, "present")
    store = _store()

    first = select_provider_account(
        store,
        service_id="image_relay",
        capability="image",
        account_pool_id="image_relay_pool",
        routing_key="project:item:one",
    )
    repeat = select_provider_account(
        store,
        service_id="image_relay",
        capability="image",
        account_pool_id="image_relay_pool",
        routing_key="project:item:one",
    )
    selected = {
        select_provider_account(
            store,
            service_id="image_relay",
            capability="image",
            account_pool_id="image_relay_pool",
            routing_key=f"project:item:{index}",
        ).account_id
        for index in range(32)
    }

    assert repeat.account_id == first.account_id
    assert selected == {"crazyrouter", "crazyrouter_image_a", "crazyrouter_image_b"}


def test_provider_account_pool_respects_concurrency_limit_and_releases(monkeypatch) -> None:
    for name in ("AFS_POOL_A", "AFS_POOL_B", "AFS_POOL_C"):
        monkeypatch.setenv(name, "present")
    store = _store()

    with reserve_provider_account(
        store,
        service_id="image_relay",
        capability="image",
        account_pool_id="image_relay_pool",
        routing_key="first",
    ) as first:
        with reserve_provider_account(
            store,
            service_id="image_relay",
            capability="image",
            account_pool_id="image_relay_pool",
            routing_key="second",
        ) as second:
            with reserve_provider_account(
                store,
                service_id="image_relay",
                capability="image",
                account_pool_id="image_relay_pool",
                routing_key="third",
            ) as third:
                assert {first.account_id, second.account_id, third.account_id} == {
                    "crazyrouter",
                    "crazyrouter_image_a",
                    "crazyrouter_image_b",
                }
                with pytest.raises(ModelGatewayError, match="concurrency limit"):
                    with reserve_provider_account(
                        store,
                        service_id="image_relay",
                        capability="image",
                        account_pool_id="image_relay_pool",
                        routing_key="fourth",
                    ):
                        pass

    with reserve_provider_account(
        store,
        service_id="image_relay",
        capability="image",
        account_pool_id="image_relay_pool",
        routing_key="after-release",
    ) as released:
        assert released.account_id in {"crazyrouter", "crazyrouter_image_a", "crazyrouter_image_b"}
