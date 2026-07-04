from __future__ import annotations

import base64
import binascii
import re
from typing import Any

from agentflow.algorithms.structured_source_output_qa_checklist._contract import ALGORITHM_ID, NON_CLAIMS, SCHEMA_VERSION


SAFE_ID_RE = re.compile(r"[^0-9A-Za-z_.:-]+")
UNSAFE_FIELD_NAMES = {
    "api_key",
    "access_token",
    "refresh_token",
    "authorization",
    "auth_header",
    "bearer",
    "token",
    "cookie",
    "session",
    "secret",
    "provider_key",
    "client_secret",
    "private_key",
    "signed_url",
    "provider_raw_payload",
    "provider_raw_response",
    "raw_provider_payload",
    "raw_provider_response",
    "raw_payload",
    "raw_response",
    "image_path",
    "output_path",
    "request_path",
    "local_path",
    "media_bytes",
    "image_bytes",
    "file_bytes",
    "generated_media_bytes",
    "data_base64",
    "data_uri",
    "base64",
}
UNSAFE_VALUE_RE = re.compile(
    r"(?i)(bearer\s+\S+|authorization\s*:|api[\s_.-]*key|access[\s_.-]*token|refresh[\s_.-]*token|"
    r"provider[\s_.-]*key|client[\s_.-]*secret|private[\s_.-]*key|secret|cookie\s*=|signed[\s_.-]*url|"
    r"https?://|data:|;base64,|data_base64|raw[\s_.-]*provider|raw[\s_.-]*(payload|response)|"
    r"media[\s_.-]*bytes|image[\s_.-]*bytes|file[\s_.-]*bytes|generated[\s_.-]*media[\s_.-]*bytes|"
    r"[a-z]:\\|/(home|users|tmp|var/lib/afs-runtime)/|\.mp4\b|\.mov\b|\.png\b|\.jpg\b)"
)
BASE64_MEDIA_PREFIXES = ("/9j/", "ivborw0kggo", "r0lgod", "uklgr", "aaaagftyp", "jvberi0", "suqz", "t2dduw")
MEDIA_MAGIC_BYTES = (b"\x89PNG\r\n\x1a\n", b"\xff\xd8\xff", b"GIF87a", b"GIF89a", b"RIFF", b"%PDF", b"ID3", b"OggS")


def safe_source_ref(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_ref_id": safe_token(item.get("source_ref_id") or item.get("artifact_id")),
        "project_id": safe_token(item.get("project_id")),
        "category": safe_token(item.get("category") or item.get("source_type")),
        "artifact_id": safe_token(item.get("artifact_id")),
        "safe_preview_ref": safe_route(item.get("safe_preview_ref")),
        "sha256": safe_hash(item.get("sha256")),
        "byte_count": safe_int(item.get("byte_count")),
        "provider_calls_started": bool(item.get("provider_calls_started")),
    }


def safe_output_ref(item: dict[str, Any]) -> dict[str, Any]:
    dimensions = item.get("dimensions") if isinstance(item.get("dimensions"), dict) else {}
    return {
        "output_ref_id": safe_token(item.get("output_ref_id") or item.get("candidate_id") or item.get("artifact_id")),
        "project_id": safe_token(item.get("project_id")),
        "target_id": safe_token(item.get("target_id")),
        "candidate_id": safe_token(item.get("candidate_id")),
        "artifact_id": safe_token(item.get("artifact_id")),
        "safe_preview_ref": safe_route(item.get("safe_preview_ref")),
        "byte_count": safe_int(item.get("byte_count")),
        "sha256": safe_hash(item.get("sha256")),
        "width": safe_int(item.get("width") or dimensions.get("width")),
        "height": safe_int(item.get("height") or dimensions.get("height")),
        "aspect_ratio": safe_token(item.get("aspect_ratio")),
        "duration_seconds": safe_number(item.get("duration_seconds")),
        "provider_gate": safe_token(item.get("provider_gate")),
        "provider_calls_started": bool(item.get("provider_calls_started")),
        "runtime_state": safe_token(item.get("runtime_state") or item.get("status")),
        "batch_status": safe_token(item.get("batch_status")),
        "recovery_status": safe_token(item.get("recovery_status")),
        "retry_default_scope": safe_token(item.get("retry_default_scope")),
    }


