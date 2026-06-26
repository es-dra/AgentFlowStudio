from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request


LOG_LEVEL_ENV = "AFS_LOG_LEVEL"
SLOW_REQUEST_MS_ENV = "AFS_SLOW_REQUEST_MS"
DEFAULT_SLOW_REQUEST_MS = 3000
AUDIT_LOGGER_NAME = "afs.runtime.audit"
REQUEST_LOGGER_NAME = "afs.runtime.request"


def configure_runtime_logging(env: dict[str, str] | None = None) -> None:
    values = env if env is not None else os.environ
    level_name = str(values.get(LOG_LEVEL_ENV, "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(level=level, format="%(levelname)s:%(name)s:%(message)s")
    logging.getLogger(AUDIT_LOGGER_NAME).setLevel(level)
    logging.getLogger(REQUEST_LOGGER_NAME).setLevel(level)


def configure_runtime_request_logging(app: FastAPI, env: dict[str, str] | None = None) -> None:
    values = env if env is not None else os.environ
    slow_ms = _int_env(values.get(SLOW_REQUEST_MS_ENV), DEFAULT_SLOW_REQUEST_MS)

    @app.middleware("http")
    async def runtime_request_logging_middleware(request: Request, call_next):
        request_id = _request_id(request)
        request.state.request_id = request_id
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
            logging.getLogger(REQUEST_LOGGER_NAME).exception(
                "runtime_request_exception %s",
                _json({
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "elapsed_ms": elapsed_ms,
                }),
            )
            raise
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        if response.status_code >= 500 or elapsed_ms >= slow_ms:
            logging.getLogger(REQUEST_LOGGER_NAME).warning(
                "runtime_request_slow_or_error %s",
                _json({
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed_ms,
                }),
            )
        return response


def audit_event(event_type: str, **fields: Any) -> None:
    payload = {
        "event_type": event_type,
        **{key: _safe_value(value) for key, value in fields.items() if value not in (None, "")},
    }
    logging.getLogger(AUDIT_LOGGER_NAME).info("runtime_audit %s", _json(payload))


def request_id_from_request(request: Request | None) -> str:
    if request is None:
        return ""
    existing = str(getattr(getattr(request, "state", None), "request_id", "") or "")
    if existing:
        return existing
    value = _request_id(request)
    request.state.request_id = value
    return value


def client_ip_from_request(request: Request) -> str:
    forwarded_for = str(request.headers.get("x-forwarded-for") or "")
    if forwarded_for:
        return forwarded_for.split(",")[-1].strip()[:80]
    return str(request.client.host if request.client else "")[:80]


def _request_id(request: Request) -> str:
    existing = str(getattr(getattr(request, "state", None), "request_id", "") or "")
    if existing:
        return existing
    value = str(request.headers.get("x-request-id") or "").strip()
    return value[:80] if value else f"req_{uuid4().hex[:12]}"


def _int_env(value: str | None, default: int) -> int:
    try:
        parsed = int(str(value or "").strip())
    except ValueError:
        return default
    return max(0, parsed)


def _safe_value(value: Any) -> Any:
    if isinstance(value, (int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key)[:80]: _safe_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_safe_value(item) for item in value[:20]]
    return str(value)[:240]


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


__all__ = (
    "audit_event",
    "client_ip_from_request",
    "configure_runtime_logging",
    "configure_runtime_request_logging",
    "request_id_from_request",
)
