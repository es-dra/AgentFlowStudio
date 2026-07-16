from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from agentflow.harness.json_io import exclusive_file_lock, write_json
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_store import RuntimeStore, read_json, safe_id


SCHEMA_VERSION = "afs_runtime_submit_idempotency.v0.2"
VOLATILE_REQUEST_FIELDS = {"generated_at"}
LEASE_TTL_SECONDS = 15 * 60
RECLAIMABLE_STATUSES = {"reserved", "pending"}


@dataclass(frozen=True)
class SubmitIdempotencyReservation:
    state: Literal["reserved", "replay", "conflict", "pending"]
    project_id: str
    action: str
    stable_request_id: str
    fingerprint: str
    ledger_dir: Path
    ledger: dict[str, Any]
    response: dict[str, Any] | None = None

    @property
    def is_reserved(self) -> bool:
        return self.state == "reserved"


def begin_submit_idempotency(
    store: RuntimeStore,
    *,
    project_id: str,
    action: str,
    request: Any,
    client_request_id: str = "",
    request_id: str = "",
) -> SubmitIdempotencyReservation:
    fingerprint = submit_request_fingerprint(request)
    stable_request_id = stable_submit_request_id(client_request_id, fingerprint)
    ledger_dir = _ledger_dir(store, project_id, action, stable_request_id)
    ledger_path = ledger_dir / "ledger.json"
    response_path = ledger_dir / "response.json"
    ledger_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Directory creation is the atomic reservation primitive for the local Runtime model.
        ledger_dir.mkdir()
    except FileExistsError:
        with exclusive_file_lock(ledger_dir / "ledger.transaction.lock"):
            try:
                ledger = read_json(ledger_path)
            except (FileNotFoundError, ValueError, json.JSONDecodeError, UnicodeDecodeError):
                ledger = {}
            existing_fingerprint = str(ledger.get("fingerprint") or "")
            if existing_fingerprint and existing_fingerprint != fingerprint:
                return SubmitIdempotencyReservation(
                    state="conflict",
                    project_id=project_id,
                    action=action,
                    stable_request_id=stable_request_id,
                    fingerprint=fingerprint,
                    ledger_dir=ledger_dir,
                    ledger=ledger,
                )
            if response_path.exists():
                return SubmitIdempotencyReservation(
                    state="replay",
                    project_id=project_id,
                    action=action,
                    stable_request_id=stable_request_id,
                    fingerprint=fingerprint,
                    ledger_dir=ledger_dir,
                    ledger=ledger,
                    response=read_json(response_path),
                )
            if _can_reclaim_provider_free_attempt(ledger, incoming_fingerprint=fingerprint):
                ledger = _reclaim_provider_free_attempt(
                    ledger_dir,
                    ledger,
                    project_id=project_id,
                    action=action,
                    stable_request_id=stable_request_id,
                    fingerprint=fingerprint,
                    request_id=request_id,
                    client_request_id=client_request_id,
                )
                return SubmitIdempotencyReservation(
                    state="reserved",
                    project_id=project_id,
                    action=action,
                    stable_request_id=stable_request_id,
                    fingerprint=fingerprint,
                    ledger_dir=ledger_dir,
                    ledger=ledger,
                )
            return SubmitIdempotencyReservation(
                state="pending",
                project_id=project_id,
                action=action,
                stable_request_id=stable_request_id,
                fingerprint=fingerprint,
                ledger_dir=ledger_dir,
                ledger=ledger,
            )

    ledger = _new_attempt_ledger(
        project_id=project_id,
        action=action,
        stable_request_id=stable_request_id,
        fingerprint=fingerprint,
        request_id=request_id,
        client_request_id=client_request_id,
        attempt_number=1,
    )
    write_json(ledger_path, ledger)
    return SubmitIdempotencyReservation(
        state="reserved",
        project_id=project_id,
        action=action,
        stable_request_id=stable_request_id,
        fingerprint=fingerprint,
        ledger_dir=ledger_dir,
        ledger=ledger,
    )


