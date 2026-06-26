from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from agentflow_studio.model_gateway.errors import ModelConfigError


COMPANY_PROVIDER_CONFIG_ENV = "AFS_PROVIDER_CONFIG"
DEFAULT_COMPANY_PROVIDER_SECRETS: Path | None = None
IMAGE_RELAY_SERVICE_ID = "image_relay"
IMAGE_RELAY_POOL_ID = "image_relay_pool"
LEGACY_CODEX_IMAGE_SERVICE_ID = "codex_image"
LEGACY_CODEX_IMAGE_POOL_ID = "codex_image_pool"


class CompanyProviderSecrets(BaseModel):
    schema_version: str
    accounts: dict[str, dict[str, Any]] = Field(default_factory=dict)
    account_pools: dict[str, dict[str, Any]] = Field(default_factory=dict)
    services: dict[str, dict[str, Any]] = Field(default_factory=dict)

    def account(self, account_id: str) -> dict[str, Any]:
        try:
            account = self.accounts[account_id]
        except KeyError as exc:
            raise ModelConfigError(f"Provider account not found: {account_id}") from exc
        if not isinstance(account, dict):
            raise ModelConfigError(f"Provider account must be an object: {account_id}")
        return account

    def service(self, service_id: str) -> dict[str, Any]:
        try:
            service = self.services[service_id]
        except KeyError as exc:
            raise ModelConfigError(f"Provider service not found: {service_id}") from exc
        if not isinstance(service, dict):
            raise ModelConfigError(f"Provider service must be an object: {service_id}")
        return service


def load_company_provider_secrets(
    path: str | Path | None = DEFAULT_COMPANY_PROVIDER_SECRETS,
) -> CompanyProviderSecrets:
    config_path = resolve_company_provider_secrets_path(path)
    if not config_path.is_file():
        raise ModelConfigError(f"Company provider secret file not found: {config_path}")
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ModelConfigError(f"Company provider secret JSON is invalid: {config_path}") from exc
    if not isinstance(payload, dict):
        raise ModelConfigError(f"Company provider secret JSON must be an object: {config_path}")
    payload = _with_image_relay_service(payload)
    try:
        return CompanyProviderSecrets.model_validate(payload)
    except ValidationError as exc:
        raise ModelConfigError(f"Company provider secret JSON schema is invalid: {config_path}: {exc}") from exc


def resolve_company_provider_secrets_path(path: str | Path | None = None) -> Path:
    if path is not None:
        return Path(path)
    env_path = os.environ.get(COMPANY_PROVIDER_CONFIG_ENV, "").strip()
    if env_path:
        return Path(env_path)
    raise ModelConfigError(
        "Company provider config path is required; pass --provider-config "
        f"or set {COMPANY_PROVIDER_CONFIG_ENV}."
    )


def resolve_ref(root: dict[str, Any], ref: str) -> Any:
    if not ref:
        raise ModelConfigError("Provider config reference is empty")
    current: Any = root
    for part in ref.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ModelConfigError(f"Provider config reference not found: {ref}")
        current = current[part]
    return current


def _with_image_relay_service(payload: dict[str, Any]) -> dict[str, Any]:
    services = payload.get("services")
    if not isinstance(services, dict):
        return payload
    if IMAGE_RELAY_SERVICE_ID in services:
        return payload
    legacy_service = services.get(LEGACY_CODEX_IMAGE_SERVICE_ID)
    if not _is_legacy_api_relay_image_service(legacy_service):
        return payload

    next_payload = dict(payload)
    next_services = dict(services)
    next_services.pop(LEGACY_CODEX_IMAGE_SERVICE_ID, None)
    next_services[IMAGE_RELAY_SERVICE_ID] = _image_relay_service_from_legacy(legacy_service)
    next_payload["services"] = next_services

    account_pools = payload.get("account_pools")
    if isinstance(account_pools, dict):
        next_pools = dict(account_pools)
        legacy_pool = next_pools.pop(LEGACY_CODEX_IMAGE_POOL_ID, None)
        if isinstance(legacy_pool, dict):
            next_pools[IMAGE_RELAY_POOL_ID] = _image_relay_pool_from_legacy(legacy_pool)
        next_payload["account_pools"] = next_pools
    return next_payload


def _is_legacy_api_relay_image_service(value: Any) -> bool:
    return (
        isinstance(value, dict)
        and str(value.get("provider") or "") == "api_relay"
        and str(value.get("capability") or "") == "image"
    )


def _image_relay_service_from_legacy(service: dict[str, Any]) -> dict[str, Any]:
    next_service = dict(service)
    next_service.setdefault("edit_endpoint", "/images/edits")
    descriptor = next_service.get("descriptor")
    if isinstance(descriptor, dict):
        next_descriptor = dict(descriptor)
        next_descriptor["account_pool_id"] = IMAGE_RELAY_POOL_ID
        next_descriptor["reference_image_slots"] = max(1, int(next_descriptor.get("reference_image_slots") or 0))
        next_service["descriptor"] = next_descriptor
    return next_service


def _image_relay_pool_from_legacy(pool: dict[str, Any]) -> dict[str, Any]:
    next_pool = dict(pool)
    accounts = next_pool.get("accounts")
    if isinstance(accounts, list):
        next_accounts = []
        for item in accounts:
            if isinstance(item, dict):
                next_item = dict(item)
                if next_item.get("service_id") == LEGACY_CODEX_IMAGE_SERVICE_ID:
                    next_item["service_id"] = IMAGE_RELAY_SERVICE_ID
                next_accounts.append(next_item)
            else:
                next_accounts.append(item)
        next_pool["accounts"] = next_accounts
    return next_pool
