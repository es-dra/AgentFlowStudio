from __future__ import annotations

import hashlib
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from agentflow.harness.json_io import exclusive_file_lock, write_json
from apps.api.runtime_store import read_json
from apps.api.runtime_video_task_state import provider_task_for_state


SCHEMA_VERSION = "afs.video_dispatch_outbox.v0.1"
LEASE_TTL_SECONDS = 15 * 60


def prepare_dispatch_outbox(
    output_dir: Path,
    *,
    project_id: str,
    job_id: str,
    manifest_id: str,
    manifest_hash: str,
    item_id: str,
) -> dict[str, Any]:
    path = _path(output_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with exclusive_file_lock(path.with_suffix(".lock")):
        if path.is_file():
            existing = read_json(path)
            _assert_identity(existing, project_id, job_id, manifest_id, manifest_hash, item_id)
            return existing
        now_value = datetime.now(UTC)
        now = now_value.isoformat()
        value = {
            "schema_version": SCHEMA_VERSION,
            "project_id": project_id,
            "job_id": job_id,
            "manifest_id": manifest_id,
            "manifest_hash": manifest_hash,
            "item_id": item_id,
            "state": "prepared",
            "network_disposition": "never_started",
            "provider_calls_started": False,
            "provider_task": None,
            "provider_task_fingerprint": "",
            "reconcile_required": False,
            "lease": {
                "lease_id": f"video-dispatch-lease-{uuid4().hex}",
                "status": "prepared",
                "started_at": now,
                "expires_at": (
                    now_value + timedelta(seconds=LEASE_TTL_SECONDS)
                ).isoformat(),
                "ttl_seconds": LEASE_TTL_SECONDS,
            },
            "created_at": now,
            "updated_at": now,
        }
        write_json(path, value)
        return value


def mark_network_may_have_started(output_dir: Path) -> dict[str, Any]:
    return _transition(
        output_dir,
        expected={"prepared"},
        updates={
            "state": "dispatching",
            "network_disposition": "may_have_dispatched",
            "provider_calls_started": True,
            "reconcile_required": True,
            "reconcile_reason": "provider_submit_started_without_durable_task_identity",
            "lease_status": "network_claimed",
        },
    )


def record_provider_task(output_dir: Path, provider_task: Mapping[str, Any]) -> dict[str, Any]:
    safe_task = provider_task_for_state(dict(provider_task))
    task_id = str((safe_task.get("task") or {}).get("task_id") or "")
    if not task_id:
        raise ValueError("provider task identity is missing")
    return _transition(
        output_dir,
        expected={"dispatching", "submitted"},
        updates={
            "state": "submitted",
            "network_disposition": "dispatched_with_task_identity",
            "provider_calls_started": True,
            "provider_task": safe_task,
            "provider_task_fingerprint": hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:16],
            "reconcile_required": False,
            "reconcile_reason": "",
            "lease_status": "task_recorded",
        },
    )


def mark_reconcile_required(output_dir: Path, reason: str) -> dict[str, Any]:
    return _transition(
        output_dir,
        expected={"dispatching", "submitted", "reconcile_required"},
        updates={
            "state": "reconcile_required",
            "network_disposition": "may_have_dispatched",
            "provider_calls_started": True,
            "reconcile_required": True,
            "reconcile_reason": str(reason or "provider_submit_outcome_unknown")[:120],
            "lease_status": "reconcile_required",
        },
    )


def load_dispatch_outbox(output_dir: Path) -> dict[str, Any]:
    path = _path(output_dir)
    if not path.is_file():
        return {}
    value = read_json(path)
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("video dispatch outbox schema is invalid")
    return value


def recover_provider_task(output_dir: Path) -> dict[str, Any]:
    value = load_dispatch_outbox(output_dir)
    task = value.get("provider_task")
    if (
        value.get("network_disposition") != "dispatched_with_task_identity"
        or not isinstance(task, Mapping)
    ):
        raise ValueError("video dispatch requires provider-side reconciliation before polling")
    return deepcopy(dict(task))


def _transition(
    output_dir: Path,
    *,
    expected: set[str],
    updates: Mapping[str, Any],
) -> dict[str, Any]:
    path = _path(output_dir)
    with exclusive_file_lock(path.with_suffix(".lock")):
        value = load_dispatch_outbox(output_dir)
        if str(value.get("state") or "") not in expected:
            if all(value.get(key) == expected_value for key, expected_value in updates.items()):
                return value
            raise ValueError("video dispatch outbox transition is not allowed")
        next_updates = deepcopy(dict(updates))
        lease_status = str(next_updates.pop("lease_status", "") or "")
        value.update(next_updates)
        if lease_status:
            value["lease"] = {
                **(
                    dict(value.get("lease"))
                    if isinstance(value.get("lease"), Mapping)
                    else {}
                ),
                "status": lease_status,
                "updated_at": _now(),
            }
        value["updated_at"] = _now()
        write_json(path, value)
        return value


def _assert_identity(
    value: Mapping[str, Any],
    project_id: str,
    job_id: str,
    manifest_id: str,
    manifest_hash: str,
    item_id: str,
) -> None:
    expected = (project_id, job_id, manifest_id, manifest_hash, item_id)
    actual = tuple(
        str(value.get(field) or "")
        for field in ("project_id", "job_id", "manifest_id", "manifest_hash", "item_id")
    )
    if actual != expected:
        raise ValueError("video dispatch outbox identity conflict")


def _path(output_dir: Path) -> Path:
    return output_dir / "video_dispatch_outbox.json"


def _now() -> str:
    return datetime.now(UTC).isoformat()


__all__ = (
    "load_dispatch_outbox",
    "mark_network_may_have_started",
    "mark_reconcile_required",
    "prepare_dispatch_outbox",
    "record_provider_task",
    "recover_provider_task",
)
