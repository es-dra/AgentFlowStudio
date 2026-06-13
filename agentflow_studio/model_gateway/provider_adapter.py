from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

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
FrameSlotRequirement = Literal["required", "optional", "unsupported"]


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
    frame_slots: dict[str, FrameSlotRequirement] = Field(default_factory=dict)
    frame_modes: list[str] = Field(default_factory=list)
    supported_durations_sec: list[int] = Field(default_factory=list)
    supported_resolutions: list[str] = Field(default_factory=list)
    async_poll_interval_sec: float | None = Field(default=None, gt=0)
    async_timeout_sec: float | None = Field(default=None, gt=0)
    async_max_polls: int | None = Field(default=None, gt=0)
    prompt_profile: str | None = None
    cost_estimate: dict[str, Any] = Field(default_factory=dict)

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

    @field_validator("frame_slots")
    @classmethod
    def _validate_frame_slots(cls, values: dict[str, FrameSlotRequirement]) -> dict[str, FrameSlotRequirement]:
        for key in values:
            if key not in {"first_frame", "last_frame"}:
                raise ValueError("frame_slots may only contain first_frame and last_frame")
        return values

    @field_validator("supported_durations_sec")
    @classmethod
    def _validate_durations(cls, values: list[int]) -> list[int]:
        for value in values:
            if int(value) <= 0:
                raise ValueError("supported_durations_sec entries must be positive")
        return values

    @field_validator("supported_resolutions")
    @classmethod
    def _validate_resolutions(cls, values: list[str]) -> list[str]:
        for value in values:
            text = str(value)
            if not (text.endswith("p") and text[:-1].isdigit()) and "x" not in text:
                raise ValueError("supported_resolutions entries must use 720p or WxH format")
        return values

    @model_validator(mode="after")
    def _validate_video_v02(self) -> "ProviderDescriptor":
        if self.schema_version == "provider_descriptor.v0.2" and self.modality == "video":
            if self.frame_slots.get("first_frame") != "required":
                raise ValueError("video provider_descriptor.v0.2 requires frame_slots.first_frame=required")
            if not self.frame_modes:
                raise ValueError("video provider_descriptor.v0.2 requires frame_modes")
            if not self.supported_durations_sec:
                raise ValueError("video provider_descriptor.v0.2 requires supported_durations_sec")
            if not self.supported_resolutions:
                raise ValueError("video provider_descriptor.v0.2 requires supported_resolutions")
            if not self.prompt_profile:
                raise ValueError("video provider_descriptor.v0.2 requires prompt_profile")
        return self


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
    duration_sec: int | None = None
    resolution: str | None = None
    motion: str = ""


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
    KlingVideoAdapter,
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
        store = _normalize_store_required_gates(store)
        adapters: dict[str, ProviderAdapter] = {}
        descriptors: dict[str, ProviderDescriptor] = {}
        legacy_descriptorless = _is_legacy_descriptorless_kling_store(store)
        for service_id, service in sorted(store.services.items()):
            provider = str(service.get("provider") or "")
            capability = _service_capability(service)
            if not _is_adapter_service(provider, capability):
                continue
            descriptor = _descriptor_for_service(service_id, service, allow_legacy=legacy_descriptorless)
            descriptors[service_id] = descriptor
            capability = str(service.get("capability") or descriptor.modality)
            if capability == "image" and provider == "minimax":
                adapters[service_id] = MiniMaxImageAdapter(store, service_id, descriptor)
                continue
            if capability == "llm" and provider in {"openai_compatible", "minimax", "deepseek"}:
                adapters[service_id] = OpenAICompatibleLLMAdapter(store, service_id, descriptor)
                continue
            if capability == "llm" and provider == "minimax_cli":
                adapters[service_id] = MiniMaxCliLLMAdapter(store, service_id, descriptor)
                continue
            if capability == "video" and provider == "fake":
                adapters[service_id] = FakeAsyncVideoAdapter(store, service_id, descriptor)
                continue
            if capability == "video" and provider == "kling":
                adapters[service_id] = KlingVideoAdapter(store, service_id, descriptor)
                continue
        return cls(store, adapters, descriptors)

    def descriptor(self, service_id: str) -> ProviderDescriptor:
        try:
            return self._descriptors[service_id]
        except KeyError as exc:
            raise ModelConfigError(f"Provider service not found: {service_id}") from exc

    def dispatch(self, capability: str, service_id: str, request: ProviderDispatchRequest) -> dict[str, Any]:
        task = self.submit(capability, service_id, request)
        return self.poll(capability, service_id, task)

    def submit(self, capability: str, service_id: str, request: ProviderDispatchRequest) -> dict[str, Any]:
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
        return {"service_id": service_id, "capability": capability, "task": task}

    def poll(self, capability: str, service_id: str, task: dict[str, Any]) -> dict[str, Any]:
        try:
            adapter = self._adapters[service_id]
        except KeyError as exc:
            raise ModelConfigError(f"Provider service not found: {service_id}") from exc
        if adapter.descriptor.modality != capability:
            raise ModelConfigError(f"Provider service {service_id} does not support capability: {capability}")
        raw = adapter.poll(dict(task.get("task") or task))
        return adapter.normalize(raw)


