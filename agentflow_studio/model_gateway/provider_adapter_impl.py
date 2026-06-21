from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets, resolve_ref
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.kling_video_smoke import poll_kling_i2v_task_once, submit_kling_i2v_task
from agentflow_studio.model_gateway.openai_compatible import OpenAICompatibleProvider
from agentflow_studio.model_gateway.provider_account_pool import ProviderAccountSelection
from agentflow_studio.model_gateway.provider_adapter import ProviderDescriptor, ProviderDispatchRequest


DEFAULT_DEEPSEEK_TEXT_MODEL = "deepseek-chat"


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
        model = (
            request.model_name_override
            or service.get("model")
            or _model_from_ref(self.store, service)
            or default_models.get("llm")
            or _legacy_llm_default_model(service)
        )
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


class KlingVideoAdapter:
    def __init__(self, store: CompanyProviderSecrets, service_id: str, descriptor: ProviderDescriptor) -> None:
        self.store = store
        self.service_id = service_id
        self.descriptor = descriptor

    def validate(self, request: ProviderDispatchRequest) -> None:
        _require_gate(self.descriptor.required_gate)
        service = self.store.service(self.service_id)
        if service.get("api_family") != "i2v":
            raise ModelConfigError(f"Kling Studio adapter only supports i2v services: {self.service_id}")
        if request.aspect_ratio not in self.descriptor.supported_aspect_ratios:
            raise ModelConfigError(f"unsupported aspect ratio for {self.service_id}: {request.aspect_ratio}")
        if len(request.prompt) > self.descriptor.prompt_char_limit:
            raise ModelConfigError(f"prompt_char_limit exceeded for {self.service_id}")
        if request.candidate_count != 1:
            raise ModelConfigError("Kling I2V candidate_count must be 1")
        if len(request.reference_image_paths) > self.descriptor.reference_image_slots:
            raise ModelConfigError(f"reference_image_slots exceeded for {self.service_id}")
        if request.subject_reference_image_path is None and not request.reference_image_paths:
            raise ModelConfigError("Kling I2V requires an explicit first frame image")
        duration = request.duration_sec or _first_or_default(self.descriptor.supported_durations_sec, 5)
        if self.descriptor.supported_durations_sec and duration not in self.descriptor.supported_durations_sec:
            raise ModelConfigError(f"unsupported duration for {self.service_id}: {duration}")
        resolution = request.resolution or _first_or_default(self.descriptor.supported_resolutions, "")
        if self.descriptor.supported_resolutions and resolution not in self.descriptor.supported_resolutions:
            raise ModelConfigError(f"unsupported resolution for {self.service_id}: {resolution}")

    def translate(
        self,
        request: ProviderDispatchRequest,
        account_selection: ProviderAccountSelection,
    ) -> dict[str, Any]:
        first_frame = request.subject_reference_image_path or request.reference_image_paths[0]
        service = self.store.service(self.service_id)
        return {
            "service_id": self.service_id,
            "prompt": request.prompt,
            "image_path": Path(first_frame),
            "output_dir": request.output_dir,
            "duration": str(request.duration_sec or _first_or_default(self.descriptor.supported_durations_sec, 5)),
            "mode": str(service.get("mode") or "pro"),
            "poll_interval_sec": float(self.descriptor.async_poll_interval_sec or 5.0),
            "max_polls": int(self.descriptor.async_max_polls or 120),
            "timeout_sec": float(request.timeout_sec or self.descriptor.async_timeout_sec or 120.0),
            "transport": str(service.get("transport") or "httpx"),
            "model_name_override": request.model_name_override,
        }

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]:
        state = submit_kling_i2v_task(
            self.store,
            service_id=str(plan["service_id"]),
            prompt=str(plan["prompt"]),
            image_path=plan["image_path"],
            output_dir=plan["output_dir"],
            duration=str(plan["duration"]),
            mode=str(plan["mode"]),
            timeout_sec=float(plan["timeout_sec"]),
            transport=str(plan["transport"]),
            model_name_override=plan.get("model_name_override"),
        )
        return {
            "status": "submitted",
            "state": state,
            "output_dir": str(plan["output_dir"]),
            "timeout_sec": float(plan["timeout_sec"]),
            "transport": str(plan["transport"]),
        }

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        status = str(task.get("status") or "")
        if status == "already_complete":
            return task["raw"]
        state = task.get("state")
        if not isinstance(state, dict):
            raise ModelGatewayError("Kling adapter task state is missing")
        return poll_kling_i2v_task_once(
            self.store,
            output_dir=task.get("output_dir") or ".",
            state=state,
            timeout_sec=float(task.get("timeout_sec") or 120.0),
            transport=str(task.get("transport") or "httpx"),
        )

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
        return "Image provider rejected the configured credential."
    if "api" in lowered or "key" in lowered or "secret" in lowered:
        return "Provider configuration is not ready."
    return value[:160]


def _model_from_ref(store: CompanyProviderSecrets, service: dict[str, Any]) -> str:
    ref = service.get("default_model_ref")
    if not isinstance(ref, str) or not ref.strip():
        return ""
    value = resolve_ref(store.model_dump(mode="python"), ref.strip())
    return str(value or "").strip()


def _legacy_llm_default_model(service: dict[str, Any]) -> str:
    provider = str(service.get("provider") or "")
    if provider == "deepseek":
        return DEFAULT_DEEPSEEK_TEXT_MODEL
    return ""


def _first_or_default(values: list[Any], default: Any) -> Any:
    return values[0] if values else default


__all__ = (
    "FakeAsyncVideoAdapter",
    "KlingVideoAdapter",
    "OpenAICompatibleLLMAdapter",
)
