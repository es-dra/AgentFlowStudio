from __future__ import annotations

import json
import os
import uuid
import urllib.error
import urllib.request
from typing import Any

from agentflow_studio.model_gateway.errors import ModelGatewayError


def post_multipart(
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
    boundary = f"afs-{uuid.uuid4().hex}"
    body = _multipart_body(
        payload.get("fields") if isinstance(payload.get("fields"), dict) else {},
        payload.get("files") if isinstance(payload.get("files"), list) else [],
        boundary,
    )
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Accept": "application/json",
    }
    api_key = credential_value or (os.environ.get(str(credential_env or "")) if credential_env else None)
    if api_key:
        headers[auth_header] = f"{auth_scheme} {api_key}".strip() if auth_scheme else str(api_key)
    request = urllib.request.Request(
        _join_url(base_url, endpoint),
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_sec) as response:
            response_body = response.read()
    except urllib.error.HTTPError as exc:
        raise ModelGatewayError(f"API relay HTTP error {exc.code}") from exc
    except TimeoutError as exc:
        raise ModelGatewayError("API relay request timed out while reading provider result") from exc
    except urllib.error.URLError as exc:
        if _looks_like_timeout(str(exc.reason)):
            raise ModelGatewayError("API relay request timed out while reading provider result") from exc
        raise ModelGatewayError(f"API relay request failed: {_safe_error(str(exc.reason))}") from exc
    try:
        decoded = json.loads(response_body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ModelGatewayError("API relay response is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ModelGatewayError("API relay response JSON must be an object")
    return decoded


def _multipart_body(fields: dict[str, Any], files: list[Any], boundary: str) -> bytes:
    chunks: list[bytes] = []
    for name, value in fields.items():
        if value in (None, ""):
            continue
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{_quote_header(str(name))}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )
    for item in files:
        if not isinstance(item, dict):
            continue
        field_name = str(item.get("field_name") or "image")
        filename = str(item.get("filename") or "source.png")
        mime_type = str(item.get("mime_type") or "application/octet-stream")
        data = item.get("data")
        if not isinstance(data, bytes):
            raise ModelGatewayError("API relay multipart file data must be bytes")
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="{_quote_header(field_name)}"; '
                    f'filename="{_quote_header(filename)}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {mime_type}\r\n\r\n".encode("utf-8"),
                data,
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks)


def _quote_header(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "").replace("\n", "")


def _join_url(base_url: str, endpoint: str) -> str:
    return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"


def _safe_error(value: str) -> str:
    lowered = value.lower()
    if any(term in lowered for term in ("api", "key", "secret", "token", "authorization", "cookie")):
        return "API relay configuration is not ready."
    return " ".join(value.split())[:160] or "API relay request failed."


def _looks_like_timeout(value: str) -> bool:
    lowered = value.lower()
    return "timed out" in lowered or "timeout" in lowered


__all__ = ("post_multipart",)
