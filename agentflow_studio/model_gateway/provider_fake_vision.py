from __future__ import annotations

import hashlib
import os
from typing import Any

from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.provider_account_pool import ProviderAccountSelection
from agentflow_studio.model_gateway.provider_adapter import ProviderDescriptor, ProviderDispatchRequest


TRUE_VALUES = {"1", "true", "yes", "on"}


class FakeVisionAdapter:
    def __init__(self, service_id: str, descriptor: ProviderDescriptor) -> None:
        self.service_id = service_id
        self.descriptor = descriptor

    def validate(self, request: ProviderDispatchRequest) -> None:
        _require_gate(self.descriptor.required_gate)
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
            "prompt_char_count": len(request.prompt),
            "reference_image_count": len(request.reference_image_paths),
        }

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]:
        return {"status": "already_complete", "raw": plan}

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        return task["raw"]

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "succeeded",
            "task_id": raw.get("task_id"),
            "provider_calls_started": True,
            "safe_manifest": {
                "provider_raw_response_stored": False,
                "media_bytes_returned_by_api": False,
                "signed_urls_returned_by_api": False,
                "local_paths_returned_by_api": False,
            },
            "safe_evidence": {
                "prompt_char_count": raw.get("prompt_char_count", 0),
                "reference_image_count": raw.get("reference_image_count", 0),
            },
        }

    def safe_error(self, error: Exception) -> dict[str, str]:
        return {"error": type(error).__name__, "reason": "Fake vision adapter failed.", "required_gate": self.descriptor.required_gate}


def _require_gate(required_gate: str) -> None:
    if os.environ.get(required_gate, "").strip().lower() not in TRUE_VALUES:
        raise ModelGatewayError(f"Remote provider gate is closed: {required_gate}")


__all__ = ("FakeVisionAdapter",)
