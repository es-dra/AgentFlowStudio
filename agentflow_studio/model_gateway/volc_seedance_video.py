from __future__ import annotations

import base64
import hashlib
import http.client
import ipaddress
import json
import os
import re
import socket
import ssl
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse

from agentflow_studio.model_gateway.artifact_host_policy import (
    ArtifactHostPolicy,
    artifact_host_policy,
    artifact_host_policy_from_service,
)
from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError, ModelProviderError
from agentflow_studio.model_gateway.provider_account_pool import ProviderAccountSelection
from agentflow_studio.model_gateway.provider_adapter import ProviderDescriptor, ProviderDispatchRequest


TRUE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_CREATE_ENDPOINT = "/volc/v1/contents/generations/tasks"
DEFAULT_QUERY_ENDPOINT = f"{DEFAULT_CREATE_ENDPOINT}/{{id}}"
DEFAULT_INPUT_UPLOAD_ENDPOINT = "/v1/files/uploads/base64"
EXACT_MODEL_ID = "doubao-seedance-2-0"
MAX_ERROR_BODY_BYTES = 8192
MAX_ARTIFACT_REDIRECTS = 3
ARTIFACT_REDIRECT_STATUSES = {301, 302, 303, 307, 308}
SAFE_TASK_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,159}$")
PUBLIC_REQUEST_FIELDS = {
    "model",
    "content",
    "generate_audio",
    "ratio",
    "resolution",
    "duration",
    "watermark",
    "seed",
}


