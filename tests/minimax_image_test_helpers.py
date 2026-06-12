from __future__ import annotations

import json

from agentflow_studio.model_gateway.company_secrets import load_company_provider_secrets


def store(tmp_path, use_env_key: bool = False, use_mmx_cli: bool = False):
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(
        json.dumps(provider_config(use_env_key=use_env_key, use_mmx_cli=use_mmx_cli)),
        encoding="utf-8",
    )
    return load_company_provider_secrets(config_path)


def provider_config(*, use_env_key: bool = False, use_mmx_cli: bool = False) -> dict:
    account = {
        "auth_type": "api_key",
        "base_url": "https://api.minimax.io",
        "default_models": {"image": ""},
    }
    service = {
        "provider": "minimax",
        "account_ref": "minimax",
        "capability": "image",
        "api_family": "t2i",
        "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
        "descriptor": {
            "schema_version": "provider_descriptor.v0.1",
            "modality": "image",
            "execution_mode": "sync",
            "capabilities": ["image"],
            "account_pool_id": "minimax_image_pool",
            "reference_image_slots": 1,
            "supported_aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16"],
            "prompt_char_limit": 1500,
            "seed_supported": True,
            "cost_hint": "test-only",
            "rate_limit_hint": "test-only",
            "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
        },
    }
    account_pool_entry = {
        "account_id": "minimax",
        "service_id": "minimax_image",
        "credential_env": "MINIMAX_API_KEY" if use_env_key else None,
        "enabled_capabilities": ["image"],
        "enabled": True,
        "priority": 10,
        "weight": 1,
        "concurrency_limit": 1,
        "health_state": "healthy",
    }
    if use_mmx_cli:
        account["execution_backend"] = "mmx_cli"
        account["region"] = "cn"
        service["execution_backend"] = "mmx_cli"
        account_pool_entry["credential_env"] = None
    elif use_env_key:
        account["api_key_env"] = "MINIMAX_API_KEY"
    else:
        account["api_key"] = "fk-mm-key"
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {"minimax": account},
        "account_pools": {"minimax_image_pool": {"accounts": [account_pool_entry]}},
        "services": {"minimax_image": service},
    }
