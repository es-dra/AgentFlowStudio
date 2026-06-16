from __future__ import annotations

import os
from typing import Any

from agentflow_studio.model_gateway.codex_image_handoff import create_handoff_task, poll_handoff_task
from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.provider_account_pool import ProviderAccountSelection
from agentflow_studio.model_gateway.provider_adapter import ProviderDescriptor, ProviderDispatchRequest


class CodexImageHandoffAdapter:
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
        if request.candidate_count != 1:
            raise ModelConfigError("Codex image handoff candidate_count must be 1")
        if len(request.reference_image_paths) > self.descriptor.reference_image_slots:
            raise ModelConfigError(f"reference_image_slots exceeded for {self.service_id}")

    def translate(
        self,
        request: ProviderDispatchRequest,
        account_selection: ProviderAccountSelection,
    ) -> dict[str, Any]:
        return {
            "service_id": self.service_id,
            "prompt": request.prompt,
            "output_dir": request.output_dir,
            "aspect_ratio": request.aspect_ratio,
            "candidate_count": request.candidate_count,
            "timeout_sec": request.timeout_sec,
            "reference_image_paths": tuple(request.reference_image_paths),
            "subject_reference_image_path": request.subject_reference_image_path,
            "seed": request.seed,
            "account": account_selection.public_summary(),
        }

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]:
        return create_handoff_task(plan)

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        return poll_handoff_task(task)

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
    if any(term in lowered for term in ("api", "key", "secret", "token", "authorization", "cookie")):
        return "Image generation worker configuration is not ready."
    return value[:160]


__all__ = ("CodexImageHandoffAdapter",)
