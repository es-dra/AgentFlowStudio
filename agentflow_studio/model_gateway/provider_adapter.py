from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, ValidationError, field_validator

from agentflow_studio.model_gateway.company_secrets import (
    CompanyProviderSecrets,
    load_company_provider_secrets,
)
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.minimax_image_smoke import run_minimax_image_smoke


ProviderModality = Literal["image", "video", "llm", "asr"]
ProviderExecutionMode = Literal["sync", "async"]


class ProviderDescriptor(BaseModel):
    schema_version: str = "provider_descriptor.v0.1"
    modality: ProviderModality
    execution_mode: ProviderExecutionMode
    reference_image_slots: int = Field(ge=0, le=8)
    supported_aspect_ratios: list[str] = Field(min_length=1)
    prompt_char_limit: int = Field(gt=0, le=20000)
    seed_supported: bool
    cost_hint: str = ""
    required_gate: str

    @field_validator("required_gate")
    @classmethod
    def _validate_gate(cls, value: str) -> str:
        if not value.startswith("AFS_ALLOW_REMOTE_"):
            raise ValueError("required_gate must be an AFS_ALLOW_REMOTE_* environment variable")
        return value

    @field_validator("supported_aspect_ratios")
    @classmethod
    def _validate_ratios(cls, values: list[str]) -> list[str]:
        for value in values:
            left, sep, right = value.partition(":")
            if sep != ":" or not left.isdigit() or not right.isdigit():
                raise ValueError("supported_aspect_ratios entries must use N:N format")
            if int(left) <= 0 or int(right) <= 0:
                raise ValueError("supported_aspect_ratios entries must be positive")
        return values


@dataclass(frozen=True)
class ProviderDispatchRequest:
    prompt: str
    output_dir: Path
    aspect_ratio: str = "9:16"
    candidate_count: int = 1
    timeout_sec: float = 120.0
    model_name_override: str | None = None
    reference_image_paths: tuple[Path | str, ...] = ()
    subject_reference_image_path: Path | str | None = None
    seed: int | None = None


class ProviderAdapter(Protocol):
    descriptor: ProviderDescriptor

    def validate(self, request: ProviderDispatchRequest) -> None: ...

    def translate(self, request: ProviderDispatchRequest) -> dict[str, Any]: ...

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]: ...

    def poll(self, task: dict[str, Any]) -> dict[str, Any]: ...

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]: ...

    def safe_error(self, error: Exception) -> dict[str, str]: ...


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
        gate = os.environ.get(self.descriptor.required_gate, "").strip().lower()
        if gate not in {"1", "true", "yes", "on"}:
            raise ModelGatewayError(f"Remote provider gate is closed: {self.descriptor.required_gate}")

    def translate(self, request: ProviderDispatchRequest) -> dict[str, Any]:
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


class ProviderRegistry:
    def __init__(
        self,
        store: CompanyProviderSecrets,
        adapters: dict[str, ProviderAdapter],
        descriptors: dict[str, ProviderDescriptor],
    ) -> None:
        self.store = store
        self._adapters = adapters
        self._descriptors = descriptors

    @classmethod
    def from_store(cls, store: CompanyProviderSecrets) -> "ProviderRegistry":
        adapters: dict[str, ProviderAdapter] = {}
        descriptors: dict[str, ProviderDescriptor] = {}
        for service_id, service in sorted(store.services.items()):
            descriptor = _descriptor_for_service(service_id, service)
            descriptors[service_id] = descriptor
            capability = str(service.get("capability") or descriptor.modality)
            provider = str(service.get("provider") or "")
            if capability == "image" and provider == "minimax":
                adapters[service_id] = MiniMaxImageAdapter(store, service_id, descriptor)
                continue
        return cls(store, adapters, descriptors)

    def descriptor(self, service_id: str) -> ProviderDescriptor:
        try:
            return self._descriptors[service_id]
        except KeyError as exc:
            raise ModelConfigError(f"Provider service not found: {service_id}") from exc

    def dispatch(self, capability: str, service_id: str, request: ProviderDispatchRequest) -> dict[str, Any]:
        try:
            adapter = self._adapters[service_id]
        except KeyError as exc:
            raise ModelConfigError(f"Provider service not found: {service_id}") from exc
        if adapter.descriptor.modality != capability:
            raise ModelConfigError(f"Provider service {service_id} does not support capability: {capability}")
        adapter.validate(request)
        plan = adapter.translate(request)
        task = adapter.submit(plan)
        raw = adapter.poll(task)
        return adapter.normalize(raw)


def load_provider_registry(path: str | Path | None = None) -> ProviderRegistry:
    return ProviderRegistry.from_store(load_company_provider_secrets(path))


def _descriptor_for_service(service_id: str, service: dict[str, Any]) -> ProviderDescriptor:
    payload = service.get("descriptor")
    if not isinstance(payload, dict):
        raise ModelConfigError(f"Provider service descriptor is required: {service_id}")
    try:
        return ProviderDescriptor.model_validate(payload)
    except ValidationError as exc:
        raise ModelConfigError(f"Provider service descriptor is invalid: {service_id}: {exc}") from exc


def _safe_error(value: str) -> str:
    lowered = value.lower()
    if "status_code 2049" in lowered and "invalid api key" in lowered:
        return "MiniMax image response status_code 2049: invalid API Key"
    if "api" in lowered or "key" in lowered or "secret" in lowered:
        return "Provider configuration is not ready."
    return value[:160]


__all__ = (
    "MiniMaxImageAdapter",
    "ProviderAdapter",
    "ProviderDescriptor",
    "ProviderDispatchRequest",
    "ProviderRegistry",
    "load_provider_registry",
)
