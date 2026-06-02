from __future__ import annotations

import base64
import time
from pathlib import Path
from typing import Any, Callable

import httpx

from agentflow_studio.model_gateway.errors import ModelConfigError, ModelProviderError
from agentflow_studio.model_gateway.kling_auth import encode_kling_jwt
from agentflow_studio.model_gateway.kling_transport import (
    download_curl,
    provider_code_hint,
    request_json_curl,
)


JsonRequest = Callable[..., dict[str, Any]]
VideoDownload = Callable[..., tuple[bytes, str]]


def build_runtime_payload(plan_payload: dict[str, Any], image_path: Path) -> dict[str, Any]:
    payload = dict(plan_payload)
    payload["image"] = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return payload


def build_runtime_token(account: dict[str, Any]) -> str:
    jwt_config = account.get("jwt") if isinstance(account.get("jwt"), dict) else {}
    return encode_kling_jwt(
        access_key=str(account.get("access_key") or ""),
        secret_key=str(account.get("secret_key") or ""),
        ttl_seconds=int(jwt_config.get("ttl_seconds") or 1800),
        nbf_skew_seconds=int(jwt_config.get("nbf_skew_seconds") or -5),
    )


def request_json(
    url: str,
    *,
    method: str,
    authorization: str,
    payload: dict[str, Any] | None = None,
    timeout_sec: float,
) -> dict[str, Any]:
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            response = client.request(method, url, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ModelProviderError(_safe_http_status_message("Kling video", exc.response)) from exc
    except httpx.HTTPError as exc:
        raise ModelProviderError(f"Kling video request failed: {_safe_http_error(exc)}") from exc
    try:
        decoded = response.json()
    except ValueError as exc:
        raise ModelProviderError("Kling video response is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ModelProviderError("Kling video response JSON must be an object")
    ensure_provider_success(decoded)
    return decoded


def request_json_with_transport(transport: str) -> JsonRequest:
    if transport == "httpx":
        return request_json
    if transport == "curl":
        return request_json_via_curl
    raise ModelConfigError(f"Unsupported Kling HTTP transport: {transport}")


def download_with_transport(transport: str) -> VideoDownload:
    if transport == "httpx":
        return download
    if transport == "curl":
        return download_via_curl
    raise ModelConfigError(f"Unsupported Kling HTTP transport: {transport}")


def request_json_via_curl(
    url: str,
    *,
    method: str,
    authorization: str,
    payload: dict[str, Any] | None = None,
    timeout_sec: float,
) -> dict[str, Any]:
    decoded = request_json_curl(
        url,
        method=method,
        authorization=authorization,
        payload=payload,
        timeout_sec=timeout_sec,
        error_prefix="Kling video",
    )
    ensure_provider_success(decoded)
    return decoded


def poll_video_task(
    url_template: str,
    *,
    task_id: str,
    authorization: str,
    request_json: JsonRequest,
    poll_interval_sec: float,
    max_polls: int,
    timeout_sec: float,
) -> dict[str, Any]:
    if max_polls < 1:
        raise ModelProviderError("Kling video smoke max_polls must be at least 1")
    query_url = url_template.format(id=task_id)
    last_status = ""
    for attempt in range(max_polls):
        response = request_json(
            query_url,
            method="GET",
            authorization=authorization,
            timeout_sec=timeout_sec,
        )
        data = response_data(response)
        status = str(data.get("task_status") or "").lower()
        last_status = status
        if status in {"succeed", "succeeded", "success"}:
            return data
        if status in {"failed", "fail"}:
            raise ModelProviderError("Kling video task failed")
        if attempt < max_polls - 1 and poll_interval_sec > 0:
            time.sleep(poll_interval_sec)
    raise ModelProviderError(f"Kling video task did not finish after {max_polls} polls; last status: {last_status}")


def download(url: str, *, timeout_sec: float) -> tuple[bytes, str]:
    try:
        with httpx.Client(timeout=timeout_sec) as client:
            response = client.request("GET", url)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise ModelProviderError(f"Kling video download HTTP error {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise ModelProviderError(f"Kling video download failed: {_safe_http_error(exc)}") from exc
    body = response.content
    content_type = str(response.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    if not body:
        raise ModelProviderError("Kling video download returned empty content")
    return body, content_type


def download_via_curl(url: str, *, timeout_sec: float) -> tuple[bytes, str]:
    return download_curl(url, timeout_sec=timeout_sec, error_prefix="Kling video")


def task_video_url(task_data: dict[str, Any]) -> str:
    task_result = task_data.get("task_result")
    if not isinstance(task_result, dict):
        raise ModelProviderError("Kling video task missing task_result")
    videos = task_result.get("videos")
    if not isinstance(videos, list) or not videos:
        raise ModelProviderError("Kling video task missing result videos")
    first = videos[0]
    if not isinstance(first, dict):
        raise ModelProviderError("Kling video result entry must be an object")
    url = first.get("url")
    if not isinstance(url, str) or not url.strip():
        raise ModelProviderError("Kling video result missing video URL")
    return url.strip()


def response_data(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    if not isinstance(data, dict):
        raise ModelProviderError("Kling video response missing data object")
    return data


def ensure_provider_success(response: dict[str, Any]) -> None:
    code = response.get("code")
    if code in {None, 0, "0"}:
        return
    raise ModelProviderError(f"Kling video response code {code}")


def video_extension(content_type: str) -> str:
    if content_type == "video/mp4":
        return ".mp4"
    if content_type == "video/webm":
        return ".webm"
    return ".video"


def _safe_http_error(exc: httpx.HTTPError) -> str:
    return exc.__class__.__name__


def _safe_http_status_message(prefix: str, response: httpx.Response) -> str:
    message = f"{prefix} HTTP error {response.status_code}"
    try:
        payload = response.json()
    except ValueError:
        return message
    if not isinstance(payload, dict):
        return message
    code = payload.get("code")
    if code in {None, ""}:
        return message
    return f"{message}; provider code {code}: {provider_code_hint(code)}"
