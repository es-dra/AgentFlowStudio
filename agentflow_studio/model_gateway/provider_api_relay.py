from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets, resolve_ref
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError
from agentflow_studio.model_gateway.image_utils import image_dimensions, image_extension
from agentflow_studio.model_gateway.provider_account_pool import ProviderAccountSelection
from agentflow_studio.model_gateway.provider_adapter import ProviderDescriptor, ProviderDispatchRequest


TRUE_VALUES = {"1", "true", "yes", "on"}


class ApiRelayAdapter:
    """Generic server-side model relay adapter for LLM, vision, and image tasks."""

    def __init__(self, store: CompanyProviderSecrets, service_id: str, descriptor: ProviderDescriptor) -> None:
        self.store = store
        self.service_id = service_id
        self.descriptor = descriptor

    def validate(self, request: ProviderDispatchRequest) -> None:
        _require_gate(self.descriptor.required_gate)
        if len(request.prompt) > self.descriptor.prompt_char_limit:
            raise ModelConfigError(f"prompt_char_limit exceeded for {self.service_id}")
        if request.aspect_ratio not in self.descriptor.supported_aspect_ratios:
            raise ModelConfigError(f"unsupported aspect ratio for {self.service_id}: {request.aspect_ratio}")
        if len(request.reference_image_paths) > self.descriptor.reference_image_slots:
            raise ModelConfigError(f"reference_image_slots exceeded for {self.service_id}")
        if self.descriptor.modality == "image" and request.candidate_count < 1:
            raise ModelConfigError("image candidate_count must be at least 1")

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
            or default_models.get(self.descriptor.modality)
            or "server-configured"
        )
        return {
            "base_url": _base_url(account, service),
            "endpoint": str(service.get("endpoint") or _endpoint_from_ref(self.store, service) or "/v1/afs/provider"),
            "credential_value": account.get("api_key"),
            "credential_env": account_selection.credential_env or account.get("api_key_env") or service.get("api_key_env"),
            "auth_header": str(service.get("auth_header") or account.get("auth_header") or "Authorization"),
            "auth_scheme": str(service.get("auth_scheme") or account.get("auth_scheme") or "Bearer"),
            "timeout_sec": float(request.timeout_sec),
            "payload": _relay_payload(
                service_id=self.service_id,
                capability=self.descriptor.modality,
                model=str(model),
                request=request,
            ),
            "output_dir": request.output_dir,
            "candidate_count": request.candidate_count,
        }

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]:
        response = _post_json(
            base_url=str(plan["base_url"]),
            endpoint=str(plan["endpoint"]),
            payload=plan["payload"],
            credential_value=plan.get("credential_value"),
            credential_env=plan.get("credential_env"),
            auth_header=str(plan.get("auth_header") or "Authorization"),
            auth_scheme=str(plan.get("auth_scheme") or "Bearer"),
            timeout_sec=float(plan.get("timeout_sec") or 120.0),
        )
        if self.descriptor.modality == "image":
            response = {
                **response,
                "outputs": _write_image_outputs(
                    Path(plan["output_dir"]),
                    response,
                    int(plan.get("candidate_count") or 1),
                ),
            }
        return {"status": "already_complete", "raw": response}

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        return task["raw"]

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        if self.descriptor.modality == "llm":
            return {"text": _extract_text(raw), "provider_calls_started": True}
        if self.descriptor.modality == "vision":
            return _normalize_vision(raw)
        if self.descriptor.modality == "image":
            return {
                "status": str(raw.get("status") or "succeeded"),
                "provider_calls_started": True,
                "provider_raw_response_stored": False,
                "outputs": raw.get("outputs") if isinstance(raw.get("outputs"), list) else [],
            }
        return raw

    def safe_error(self, error: Exception) -> dict[str, str]:
        return {"error": type(error).__name__, "reason": _safe_error(str(error)), "required_gate": self.descriptor.required_gate}


def _relay_payload(
    *,
    service_id: str,
    capability: str,
    model: str,
    request: ProviderDispatchRequest,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "afs_provider_relay_request.v0.1",
        "service_id": service_id,
        "capability": capability,
        "model": model,
        "task_type": request.task_type,
        "prompt": request.prompt,
        "aspect_ratio": request.aspect_ratio,
        "candidate_count": request.candidate_count,
        "seed": request.seed,
        "duration_sec": request.duration_sec,
        "resolution": request.resolution,
        "motion": request.motion,
    }
    refs = _reference_images_payload(request.reference_image_paths)
    if refs:
        payload["reference_images"] = refs
    if request.subject_reference_image_path is not None:
        payload["subject_reference_image"] = _reference_image_payload(request.subject_reference_image_path, 1)
    return {key: value for key, value in payload.items() if value not in (None, "", [])}


def _reference_images_payload(paths: tuple[Path | str, ...]) -> list[dict[str, Any]]:
    images = []
    for index, path in enumerate(paths, start=1):
        images.append(_reference_image_payload(path, index))
    return images


def _reference_image_payload(path: Path | str, index: int) -> dict[str, Any]:
    image_path = Path(path)
    if not image_path.is_file():
        raise ModelGatewayError("Relay reference image is missing")
    image_bytes = image_path.read_bytes()
    mime_type = _mime_type_for_bytes(image_bytes)
    if not mime_type:
        raise ModelGatewayError("Relay reference image must be PNG or JPEG")
    return {
        "name": f"reference_{index:03d}{image_path.suffix.lower() or '.png'}",
        "mime_type": mime_type,
        "byte_count": len(image_bytes),
        "sha256": hashlib.sha256(image_bytes).hexdigest(),
        "data_base64": base64.b64encode(image_bytes).decode("ascii"),
    }


