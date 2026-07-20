from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Literal

from agentflow_studio.production.manga_first_l4a_compiler import validate_manga_first_manifest
from agentflow_studio.production.manga_first_l4a_schema import (
    CheckpointStateError,
    ProductionTruthManifest,
    json_digest,
    read_json_object,
    write_json_atomic,
)


CheckpointAction = Literal[
    "acquire_lease",
    "takeover_expired",
    "pause",
    "cancel",
    "retry",
    "dlq",
    "complete",
]


class CheckpointLedgerStore:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def initialize(self, manifest: ProductionTruthManifest | dict[str, Any]) -> dict[str, Any]:
        parsed = validate_manga_first_manifest(manifest)
        state = {
            "schema_version": "afs.manga_first_l4b.checkpoint_ledger.v0.2",
            "project_id": parsed.project_id,
            "manifest_sha256": parsed.manifest_sha256,
            "provider_dispatch_count": 0,
            "version": 1,
            "project_control_state": "active",
            "idempotency_records": {},
            "charge_fingerprints": {},
            "shots": {
                item["shot_id"]: {
                    "shot_id": item["shot_id"],
                    "status": "waiting_provider_authorization",
                    "completed": False,
                    "charge_fingerprint": None,
                    "charge_reservation_count": 0,
                    "attempt_ids": [],
                }
                for item in parsed.shots
            },
            "checkpoints": {
                item["stage"]: {
                    **item,
                    "lease": None,
                    "retry_count": 0,
                    "control_state": "active",
                    "dlq": None,
                }
                for item in parsed.checkpoints
            },
        }
        self._write(state)
        return state

    def apply(
        self,
        *,
        stage: str,
        action: CheckpointAction,
        idempotency_key: str,
        worker_id: str = "l4b-worker",
        now: str = "2026-07-18T00:00:00+00:00",
        lease_expires_at: str = "2026-07-18T00:15:00+00:00",
        reason: str = "",
    ) -> dict[str, Any]:
        state = self._read()
        replay = _idempotent_replay(state, idempotency_key)
        if replay is not None:
            return replay
        checkpoint = _checkpoint(state, stage)
        if action == "acquire_lease":
            _acquire_lease(checkpoint, worker_id=worker_id, now=now, lease_expires_at=lease_expires_at)
        elif action == "takeover_expired":
            _takeover_expired(checkpoint, worker_id=worker_id, now=now, lease_expires_at=lease_expires_at)
        elif action == "pause":
            checkpoint["control_state"] = "paused"
        elif action == "cancel":
            checkpoint["control_state"] = "cancelled"
            checkpoint["status"] = "cancelled"
            checkpoint["lease"] = None
        elif action == "retry":
            checkpoint["retry_count"] = int(checkpoint.get("retry_count") or 0) + 1
            checkpoint["status"] = "queued"
            checkpoint["lease"] = None
        elif action == "dlq":
            checkpoint["status"] = "dead_letter"
            checkpoint["dlq"] = {"reason": reason or "unspecified", "recorded_at": now}
            checkpoint["lease"] = None
        elif action == "complete":
            checkpoint["status"] = "succeeded"
            checkpoint["lease"] = None
        else:
            raise CheckpointStateError("unsupported checkpoint action")
        state["version"] = int(state["version"]) + 1
        result = {"version": state["version"], "checkpoint": deepcopy(checkpoint)}
        _record_idempotency(state, idempotency_key, {"stage": stage, "action": action}, result)
        self._write(state)
        return result

    def reserve_shot_charge(
        self,
        *,
        stage: Literal["keyframe", "video"],
        shot_id: str,
        capability: Literal["image", "video"],
        prompt_sha256: str,
        attempt_id: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        state = self._read()
        replay = _idempotent_replay(state, idempotency_key)
        if replay is not None:
            return replay
        shot = _shot(state, shot_id)
        fingerprint = charge_fingerprint(
            project_id=str(state["project_id"]),
            manifest_sha256=str(state["manifest_sha256"]),
            stage=stage,
            shot_id=shot_id,
            capability=capability,
            prompt_sha256=prompt_sha256,
        )
        if shot.get("completed") is True:
            result = {
                "status": "skipped_already_completed",
                "shot_id": shot_id,
                "charge_fingerprint": shot.get("charge_fingerprint") or fingerprint,
                "charge_reserved": False,
                "provider_dispatch_count": 0,
            }
            _record_idempotency(state, idempotency_key, {"shot_id": shot_id, "stage": stage}, result)
            self._write(state)
            return result
        existing = shot.get("charge_fingerprint")
        if existing and existing != fingerprint:
            raise CheckpointStateError("shot already has a different charge fingerprint")
        shot["charge_fingerprint"] = fingerprint
        shot["status"] = "reserved_provider_charge_fingerprint"
        shot["charge_reservation_count"] = int(shot.get("charge_reservation_count") or 0) + (0 if existing else 1)
        attempts = list(shot.get("attempt_ids") or [])
        if attempt_id not in attempts:
            attempts.append(attempt_id)
        shot["attempt_ids"] = attempts
        state["charge_fingerprints"][fingerprint] = {
            "stage": stage,
            "shot_id": shot_id,
            "capability": capability,
            "prompt_sha256": prompt_sha256,
            "attempt_id": attempt_id,
            "provider_dispatch_count": 0,
        }
        state["version"] = int(state["version"]) + 1
        result = {
            "status": "charge_fingerprint_reserved",
            "shot_id": shot_id,
            "charge_fingerprint": fingerprint,
            "charge_reserved": existing is None,
            "provider_dispatch_count": 0,
        }
        _record_idempotency(state, idempotency_key, {"shot_id": shot_id, "stage": stage}, result)
        self._write(state)
        return result

    def complete_shot(self, *, shot_id: str, idempotency_key: str) -> dict[str, Any]:
        state = self._read()
        replay = _idempotent_replay(state, idempotency_key)
        if replay is not None:
            return replay
        shot = _shot(state, shot_id)
        if not shot.get("charge_fingerprint"):
            raise CheckpointStateError("shot cannot complete before charge fingerprint reservation")
        shot["completed"] = True
        shot["status"] = "succeeded"
        state["version"] = int(state["version"]) + 1
        result = {
            "status": "shot_completed",
            "shot_id": shot_id,
            "charge_fingerprint": shot["charge_fingerprint"],
            "provider_dispatch_count": 0,
        }
        _record_idempotency(state, idempotency_key, {"shot_id": shot_id, "action": "complete_shot"}, result)
        self._write(state)
        return result

    def load(self) -> dict[str, Any]:
        return self._read()

    def _read(self) -> dict[str, Any]:
        return read_json_object(self.path)

    def _write(self, state: dict[str, Any]) -> None:
        write_json_atomic(self.path, state)


def charge_fingerprint(
    *,
    project_id: str,
    manifest_sha256: str,
    stage: str,
    shot_id: str,
    capability: str,
    prompt_sha256: str,
) -> str:
    return json_digest(
        {
            "schema_version": "afs.manga_first_l4b.charge_fingerprint.v0.1",
            "project_id": project_id,
            "manifest_sha256": manifest_sha256,
            "stage": stage,
            "shot_id": shot_id,
            "capability": capability,
            "prompt_sha256": prompt_sha256,
        }
    )


def _checkpoint(state: dict[str, Any], stage: str) -> dict[str, Any]:
    try:
        return state["checkpoints"][stage]
    except KeyError as exc:
        raise CheckpointStateError("checkpoint stage does not exist") from exc


def _shot(state: dict[str, Any], shot_id: str) -> dict[str, Any]:
    try:
        return state["shots"][shot_id]
    except KeyError as exc:
        raise CheckpointStateError("shot does not exist") from exc


def _idempotent_replay(state: dict[str, Any], idempotency_key: str) -> dict[str, Any] | None:
    records = state.setdefault("idempotency_records", {})
    if idempotency_key in records:
        return deepcopy(records[idempotency_key]["result"])
    return None


def _record_idempotency(
    state: dict[str, Any],
    idempotency_key: str,
    intent: dict[str, Any],
    result: dict[str, Any],
) -> None:
    state.setdefault("idempotency_records", {})[idempotency_key] = {
        "intent_sha256": json_digest(intent),
        "result": deepcopy(result),
    }


def _acquire_lease(checkpoint: dict[str, Any], *, worker_id: str, now: str, lease_expires_at: str) -> None:
    lease = checkpoint.get("lease")
    if lease and lease.get("expires_at", "") > now and lease.get("worker_id") != worker_id:
        raise CheckpointStateError("checkpoint lease is still active")
    checkpoint["lease"] = {"worker_id": worker_id, "acquired_at": now, "expires_at": lease_expires_at}
    checkpoint["status"] = "running"


def _takeover_expired(checkpoint: dict[str, Any], *, worker_id: str, now: str, lease_expires_at: str) -> None:
    lease = checkpoint.get("lease")
    if not lease or lease.get("expires_at", "") > now:
        raise CheckpointStateError("only expired leases can be taken over")
    checkpoint["lease"] = {
        "worker_id": worker_id,
        "acquired_at": now,
        "expires_at": lease_expires_at,
        "takeover_of": lease.get("worker_id"),
    }
    checkpoint["status"] = "running"
