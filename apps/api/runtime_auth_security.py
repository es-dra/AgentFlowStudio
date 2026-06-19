from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any


TRUE_VALUES = {"1", "true", "yes", "on"}


def password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    iterations = 200_000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, digest = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), int(iterations)).hex()
        return hmac.compare_digest(candidate, digest)
    except (ValueError, TypeError):
        return False


def normalize_email(value: str) -> str:
    text = str(value or "").strip().lower()
    return text if "@" in text and "." in text.rsplit("@", 1)[-1] else ""


def normalize_invite_code(value: str) -> str:
    return str(value or "").strip()


def hash_text(value: str) -> str:
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def bearer_token(header: str) -> str:
    if not header.lower().startswith("bearer "):
        return ""
    return header.split(" ", 1)[1].strip()


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def enabled(value: str | None) -> bool:
    return str(value or "").strip().lower() in TRUE_VALUES


def session_expired(session: dict[str, Any], *, ttl_hours: int) -> bool:
    created_at = parse_datetime(str(session.get("created_at", "")))
    if not created_at:
        return True
    return datetime.now(timezone.utc) - created_at > timedelta(hours=ttl_hours)


def parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = (
    "bearer_token",
    "enabled",
    "hash_text",
    "normalize_email",
    "normalize_invite_code",
    "new_session_token",
    "now",
    "password_hash",
    "session_expired",
    "verify_password",
)