def has_unsafe_payload(payload: Any) -> bool:
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key or "").lower()
            if key_text in UNSAFE_FIELD_NAMES or key_text.endswith("_path"):
                return True
            if has_unsafe_payload(value):
                return True
        return False
    if isinstance(payload, list):
        return any(has_unsafe_payload(item) for item in payload)
    if isinstance(payload, (bytes, bytearray)):
        return True
    if isinstance(payload, str):
        return bool(UNSAFE_VALUE_RE.search(payload) or looks_like_base64_media(payload))
    return False


def project_mismatch(project_id: str, items: list[dict[str, Any]]) -> bool:
    expected = safe_token(project_id)
    return any(safe_token(item.get("project_id")) not in {"", expected} for item in items)


def target_mismatch(target_id: str, items: list[dict[str, Any]]) -> bool:
    expected = safe_token(target_id)
    return any(safe_token(item.get("target_id")) not in {"", expected} for item in items)


def safe_enum(value: Any, allowed: tuple[str, ...], default: str) -> str:
    token = safe_token(value)
    return token if token in allowed else default


def safe_token(value: Any) -> str:
    return SAFE_ID_RE.sub("_", str(value or "")).strip("_")[:160]


def safe_note(value: Any) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return ""
    if has_unsafe_payload(text):
        return "[redacted unsafe note]"
    return text[:240]


def safe_route(value: Any) -> str:
    text = str(value or "").strip()
    if not text.startswith("/") or UNSAFE_VALUE_RE.search(text):
        return ""
    return text[:240]


def safe_hash(value: Any) -> str:
    text = str(value or "").strip().lower()
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def safe_number(value: Any) -> float:
    try:
        return round(max(0.0, float(value or 0)), 3)
    except (TypeError, ValueError):
        return 0.0


def dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in safe_list(value) if isinstance(item, dict)]


def safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def looks_like_base64_media(value: str) -> bool:
    compact = "".join(str(value or "").split())
    lower = compact.lower()
    if any(lower.startswith(prefix) for prefix in BASE64_MEDIA_PREFIXES):
        return True
    if len(compact) < 120 or len(compact) % 4 != 0:
        return False
    if any(ch not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for ch in compact):
        return False
    try:
        decoded = base64.b64decode(compact, validate=True)
    except (binascii.Error, ValueError):
        return False
    return any(decoded.startswith(prefix) for prefix in MEDIA_MAGIC_BYTES) or len(decoded) >= 512


def minimal_blocked_packet(project_id: str, target_id: str, checklist_id: str) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_structured_source_output_qa_checklist",
        "schema_version": SCHEMA_VERSION,
        "algorithm_id": ALGORITHM_ID,
        "project_id": safe_token(project_id),
        "target_id": safe_token(target_id),
        "checklist_id": safe_token(checklist_id) or f"checklist:{safe_token(target_id)}",
        "packet_state": "blocked_unsafe",
        "summary_counts": {
            "total_item_count": 0,
            "required_item_count": 0,
            "required_items_followed_count": 0,
            "required_items_blocked_count": 0,
            "critical_fail_count": 1,
            "waiver_required_count": 0,
            "waiver_applied_count": 0,
            "invalid_waiver_count": 0,
            "unverifiable_count": 0,
            "conflict_count": 0,
        },
        "checklist_items": [],
        "waiver_validation": {"valid_waiver_count": 0, "invalid_waiver_count": 0, "waivers": []},
        "safety_boundary": {"provider_calls_started": False, "writes_long_term_memory": False, "writes_company_kb": False},
        "non_claims": NON_CLAIMS,
    }
