from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from narratocut.model_gateway.errors import ModelConfigError


COMPANY_PROVIDER_CONFIG_ENV = "NARRATOCUT_PROVIDER_CONFIG"
DEFAULT_COMPANY_PROVIDER_SECRETS: Path | None = None


class CompanyProviderSecrets(BaseModel):
    schema_version: str
    accounts: dict[str, dict[str, Any]] = Field(default_factory=dict)
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