def _new_attempt_ledger(
    *,
    project_id: str,
    action: str,
    stable_request_id: str,
    fingerprint: str,
    request_id: str,
    client_request_id: str,
    attempt_number: int,
    reclaimed_attempts: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    now = _now_datetime()
    lease_expires_at = now + timedelta(seconds=LEASE_TTL_SECONDS)
    attempt_id = f"attempt-{uuid4().hex}"
    lease_id = f"lease-{uuid4().hex}"
    return {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "action": action,
        "stable_request_id": stable_request_id,
        "fingerprint": fingerprint,
        "status": "reserved",
        "attempt_id": attempt_id,
        "attempt_number": attempt_number,
        "attempt_status": "active",
        "lease": {
            "lease_id": lease_id,
            "status": "active",
            "started_at": now.isoformat(),
            "expires_at": lease_expires_at.isoformat(),
            "ttl_seconds": LEASE_TTL_SECONDS,
        },
        "job_id": "",
        "provider_calls_started": False,
        "request_id": request_id,
        "client_request_id": client_request_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "reclaimed_attempts": list(reclaimed_attempts or []),
    }


def complete_submit_idempotency(
    reservation: SubmitIdempotencyReservation,
    *,
    job_id: str,
    response: dict[str, Any],
    provider_calls_started: bool,
) -> None:
    if not reservation.is_reserved:
        return
    response_path = reservation.ledger_dir / "response.json"
    write_json(response_path, response)
    ledger = {
        **reservation.ledger,
        "status": "completed",
        "attempt_status": "completed",
        "job_id": job_id,
        "provider_calls_started": bool(provider_calls_started),
        "response_sha256": _json_digest(response),
        "updated_at": _now(),
    }
    if isinstance(ledger.get("lease"), dict):
        ledger["lease"] = {
            **ledger["lease"],
            "status": "completed",
            "completed_at": ledger["updated_at"],
        }
    write_json(reservation.ledger_dir / "ledger.json", ledger)


def abort_submit_idempotency(reservation: SubmitIdempotencyReservation | None) -> None:
    if reservation is None or not reservation.is_reserved:
        return
    shutil.rmtree(reservation.ledger_dir, ignore_errors=True)


def submit_idempotency_error_detail(
    reservation: SubmitIdempotencyReservation,
    *,
    request_id: str = "",
    client_request_id: str = "",
    node_id: str = "",
) -> dict[str, Any]:
    conflict = reservation.state == "conflict"
    existing_job_id = str(reservation.ledger.get("job_id") or "")
    provider_calls_started = bool(reservation.ledger.get("provider_calls_started"))
    lease = reservation.ledger.get("lease") if isinstance(reservation.ledger.get("lease"), dict) else {}
    detail = safe_error_detail(
        "idempotency_conflict" if conflict else "idempotency_request_in_progress",
        detail_code="idempotency_conflict" if conflict else "idempotency_request_in_progress",
        message=(
            "Submit request id was reused with a different payload."
            if conflict
            else "Submit request is still reserved and has no completed response yet."
        ),
        user_action=(
            "Use a new client request id for changed generation parameters."
            if conflict
            else "Retry the same request after the first submit returns."
        ),
        request_id=request_id,
        client_request_id=client_request_id,
        project_id=reservation.project_id,
        node_id=node_id,
        action=reservation.action,
        stage="idempotency",
        status="conflict" if conflict else "blocked",
        retryable=not conflict,
        details={
            "provider_calls_started": provider_calls_started,
            "stable_request_id": reservation.stable_request_id,
            "existing_job_id": existing_job_id,
            "existing_fingerprint": str(reservation.ledger.get("fingerprint") or ""),
            "incoming_fingerprint": reservation.fingerprint,
            "idempotency_scope": f"{reservation.project_id}/{reservation.action}",
            "attempt_id": str(reservation.ledger.get("attempt_id") or ""),
            "attempt_number": _int_value(reservation.ledger.get("attempt_number"), default=0),
            "lease_status": str(lease.get("status") or ""),
            "lease_expires_at": str(lease.get("expires_at") or ""),
        },
    )
    detail["provider_calls_started"] = provider_calls_started
    return detail


def _can_reclaim_provider_free_attempt(ledger: dict[str, Any], *, incoming_fingerprint: str) -> bool:
    if bool(ledger.get("provider_calls_started")):
        return False
    if str(ledger.get("fingerprint") or "") != incoming_fingerprint:
        return False
    if str(ledger.get("status") or "") not in RECLAIMABLE_STATUSES:
        return False
    return _lease_is_stale(ledger)


def _reclaim_provider_free_attempt(
    ledger_dir: Path,
    ledger: dict[str, Any],
    *,
    project_id: str,
    action: str,
    stable_request_id: str,
    fingerprint: str,
    request_id: str,
    client_request_id: str,
) -> dict[str, Any]:
    previous_attempt_id = str(ledger.get("attempt_id") or "attempt-legacy")
    dlq_ref = _write_dlq_once(ledger_dir, ledger, previous_attempt_id=previous_attempt_id)
    previous_attempt_number = _int_value(ledger.get("attempt_number"), default=1)
    reclaimed_attempts = _list_value(ledger.get("reclaimed_attempts"))
    reclaim_ref = {
        "attempt_id": previous_attempt_id,
        "attempt_number": previous_attempt_number,
        "status": "failed",
        "reason": "stale_provider_free_lease",
        "dlq_ref": dlq_ref,
    }
    if reclaim_ref not in reclaimed_attempts:
        reclaimed_attempts.append(reclaim_ref)
    new_ledger = _new_attempt_ledger(
        project_id=project_id,
        action=action,
        stable_request_id=stable_request_id,
        fingerprint=fingerprint,
        request_id=request_id,
        client_request_id=client_request_id,
        attempt_number=previous_attempt_number + 1,
        reclaimed_attempts=reclaimed_attempts,
    )
    write_json(ledger_dir / "ledger.json", new_ledger)
    return new_ledger


def _write_dlq_once(ledger_dir: Path, ledger: dict[str, Any], *, previous_attempt_id: str) -> str:
    safe_attempt_id = safe_id(previous_attempt_id or "attempt-legacy")
    dlq_dir = ledger_dir / "dlq"
    dlq_path = dlq_dir / f"{safe_attempt_id}.json"
    dlq_ref = f"dlq/{safe_attempt_id}.json"
    if dlq_path.exists():
        return dlq_ref
    now = _now()
    failed_attempt = {
        "schema_version": "afs_runtime_submit_idempotency_dlq.v0.1",
        "status": "failed",
        "failure_reason": "stale_provider_free_lease",
        "project_id": str(ledger.get("project_id") or ""),
        "action": str(ledger.get("action") or ""),
        "stable_request_id": str(ledger.get("stable_request_id") or ""),
        "fingerprint": str(ledger.get("fingerprint") or ""),
        "attempt_id": previous_attempt_id,
        "attempt_number": _int_value(ledger.get("attempt_number"), default=1),
        "previous_status": str(ledger.get("status") or ""),
        "previous_attempt_status": str(ledger.get("attempt_status") or ""),
        "previous_job_id": str(ledger.get("job_id") or ""),
        "previous_lease": dict(ledger.get("lease") or {}) if isinstance(ledger.get("lease"), dict) else {},
        "provider_calls_started": False,
        "provider_calls_count": 0,
        "model_calls_count": 0,
        "media_calls_count": 0,
        "contains_provider_raw": False,
        "contains_secret": False,
        "contains_signed_url": False,
        "contains_media_bytes": False,
        "contains_private_absolute_asset_path": False,
        "request_payload_retained": False,
        "created_at": str(ledger.get("created_at") or ""),
        "updated_at": str(ledger.get("updated_at") or ""),
        "failed_at": now,
    }
    write_json(dlq_path, failed_attempt)
    return dlq_ref


def _lease_is_stale(ledger: dict[str, Any]) -> bool:
    now = _now_datetime()
    lease = ledger.get("lease") if isinstance(ledger.get("lease"), dict) else {}
    expires_at = _parse_datetime(str(lease.get("expires_at") or ""))
    if expires_at is not None:
        return expires_at <= now
    updated_at = _parse_datetime(str(ledger.get("updated_at") or ledger.get("created_at") or ""))
    if updated_at is None:
        return False
    return updated_at + timedelta(seconds=LEASE_TTL_SECONDS) <= now


def submit_request_fingerprint(request: Any) -> str:
    if hasattr(request, "model_dump"):
        payload = request.model_dump(mode="json", by_alias=True)
    elif isinstance(request, dict):
        payload = dict(request)
    else:
        payload = dict(getattr(request, "__dict__", {}))
    return _json_digest(_stable_payload(payload))


def stable_submit_request_id(client_request_id: str, fingerprint: str) -> str:
    cleaned = safe_id(str(client_request_id or "").strip())
    if cleaned and cleaned != "item":
        return cleaned[:120]
    return f"fingerprint-{fingerprint[:32]}"


def _stable_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): _stable_payload(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in VOLATILE_REQUEST_FIELDS
        }
    if isinstance(value, list):
        return [_stable_payload(item) for item in value]
    return value


def _ledger_dir(store: RuntimeStore, project_id: str, action: str, stable_request_id: str) -> Path:
    return store.root / "submit_idempotency" / safe_id(project_id) / safe_id(action) / safe_id(stable_request_id)


def _json_digest(payload: Any) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _now() -> str:
    return _now_datetime().isoformat()


def _now_datetime() -> datetime:
    return datetime.now(timezone.utc)


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _int_value(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


__all__ = (
    "SubmitIdempotencyReservation",
    "abort_submit_idempotency",
    "begin_submit_idempotency",
    "complete_submit_idempotency",
    "stable_submit_request_id",
    "submit_idempotency_error_detail",
    "submit_request_fingerprint",
)
