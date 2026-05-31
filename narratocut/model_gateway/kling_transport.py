from __future__ import annotations

import json
import subprocess

from narratocut.model_gateway.errors import ModelProviderError


def request_json_curl(
    url: str,
    *,
    method: str,
    authorization: str,
    payload: dict | None = None,
    timeout_sec: float,
    error_prefix: str,
) -> dict:
    stdout = run_curl(
        url,
        method=method,
        authorization=authorization,
        payload=None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        timeout_sec=timeout_sec,
    )
    status, _headers, body = split_curl_response(stdout)
    if status < 200 or status >= 300:
        raise ModelProviderError(safe_curl_status_message(error_prefix, status, body))
    try:
        decoded = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ModelProviderError(f"{error_prefix} response is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise ModelProviderError(f"{error_prefix} response JSON must be an object")
    return decoded


def download_curl(url: str, *, timeout_sec: float, error_prefix: str) -> tuple[bytes, str]:
    stdout = run_curl(url, method="GET", authorization=None, payload=None, timeout_sec=timeout_sec)
    status, headers, body = split_curl_response(stdout)
    if status < 200 or status >= 300:
        raise ModelProviderError(f"{error_prefix} download HTTP error {status}")
    content_type = str(headers.get("content-type") or "").split(";")[0].strip().lower()
    if not body:
        raise ModelProviderError(f"{error_prefix} download returned empty content")
    return body, content_type


def run_curl(
    url: str,
    *,
    method: str,
    authorization: str | None,
    payload: bytes | None,
    timeout_sec: float,
) -> bytes:
    command = ["curl.exe", "-sS", "-i", "--config", "-"]
    config = [
        curl_config("url", url),
        curl_config("request", method),
        curl_config("connect-timeout", str(max(1, int(timeout_sec)))),
        curl_config("header", "Content-Type: application/json"),
    ]
    if authorization:
        config.append(curl_config("header", f"Authorization: {authorization}"))
    if payload is not None:
        config.append(curl_config("data-binary", payload.decode("utf-8")))
    result = subprocess.run(
        command,
        input="".join(config).encode("utf-8"),
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise ModelProviderError(
            f"{method} request failed: CurlError({result.returncode})"
            f"{_safe_curl_stderr_hint(result.stderr)}"
        )
    return result.stdout


def curl_config(option: str, value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
    return f'{option} = "{escaped}"\n'


def split_curl_response(stdout: bytes) -> tuple[int, dict[str, str], bytes]:
    marker = b"\r\n\r\n"
    if marker not in stdout:
        marker = b"\n\n"
    head, body = stdout.rsplit(marker, 1)
    header_blocks = head.split(marker)
    header = header_blocks[-1].decode("iso-8859-1", errors="replace")
    lines = [line.strip() for line in header.splitlines() if line.strip()]
    if not lines:
        raise ModelProviderError("Kling curl response missing status line")
    parts = lines[0].split()
    if len(parts) < 2 or not parts[1].isdigit():
        raise ModelProviderError("Kling curl response has invalid status line")
    status = int(parts[1])
    headers: dict[str, str] = {}
    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    return status, headers, body


def safe_curl_status_message(prefix: str, status: int, body: bytes) -> str:
    message = f"{prefix} HTTP error {status}"
    try:
        payload = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return message
    if not isinstance(payload, dict):
        return message
    code = payload.get("code")
    if code in {None, ""}:
        return message
    return f"{message}; provider code {code}: {provider_code_hint(code)}"


def provider_code_hint(code: object) -> str:
    hints = {
        1000: "authentication failed",
        1001: "authorization is empty",
        1002: "authorization value is invalid",
        1003: "authorization not yet valid",
        1004: "authorization expired",
        1100: "account abnormal",
        1101: "account balance is insufficient",
        1102: "account resource package exhausted or expired",
        1103: "account lacks permission for the requested resource",
        1200: "request parameters are invalid",
        1201: "request parameter key or value is invalid",
        1202: "request method is invalid",
        1203: "requested resource or model does not exist",
        1300: "platform policy triggered",
        1301: "content safety policy triggered",
        1302: "request rate exceeds platform limit",
        1303: "concurrency or QPS exceeds resource package limit",
        1304: "IP whitelist policy triggered",
        5000: "provider internal error",
        5001: "provider temporarily unavailable",
        5002: "provider internal timeout or backlog",
    }
    try:
        normalized = int(code)
    except (TypeError, ValueError):
        return "see provider dashboard"
    return hints.get(normalized, "see provider dashboard")


def _safe_curl_stderr_hint(stderr: bytes) -> str:
    if not stderr:
        return ""
    decoded = stderr.decode("utf-8", errors="replace")
    first_line = next((line.strip() for line in decoded.splitlines() if line.strip()), "")
    if not first_line:
        return ""
    first_line = _sanitize_curl_stderr(first_line)
    return f": {first_line[:160]}"


def _sanitize_curl_stderr(text: str) -> str:
    sanitized = text
    for marker in ("http://", "https://"):
        while marker in sanitized:
            start = sanitized.index(marker)
            end = start
            while end < len(sanitized) and not sanitized[end].isspace():
                end += 1
            sanitized = f"{sanitized[:start]}<redacted-url>{sanitized[end:]}"
    for sensitive in ("Bearer", "Authorization", "access_key", "secret_key", "token", "secret", "key"):
        sanitized = _redact_after_marker(sanitized, sensitive)
    return sanitized


def _redact_after_marker(text: str, marker: str) -> str:
    lower = text.lower()
    marker_lower = marker.lower()
    index = lower.find(marker_lower)
    while index != -1:
        cursor = index + len(marker)
        while cursor < len(text) and text[cursor] in {" ", "=", ":", "\t"}:
            cursor += 1
        end = cursor
        while end < len(text) and not text[end].isspace():
            end += 1
        if end > cursor:
            text = f"{text[:cursor]}<redacted>{text[end:]}"
            lower = text.lower()
        index = lower.find(marker_lower, cursor + len("<redacted>"))
    return text