class VolcSeedanceVideoAdapter:
    """Async Volc/Seedance video task adapter for relay-style providers."""

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
            raise ModelConfigError("Seedance video candidate_count must be 1")
        if len(request.reference_image_paths) > self.descriptor.reference_image_slots:
            raise ModelConfigError(f"reference_image_slots exceeded for {self.service_id}")
        input_mode = request.input_mode or ("first_last_frame" if len(request.reference_image_paths) > 1 else "first_frame")
        if self.descriptor.frame_modes and input_mode not in self.descriptor.frame_modes:
            raise ModelConfigError(f"unsupported input mode for {self.service_id}: {input_mode}")
        if request.reference_image_paths:
            _frame_roles(input_mode, len(request.reference_image_paths))
        duration = request.duration_sec or (self.descriptor.supported_durations_sec[0] if self.descriptor.supported_durations_sec else 5)
        if self.descriptor.supported_durations_sec and duration not in self.descriptor.supported_durations_sec:
            raise ModelConfigError(f"unsupported duration for {self.service_id}: {duration}")
        resolution = request.resolution or (self.descriptor.supported_resolutions[0] if self.descriptor.supported_resolutions else "")
        if self.descriptor.supported_resolutions and resolution not in self.descriptor.supported_resolutions:
            raise ModelConfigError(f"unsupported resolution for {self.service_id}: {resolution}")

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
            or default_models.get("video")
            or EXACT_MODEL_ID
        )
        if str(model) != EXACT_MODEL_ID:
            raise ModelConfigError(
                f"Seedance video service must use exact non-fast model: {EXACT_MODEL_ID}"
            )
        endpoint = str(service.get("endpoint") or DEFAULT_CREATE_ENDPOINT)
        if endpoint != DEFAULT_CREATE_ENDPOINT:
            raise ModelConfigError(
                f"Seedance video service must use native task endpoint: {DEFAULT_CREATE_ENDPOINT}"
            )
        query_endpoint = str(service.get("query_endpoint") or "")
        if query_endpoint != DEFAULT_QUERY_ENDPOINT:
            raise ModelConfigError(
                f"Seedance video service must use native task poll endpoint: {DEFAULT_QUERY_ENDPOINT}"
            )
        output_host_policy = artifact_host_policy_from_service(service)
        if not output_host_policy.configured:
            raise ModelConfigError("Seedance video artifact host allowlist must not be empty")
        exposure = _verified_exposure_contract(service)
        return {
            "base_url": _base_url(account, service),
            "endpoint": endpoint,
            "query_endpoint": query_endpoint,
            "credential_value": account.get("api_key"),
            "credential_env": account_selection.credential_env or account.get("api_key_env") or service.get("api_key_env"),
            "auth_header": str(service.get("auth_header") or account.get("auth_header") or "Authorization"),
            "auth_scheme": str(service.get("auth_scheme") or account.get("auth_scheme") or "Bearer"),
            "timeout_sec": float(service.get("submit_timeout_sec") or self.descriptor.async_timeout_sec or request.timeout_sec or 120.0),
            "download_timeout_sec": float(service.get("download_timeout_sec") or 180.0),
            "artifact_host_policy": output_host_policy.as_task_contract(),
            "allowed_url_hosts": output_host_policy.exact_hosts,
            "allowed_input_hosts": _allowed_input_hosts(service, output_host_policy.exact_hosts),
            "input_upload_endpoint": str(
                service.get("input_upload_endpoint") or DEFAULT_INPUT_UPLOAD_ENDPOINT
            ),
            "pricing_exposure": exposure,
            "output_dir": request.output_dir,
            "payload": _seedance_payload(service=service, model=str(model), request=request),
        }

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]:
        payload, upload_count = _upload_payload_images(plan)
        response = _request_json(
            _join_url(str(plan["base_url"]), str(plan["endpoint"])),
            method="POST",
            payload=payload,
            credential_value=plan.get("credential_value"),
            credential_env=plan.get("credential_env"),
            auth_header=str(plan.get("auth_header") or "Authorization"),
            auth_scheme=str(plan.get("auth_scheme") or "Bearer"),
            timeout_sec=float(plan.get("timeout_sec") or 120.0),
        )
        task_id = _task_id(response)
        return {
            "status": "submitted",
            "task_id": task_id,
            "model": str(payload.get("model") or ""),
            "duration_sec": int(payload.get("duration") or 0),
            "resolution": str(payload.get("resolution") or ""),
            "input_upload_count": upload_count,
            "input_urls_persisted": False,
            "query_url_template": _join_url(str(plan["base_url"]), str(plan["query_endpoint"])),
            "timeout_sec": float(plan.get("timeout_sec") or 120.0),
            "download_timeout_sec": float(plan.get("download_timeout_sec") or 180.0),
            "allowed_url_hosts": tuple(plan.get("allowed_url_hosts") or ()),
            "artifact_host_policy": dict(plan.get("artifact_host_policy") or {}),
            "pricing_exposure": dict(plan["pricing_exposure"]),
            "output_dir": str(plan["output_dir"]),
        }

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        task_id = str(task.get("task_id") or "")
        if not SAFE_TASK_ID.fullmatch(task_id):
            raise ModelGatewayError("Seedance video task id is invalid")
        query_template = str(task.get("query_url_template") or "")
        if not query_template.endswith(DEFAULT_QUERY_ENDPOINT):
            raise ModelGatewayError("Seedance video task poll endpoint is invalid")
        response = _request_json(
            query_template.format(id=quote(task_id, safe="")),
            method="GET",
            payload=None,
            credential_value=None,
            credential_env=str(task.get("credential_env") or _credential_env_for_service(self.store, self.service_id) or ""),
            auth_header=str(task.get("auth_header") or _auth_header_for_service(self.store, self.service_id) or "Authorization"),
            auth_scheme=str(task.get("auth_scheme") or _auth_scheme_for_service(self.store, self.service_id) or "Bearer"),
            timeout_sec=float(task.get("timeout_sec") or 120.0),
        )
        status = _task_status(response)
        if status in {"not_start", "queued", "pending", "running", "processing", "submitted", "in_progress"}:
            return {"status": "running", "task": {"task_id": task_id}}
        if status not in {"succeeded", "success", "completed", "done"}:
            raise ModelProviderError(_task_failure_reason(response, status))
        video_url = _video_url(response)
        current_host_policy = artifact_host_policy_from_service(
            self.store.service(self.service_id)
        )
        video_bytes, content_type = _download_video(
            video_url,
            timeout_sec=float(task.get("download_timeout_sec") or task.get("timeout_sec") or 120.0),
            artifact_policy=current_host_policy,
        )
        output_dir = Path(str(task.get("output_dir") or "."))
        video_ref = f"video_candidates/candidate_001{_video_extension(content_type)}"
        video_path = output_dir / video_ref
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(video_bytes)
        usage = _safe_usage(response)
        billing = _seedance_billing_hint(task, response)
        return {
            "status": "succeeded",
            "provider_calls_started": True,
            "provider_raw_response_stored": False,
            "usage": usage,
            "billing": billing,
            "outputs": [
                {
                    "candidate_id": "candidate_001",
                    "video_path": video_ref,
                    "byte_count": len(video_bytes),
                    "sha256": hashlib.sha256(video_bytes).hexdigest(),
                    "provider_url_persisted": False,
                }
            ],
        }

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        return raw

    def safe_error(self, error: Exception) -> dict[str, str]:
        return {"error": type(error).__name__, "reason": _safe_error(str(error)), "required_gate": self.descriptor.required_gate}


