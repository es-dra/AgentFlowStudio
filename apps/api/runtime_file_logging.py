from __future__ import annotations

import os
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


FILE_LOG_ENABLED_ENV = "AFS_FILE_LOG_ENABLED"
FILE_LOG_DIR_ENV = "AFS_FILE_LOG_DIR"
FILE_LOG_NAME_ENV = "AFS_FILE_LOG_NAME"
FILE_LOG_LEVEL_ENV = "AFS_FILE_LOG_LEVEL"
FILE_LOG_MAX_BYTES_ENV = "AFS_FILE_LOG_MAX_BYTES"
FILE_LOG_BACKUP_COUNT_ENV = "AFS_FILE_LOG_BACKUP_COUNT"

DEFAULT_FILE_LOG_NAME = "afs-runtime"
DEFAULT_FILE_LOG_LEVEL = "INFO"
DEFAULT_FILE_LOG_MAX_BYTES = 50 * 1024 * 1024
DEFAULT_FILE_LOG_BACKUP_COUNT = 20
TRUE_VALUES = {"1", "true", "yes", "on"}
LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
SECRET_KEY_RE = re.compile(r"(?i)(api.?key|token|secret|password|cookie|authorization|credential|signed.?url)")
LOCAL_PATH_RE = re.compile(r"(?i)([a-z]:\\|/home/|/users/|/tmp/|/var/lib/afs-runtime|data/processed/runs)")

_CONFIG: dict[str, Any] = {}
_LOCK = threading.Lock()


def configure_runtime_file_logging(env: dict[str, str] | None = None) -> None:
    values = env if env is not None else os.environ
    enabled = str(values.get(FILE_LOG_ENABLED_ENV, "")).strip().lower() in TRUE_VALUES
    log_dir = str(values.get(FILE_LOG_DIR_ENV, "")).strip()
    _CONFIG.clear()
    _CONFIG.update({
        "enabled": bool(enabled and log_dir),
        "log_dir": Path(log_dir) if log_dir else None,
        "name": _safe_file_stem(values.get(FILE_LOG_NAME_ENV) or DEFAULT_FILE_LOG_NAME),
        "level": str(values.get(FILE_LOG_LEVEL_ENV) or DEFAULT_FILE_LOG_LEVEL).upper(),
        "max_bytes": _positive_int(values.get(FILE_LOG_MAX_BYTES_ENV), DEFAULT_FILE_LOG_MAX_BYTES),
        "backup_count": _positive_int(values.get(FILE_LOG_BACKUP_COUNT_ENV), DEFAULT_FILE_LOG_BACKUP_COUNT),
    })
    if _CONFIG["enabled"]:
        Path(_CONFIG["log_dir"]).mkdir(parents=True, exist_ok=True)


def runtime_file_event(domain: str, event: str, *, level: str = "INFO", **fields: Any) -> None:
    if not _CONFIG:
        configure_runtime_file_logging()
    if not _CONFIG.get("enabled"):
        return
    level_name = str(level or "INFO").upper()
    if LEVELS.get(level_name, 20) < LEVELS.get(str(_CONFIG.get("level") or "INFO").upper(), 20):
        return
    line = _format_line(level_name, domain, event, fields)
    with _LOCK:
        path = _current_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line + "\n")
        _cleanup_old_logs()


def _format_line(level: str, domain: str, event: str, fields: dict[str, Any]) -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    normalized = _normalize_fields(fields)
    parts = [
        timestamp,
        level.ljust(5),
        _safe_token(domain, "runtime"),
        _safe_token(event, "event"),
    ]
    parts.extend(f"{key}={_format_value(value)}" for key, value in normalized.items())
    return " ".join(part for part in parts if part)


