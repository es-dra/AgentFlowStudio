from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from agentflow_studio.model_gateway.errors import ModelConfigError


def build_kling_jwt_self_check(
    *,
    access_key: str,
    secret_key: str,
    ttl_seconds: int = 1800,
    nbf_skew_seconds: int = -5,
    now: int | None = None,
) -> dict[str, Any]:
    token = encode_kling_jwt(
        access_key=access_key,
        secret_key=secret_key,
        ttl_seconds=ttl_seconds,
        nbf_skew_seconds=nbf_skew_seconds,
        now=now,
    )
    header, payload, _signature = token.split(".")
    decoded_header = _decode_segment(header)
    decoded_payload = _decode_segment(payload)
    issued_at = int(now if now is not None else time.time())
    return {
        "alg": decoded_header.get("alg"),
        "typ": decoded_header.get("typ"),
        "token_segments": len(token.split(".")),
        "issuer_present": bool(decoded_payload.get("iss")),
        "ttl_seconds": int(decoded_payload["exp"]) - issued_at,
        "nbf_skew_seconds": int(decoded_payload["nbf"]) - issued_at,
    }


def encode_kling_jwt(
    *,
    access_key: str,
    secret_key: str,
    ttl_seconds: int = 1800,
    nbf_skew_seconds: int = -5,
    now: int | None = None,
) -> str:
    if not access_key:
        raise ModelConfigError("Kling access_key is required")
    if not secret_key:
        raise ModelConfigError("Kling secret_key is required")
    issued_at = int(now if now is not None else time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "iss": access_key,
        "exp": issued_at + int(ttl_seconds),
        "nbf": issued_at + int(nbf_skew_seconds),
    }
    signing_input = f"{_encode_segment(header)}.{_encode_segment(payload)}"
    signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{signing_input}.{_base64url(signature)}"


def kling_account_credentials(account: dict[str, Any]) -> tuple[str, str]:
    access_env = str(account.get("access_key_env") or "").strip()
    secret_env = str(account.get("secret_key_env") or "").strip()
    access_key = str(account.get("access_key") or (os.environ.get(access_env) if access_env else "") or "")
    secret_key = str(account.get("secret_key") or (os.environ.get(secret_env) if secret_env else "") or "")
    return access_key, secret_key


def _encode_segment(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return _base64url(raw)


def _decode_segment(segment: str) -> dict[str, Any]:
    padding = "=" * (-len(segment) % 4)
    decoded = base64.urlsafe_b64decode(f"{segment}{padding}".encode("ascii"))
    payload = json.loads(decoded.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ModelConfigError("Kling JWT segment payload must be an object")
    return payload


def _base64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
