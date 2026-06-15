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
from agentflow_studio.model_gateway.minimax_image_plan import (
    api_key,
    build_minimax_image_request_plan,
    resolve_image_base_url,
)
from agentflow_studio.model_gateway.provider_adapter import ProviderRegistry


TRUE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_SERVICE_ID = "minimax_image"


def main() -> int:
    service_id = os.environ.get("AFS_MINIMAX_IMAGE_PREFLIGHT_SERVICE", DEFAULT_SERVICE_ID).strip() or DEFAULT_SERVICE_ID
    config_path, config_source = _config_source()
    report: dict[str, Any] = {
        "schema_version": "minimax_image_provider_preflight.v0.1",
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
        report["checks"] = {"block_id": _block_id_for_error(str(exc)), "error": _safe_error(str(exc))}
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    try:
        service = store.service(service_id)
    except (ModelConfigError, ValueError) as exc:
        report["status"] = "blocked"
        report["checks"] = {
            "block_id": "provider_service_missing",
            "service_present": False,
            "available_image_service_ids": _image_service_ids(store),
            "error": _safe_error(str(exc)),
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1

    try:
        account = store.account(str(service.get("account_ref") or ""))
        registry = ProviderRegistry.from_store(store)
        descriptor = registry.descriptor(service_id)
        backend = str(service.get("execution_backend") or account.get("execution_backend") or "rest_api")
        required_gate = str(descriptor.required_gate or "AFS_ALLOW_REMOTE_IMAGE")
        credentials = _credential_presence(account, backend)
        plan = build_minimax_image_request_plan(
            store,
            service_id=service_id,
            prompt="preflight only",
            aspect_ratio="9:16",
            candidate_count=1,
            require_live_gate=False,
        )
        report["checks"] = {
            "service_present": True,
            "provider": service.get("provider"),
            "capability": service.get("capability"),
            "execution_backend": backend,
            "descriptor_schema_version": descriptor.schema_version,
            "reference_image_slots": descriptor.reference_image_slots,
            "supported_aspect_ratios": descriptor.supported_aspect_ratios,
            "prompt_char_limit": descriptor.prompt_char_limit,
            "gate": {"env": required_gate, "enabled": os.environ.get(required_gate, "").strip().lower() in TRUE_VALUES},
            "credential_presence": credentials,
            "runtime": {"base_url_present": bool(resolve_image_base_url(store, account, service))},
            "plan": {
                "api_family": plan.get("api_family"),
                "model": (plan.get("create_request") or {}).get("json", {}).get("model"),
                "candidate_count": (plan.get("create_request") or {}).get("json", {}).get("n"),
                "provider_url_persisted": False,
            },
        }
        if backend == "mmx_cli":
            report["status"] = "backend_unverified"
            report["checks"]["block_id"] = "mmx_cli_backend_unverified"
        elif not credentials["api_key_present"]:
            report["status"] = "missing_credentials"
            report["checks"]["block_id"] = "provider_credentials_missing"
        elif not report["checks"]["gate"]["enabled"]:
            report["status"] = "gate_closed"
            report["checks"]["block_id"] = "image_gate_closed"
        else:
            report["status"] = "ready"
    except (ModelConfigError, ValueError) as exc:
        report["status"] = "blocked"
        report["checks"]["block_id"] = _block_id_for_error(str(exc))
        report["checks"]["error"] = _safe_error(str(exc))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] in {"ready", "missing_credentials", "gate_closed", "backend_unverified"} else 1


def _config_source() -> tuple[Path, str]:
    env_path = os.environ.get("AFS_PROVIDER_CONFIG", "").strip()
    if env_path:
        return Path(env_path), "AFS_PROVIDER_CONFIG"
    local = Path("configs/providers.local.json")
    if local.is_file():
        return local, "configs/providers.local.json"
    return Path("configs/providers.example.json"), "configs/providers.example.json"


def _credential_presence(account: dict[str, Any], backend: str) -> dict[str, Any]:
    env_name = str(account.get("api_key_env") or "").strip()
    try:
        present = bool(api_key(account)) if backend != "mmx_cli" else False
    except (ModelConfigError, ValueError):
        present = False
    return {"api_key_present": present, "api_key_env": env_name or None}


def _image_service_ids(store: Any) -> list[str]:
    services = getattr(store, "services", {})
    if not isinstance(services, dict):
        return []
    return sorted(
        str(service_id)
        for service_id, service in services.items()
        if isinstance(service, dict) and service.get("capability") == "image"
    )


def _safe_error(value: str) -> str:
    lowered = value.lower()
    if "api" in lowered or "key" in lowered or "secret" in lowered or "token" in lowered or "authorization" in lowered:
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
