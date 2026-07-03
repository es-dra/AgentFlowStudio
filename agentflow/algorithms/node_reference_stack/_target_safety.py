from __future__ import annotations

import base64
import binascii
from typing import Any

from agentflow.algorithms.node_reference_stack._contract import SAFE_TOKEN_RE, UNSAFE_REF_MARKERS


BASE64_MEDIA_PREFIXES = (
    "/9j/",
    "ivborw0kggo",
    "r0lgod",
    "uklgr",
    "aaaagftyp",
    "jvberi0",
    "suqz",
    "t2dduw",
)
MEDIA_MAGIC_BYTES = (
    b"\x89PNG\r\n\x1a\n",
    b"\xff\xd8\xff",
    b"GIF87a",
    b"GIF89a",
    b"RIFF",
    b"\x00\x00\x00",
    b"%PDF",
    b"ID3",
    b"OggS",
)


def target_ref(value: Any) -> tuple[str, bool]:
    if isinstance(value, (bytes, bytearray)):
        return "unsafe_ref_redacted", True
    text = str(value or "").strip()
    unsafe = _is_unsafe_target_ref(text)
    return ("unsafe_ref_redacted" if unsafe else safe_token(text), unsafe)


def safe_token(value: Any) -> str:
    return SAFE_TOKEN_RE.sub("_", str(value or "")).strip("_")[:160]


def _is_unsafe_target_ref(text: str) -> bool:
    lower = text.lower()
    if any(marker in lower for marker in UNSAFE_REF_MARKERS):
        return True
    return _looks_like_base64_media_ref(text)


def _looks_like_base64_media_ref(text: str) -> bool:
    compact = "".join(str(text or "").split())
    lower = compact.lower()
    if any(lower.startswith(prefix) for prefix in BASE64_MEDIA_PREFIXES):
        return True
    if len(compact) < 120 or len(compact) % 4 != 0:
        return False
    if any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for ch in compact):
        return False
    if compact.count("=") > 2 or "=" in compact.rstrip("="):
        return False
    try:
        decoded = base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError):
        return False
    if any(decoded.startswith(prefix) for prefix in MEDIA_MAGIC_BYTES):
        return True
    return len(decoded) >= 512
