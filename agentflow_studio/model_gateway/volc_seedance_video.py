from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from agentflow_studio.model_gateway.company_secrets import CompanyProviderSecrets
from agentflow_studio.model_gateway.errors import ModelConfigError, ModelGatewayError, ModelProviderError
from agentflow_studio.model_gateway.provider_account_pool import ProviderAccountSelection
from agentflow_studio.model_gateway.provider_adapter import ProviderDescriptor, ProviderDispatchRequest


TRUE_VALUES = {"1", "true", "yes", "on"}
DEFAULT_CREATE_ENDPOINT = "/volc/v1/contents/generations/tasks"
MAX_ERROR_BODY_BYTES = 8192


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
            or "doubao-seedance-2-0-fast"
        )
        endpoint = str(service.get("endpoint") or DEFAULT_CREATE_ENDPOINT)
        return {
            "base_url": _base_url(account, service),
            "endpoint": endpoint,
            "query_endpoint": str(service.get("query_endpoint") or f"{endpoint.rstrip('/')}/{{id}}"),
            "credential_value": account.get("api_key"),
            "credential_env": account_selection.credential_env or account.get("api_key_env") or service.get("api_key_env"),
            "auth_header": str(service.get("auth_header") or account.get("auth_header") or "Authorization"),
            "auth_scheme": str(service.get("auth_scheme") or account.get("auth_scheme") or "Bearer"),
            "timeout_sec": float(service.get("submit_timeout_sec") or self.descriptor.async_timeout_sec or request.timeout_sec or 120.0),
            "download_timeout_sec": float(service.get("download_timeout_sec") or 180.0),
            "allowed_url_hosts": _allowed_url_hosts(service),
            "output_dir": request.output_dir,
            "payload": _seedance_payload(service=service, model=str(model), request=request),
        }

    def submit(self, plan: dict[str, Any]) -> dict[str, Any]:
        response = _request_json(
            _join_url(str(plan["base_url"]), str(plan["endpoint"])),
            method="POST",
            payload=plan["payload"],
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
            "query_url_template": _join_url(str(plan["base_url"]), str(plan["query_endpoint"])),
            "timeout_sec": float(plan.get("timeout_sec") or 120.0),
            "download_timeout_sec": float(plan.get("download_timeout_sec") or 180.0),
            "allowed_url_hosts": tuple(plan.get("allowed_url_hosts") or ()),
            "output_dir": str(plan["output_dir"]),
        }

    def poll(self, task: dict[str, Any]) -> dict[str, Any]:
        task_id = str(task.get("task_id") or "")
        if not task_id:
            raise ModelGatewayError("Seedance video task id is missing")
        response = _request_json(
            str(task.get("query_url_template") or "").format(id=task_id),
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
        video_bytes, content_type = _download_video(
            video_url,
            timeout_sec=float(task.get("download_timeout_sec") or task.get("timeout_sec") or 120.0),
            allowed_url_hosts=tuple(task.get("allowed_url_hosts") or ()),
        )
        output_dir = Path(str(task.get("output_dir") or "."))
        video_ref = f"video_candidates/candidate_001{_video_extension(content_type)}"
        video_path = output_dir / video_ref
        video_path.parent.mkdir(parents=True, exist_ok=True)
        video_path.write_bytes(video_bytes)
        return {
            "status": "succeeded",
            "provider_calls_started": True,
            "provider_raw_response_stored": False,
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
    roles = service.get("reference_roles") if isinstance(service.get("reference_roles"), list) else []
    for index, path in enumerate(request.reference_image_paths, start=1):
        role = str(roles[index - 1]) if index <= len(roles) else ("first_frame" if index == 1 else "last_frame")
        item = {"type": "image_url", "image_url": {"url": _image_data_url(path)}}
        if role:
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
        payload.update(extra_body)
    return {key: value for key, value in payload.items() if value not in (None, "", [])}


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


def _download_video(url: str, *, timeout_sec: float, allowed_url_hosts: tuple[str, ...]) -> tuple[bytes, str]:
    if not _host_allowed(url, allowed_url_hosts):
        raise ModelProviderError("Seedance video download host is not allowed")
    try:
        with urllib.request.urlopen(url, timeout=timeout_sec) as response:
            body = response.read()
            content_type = str(response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    except urllib.error.HTTPError as exc:
        raise ModelProviderError(f"Seedance video download HTTP error {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ModelProviderError(f"Seedance video download failed: {_safe_error(str(exc.reason))}") from exc
    if not body:
        raise ModelProviderError("Seedance video download returned empty content")
    return body, content_type


def _task_id(response: dict[str, Any]) -> str:
    data = _response_data(response)
    for key in ("id", "task_id"):
        value = data.get(key) or response.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
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


def _host_allowed(url: str, allowed: tuple[str, ...]) -> bool:
    if not allowed:
        return True
    host = (urlparse(url).hostname or "").lower()
    for item in allowed:
        normalized = item.lower().lstrip(".")
        if host == normalized or host.endswith(f".{normalized}"):
            return True
    return False


def _base_url(account: dict[str, Any], service: dict[str, Any]) -> str:
    env_name = str(service.get("base_url_env") or account.get("base_url_env") or "").strip()
    if env_name and os.environ.get(env_name, "").strip():
        return os.environ[env_name].strip()
    return str(service.get("base_url") or account.get("base_url") or "").strip()

def _join_url(base_url: str, endpoint: str) -> str:
    if not base_url:
        raise ModelGatewayError("Seedance video base_url is not configured")
    return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

def _allowed_url_hosts(service: dict[str, Any]) -> tuple[str, ...]:
    value = service.get("allowed_artifact_hosts")
    if not isinstance(value, list):
        return ()
    return tuple(str(item).lower().strip() for item in value if str(item).strip())

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
