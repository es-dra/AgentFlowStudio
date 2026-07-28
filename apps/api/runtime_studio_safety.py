from __future__ import annotations

from typing import Any, Mapping

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS


PRIVATE_KEY_MARKERS = {
    "api_key",
    "access_token",
    "refresh_token",
    "secret",
    "authorization",
    "cookie",
    "signed_url",
    "local_path",
    "absolute_path",
    "raw_response",
    "provider_response",
}
PRIVATE_VALUE_MARKERS = tuple(
    fragment.lower() for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
) + (
    "x-amz-signature",
    "x-goog-signature",
    "signature=",
    "token=",
)
OMIT = object()


def sanitize_public_value(value: Any, *, depth: int = 0) -> Any:
    if depth > 4:
        return OMIT
    if value is None or isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, str):
        safe = safe_text(value, 1000)
        return safe if safe else OMIT
    if isinstance(value, list):
        result = []
        for item in value[:50]:
            safe_item = sanitize_public_value(item, depth=depth + 1)
            if safe_item is not OMIT:
                result.append(safe_item)
        return result
    if isinstance(value, Mapping):
        result = {}
        for key, item in list(value.items())[:50]:
            safe_nested_key = safe_key(key)
            if not safe_nested_key:
                continue
            safe_item = sanitize_public_value(item, depth=depth + 1)
            if safe_item is not OMIT:
                result[safe_nested_key] = safe_item
        return result
    return OMIT


def safe_key(value: Any) -> str:
    text = str(value or "").strip()
    lowered = text.lower()
    if not text or any(marker in lowered for marker in PRIVATE_KEY_MARKERS):
        return ""
    return safe_text(text, 80)


def safe_identifier(value: Any, limit: int = 160) -> str:
    text = safe_text(value, limit)
    if not text or any(character in text for character in ("/", "\\", "?", "#")):
        return ""
    return text


def safe_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())[:limit]
    lowered = text.lower()
    if not text or any(marker in lowered for marker in PRIVATE_VALUE_MARKERS):
        return ""
    return text


__all__ = (
    "OMIT",
    "safe_identifier",
    "safe_key",
    "safe_text",
    "sanitize_public_value",
)
