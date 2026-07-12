from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request

from apps.api.runtime_file_logging import configure_runtime_file_logging, runtime_file_event
from apps.api.runtime_log_safety import safe_log_key, safe_log_value, sanitize_log_text, should_omit_log_key


LOG_LEVEL_ENV = "AFS_LOG_LEVEL"
SLOW_REQUEST_MS_ENV = "AFS_SLOW_REQUEST_MS"
REQUEST_RECEIVED_LOG_ENV = "AFS_LOG_REQUEST_RECEIVED"
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
    configure_runtime_file_logging(values)


def configure_runtime_request_logging(app: FastAPI, env: dict[str, str] | None = None) -> None:
    values = env if env is not None else os.environ
    slow_ms = _int_env(values.get(SLOW_REQUEST_MS_ENV), DEFAULT_SLOW_REQUEST_MS)
    log_received = str(values.get(REQUEST_RECEIVED_LOG_ENV, "")).strip().lower() in {"1", "true", "yes", "on"}

    @app.middleware("http")
    async def runtime_request_logging_middleware(request: Request, call_next):
        request_id = _request_id(request)
        request.state.request_id = request_id
        request.state.client_request_id = client_request_id_from_request(request)
        request.state.user_action = user_action_from_request(request)
        request.state.studio_node_id = studio_node_id_from_request(request)
        request.state.studio_node_type = studio_node_type_from_request(request)
        started = time.perf_counter()
        if log_received:
            logging.getLogger(REQUEST_LOGGER_NAME).info(
                "runtime_request_received %s",
                _json({
                    "request_id": request_id,
                    "client_request_id": request.state.client_request_id,
                    "user_action": request.state.user_action,
                    "studio_node_id": request.state.studio_node_id,
                    "studio_node_type": request.state.studio_node_type,
                    "method": request.method,
                    "path": request.url.path,
                }),
            )
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
            runtime_file_event(
                "request",
                "exception",
                level="ERROR",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                elapsed_ms=elapsed_ms,
            )
            raise
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        if request.state.client_request_id:
            response.headers["X-Client-Request-ID"] = str(request.state.client_request_id)
        if response.status_code >= 400 or elapsed_ms >= slow_ms:
            logging.getLogger(REQUEST_LOGGER_NAME).warning(
                "runtime_request_slow_or_error %s",
                _json({
                    "request_id": request_id,
                    "client_request_id": request.state.client_request_id,
                    "user_action": request.state.user_action,
                    "studio_node_id": request.state.studio_node_id,
                    "studio_node_type": request.state.studio_node_type,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "elapsed_ms": elapsed_ms,
                }),
            )
            runtime_file_event(
                "request",
                "failed" if response.status_code >= 400 else "slow",
                level="WARNING" if response.status_code < 500 else "ERROR",
                request_id=request_id,
                client_request_id=request.state.client_request_id,
                user_action=request.state.user_action,
                studio_node_id=request.state.studio_node_id,
                studio_node_type=request.state.studio_node_type,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                elapsed_ms=elapsed_ms,
            )
        return response


def audit_event(event_type: str, **fields: Any) -> None:
    payload = {
        "event_type": event_type,
        **{
            safe_log_key(key): _safe_value(value, key=str(key))
            for key, value in fields.items()
            if value not in (None, "") and not should_omit_log_key(key)
        },
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


def client_request_id_from_request(request: Request | None) -> str:
    if request is None:
        return ""
    existing = str(getattr(getattr(request, "state", None), "client_request_id", "") or "")
    if existing:
        return existing
    return _safe_header(request, "x-client-request-id", 120)


def user_action_from_request(request: Request | None) -> str:
    if request is None:
        return ""
    existing = str(getattr(getattr(request, "state", None), "user_action", "") or "")
    if existing:
        return existing
    return _safe_header(request, "x-user-action", 120)


def studio_node_id_from_request(request: Request | None) -> str:
    if request is None:
        return ""
    existing = str(getattr(getattr(request, "state", None), "studio_node_id", "") or "")
    if existing:
        return existing
    return _safe_header(request, "x-studio-node-id", 120)


def studio_node_type_from_request(request: Request | None) -> str:
    if request is None:
        return ""
    existing = str(getattr(getattr(request, "state", None), "studio_node_type", "") or "")
    if existing:
        return existing
    return _safe_header(request, "x-studio-node-type", 80)


def client_ip_from_request(request: Request) -> str:
    forwarded_for = str(request.headers.get("x-forwarded-for") or "")
    if forwarded_for:
        return forwarded_for.split(",")[-1].strip()[:80]
    return str(request.client.host if request.client else "")[:80]


def log_business_event(event_type: str, /, **fields: Any) -> None:
    file_log_domain = str(fields.pop("file_log_domain", "") or _domain_from_event(event_type))
    file_log_event = str(fields.pop("file_log_event", "") or _event_from_event_type(event_type))
    file_log_level = str(fields.pop("file_log_level", "INFO") or "INFO")
    payload = {
        safe_log_key(key): _safe_value(value, key=str(key))
        for key, value in fields.items()
        if value not in (None, "") and not should_omit_log_key(key)
    }
    logging.getLogger(REQUEST_LOGGER_NAME).info("%s %s", event_type, _json(payload))
    runtime_file_event(
        file_log_domain,
        file_log_event,
        level=file_log_level,
        **payload,
    )


def _request_id(request: Request) -> str:
    existing = str(getattr(getattr(request, "state", None), "request_id", "") or "")
    if existing:
        return existing
    value = str(request.headers.get("x-request-id") or "").strip()
    return value[:80] if value else f"req_{uuid4().hex[:12]}"


def _safe_header(request: Request, name: str, limit: int) -> str:
    value = str(request.headers.get(name) or "").strip()
    return sanitize_log_text(value, key=name, limit=limit)


def _int_env(value: str | None, default: int) -> int:
    try:
        parsed = int(str(value or "").strip())
    except ValueError:
        return default
    return max(0, parsed)


def _safe_value(value: Any, *, key: str = "") -> Any:
    return safe_log_value(value, key=key, string_limit=240)


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _domain_from_event(event_type: str) -> str:
    text = str(event_type or "")
    if text.startswith("video_generation"):
        return "video"
    if text.startswith("runtime_request") or text.startswith("request_"):
        return "request"
    if text.startswith("auth."):
        return "auth"
    return text.split("_", 1)[0] or "runtime"


def _event_from_event_type(event_type: str) -> str:
    text = str(event_type or "event")
    if text.startswith("video_generation_"):
        return text.removeprefix("video_generation_")
    if text.startswith("runtime_request_"):
        return text.removeprefix("runtime_request_")
    return text


__all__ = (
    "audit_event",
    "client_request_id_from_request",
    "client_ip_from_request",
    "configure_runtime_logging",
    "configure_runtime_request_logging",
    "log_business_event",
    "request_id_from_request",
    "studio_node_id_from_request",
    "studio_node_type_from_request",
    "user_action_from_request",
)