def load_provider_registry(path: str | Path | None = None) -> ProviderRegistry:
    return ProviderRegistry.from_store(load_company_provider_secrets(path))


def _descriptor_for_service(service_id: str, service: dict[str, Any], *, allow_legacy: bool = False) -> ProviderDescriptor:
    payload = service.get("descriptor")
    if not isinstance(payload, dict):
        if allow_legacy:
            return _legacy_descriptor_for_service(service_id, service)
        raise ModelConfigError(f"Provider service descriptor is required: {service_id}")
    capability = str(service.get("capability") or payload.get("modality") or "image")
    payload = _normalize_descriptor_required_gate(payload, capability)
    try:
        descriptor = ProviderDescriptor.model_validate(payload)
    except ValidationError as exc:
        raise ModelConfigError(f"Provider service descriptor is invalid: {service_id}: {exc}") from exc
    if not descriptor.capabilities:
        descriptor = descriptor.model_copy(update={"capabilities": [descriptor.modality]})
    if descriptor.modality not in descriptor.capabilities:
        raise ModelConfigError(f"Provider service descriptor capabilities must include modality: {service_id}")
    return descriptor


def _service_capability(service: dict[str, Any]) -> str:
    value = str(service.get("capability") or "")
    if value:
        return value
    descriptor = service.get("descriptor")
    if isinstance(descriptor, dict):
        return str(descriptor.get("modality") or "")
    return ""


def _is_adapter_service(provider: str, capability: str) -> bool:
    if provider == "company_gateway" or "/" in capability:
        return False
    return True


def _normalize_store_required_gates(store: CompanyProviderSecrets) -> CompanyProviderSecrets:
    services: dict[str, dict[str, Any]] = {}
    changed = False
    for service_id, service in store.services.items():
        next_service = dict(service)
        capability = str(next_service.get("capability") or "")
        descriptor = next_service.get("descriptor")
        if not capability and isinstance(descriptor, dict):
            capability = str(descriptor.get("modality") or "")
        configured = str(next_service.get("required_gate") or "")
        normalized = _legacy_required_gate(capability or "image", configured)
        if normalized != configured:
            next_service["required_gate"] = normalized
            changed = True
        if isinstance(descriptor, dict):
            normalized_descriptor = _normalize_descriptor_required_gate(descriptor, capability or "image")
            if normalized_descriptor != descriptor:
                next_service["descriptor"] = normalized_descriptor
                changed = True
        services[service_id] = next_service
    if not changed:
        return store
    return store.model_copy(update={"services": services})


def _normalize_descriptor_required_gate(payload: dict[str, Any], capability: str) -> dict[str, Any]:
    configured = str(payload.get("required_gate") or "")
    normalized = _legacy_required_gate(capability, configured)
    if normalized == configured:
        return payload
    next_payload = dict(payload)
    next_payload["required_gate"] = normalized
    return next_payload