def _normalize_fields(fields: dict[str, Any]) -> dict[str, Any]:
    aliases = {
        "request_id": "req",
        "client_request_id": "client_req",
        "project_id": "project",
        "node_id": "node",
        "studio_node_id": "node",
        "provider_service_id": "provider",
        "duration_sec": "duration",
        "aspect_ratio": "ratio",
        "status_code": "status",
        "job_id": "job",
        "provider_task_id": "provider_task",
    }
    preferred = [
        "req",
        "client_req",
        "method",
        "path",
        "status",
        "project",
        "node",
        "action",
        "stage",
        "provider",
        "model",
        "duration",
        "resolution",
        "ratio",
        "job",
        "provider_task",
        "candidate",
        "error",
        "reason",
        "message",
        "user_action",
        "elapsed_ms",
        "llm_elapsed_ms",
        "provider_elapsed_ms",
        "retry_or_salvage_ms",
        "provider_output_length",
        "provider_error_markers",
        "missing_sections",
        "provider_output_preview",
        "provider_prompt",
        "provider_prompt_length",
        "provider_prompt_sha256",
        "provider_prompt_truncated",
        "provider_prompt_risk_terms",
        "retryable",
    ]
    result: dict[str, Any] = {}
    for raw_key, raw_value in fields.items():
        if raw_value in (None, ""):
            continue
        key = aliases.get(str(raw_key), str(raw_key))
        if SECRET_KEY_RE.search(key):
            continue
        value = _safe_value(raw_value, key=key)
        if value in (None, ""):
            continue
        result[_safe_token(key, "field")] = value
    ordered: dict[str, Any] = {}
    for key in preferred:
        if key in result:
            ordered[key] = result.pop(key)
    for key in sorted(result):
        ordered[key] = result[key]
    if "duration" in ordered and isinstance(ordered["duration"], int):
        ordered["duration"] = f"{ordered['duration']}s"
    return ordered


def _safe_value(value: Any, *, key: str = "") -> Any:
    if isinstance(value, bool) or isinstance(value, int) or isinstance(value, float):
        return value
    if isinstance(value, list):
        items = [_safe_value(item, key=key) for item in value[:10]]
        return ",".join(str(item) for item in items if item not in (None, ""))
    if isinstance(value, dict):
        return ",".join(
            f"{_safe_token(item_key, 'field')}:{_safe_value(item, key=str(item_key))}"
            for item_key, item in list(value.items())[:10]
            if not SECRET_KEY_RE.search(str(item_key))
        )
    text = " ".join(str(value or "").split()).strip()
    if not text or SECRET_KEY_RE.search(text):
        return ""
    text = re.sub(r"data:[^\s]+", "[data-url omitted]", text, flags=re.IGNORECASE)
    text = re.sub(r"https?://\S+", "[url omitted]", text, flags=re.IGNORECASE)
    text = LOCAL_PATH_RE.sub("[path omitted]", text)
    limit = 4000 if "prompt" in str(key).lower() else 240
    return text[:limit]


def _format_value(value: Any) -> str:
    text = str(value)
    if not text:
        return '""'
    if re.search(r"\s|[\"=]", text):
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return text


def _current_log_path() -> Path:
    log_dir = Path(_CONFIG["log_dir"])
    stem = str(_CONFIG.get("name") or DEFAULT_FILE_LOG_NAME)
    date_part = datetime.now().strftime("%Y-%m-%d")
    max_bytes = int(_CONFIG.get("max_bytes") or DEFAULT_FILE_LOG_MAX_BYTES)
    base = log_dir / f"{stem}-{date_part}.log"
    if not base.exists() or base.stat().st_size < max_bytes:
        return base
    for index in range(1, int(_CONFIG.get("backup_count") or DEFAULT_FILE_LOG_BACKUP_COUNT) + 1):
        candidate = log_dir / f"{stem}-{date_part}.{index}.log"
        if not candidate.exists() or candidate.stat().st_size < max_bytes:
            return candidate
    return log_dir / f"{stem}-{date_part}.{datetime.now().strftime('%H%M%S')}.log"


def _cleanup_old_logs() -> None:
    backup_count = int(_CONFIG.get("backup_count") or DEFAULT_FILE_LOG_BACKUP_COUNT)
    if backup_count <= 0:
        return
    log_dir = Path(_CONFIG["log_dir"])
    stem = str(_CONFIG.get("name") or DEFAULT_FILE_LOG_NAME)
    files = sorted(log_dir.glob(f"{stem}-*.log"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in files[backup_count:]:
        try:
            path.unlink()
        except OSError:
            pass


def _safe_token(value: Any, fallback: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_.:/-]+", "_", str(value or "").strip()).strip("_")
    return text[:120] or fallback


def _safe_file_stem(value: Any) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(value or DEFAULT_FILE_LOG_NAME)).strip("-") or DEFAULT_FILE_LOG_NAME


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(str(value or "").strip())
    except ValueError:
        return default
    return parsed if parsed > 0 else default


__all__ = (
    "configure_runtime_file_logging",
    "runtime_file_event",
)
