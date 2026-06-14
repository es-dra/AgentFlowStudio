from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agentflow_studio.model_gateway.company_secrets import load_company_provider_secrets
from agentflow_studio.model_gateway.errors import ModelConfigError
from agentflow_studio.model_gateway.kling_auth import build_kling_jwt_self_check
from agentflow_studio.model_gateway.provider_adapter import ProviderRegistry


TRUE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_SERVICE_ID = "kling_i2v"


def main() -> int:
    service_id = os.environ.get("AFS_KLING_PREFLIGHT_SERVICE", DEFAULT_SERVICE_ID).strip() or DEFAULT_SERVICE_ID
    config_path, config_source = _config_source()
    report = {
        "schema_version": "kling_provider_preflight.v0.1",
        "config_source": config_source,
        "service_id": service_id,
        "status": "unknown",
        "checks": {},
        "secrets_printed": False,
    }
    try:
        store = load_company_provider_secrets(config_path)
    except (ModelConfigError, ValueError) as exc:
        report["status"] = "blocked"
        report["checks"] = {
            "block_id": _block_id_for_error(str(exc)),
            "error": _safe_error(str(exc)),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    try:
        service = store.service(service_id)
    except (ModelConfigError, ValueError) as exc:
        report["status"] = "blocked"
        report["checks"] = {
            "block_id": "provider_service_missing",
            "service_present": False,
            "available_video_service_ids": _video_service_ids(store),
            "error": _safe_error(str(exc)),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    try:
        account = store.account(str(service.get("account_ref") or ""))
        registry = ProviderRegistry.from_store(store)
        descriptor = registry.descriptor(service_id)
        required_gate = str(descriptor.required_gate or service.get("required_gate") or "AFS_ALLOW_REMOTE_VIDEO")
        report["checks"] = {
            "service_present": True,
            "provider": service.get("provider"),
            "capability": service.get("capability"),
            "api_family": service.get("api_family"),
            "descriptor_schema_version": descriptor.schema_version,
            "prompt_profile": descriptor.prompt_profile,
            "frame_slots": descriptor.frame_slots,
            "durations": descriptor.supported_durations_sec,
            "resolutions": descriptor.supported_resolutions,
            "gate": {
                "env": required_gate,
                "enabled": os.environ.get(required_gate, "").strip().lower() in TRUE_VALUES,
            },
            "credential_presence": _credential_presence(account),
            "jwt_self_check": _jwt_self_check(account),
        }
        credentials_ready = (
            report["checks"]["credential_presence"]["access_key_present"]
            and report["checks"]["credential_presence"]["secret_key_present"]
        )
        gate_ready = report["checks"]["gate"]["enabled"]
        if credentials_ready and gate_ready:
            report["status"] = "ready"
        elif not credentials_ready:
            report["status"] = "missing_credentials"
            report["checks"]["block_id"] = "provider_credentials_missing"
        else:
            report["status"] = "gate_closed"
            report["checks"]["block_id"] = "video_gate_closed"
    except (ModelConfigError, ValueError) as exc:
        report["status"] = "blocked"
        report["checks"]["block_id"] = _block_id_for_error(str(exc))
        report["checks"]["error"] = _safe_error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"ready", "missing_credentials", "gate_closed"} else 1


def _config_source() -> tuple[Path, str]:
    env_path = os.environ.get("AFS_PROVIDER_CONFIG", "").strip()
    if env_path:
        return Path(env_path), "AFS_PROVIDER_CONFIG"
    local = Path("configs/providers.local.json")
    if local.is_file():
        return local, "configs/providers.local.json"
    return Path("configs/providers.example.json"), "configs/providers.example.json"


def _credential_presence(account: dict[str, Any]) -> dict[str, Any]:
    access_value = str(account.get("access_key") or "")
    secret_value = str(account.get("secret_key") or "")
    access_env = str(account.get("access_key_env") or "").strip()
    secret_env = str(account.get("secret_key_env") or "").strip()
    return {
        "access_key_present": bool(access_value or (access_env and os.environ.get(access_env))),
        "secret_key_present": bool(secret_value or (secret_env and os.environ.get(secret_env))),
        "access_key_env": access_env or None,
        "secret_key_env": secret_env or None,
    }


def _video_service_ids(store: Any) -> list[str]:
    services = getattr(store, "services", {})
    if not isinstance(services, dict):
        return []
    return sorted(
        str(service_id)
        for service_id, service in services.items()
        if isinstance(service, dict) and (service.get("capability") == "video" or service.get("provider") == "kling")
    )


def _jwt_self_check(account: dict[str, Any]) -> dict[str, Any]:
    access_key = str(account.get("access_key") or os.environ.get(str(account.get("access_key_env") or ""), "") or "")
    secret_key = str(account.get("secret_key") or os.environ.get(str(account.get("secret_key_env") or ""), "") or "")
    if not access_key or not secret_key:
        return {"available": False, "reason": "missing_credentials"}
    jwt_config = account.get("jwt") if isinstance(account.get("jwt"), dict) else {}
    return {
        "available": True,
        **build_kling_jwt_self_check(
            access_key=access_key,
            secret_key=secret_key,
            ttl_seconds=int(jwt_config.get("ttl_seconds") or 1800),
            nbf_skew_seconds=int(jwt_config.get("nbf_skew_seconds") or -5),
        ),
    }


def _safe_error(value: str) -> str:
    lowered = value.lower()
    if "key" in lowered or "secret" in lowered or "token" in lowered or "authorization" in lowered:
        return "Provider configuration is not ready."
    return value[:180]


def _block_id_for_error(value: str) -> str:
    lowered = value.lower()
    if "not found" in lowered and "service" in lowered:
        return "provider_service_missing"
    if "not found" in lowered and "account" in lowered:
        return "provider_account_missing"
    if "file not found" in lowered or "config path is required" in lowered:
        return "provider_config_missing"
    if "json is invalid" in lowered or "schema is invalid" in lowered:
        return "provider_config_invalid"
    return "provider_config_not_ready"


if __name__ == "__main__":
    raise SystemExit(main())
