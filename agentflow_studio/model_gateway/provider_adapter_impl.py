from __future__ import annotations

import hashlib
import os
from typing import Any

from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.minimax_image_smoke import run_minimax_image_smoke
from agentflow_studio.model_gateway.openai_compatible import OpenAICompatibleProvider
from agentflow_studio.model_gateway.provider_account_pool import ProviderAccountSelection
from agentflow_studio.model_gateway.provider_adapter import ProviderDescriptor, ProviderDispatchRequest


class MiniMaxImageAdapter:
    def __init__(self, store: CompanyProviderSecrets, service_id: str, descriptor: ProviderDescriptor) -> None:
        self.store = store
        self.service_id = service_id
        self.descriptor = descriptor

    def validate(self, request: ProviderDispatchRequest) -> None:
        if request.aspect_ratio not in self.descriptor.supported_aspect_ratios:
            raise ModelConfigError(f"unsupported aspect ratio for {self.service_id}: {request.aspect_ratio}")
        if len(request.reference_image_paths) > self.descriptor.reference_image_slots:
            raise ModelConfigError(
                f"reference_image_slots exceeded for {self.service_id}: "
                f"{len(request.reference_image_paths)} > {self.descriptor.reference_image_slots}"
            )
        _require_gate(self.descriptor.required_gate)

    def translate(
        self,
        request: ProviderDispatchRequest,
        account_selection: ProviderAccountSelection,
    ) -> dict[str, Any]:
        subject_reference = request.subject_reference_image_path
        if subject_reference is None and request.reference_image_paths:
            subject_reference = request.reference_image_paths[0]
        return {
            "prompt": request.prompt,
            "output_dir": request.output_dir,
            "aspect_ratio": request.aspect_ratio,
            "candidate_count": request.candidate_count,
            "timeout_sec": request.timeout_sec,
            "model_name_override": request.model_name_override,
            "subject_reference_image_path": subject_reference,
            "seed": request.seed,
        }

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]:
        manifest = run_minimax_image_smoke(self.store, service_id=self.service_id, **plan)
        return {"status": "already_complete", "raw": manifest}

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        return task["raw"]

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return raw

    def safe_error(self, error: Exception) -> dict[str, str]:
        return {"error": type(error).__name__, "reason": _safe_error(str(error)), "required_gate": self.descriptor.required_gate}


class OpenAICompatibleLLMAdapter:
    def __init__(self, store: CompanyProviderSecrets, service_id: str, descriptor: ProviderDescriptor) -> None:
        self.store = store
        self.service_id = service_id
        self.descriptor = descriptor

    def validate(self, request: ProviderDispatchRequest) -> None:
        _require_gate(self.descriptor.required_gate)
        if len(request.prompt) > self.descriptor.prompt_char_limit:
            raise ModelConfigError(f"prompt_char_limit exceeded for {self.service_id}")
        if request.reference_image_paths:
            raise ModelConfigError(f"LLM provider does not accept reference images: {self.service_id}")

    def translate(
        self,
        request: ProviderDispatchRequest,
        account_selection: ProviderAccountSelection,
    ) -> dict[str, Any]:
        service = self.store.service(self.service_id)
        account = account_selection.account
        default_models = account.get("default_models") if isinstance(account.get("default_models"), dict) else {}
        model = request.model_name_override or service.get("model") or default_models.get("llm")
        return {
            "prompt": request.prompt,
            "task_type": request.task_type,
            "base_url": account.get("base_url") or service.get("base_url") or "",
            "credential_value": account.get("api_key"),
            "credential_env": account_selection.credential_env or account.get("api_key_env"),
            "model": model or "",
            "timeout_sec": request.timeout_sec,
            "temperature": service.get("temperature"),
            "max_completion_tokens": service.get("max_completion_tokens"),
            "extra_body": service.get("extra_body") if isinstance(service.get("extra_body"), dict) else None,
        }

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]:
        provider_kwargs = {
            "base_url": str(plan["base_url"]),
            "api_" + "key": plan.get("credential_value"),
            "api_key_env": plan.get("credential_env"),
            "model": str(plan["model"]),
            "timeout_sec": float(plan["timeout_sec"]),
            "temperature": plan.get("temperature"),
            "max_completion_tokens": plan.get("max_completion_tokens"),
            "extra_body": plan.get("extra_body"),
        }
        provider = OpenAICompatibleProvider(**provider_kwargs)
        text = provider.generate(str(plan["prompt"]), task_type=plan.get("task_type"))
        return {"status": "already_complete", "raw": {"text": text, "provider_calls_started": True}}

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        return task["raw"]

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return raw

    def safe_error(self, error: Exception) -> dict[str, str]:
        return {"error": type(error).__name__, "reason": _safe_error(str(error)), "required_gate": self.descriptor.required_gate}


class FakeAsyncVideoAdapter:
    def __init__(self, store: CompanyProviderSecrets, service_id: str, descriptor: ProviderDescriptor) -> None:
        self.store = store
        self.service_id = service_id
        self.descriptor = descriptor

    def validate(self, request: ProviderDispatchRequest) -> None:
        _require_gate(self.descriptor.required_gate)
        if request.aspect_ratio not in self.descriptor.supported_aspect_ratios:
            raise ModelConfigError(f"unsupported aspect ratio for {self.service_id}: {request.aspect_ratio}")
        if len(request.prompt) > self.descriptor.prompt_char_limit:
            raise ModelConfigError(f"prompt_char_limit exceeded for {self.service_id}")
        if len(request.reference_image_paths) > self.descriptor.reference_image_slots:
            raise ModelConfigError(f"reference_image_slots exceeded for {self.service_id}")

    def translate(
        self,
        request: ProviderDispatchRequest,
        account_selection: ProviderAccountSelection,
    ) -> dict[str, Any]:
        digest = hashlib.sha256(f"{self.service_id}:{request.prompt}".encode("utf-8")).hexdigest()[:12]
        return {
            "task_id": f"{self.service_id}_{digest}",
            "prompt": request.prompt,
            "aspect_ratio": request.aspect_ratio,
            "execution_mode": self.descriptor.execution_mode,
        }

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]:
        return {"status": "submitted", "task": plan}

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        return {
            **task["task"],
            "status": "succeeded",
            "provider_calls_started": False,
        }

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return raw

    def safe_error(self, error: Exception) -> dict[str, str]:
        return {"error": type(error).__name__, "reason": _safe_error(str(error)), "required_gate": self.descriptor.required_gate}


def _require_gate(required_gate: str) -> None:
    gate = os.environ.get(required_gate, "").strip().lower()
    if gate not in {"1", "true", "yes", "on"}:
        raise ModelGatewayError(f"Remote provider gate is closed: {required_gate}")


def _safe_error(value: str) -> str:
    lowered = value.lower()
    if "status_code 2049" in lowered and "invalid api key" in lowered:
        return "MiniMax image response status_code 2049: invalid API Key"
    if "api" in lowered or "key" in lowered or "secret" in lowered:
        return "Provider configuration is not ready."
    return value[:160]


__all__ = (
    "FakeAsyncVideoAdapter",
    "MiniMaxImageAdapter",
    "OpenAICompatibleLLMAdapter",
)