def _seedance_payload(*, service: dict[str, Any], model: str, request: ProviderDispatchRequest) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "text", "text": request.prompt}]
    input_mode = request.input_mode or (
        "first_last_frame" if len(request.reference_image_paths) > 1 else "first_frame"
    )
    roles = _frame_roles(input_mode, len(request.reference_image_paths))
    for path, role in zip(request.reference_image_paths, roles, strict=True):
        item = {"type": "image_url", "image_url": {"url": _image_data_url(path)}}
        item["role"] = role
        content.append(item)
    payload: dict[str, Any] = {
        "model": model,
        "content": content,
        "resolution": request.resolution,
        "ratio": request.aspect_ratio,
        "duration": request.duration_sec,
        "watermark": bool(service.get("watermark", False)),
    }
    if request.seed is not None:
        payload["seed"] = request.seed
    for key in ("camera_fixed", "generate_audio", "return_last_frame"):
        if key in service:
            payload[key] = bool(service.get(key))
    extra_body = service.get("extra_body")
    if isinstance(extra_body, dict):
        for raw_key, value in extra_body.items():
            if value in (None, "", []):
                continue
            key = str(raw_key)
            if key not in PUBLIC_REQUEST_FIELDS:
                raise ModelConfigError(
                    f"Seedance extra_body field is not in the public request contract: {key}"
                )
            if key in payload:
                if value != payload[key]:
                    raise ModelConfigError(f"Seedance extra_body cannot override request field: {key}")
                continue
            payload[key] = value
    return {key: value for key, value in payload.items() if value not in (None, "", [])}


def _frame_roles(input_mode: str, count: int) -> tuple[str, ...]:
    if input_mode == "first_frame":
        if count != 1:
            raise ModelConfigError("Seedance first_frame mode requires exactly one image")
        return ("first_frame",)
    if input_mode == "first_last_frame":
        if count != 2:
            raise ModelConfigError("Seedance first_last_frame mode requires exactly two images")
        return ("first_frame", "last_frame")
    if input_mode == "reference_images":
        if count < 1:
            raise ModelConfigError("Seedance reference_images mode requires at least one image")
        return tuple("reference_image" for _ in range(count))
    raise ModelConfigError(f"unsupported Seedance image input mode: {input_mode}")


