from __future__ import annotations

import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from narratocut.model_gateway.company_secrets import CompanyProviderSecrets, resolve_ref
from narratocut.model_gateway.errors import ModelConfigError, ModelProviderError
from narratostudio.posterflow.minimax_provider import (
    DEFAULT_MINIMAX_BASE_URL,
    DEFAULT_MINIMAX_IMAGE_MODEL,
)


REMOTE_TRUE_VALUES = {"1", "true", "yes", "on"}


def build_minimax_image_request_plan(
    store: CompanyProviderSecrets,
    *,
    service_id: str,
    prompt: str,
    aspect_ratio: str = "9:16",
    candidate_count: int = 1,
    model_name_override: str | None = None,
    subject_reference_image_ref: str | None = None,
    require_live_gate: bool = False,
) -> dict[str, Any]:
    service = store.service(service_id)
    account = store.account(str(service.get("account_ref") or ""))
    ensure_minimax_image_service(service, service_id)
    ensure_prompt(prompt)

    required_gate = str(service.get("required_gate") or "")
    gate_enabled = gate_enabled_for(required_gate)
    if require_live_gate and not gate_enabled:
        raise ModelProviderError(f"Remote image calls are disabled; set {required_gate}=true to enable them")

    model_name = resolve_model_name(store, account, service, model_name_override)
    base_url = resolve_image_base_url(store, account, service)
    create_json: dict[str, Any] = {
        "model": model_name,
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "response_format": "base64",
        "n": candidate_count,
    }
    subject_reference = subject_reference_plan(subject_reference_image_ref)
    if subject_reference is not None:
        create_json["subject_reference"] = [
            {"type": "character", "image_file": "<runtime_subject_reference_data_url>"}
        ]

    plan = {
        "schema_version": "minimax_image_request_plan.v1",
        "service_id": service_id,
        "provider": "minimax_image",
        "api_family": "i2i" if subject_reference is not None else str(service.get("api_family") or "t2i"),
        "capability": service.get("capability"),
        "required_gate": required_gate,
        "gate_status": "enabled" if gate_enabled else "disabled",
        "live_call_authorized": gate_enabled,
        "auth": {
            "auth_type": account.get("auth_type"),
            "api_key_present": bool(api_key(account)),
            "authorization_scheme": "Bearer",
            "authorization_header_persisted": False,
            "api_key_persisted": False,
        },
        "create_request": {
            "method": "POST",
            "url": "<minimax_image_generation_endpoint>",
            "headers": {
                "Authorization": "<runtime_authorization_header>",
                "Content-Type": "application/json",
            },
            "json": create_json,
        },
        "runtime": {
            "base_url_normalized_for_runtime": bool(base_url),
            "provider_url_persisted": False,
        },
        "artifact_policy": {
            "persist_provider_urls": False,
            "persist_authorization_header": False,
            "output_root": "ignored run directory",
        },
        "claim_boundary": "dry_run_request_plan_only",
    }
    if subject_reference is not None:
        plan["subject_reference"] = subject_reference
    return plan


def ensure_minimax_image_service(service: dict[str, Any], service_id: str) -> None:
    if service.get("provider") != "minimax":
        raise ModelConfigError(f"Provider service is not a MiniMax service: {service_id}")
    if service.get("capability") != "image":
        raise ModelConfigError(f"MiniMax image smoke requires image capability: {service_id}")


def ensure_prompt(prompt: str) -> None:
    if not prompt.strip():
        raise ModelConfigError("MiniMax image prompt is required")


def resolve_image_base_url(
    store: CompanyProviderSecrets,
    account: dict[str, Any],
    service: dict[str, Any],
) -> str:
    ref = service.get("base_url_ref")
    if isinstance(ref, str) and ref.strip():
        raw = str(resolve_ref(store.model_dump(mode="python"), ref) or "")
    else:
        raw = str(account.get("image_base_url") or account.get("base_url") or DEFAULT_MINIMAX_BASE_URL)
    return normalize_minimax_image_base_url(raw)


def normalize_minimax_image_base_url(base_url: str) -> str:
    raw = base_url.strip().rstrip("/")
    if not raw:
        return DEFAULT_MINIMAX_BASE_URL
    parsed = urlparse(raw)
    if not parsed.scheme or not parsed.netloc:
        raise ModelConfigError("MiniMax base_url must include scheme and host")
    path = parsed.path.strip("/")
    if path in {"", "v1"}:
        return raw
    return urlunparse((parsed.scheme, parsed.netloc, "", "", "", ""))


def resolve_model_name(
    store: CompanyProviderSecrets,
    account: dict[str, Any],
    service: dict[str, Any],
    model_name_override: str | None,
) -> str:
    if model_name_override is not None:
        model_name = model_name_override.strip()
        if not model_name:
            raise ModelConfigError("MiniMax model_name_override cannot be blank")
        return model_name
    ref = service.get("default_model_ref")
    if isinstance(ref, str) and ref.strip():
        model_from_ref = str(resolve_ref(store.model_dump(mode="python"), ref) or "").strip()
        if model_from_ref:
            return model_from_ref
    default_models = account.get("default_models") if isinstance(account.get("default_models"), dict) else {}
    model_from_account = str(default_models.get("image") or "").strip()
    return model_from_account or DEFAULT_MINIMAX_IMAGE_MODEL


def api_key(account: dict[str, Any]) -> str:
    value = account.get("api_key") or account.get("token_plan_key") or account.get("bearer_token")
    if not isinstance(value, str) or not value.strip():
        raise ModelConfigError("MiniMax account requires api_key")
    return value.strip()


def gate_enabled_for(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in REMOTE_TRUE_VALUES


def subject_reference_plan(image_ref: str | None) -> dict[str, Any] | None:
    if image_ref is None:
        return None
    clean_ref = str(image_ref).strip()
    if not clean_ref:
        raise ModelConfigError("MiniMax subject_reference_image_ref cannot be blank")
    return {
        "image_ref": Path(clean_ref).name,
        "type": "character",
        "image_file_persisted": False,
    }
