from __future__ import annotations

import re
from typing import Any, Mapping
from urllib.parse import parse_qsl, urlsplit

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
PRIVATE_KEY_TERMS = {
    "authorization",
    "cookie",
    "credential",
    "password",
    "path",
    "sas",
    "secret",
    "signature",
    "token",
}
SIGNED_QUERY_KEYS = {
    "access_token",
    "auth",
    "authorization",
    "key",
    "sig",
    "signature",
    "token",
    "x-amz-credential",
    "x-amz-signature",
    "x-goog-credential",
    "x-goog-signature",
}
PRIVATE_VALUE_MARKERS = tuple(
    fragment.lower() for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
) + (
    "x-amz-signature",
    "x-goog-signature",
    "sig=",
    "signature=",
    "token=",
)
POSIX_PRIVATE_PATH = re.compile(
    r"(?<![A-Za-z0-9_])/(?:etc|home|mnt|opt|private|root|srv|tmp|usr|var)(?:/[^/\s?#]+)+",
    re.IGNORECASE,
)
URL_CANDIDATE = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
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
    normalized = re.sub(r"[^a-z0-9]+", "_", lowered).strip("_")
    terms = {item for item in normalized.split("_") if item}
    if (
        not text
        or any(marker in lowered for marker in PRIVATE_KEY_MARKERS)
        or bool(terms & PRIVATE_KEY_TERMS)
        or {"api", "key"} <= terms
    ):
        return ""
    return safe_text(text, 80)


def safe_identifier(value: Any, limit: int = 160) -> str:
    text = safe_text(value, limit)
    if not text or any(character in text for character in ("/", "\\", "?", "#")):
        return ""
    return text


def safe_text(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())[:limit]
    if not text or _contains_private_value(text):
        return ""
    return text


def assert_safe_public_payload(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not safe_key(key):
                raise ValueError("public payload contains a sensitive key")
            assert_safe_public_payload(item)
        return
    if isinstance(value, list):
        for item in value:
            assert_safe_public_payload(item)
        return
    if isinstance(value, str) and _contains_private_value(value):
        raise ValueError("public payload contains a private value")


def _contains_private_value(text: str) -> bool:
    lowered = text.lower()
    if any(marker in lowered for marker in PRIVATE_VALUE_MARKERS):
        return True
    if POSIX_PRIVATE_PATH.search(text):
        return True
    for candidate in URL_CANDIDATE.findall(text):
        try:
            query_keys = {
                key.lower()
                for key, _value in parse_qsl(urlsplit(candidate).query, keep_blank_values=True)
            }
        except ValueError:
            return True
        if query_keys & SIGNED_QUERY_KEYS:
            return True
    return False


__all__ = (
    "OMIT",
    "assert_safe_public_payload",
    "safe_identifier",
    "safe_key",
    "safe_text",
    "sanitize_public_value",
)