def _post_json(
    *,
    base_url: str,
    endpoint: str,
    payload: dict[str, Any],
    credential_value: str | None,
    credential_env: str | None,
    auth_header: str,
    auth_scheme: str,
    timeout_sec: float,
) -> dict[str, Any]:
    if not base_url:
        raise ModelGatewayError("API relay base_url is not configured")
    api_key = credential_value or (os.environ.get(str(credential_env or "")) if credential_env else None)
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if api_key:
        headers[auth_header] = f"{auth_scheme} {api_key}".strip() if auth_scheme else str(api_key)
    request = urllib.request.Request(
        _join_url(base_url, endpoint),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        raise ModelGatewayError(f"API relay HTTP error {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ModelGatewayError(f"API relay request failed: {_safe_error(str(exc.reason))}") from exc
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ModelGatewayError("API relay response is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ModelGatewayError("API relay response JSON must be an object")
    return decoded


def _write_image_outputs(output_root: Path, response: dict[str, Any], candidate_count: int) -> list[dict[str, Any]]:
    images = _response_images(response)
    if len(images) < candidate_count:
        raise ModelGatewayError("API relay image response missing image entries")
    image_dir = output_root / "image_candidates"
    image_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[dict[str, Any]] = []
    for index, item in enumerate(images[:candidate_count], start=1):
        image_bytes = _decode_image_item(item)
        extension = image_extension(image_bytes)
        if not extension:
            raise ModelGatewayError("API relay image response must be PNG or JPEG")
        candidate_id = f"candidate_{index:03d}"
        image_ref = f"image_candidates/{candidate_id}{extension}"
        (output_root / image_ref).write_bytes(image_bytes)
        outputs.append(
            {
                "candidate_id": candidate_id,
                "image_path": image_ref,
                "byte_count": len(image_bytes),
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
                **image_dimensions(image_bytes),
                "provider_url_persisted": False,
            }
        )
    return outputs


def _response_images(response: dict[str, Any]) -> list[Any]:
    for key in ("images", "outputs", "candidates"):
        value = response.get(key)
        if isinstance(value, list):
            return value
    data = response.get("data")
    if isinstance(data, dict):
        value = data.get("images") or data.get("image_base64")
        if isinstance(value, list):
            return value
    if isinstance(response.get("image_base64"), str):
        return [response["image_base64"]]
    return []


def _decode_image_item(item: Any) -> bytes:
    if isinstance(item, str):
        encoded = item
    elif isinstance(item, dict):
        encoded = str(item.get("data_base64") or item.get("image_base64") or item.get("base64") or "")
    else:
        encoded = ""
    try:
        return base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError) as exc:
        raise ModelGatewayError("API relay image response contains invalid base64") from exc


def _normalize_vision(raw: dict[str, Any]) -> dict[str, Any]:
    observation = raw.get("observation") if isinstance(raw.get("observation"), dict) else raw
    labels = observation.get("labels") if isinstance(observation.get("labels"), list) else []
    return {
        "status": str(raw.get("status") or "succeeded"),
        "provider_calls_started": True,
        "provider_raw_response_stored": False,
        "provider_observation": {
            "description": str(observation.get("description") or observation.get("summary") or ""),
            "summary": str(observation.get("summary") or observation.get("description") or ""),
            "labels": [str(item) for item in labels[:16]],
            "feature_card": observation.get("feature_card") if isinstance(observation.get("feature_card"), dict) else {},
            "segments": observation.get("segments") if isinstance(observation.get("segments"), list) else [],
        },
        "safe_manifest": {
            "provider_raw_response_stored": False,
            "media_bytes_returned_by_api": False,
            "signed_urls_returned_by_api": False,
            "local_paths_returned_by_api": False,
        },
        "safe_evidence": raw.get("safe_evidence") if isinstance(raw.get("safe_evidence"), dict) else {},
    }


def _extract_text(raw: dict[str, Any]) -> str:
    for key in ("text", "content", "output_text", "response"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    choices = raw.get("choices")
    if isinstance(choices, list):
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                return message["content"].strip()
            if isinstance(choice.get("text"), str):
                return choice["text"].strip()
    raise ModelGatewayError("API relay LLM response missing text")


def _model_from_ref(store: CompanyProviderSecrets, service: dict[str, Any]) -> str:
    ref = service.get("default_model_ref")
    if not isinstance(ref, str) or not ref.strip():
        return ""
    value = resolve_ref(store.model_dump(mode="python"), ref.strip())
    return str(value or "").strip()


def _endpoint_from_ref(store: CompanyProviderSecrets, service: dict[str, Any]) -> str:
    ref = service.get("endpoint_ref")
    if not isinstance(ref, str) or not ref.strip():
        return ""
    value = resolve_ref(store.model_dump(mode="python"), ref.strip())
    return str(value or "").strip()


def _base_url(account: dict[str, Any], service: dict[str, Any]) -> str:
    env_name = str(service.get("base_url_env") or account.get("base_url_env") or "").strip()
    if env_name:
        env_value = os.environ.get(env_name, "").strip()
        if env_value:
            return env_value
    return str(account.get("base_url") or service.get("base_url") or "").strip()


def _join_url(base_url: str, endpoint: str) -> str:
    return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"


def _mime_type_for_bytes(image_bytes: bytes) -> str:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    return ""


def _require_gate(required_gate: str) -> None:
    if os.environ.get(required_gate, "").strip().lower() not in TRUE_VALUES:
        raise ModelGatewayError(f"Remote provider gate is closed: {required_gate}")


def _safe_error(value: str) -> str:
    lowered = value.lower()
    if any(term in lowered for term in ("api", "key", "secret", "token", "authorization", "cookie")):
        return "API relay configuration is not ready."
    return " ".join(value.split())[:160] or "API relay request failed."


__all__ = ("ApiRelayAdapter",)
