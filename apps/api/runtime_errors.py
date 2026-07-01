from __future__ import annotations

import re
from typing import Any


LOCAL_PATH_PATTERN = re.compile(r"(?i)([a-z]:\\|/users/|/home/|/tmp/|data/processed/runs)")
UNSAFE_RESPONSE_MARKERS = (
    "d:\\",
    "c:\\",
    "/sessions",
    "providers.local.json",
    "api_key",
    "token",
    "signed_url",
    "bearer ",
    "authorization",
    "provider raw",
)


class RuntimeApiError(ValueError):
    def __init__(
        self,
        error: str,
        message: str,
        *,
        stage: str = "",
        status_code: int = 422,
        user_action: str = "",
        retryable: bool = False,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(error)
        self.error = safe_error_code(error)
        self.message = safe_public_text(message, fallback=self.error)
        self.stage = safe_error_code(stage) if stage else ""
        self.status_code = status_code
        self.user_action = safe_public_text(user_action, fallback="")
        self.retryable = retryable
        self.details = safe_public_details(details or {})


def safe_error_detail(
    error: str,
    detail_code: str = "invalid_request",
    *,
    message: str = "",
    user_action: str = "",
    request_id: str = "",
    client_request_id: str = "",
    project_id: str = "",
    node_id: str = "",
    action: str = "",
    stage: str = "",
    status: str = "failed",
    retryable: bool = False,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "error": safe_error_code(error),
        "detail_code": safe_error_code(detail_code),
        "status": safe_error_code(status),
        "retryable": bool(retryable),
    }
    optional = {
        "message": safe_public_text(message, fallback=""),
        "user_action": safe_public_text(user_action, fallback=""),
        "request_id": safe_public_text(request_id, fallback=""),
        "client_request_id": safe_public_text(client_request_id, fallback=""),
        "project_id": safe_public_text(project_id, fallback=""),
        "node_id": safe_public_text(node_id, fallback=""),
        "action": safe_error_code(action),
        "stage": safe_error_code(stage),
    }
    payload.update({key: value for key, value in optional.items() if value})
    if details:
        payload["details"] = safe_public_details(details)
    return payload


def runtime_api_error_detail(
    exc: RuntimeApiError,
    *,
    request_id: str = "",
    client_request_id: str = "",
    project_id: str = "",
    node_id: str = "",
    action: str = "",
) -> dict[str, Any]:
    return safe_error_detail(
        exc.error,
        message=exc.message,
        user_action=exc.user_action,
        request_id=request_id,
        client_request_id=client_request_id,
        project_id=project_id,
        node_id=node_id,
        action=action,
        stage=exc.stage,
        retryable=exc.retryable,
        details=exc.details,
    )


def safe_exception_detail(exc: Exception, fallback: str) -> str:
    text = str(exc).strip()
    if not text or response_contains_unsafe_marker(text):
        return fallback
    return text[:200]


def safe_public_text(value: Any, *, fallback: str = "") -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text or response_contains_unsafe_marker(text):
        return fallback
    return text[:240]


def safe_error_code(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"[^a-z0-9_.-]+", "_", text).strip("_")
    return text[:80] or "unknown_error"


def safe_public_details(details: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in details.items():
        safe_key = safe_error_code(key)
        if isinstance(value, (int, float, bool)) or value is None:
            payload[safe_key] = value
        elif isinstance(value, list):
            items: list[Any] = []
            for item in value[:20]:
                if isinstance(item, dict):
                    items.append(safe_public_details({str(k): v for k, v in item.items()}))
                elif isinstance(item, (int, float, bool)) or item is None:
                    items.append(item)
                else:
                    items.append(safe_public_text(item, fallback=""))
            payload[safe_key] = items
        elif isinstance(value, dict):
            payload[safe_key] = safe_public_details({str(k): v for k, v in value.items()})
        else:
            payload[safe_key] = safe_public_text(value, fallback="")
    return payload


def response_contains_unsafe_marker(payload: Any) -> bool:
    serialized = str(payload)
    lowered = serialized.lower()
    return LOCAL_PATH_PATTERN.search(serialized) is not None or any(
        marker in lowered for marker in UNSAFE_RESPONSE_MARKERS
    )


__all__ = (
    "RuntimeApiError",
    "UNSAFE_RESPONSE_MARKERS",
    "response_contains_unsafe_marker",
    "runtime_api_error_detail",
    "safe_error_detail",
    "safe_exception_detail",
    "safe_public_details",
    "safe_public_text",
)