def _is_legacy_descriptorless_kling_store(store: CompanyProviderSecrets) -> bool:
    if not store.services:
        return False
    if any(isinstance(service.get("descriptor"), dict) for service in store.services.values()):
        return False
    return any(str(service.get("provider") or "") == "kling" for service in store.services.values())


def _legacy_descriptor_for_service(service_id: str, service: dict[str, Any]) -> ProviderDescriptor:
    capability = str(service.get("capability") or "image")
    provider = str(service.get("provider") or "")
    api_family = str(service.get("api_family") or "")
    required_gate = _legacy_required_gate(capability, str(service.get("required_gate") or ""))
    if capability == "video":
        is_kling_i2v = provider == "kling" and (api_family == "i2v" or "i2v" in service_id)
        payload: dict[str, Any] = {
            "schema_version": "provider_descriptor.v0.2" if is_kling_i2v else "provider_descriptor.v0.1",
            "modality": "video",
            "execution_mode": "async",
            "capabilities": ["video"],
            "reference_image_slots": 2 if is_kling_i2v else 0,
            "supported_aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16"],
            "prompt_char_limit": 1800,
            "seed_supported": False,
            "cost_hint": "legacy-local-config",
            "rate_limit_hint": "legacy-local-config",
            "required_gate": required_gate,
        }
        if is_kling_i2v:
            payload.update(
                {
                    "frame_slots": {"first_frame": "required", "last_frame": "optional"},
                    "frame_modes": ["first_frame", "first_last_frame"],
                    "supported_durations_sec": [5, 10],
                    "supported_resolutions": ["720p", "1080p"],
                    "async_poll_interval_sec": 10,
                    "async_timeout_sec": 600,
                    "async_max_polls": 60,
                    "prompt_profile": "video_i2v_v1",
                    "cost_estimate": {"unit": "video_submit", "source": "legacy-local-config"},
                }
            )
        return ProviderDescriptor.model_validate(payload)
    if capability == "llm":
        return ProviderDescriptor.model_validate(
            {
                "schema_version": "provider_descriptor.v0.1",
                "modality": "llm",
                "execution_mode": "sync",
                "capabilities": ["llm"],
                "reference_image_slots": 0,
                "supported_aspect_ratios": ["1:1"],
                "prompt_char_limit": 12000,
                "seed_supported": False,
                "cost_hint": "legacy-local-config",
                "rate_limit_hint": "legacy-local-config",
                "required_gate": required_gate,
            }
        )
    return ProviderDescriptor.model_validate(
        {
            "schema_version": "provider_descriptor.v0.1",
            "modality": "image",
            "execution_mode": "sync",
            "capabilities": ["image"],
            "reference_image_slots": 1,
            "supported_aspect_ratios": ["1:1", "4:3", "3:4", "16:9", "9:16"],
            "prompt_char_limit": 1500,
            "seed_supported": True,
            "cost_hint": "legacy-local-config",
            "rate_limit_hint": "legacy-local-config",
            "required_gate": required_gate,
        }
    )


def _legacy_required_gate(capability: str, configured: str) -> str:
    if configured.startswith("AFS_ALLOW_REMOTE_"):
        return configured
    if configured and not configured.startswith("NARRATOCUT_ALLOW_REMOTE_"):
        return configured
    defaults = {
        "image": "AFS_ALLOW_REMOTE_IMAGE",
        "video": "AFS_ALLOW_REMOTE_VIDEO",
        "llm": "AFS_ALLOW_REMOTE_LLM",
        "asr": "AFS_ALLOW_REMOTE_ASR",
    }
    return defaults.get(capability, "AFS_ALLOW_REMOTE_IMAGE")


__all__ = (
    "MiniMaxImageAdapter",
    "OpenAICompatibleLLMAdapter",
    "FakeAsyncVideoAdapter",
    "KlingVideoAdapter",
    "MiniMaxCliLLMAdapter",
    "ProviderAdapter",
    "ProviderCapability",
    "ProviderDescriptor",
    "ProviderDispatchRequest",
    "ProviderRegistry",
    "load_provider_registry",
)
