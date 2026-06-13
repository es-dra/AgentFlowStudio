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


def safe_error_detail(error: str, detail_code: str = "invalid_request") -> dict[str, Any]:
    return {
        "error": error,
        "detail_code": detail_code,
    }


def safe_exception_detail(exc: Exception, fallback: str) -> str:
    text = str(exc).strip()
    if not text or response_contains_unsafe_marker(text):
        return fallback
    return text[:200]


def response_contains_unsafe_marker(payload: Any) -> bool:
    serialized = str(payload)
    lowered = serialized.lower()
    return LOCAL_PATH_PATTERN.search(serialized) is not None or any(
        marker in lowered for marker in UNSAFE_RESPONSE_MARKERS
    )


__all__ = (
    "UNSAFE_RESPONSE_MARKERS",
    "response_contains_unsafe_marker",
    "safe_error_detail",
    "safe_exception_detail",
)
