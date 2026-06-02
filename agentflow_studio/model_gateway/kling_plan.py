from __future__ import annotations

import os
from typing import Any

from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets, resolve_ref
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelProviderError
from agentflow_studio.model_gateway.kling_auth import build_kling_jwt_self_check


REMOTE_TRUE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_ASPECT_RATIO = "9:16"
DEFAULT_DURATION = "5"
DEFAULT_MODE = "pro"


def build_kling_request_plan(
    store: CompanyProviderSecrets,
    *,
    service_id: str,
    prompt: str,
    image_ref: str | None = None,
    duration: str = DEFAULT_DURATION,
    mode: str = DEFAULT_MODE,
    aspect_ratio: str = DEFAULT_ASPECT_RATIO,
    require_live_gate: bool = False,
    model_name_override: str | None = None,
) -> dict[str, Any]:
    service = store.service(service_id)
    account = store.account(str(service.get("account_ref") or ""))
    if service.get("provider") != "kling":
        raise ModelConfigError(f"Provider service is not a Kling service: {service_id}")
    if account.get("auth_type") != "jwt_hs256_from_ak_sk":
        raise ModelConfigError("Kling account must use jwt_hs256_from_ak_sk auth")

    required_gate = str(service.get("required_gate") or "")
    gate_enabled = _gate_enabled(required_gate)
    if require_live_gate and not gate_enabled:
        raise ModelProviderError(
            f"Remote {service.get('capability')} calls are disabled; set {required_gate}=true to enable them"
        )

    api_family = str(service.get("api_family") or "")
    create_url = _join_url(str(account.get("base_url") or ""), _resolve_ref(store, service, "create_endpoint_ref"))
    query_url = _join_url(str(account.get("base_url") or ""), _resolve_ref(store, service, "query_endpoint_ref"))
    model_name = _resolve_model_name(store, service, model_name_override)
    body = _request_body(
        api_family=api_family,
        model_name=model_name,
        prompt=prompt,
        image_ref=image_ref,
        duration=duration,
        mode=mode,
        aspect_ratio=aspect_ratio,
    )
    access_key = str(account.get("access_key") or "")
    secret_key = str(account.get("secret_key") or "")
    jwt_config = account.get("jwt") if isinstance(account.get("jwt"), dict) else {}
    jwt_self_check = build_kling_jwt_self_check(
        access_key=access_key,
        secret_key=secret_key,
        ttl_seconds=int(jwt_config.get("ttl_seconds") or 1800),
        nbf_skew_seconds=int(jwt_config.get("nbf_skew_seconds") or -5),
    )
    return {
        "schema_version": "kling_request_plan.v1",
        "service_id": service_id,
        "provider": "kling",
        "api_family": api_family,
        "capability": service.get("capability"),
        "required_gate": required_gate,
        "gate_status": "enabled" if gate_enabled else "disabled",
        "live_call_authorized": gate_enabled,
        "auth": {
            "auth_type": account.get("auth_type"),
            "access_key_present": bool(access_key),
            "secret_key_present": bool(secret_key),
            "authorization_scheme": "Bearer",
            "authorization_header_persisted": False,
            "jwt_self_check": jwt_self_check,
            "writes_token_to_disk": False,
        },
        "create_request": {
            "method": "POST",
            "url": create_url,
            "headers": {
                "Authorization": "<runtime_generated_authorization_header>",
                "Content-Type": "application/json",
            },
            "json": body,
        },
        "query_request": {
            "method": "GET",
            "url_template": query_url,
            "headers": {
                "Authorization": "<runtime_generated_authorization_header>",
            },
        },
        "artifact_policy": {
            "download_provider_urls": True,
            "persist_provider_urls": False,
            "output_root": "ignored run directory",
        },
        "claim_boundary": "dry_run_request_plan_only",
    }


def _request_body(
    *,
    api_family: str,
    model_name: str,
    prompt: str,
    image_ref: str | None,
    duration: str,
    mode: str,
    aspect_ratio: str,
) -> dict[str, Any]:
    if not prompt.strip():
        raise ModelConfigError("Kling prompt is required")
    if api_family == "t2v":
        return {
            "model_name": model_name,
            "prompt": prompt,
            "negative_prompt": "",
            "duration": duration,
            "mode": mode,
            "sound": "off",
            "aspect_ratio": aspect_ratio,
            "watermark_info": {"enabled": False},
        }
    if api_family == "i2v":
        if not image_ref:
            raise ModelConfigError("Kling I2V request plan requires image_ref")
        return {
            "model_name": model_name,
            "image": {
                "source": "local_path",
                "path": image_ref,
                "send_as": "base64_without_data_uri",
            },
            "prompt": prompt,
            "negative_prompt": "",
            "duration": duration,
            "mode": mode,
            "sound": "off",
            "watermark_info": {"enabled": False},
        }
    raise ModelConfigError(f"Unsupported Kling api_family: {api_family}")


def _resolve_ref(store: CompanyProviderSecrets, service: dict[str, Any], field: str) -> Any:
    ref = service.get(field)
    if not isinstance(ref, str):
        raise ModelConfigError(f"Kling service missing {field}")
    return resolve_ref(store.model_dump(mode="python"), ref)


def _resolve_model_name(
    store: CompanyProviderSecrets,
    service: dict[str, Any],
    model_name_override: str | None,
) -> str:
    if model_name_override is not None:
        model_name = model_name_override.strip()
        if not model_name:
            raise ModelConfigError("Kling model_name_override cannot be blank")
        return model_name
    return str(_resolve_ref(store, service, "default_model_ref") or "")


def _join_url(base_url: str, path: str) -> str:
    if not base_url:
        raise ModelConfigError("Kling base_url is required")
    if not path.startswith("/"):
        raise ModelConfigError(f"Kling endpoint must start with '/': {path}")
    return f"{base_url.rstrip('/')}{path}"


def _gate_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in REMOTE_TRUE_VALUES
