from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError


ProviderHealthState = Literal["unknown", "healthy", "degraded", "disabled"]


class ProviderAccountPoolEntry(BaseModel):
    account_id: str = Field(min_length=1)
    service_id: str | None = None
    credential_env: str | None = None
    enabled_capabilities: list[str] = Field(default_factory=list)
    enabled: bool = True
    priority: int = 100
    weight: int = Field(default=1, ge=1)
    concurrency_limit: int = Field(default=1, ge=1)
    health_state: ProviderHealthState = "unknown"

    @field_validator("credential_env")
    @classmethod
    def _validate_credential_env(cls, value: str | None) -> str | None:
        if value is None:
            return value
        trimmed = value.strip()
        if not trimmed:
            return None
        if any(char.isspace() for char in trimmed):
            raise ValueError("credential_env must be a single environment variable name")
        return trimmed


@dataclass(frozen=True)
class ProviderAccountSelection:
    account_id: str
    account: dict[str, Any]
    credential_env: str | None
    account_pool_id: str | None
    priority: int
    weight: int
    concurrency_limit: int
    health_state: str

    def public_summary(self) -> dict[str, Any]:
        return {
            "account_id": self.account_id,
            "credential_env": self.credential_env,
            "account_pool_id": self.account_pool_id,
            "priority": self.priority,
            "weight": self.weight,
            "concurrency_limit": self.concurrency_limit,
            "health_state": self.health_state,
        }


def select_provider_account(
    store: CompanyProviderSecrets,
    *,
    service_id: str,
    capability: str,
    account_pool_id: str | None,
) -> ProviderAccountSelection:
    if account_pool_id:
        return _select_from_pool(store, service_id=service_id, capability=capability, account_pool_id=account_pool_id)
    return _select_service_account_ref(store, service_id=service_id)


def _select_from_pool(
    store: CompanyProviderSecrets,
    *,
    service_id: str,
    capability: str,
    account_pool_id: str,
) -> ProviderAccountSelection:
    pool = store.account_pools.get(account_pool_id)
    if not isinstance(pool, dict):
        raise ModelConfigError(f"Provider account pool not found: {account_pool_id}")
    raw_entries = pool.get("accounts")
    if not isinstance(raw_entries, list):
        raise ModelConfigError(f"Provider account pool accounts must be a list: {account_pool_id}")
    entries: list[ProviderAccountPoolEntry] = []
    for raw_entry in raw_entries:
        try:
            entry = ProviderAccountPoolEntry.model_validate(raw_entry)
        except ValidationError as exc:
            raise ModelConfigError(f"Provider account pool entry is invalid: {account_pool_id}: {exc}") from exc
        if not _entry_matches(entry, service_id=service_id, capability=capability):
            continue
        entries.append(entry)
    if not entries:
        raise ModelConfigError(f"No enabled provider account for service {service_id} in pool {account_pool_id}")
    entry = sorted(entries, key=lambda item: (item.priority, item.account_id))[0]
    account = store.account(entry.account_id)
    _ensure_credential_env(entry.credential_env)
    return ProviderAccountSelection(
        account_id=entry.account_id,
        account=account,
        credential_env=entry.credential_env,
        account_pool_id=account_pool_id,
        priority=entry.priority,
        weight=entry.weight,
        concurrency_limit=entry.concurrency_limit,
        health_state=entry.health_state,
    )


def _select_service_account_ref(store: CompanyProviderSecrets, *, service_id: str) -> ProviderAccountSelection:
    service = store.service(service_id)
    account_id = str(service.get("account_ref") or "")
    account = store.account(account_id)
    credential_env = str(account.get("api_key_env") or "").strip() or None
    _ensure_credential_env(credential_env)
    return ProviderAccountSelection(
        account_id=account_id,
        account=account,
        credential_env=credential_env,
        account_pool_id=None,
        priority=100,
        weight=1,
        concurrency_limit=1,
        health_state="unknown",
    )


def _entry_matches(entry: ProviderAccountPoolEntry, *, service_id: str, capability: str) -> bool:
    if not entry.enabled or entry.health_state == "disabled":
        return False
    if entry.service_id and entry.service_id != service_id:
        return False
    return not entry.enabled_capabilities or capability in entry.enabled_capabilities


def _ensure_credential_env(credential_env: str | None) -> None:
    if credential_env and not os.environ.get(credential_env):
        raise ModelGatewayError(f"Provider credential env is not configured: {credential_env}")


__all__ = (
    "ProviderAccountPoolEntry",
    "ProviderAccountSelection",
    "select_provider_account",
)
