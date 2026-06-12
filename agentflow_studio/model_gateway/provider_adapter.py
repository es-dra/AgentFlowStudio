from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, ValidationError, field_validator

from agentflow_studio.model_gateway.company_secrets import (
    CompanyProviderSecrets,
    load_company_provider_secrets,
)
from agentflow_studio.model_gateway.errors import ModelConfigError
from agentflow_studio.model_gateway.provider_account_pool import (
    ProviderAccountSelection,
    select_provider_account,
)


ProviderCapability = Literal["image", "video", "llm", "asr"]
ProviderModality = ProviderCapability
ProviderExecutionMode = Literal["sync", "async"]


class ProviderDescriptor(BaseModel):
    schema_version: str = "provider_descriptor.v0.1"
    modality: ProviderModality
    execution_mode: ProviderExecutionMode
    capabilities: list[ProviderCapability] = Field(default_factory=list)
    account_pool_id: str | None = None
    reference_image_slots: int = Field(ge=0, le=8)
    supported_aspect_ratios: list[str] = Field(min_length=1)
    prompt_char_limit: int = Field(gt=0, le=20000)
    seed_supported: bool
    cost_hint: str = ""
    rate_limit_hint: str = ""
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
    task_type: str | None = None
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

    def translate(
        self,
        request: ProviderDispatchRequest,
        account_selection: ProviderAccountSelection,
    ) -> dict[str, Any]: ...

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]: ...

    def poll(self, task: dict[str, Any]) -> dict[str, Any]: ...

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]: ...

    def safe_error(self, error: Exception) -> dict[str, str]: ...


from agentflow_studio.model_gateway.provider_adapter_impl import (  # noqa: E402
    FakeAsyncVideoAdapter,
    MiniMaxCliLLMAdapter,
    MiniMaxImageAdapter,
    OpenAICompatibleLLMAdapter,
)


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
            if capability == "llm" and provider == "openai_compatible":
                adapters[service_id] = OpenAICompatibleLLMAdapter(store, service_id, descriptor)
                continue
            if capability == "llm" and provider == "minimax_cli":
                adapters[service_id] = MiniMaxCliLLMAdapter(store, service_id, descriptor)
                continue
            if capability == "video" and provider == "fake":
                adapters[service_id] = FakeAsyncVideoAdapter(store, service_id, descriptor)
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
        selection = select_provider_account(
            self.store,
            service_id=service_id,
            capability=capability,
            account_pool_id=adapter.descriptor.account_pool_id,
        )
        plan = adapter.translate(request, selection)
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
        descriptor = ProviderDescriptor.model_validate(payload)
    except ValidationError as exc:
        raise ModelConfigError(f"Provider service descriptor is invalid: {service_id}: {exc}") from exc
    if not descriptor.capabilities:
        descriptor = descriptor.model_copy(update={"capabilities": [descriptor.modality]})
    if descriptor.modality not in descriptor.capabilities:
        raise ModelConfigError(f"Provider service descriptor capabilities must include modality: {service_id}")
    return descriptor


__all__ = (
    "MiniMaxImageAdapter",
    "OpenAICompatibleLLMAdapter",
    "FakeAsyncVideoAdapter",
    "MiniMaxCliLLMAdapter",
    "ProviderAdapter",
    "ProviderCapability",
    "ProviderDescriptor",
    "ProviderDispatchRequest",
    "ProviderRegistry",
    "load_provider_registry",
)