def _upload_payload_images(plan: dict[str, Any]) -> tuple[dict[str, Any], int]:
    payload = json.loads(json.dumps(plan.get("payload") or {}, ensure_ascii=False))
    content = payload.get("content")
    if not isinstance(content, list):
        raise ModelConfigError("Seedance content contract is invalid")
    upload_count = 0
    for index, item in enumerate(content):
        if not isinstance(item, dict) or item.get("type") != "image_url":
            continue
        image_url = item.get("image_url")
        data_url = image_url.get("url") if isinstance(image_url, dict) else ""
        if not isinstance(data_url, str) or not data_url.startswith("data:image/"):
            raise ModelConfigError("Seedance local image input is invalid")
        mime_type = data_url[5:].split(";", 1)[0]
        extension = ".png" if mime_type == "image/png" else ".jpg" if mime_type == "image/jpeg" else ""
        if not extension:
            raise ModelConfigError("Seedance local image input must be PNG or JPEG")
        uploaded = _request_json(
            _join_url(
                str(plan["base_url"]),
                str(plan.get("input_upload_endpoint") or DEFAULT_INPUT_UPLOAD_ENDPOINT),
            ),
            method="POST",
            payload={
                "data": data_url,
                "filename": f"seedance-input-{index:02d}{extension}",
                "purpose": "model_input",
            },
            credential_value=plan.get("credential_value"),
            credential_env=plan.get("credential_env"),
            auth_header=str(plan.get("auth_header") or "Authorization"),
            auth_scheme=str(plan.get("auth_scheme") or "Bearer"),
            timeout_sec=float(plan.get("timeout_sec") or 120.0),
        )
        public_url = _validated_input_url(
            uploaded,
            tuple(plan.get("allowed_input_hosts") or ()),
            expected_mime_type=mime_type,
            expected_byte_count=len(base64.b64decode(data_url.split(",", 1)[1], validate=True)),
        )
        item["image_url"] = {"url": public_url}
        upload_count += 1
    return payload, upload_count


def _validated_input_url(
    response: dict[str, Any],
    allowed_hosts: tuple[str, ...],
    *,
    expected_mime_type: str,
    expected_byte_count: int,
) -> str:
    url = str(response.get("url") or "")
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    normalized = {
        str(item).lower().strip().rstrip(".")
        for item in allowed_hosts
        if str(item).strip()
    }
    try:
        port = parsed.port
    except ValueError as exc:
        raise ModelGatewayError("Seedance input upload returned an unapproved URL") from exc
    if (
        parsed.scheme.lower() != "https"
        or not host
        or host not in normalized
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or not parsed.path.startswith("/task-artifacts/tmp-inputs/")
    ):
        raise ModelGatewayError("Seedance input upload returned an unapproved URL")
    mime_type = str(response.get("mime_type") or "").split(";", 1)[0].lower()
    if mime_type != expected_mime_type:
        raise ModelGatewayError("Seedance input upload MIME type does not match")
    if int(response.get("size") or 0) != expected_byte_count:
        raise ModelGatewayError("Seedance input upload returned an invalid byte count")
    expires_at = str(response.get("expires_at") or "").strip()
    try:
        expires = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ModelGatewayError("Seedance input upload expiry is invalid") from exc
    if expires.tzinfo is None or expires.astimezone(UTC) <= datetime.now(UTC) + timedelta(minutes=5):
        raise ModelGatewayError("Seedance input upload expiry is missing")
    return url


