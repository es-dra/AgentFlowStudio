from __future__ import annotations

import json
import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.kling_video_smoke import run_kling_i2v_smoke
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


class MiniMaxCliLLMAdapter:
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
        model = request.model_name_override or service.get("model") or default_models.get("llm") or "MiniMax-M2.7"
        args = [
            *_resolve_cli_invocation(str(account.get("cli_command") or service.get("cli_command") or "mmx")),
            "text",
            "chat",
            "--model",
            str(model),
            "--max-tokens",
            str(service.get("max_completion_tokens") or 900),
            "--temperature",
            str(service.get("temperature") if service.get("temperature") is not None else 0.2),
            "--output",
            "json",
            "--non-interactive",
        ]
        system_prompt = service.get("system_prompt")
        if system_prompt:
            args.extend(["--system", str(system_prompt)])
        args.extend(["--message", request.prompt])
        region = service.get("region") or account.get("region")
        if region:
            args.extend(["--region", str(region)])
        return {"args": args, "timeout_sec": request.timeout_sec}

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]:
        completed = subprocess.run(
            list(plan["args"]),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=float(plan["timeout_sec"]),
            check=False,
        )
        if completed.returncode != 0:
            raise ModelGatewayError(f"MiniMax CLI text generation failed: {_safe_error(completed.stderr or completed.stdout)}")
        return {"status": "already_complete", "raw": {"stdout": completed.stdout, "provider_calls_started": True}}

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        return task["raw"]

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {"text": _extract_cli_text(str(raw.get("stdout") or "")), "provider_calls_started": True}

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
        manifest = run_kling_i2v_smoke(self.store, **plan)
        return {"status": "already_complete", "raw": manifest}

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        return task["raw"]

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


def _resolve_cli_invocation(command: str) -> list[str]:
    resolved = shutil.which(command) or command
    suffix = Path(resolved).suffix.lower()
    if suffix == ".ps1":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", resolved]
    return [resolved]


def _extract_cli_text(stdout: str) -> str:
    value = stdout.strip()
    if not value:
        raise ModelGatewayError("MiniMax CLI text generation returned empty output")
    try:
        payload = json.loads(value)
    except json.JSONDecodeError:
        return value
    extracted = _walk_text_payload(payload)
    if not extracted:
        raise ModelGatewayError("MiniMax CLI text generation returned no text")
    return extracted


def _walk_text_payload(payload: Any) -> str:
    if isinstance(payload, str):
        return payload.strip()
    if isinstance(payload, dict):
        for key in ("text", "content", "output", "response", "message"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            nested = _walk_text_payload(value)
            if nested:
                return nested
        choices = payload.get("choices")
        if isinstance(choices, list):
            for choice in choices:
                nested = _walk_text_payload(choice)
                if nested:
                    return nested
    if isinstance(payload, list):
        for item in payload:
            nested = _walk_text_payload(item)
            if nested:
                return nested
    return ""


def _first_or_default(values: list[Any], default: Any) -> Any:
    return values[0] if values else default


__all__ = (
    "FakeAsyncVideoAdapter",
    "KlingVideoAdapter",
    "MiniMaxImageAdapter",
    "MiniMaxCliLLMAdapter",
    "OpenAICompatibleLLMAdapter",
)
