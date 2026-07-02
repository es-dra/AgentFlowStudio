from __future__ import annotations

import re
from typing import Any

from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS


SENSITIVE_KEY_RE = re.compile(
    r"(?i)(api.?key|access.?token|refresh.?token|token|secret|password|cookie|authorization|credential|signed.?url)"
)
RAW_OR_MEDIA_KEY_RE = re.compile(
    r"(?i)(provider.?raw|raw.?payload|raw.?response|raw.?body|media.?bytes|image.?bytes|file.?bytes|data.?base64)"
)
PROMPT_KEY_RE = re.compile(r"(?i)(^|[_-])prompt($|[_-])|provider_prompt|model_prompt")
LOCAL_PATH_RE = re.compile(
    r"(?i)(?:[a-z]:\\[^\s\"']+|/(?:home|users|tmp|var/lib/afs-runtime)/[^\s\"']+|data/(?:processed/runs|raw)[^\s\"']*)"
)
MEDIA_REF_RE = re.compile(r"(?i)\S+\.(?:mp4|mov)\b")
DATA_URL_RE = re.compile(r"(?i)data:[^\s\"']+")
URL_RE = re.compile(r"(?i)https?://[^\s\"']+")
SECRET_VALUE_RE = re.compile(
    r"(?i)(api_key|access_token|refresh_token|secret_key|client_secret|authorization:|bearer\s+\S+|cookie=|signed_url)"
)


def should_omit_log_key(key: Any) -> bool:
    text = str(key or "")
    return bool(SENSITIVE_KEY_RE.search(text) or RAW_OR_MEDIA_KEY_RE.search(text))


def safe_log_value(value: Any, *, key: str = "", string_limit: int = 240) -> Any:
    if should_omit_log_key(key):
        return ""
    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
        return value
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for raw_key, raw_item in list(value.items())[:20]:
            if should_omit_log_key(raw_key):
                continue
            safe_key = safe_log_key(raw_key)
            safe_item = safe_log_value(raw_item, key=str(raw_key), string_limit=string_limit)
            if safe_key and safe_item not in (None, ""):
                result[safe_key] = safe_item
        return result
    if isinstance(value, list):
        result = [
            safe_log_value(item, key=key, string_limit=string_limit)
            for item in value[:20]
        ]
        return [item for item in result if item not in (None, "")]
    return sanitize_log_text(value, key=key, limit=string_limit)


def sanitize_log_text(value: Any, *, key: str = "", limit: int = 240) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    if PROMPT_KEY_RE.search(str(key or "")):
        return "[prompt omitted]"
    text = DATA_URL_RE.sub("[data-url omitted]", text)
    text = URL_RE.sub("[url omitted]", text)
    text = LOCAL_PATH_RE.sub("[path omitted]", text)
    text = MEDIA_REF_RE.sub("[media-ref omitted]", text)
    lowered = text.lower()
    if SECRET_VALUE_RE.search(text) or any(fragment.lower() in lowered for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS):
        return "[redacted]"
    return text[:limit]


def safe_log_key(key: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.:-]+", "_", str(key or "").strip()).strip("_")[:80]


__all__ = (
    "safe_log_key",
    "safe_log_value",
    "sanitize_log_text",
    "should_omit_log_key",
)