def _request_json(
    url: str,
    *,
    method: str,
    payload: dict[str, Any] | None,
    credential_value: str | None,
    credential_env: str | None,
    auth_header: str,
    auth_scheme: str,
    timeout_sec: float,
) -> dict[str, Any]:
    api_key = credential_value or (os.environ.get(str(credential_env or "")) if credential_env else None)
    if not api_key:
        raise ModelGatewayError("Seedance video provider credential is not configured")
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Accept": "application/json"}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    headers[auth_header] = f"{auth_scheme} {api_key}".strip() if auth_scheme else str(api_key)
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        summary = _http_error_summary(exc)
        suffix = f": {summary['provider_error_message']}" if summary.get("provider_error_message") else ""
        error = ModelGatewayError(f"Seedance video HTTP error {exc.code}{suffix}")
        error.provider_error_summary = summary  # type: ignore[attr-defined]
        raise error from exc
    except urllib.error.URLError as exc:
        raise ModelGatewayError(f"Seedance video request failed: {_safe_error(str(exc.reason))}") from exc
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ModelGatewayError("Seedance video response is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ModelGatewayError("Seedance video response JSON must be an object")
    return decoded


def _download_video(
    url: str,
    *,
    timeout_sec: float,
    allowed_url_hosts: tuple[str, ...] = (),
    allowed_url_host_suffixes: tuple[str, ...] = (),
    artifact_policy: ArtifactHostPolicy | None = None,
) -> tuple[bytes, str]:
    policy = artifact_policy or artifact_host_policy(
        exact_hosts=allowed_url_hosts,
        bucket_host_suffixes=allowed_url_host_suffixes,
    )
    current_url = str(url)
    for redirect_count in range(MAX_ARTIFACT_REDIRECTS + 1):
        parsed, addresses = _validate_artifact_url(current_url, policy)
        connection: http.client.HTTPSConnection | None = None
        try:
            connection = _PinnedHTTPSConnection(
                parsed.hostname or "",
                parsed.port or 443,
                addresses=addresses,
                timeout=timeout_sec,
            )
            path = parsed.path or "/"
            if parsed.query:
                path = f"{path}?{parsed.query}"
            connection.request("GET", path, headers={"Accept": "video/*"})
            response = connection.getresponse()
            status = int(response.status)
            if status in ARTIFACT_REDIRECT_STATUSES:
                if redirect_count >= MAX_ARTIFACT_REDIRECTS:
                    raise ModelProviderError("Seedance video download exceeded redirect limit")
                location = str(response.getheader("Location") or "").strip()
                if not location:
                    raise ModelProviderError("Seedance video download redirect is invalid")
                current_url = urljoin(current_url, location)
                continue
            if status != 200:
                raise ModelProviderError(f"Seedance video download HTTP error {status}")
            body = response.read()
            content_type = (
                str(response.getheader("Content-Type") or "")
                .split(";")[0]
                .strip()
                .lower()
            )
            if not body:
                raise ModelProviderError("Seedance video download returned empty content")
            return body, content_type
        except ModelProviderError:
            raise
        except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
            raise ModelProviderError(
                f"Seedance video download failed: {_safe_error(str(exc))}"
            ) from exc
        finally:
            if connection is not None:
                connection.close()
    raise ModelProviderError("Seedance video download exceeded redirect limit")


def _safe_usage(response: dict[str, Any]) -> dict[str, Any]:
    usage = _find_usage_object(response)
    if not usage:
        return {"provider_reported_usage": False}
    safe: dict[str, Any] = {"provider_reported_usage": True}
    for key in ("prompt_tokens", "completion_tokens", "total_tokens", "input_tokens", "output_tokens"):
        value = usage.get(key)
        if isinstance(value, (int, float)):
            safe[key] = value
    return safe


def _find_usage_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        usage = value.get("usage")
        if isinstance(usage, dict):
            return usage
        for item in value.values():
            found = _find_usage_object(item)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _find_usage_object(item)
            if found:
                return found
    return {}


def _seedance_billing_hint(task: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    usage = _safe_usage(response)
    output_tokens = usage.get("output_tokens") or usage.get("completion_tokens")
    if not isinstance(output_tokens, (int, float)):
        return {
            "provider_reported_cost": False,
            "billing_mode": "output_tokens_if_reported",
            "model": str(task.get("model") or ""),
            "duration_sec": int(task.get("duration_sec") or 0),
            "resolution": str(task.get("resolution") or ""),
        }
    return {
        "provider_reported_cost": False,
        "billing_mode": "output_tokens",
        "model": str(task.get("model") or ""),
        "duration_sec": int(task.get("duration_sec") or 0),
        "resolution": str(task.get("resolution") or ""),
        "output_tokens": output_tokens,
    }


def _task_id(response: dict[str, Any]) -> str:
    data = _response_data(response)
    for key in ("id", "task_id"):
        value = data.get(key) or response.get(key)
        if isinstance(value, str) and value.strip():
            task_id = value.strip()
            if not SAFE_TASK_ID.fullmatch(task_id):
                raise ModelProviderError("Seedance video response returned an invalid task id")
            return task_id
    raise ModelProviderError("Seedance video response missing task id")


def _task_status(response: dict[str, Any]) -> str:
    data = _response_data(response)
    for key in ("status", "task_status", "state"):
        value = data.get(key) or response.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return ""

def _task_failure_reason(response: dict[str, Any], status: str) -> str:
    strings = _collect_failure_strings(response)
    combined = " ".join(strings).lower()
    if (
        "policyviolation" in combined
        or "sensitivecontent" in combined
        or "copyright restrictions" in combined
        or "copyright" in combined
    ):
        return "Seedance video policy block: output video may be related to copyright restrictions."
    for value in strings:
        if value.strip().lower() in {"success", "failure", "failed", "task failed"}:
            continue
        safe = _safe_error(_strip_provider_request_id(value))
        if safe and safe != "Seedance video provider configuration is not ready.":
            return f"Seedance video task failed: {safe}"
    return f"Seedance video task failed with status: {status or 'unknown'}"

def _collect_failure_strings(value: Any) -> list[str]:
    keys = {"code", "error", "message", "msg", "reason", "detail", "fail_reason", "fail_message"}
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in keys and isinstance(item, str) and item.strip():
                found.append(item.strip())
            found.extend(_collect_failure_strings(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_collect_failure_strings(item))
    return found


def _http_error_summary(error: urllib.error.HTTPError) -> dict[str, Any]:
    body = _read_http_error_body(error)
    decoded = _decode_error_body(body)
    strings = _collect_failure_strings(decoded) if decoded is not None else []
    code = _first_error_value(decoded, ("code", "error_code", "err_code")) if decoded is not None else ""
    message = (
        _first_error_value(decoded, ("message", "msg", "reason", "detail", "fail_reason", "fail_message"))
        if decoded is not None
        else ""
    )
    message = message or _first_useful_error_message(strings) or str(getattr(error, "reason", "") or getattr(error, "msg", "") or "")
    return {
        "provider_error_stage": "submit_http_error",
        "provider_http_status": int(getattr(error, "code", 0) or 0),
        "provider_error_code": _safe_error_value(code, limit=80),
        "provider_error_message": _safe_error_value(message, limit=180),
        "provider_raw_response_stored": False,
    }


def _read_http_error_body(error: urllib.error.HTTPError) -> bytes:
    try:
        return error.read(MAX_ERROR_BODY_BYTES) or b""
    except Exception:
        return b""


def _decode_error_body(body: bytes) -> Any:
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        text = body.decode("utf-8", errors="replace")
        return {"message": text}


def _first_error_value(value: Any, keys: tuple[str, ...]) -> str:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in keys and isinstance(item, (str, int, float)) and str(item).strip():
                return str(item).strip()
        for item in value.values():
            found = _first_error_value(item, keys)
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _first_error_value(item, keys)
            if found:
                return found
    return ""


def _first_useful_error_message(strings: list[str]) -> str:
    for value in strings:
        text = value.strip()
        if text and text.lower() not in {"error", "failed", "failure", "bad request"}:
            return text
    return ""


def _strip_provider_request_id(value: str) -> str:
    return value.split("Request id:", 1)[0].split("request id:", 1)[0].strip()


def _video_url(response: dict[str, Any]) -> str:
    data = _response_data(response)
    for root in (data.get("content"), data.get("output"), data.get("result"), data.get("task_result"), data):
        url = _first_video_url(root)
        if url:
            return url
    raise ModelProviderError("Seedance video result missing video URL")


def _first_video_url(value: Any) -> str:
    if isinstance(value, dict):
        for key in ("video_url", "videoUrl", "url"):
            item = value.get(key)
            if isinstance(item, str) and item.startswith(("http://", "https://")):
                return item
        for key in ("video", "videos", "content", "outputs", "data"):
            found = _first_video_url(value.get(key))
            if found:
                return found
    if isinstance(value, list):
        for item in value:
            found = _first_video_url(item)
            if found:
                return found
    return ""


def _response_data(response: dict[str, Any]) -> dict[str, Any]:
    return response["data"] if isinstance(response.get("data"), dict) else response


def _image_data_url(path: Path | str) -> str:
    image_path = Path(path)
    if not image_path.is_file():
        raise ModelGatewayError("Seedance reference image is missing")
    image_bytes = image_path.read_bytes()
    mime_type = _mime_type_for_bytes(image_bytes)
    if not mime_type:
        raise ModelGatewayError("Seedance reference image must be PNG or JPEG")
    return f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"


def _mime_type_for_bytes(image_bytes: bytes) -> str:
    return "image/png" if image_bytes.startswith(b"\x89PNG\r\n\x1a\n") else "image/jpeg" if image_bytes.startswith(b"\xff\xd8") else ""


def _video_extension(content_type: str) -> str:
    if content_type == "video/webm":
        return ".webm"
    if content_type == "video/quicktime":
        return ".mov"
    return ".mp4"


def _validate_artifact_url(
    url: str,
    policy: ArtifactHostPolicy | tuple[str, ...],
) -> tuple[Any, tuple[tuple[int, tuple[Any, ...]], ...]]:
    if not isinstance(policy, ArtifactHostPolicy):
        policy = artifact_host_policy(exact_hosts=policy)
    if not policy.configured:
        raise ModelProviderError("Seedance video artifact host allowlist is empty")
    parsed = urlparse(url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ModelProviderError("Seedance video download URL is not allowed") from exc
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme.lower() != "https"
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or port not in {None, 443}
        or not policy.allows(host)
    ):
        raise ModelProviderError("Seedance video download URL is not allowed")
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None or host == "localhost":
        raise ModelProviderError("Seedance video download host must be a public DNS name")
    try:
        resolved = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        addresses = tuple(
            (int(item[0]), tuple(item[4]))
            for item in resolved
        )
        address_values = {
            ipaddress.ip_address(sockaddr[0])
            for _, sockaddr in addresses
        }
    except (OSError, ValueError) as exc:
        raise ModelProviderError("Seedance video download host could not be safely resolved") from exc
    if not addresses or any(not _public_address(address) for address in address_values):
        raise ModelProviderError("Seedance video download host resolved outside the public network")
    return parsed, addresses


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(
        self,
        host: str,
        port: int,
        *,
        addresses: tuple[tuple[int, tuple[Any, ...]], ...],
        timeout: float,
    ) -> None:
        super().__init__(
            host,
            port,
            timeout=timeout,
            context=ssl.create_default_context(),
        )
        self._pinned_addresses = addresses

    def connect(self) -> None:
        last_error: OSError | None = None
        for family, sockaddr in self._pinned_addresses:
            raw = socket.socket(family, socket.SOCK_STREAM)
            try:
                raw.settimeout(self.timeout)
                raw.connect(sockaddr)
                self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
                return
            except OSError as exc:
                last_error = exc
                raw.close()
        raise OSError("Seedance video artifact host connection failed") from last_error


def _public_address(address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    )


def _base_url(account: dict[str, Any], service: dict[str, Any]) -> str:
    env_name = str(service.get("base_url_env") or account.get("base_url_env") or "").strip()
    if env_name and os.environ.get(env_name, "").strip():
        return os.environ[env_name].strip()
    return str(service.get("base_url") or account.get("base_url") or "").strip()

def _join_url(base_url: str, endpoint: str) -> str:
    if not base_url:
        raise ModelGatewayError("Seedance video base_url is not configured")
    return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

def _allowed_input_hosts(
    service: dict[str, Any],
    artifact_hosts: tuple[str, ...],
) -> tuple[str, ...]:
    value = service.get("allowed_input_hosts")
    if isinstance(value, list):
        return tuple(str(item).lower().strip() for item in value if str(item).strip())
    return artifact_hosts


def _verified_exposure_contract(service: dict[str, Any]) -> dict[str, Any]:
    contract = (
        service.get("pricing_exposure_contract")
        if isinstance(service.get("pricing_exposure_contract"), dict)
        else {}
    )
    try:
        output_token_usd = Decimal(str(contract.get("output_token_usd") or "0"))
        worst_case_output_tokens = int(contract.get("worst_case_output_tokens") or 0)
        worst_case_cost = Decimal(str(contract.get("worst_case_cost_usd") or "0"))
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise ModelConfigError("Seedance video pricing exposure contract is invalid") from exc
    calculated = output_token_usd * worst_case_output_tokens
    if (
        contract.get("verification_state") != "verified"
        or contract.get("billing_mode") != "provider_output_tokens"
        or not str(contract.get("source_checked_at") or "").strip()
        or output_token_usd <= 0
        or worst_case_output_tokens <= 0
        or worst_case_cost != calculated
        or worst_case_cost > Decimal("2.00")
        or contract.get("provider_enforced_cost_cap") is not False
    ):
        raise ModelConfigError(
            "Seedance video requires verified pricing and worst-case exposure within the USD 2.00 program ceiling"
        )
    return {
        "verification_state": "verified",
        "billing_mode": "provider_output_tokens",
        "output_token_usd": str(output_token_usd),
        "worst_case_output_tokens": worst_case_output_tokens,
        "worst_case_cost_usd": f"{worst_case_cost:.2f}",
        "source_checked_at": str(contract["source_checked_at"]),
        "provider_enforced_cost_cap": False,
    }

def _service_account(store: CompanyProviderSecrets, service_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    service = store.service(service_id)
    account_ref = str(service.get("account_ref") or "").strip()
    account = store.account(account_ref) if account_ref else {}
    return service, account

def _credential_env_for_service(store: CompanyProviderSecrets, service_id: str) -> str:
    service, account = _service_account(store, service_id)
    return str(service.get("api_key_env") or account.get("api_key_env") or "").strip()

def _auth_header_for_service(store: CompanyProviderSecrets, service_id: str) -> str:
    service, account = _service_account(store, service_id)
    return str(service.get("auth_header") or account.get("auth_header") or "Authorization")

def _auth_scheme_for_service(store: CompanyProviderSecrets, service_id: str) -> str:
    service, account = _service_account(store, service_id)
    return str(service.get("auth_scheme") or account.get("auth_scheme") or "Bearer")

def _require_gate(required_gate: str) -> None:
    if os.environ.get(required_gate, "").strip().lower() not in TRUE_VALUES:
        raise ModelGatewayError(f"Remote provider gate is closed: {required_gate}")

def _safe_error(value: str) -> str:
    return _safe_error_value(value, limit=160) or "Seedance video request failed."


def _safe_error_value(value: Any, *, limit: int) -> str:
    text = _strip_provider_request_id(" ".join(str(value or "").split()))
    text = re.sub(r"https?://\S+", "[url omitted]", text)
    text = re.sub(r"(?i)\b[a-z]:\\\S+|/(?:home|users|tmp|var)/\S+", "[path omitted]", text)
    lowered = text.lower()
    if any(term in lowered for term in ("api key", "apikey", "secret", "token", "authorization", "cookie", "bearer ")):
        return "Seedance video provider configuration is not ready."
    if any(term in lowered for term in ("data:", ".mp4", ".mov", "signed_url", "access_token", "refresh_token")):
        return "Seedance video provider returned an unsafe error detail."
    return text[:limit]


__all__ = ("VolcSeedanceVideoAdapter",)
