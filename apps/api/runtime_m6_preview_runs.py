from __future__ import annotations

import hashlib
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from agentflow.harness.json_io import exclusive_file_lock, write_json

from apps.api.runtime_file_logging import runtime_file_event
from apps.api.runtime_production_graph import canonical_digest
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


RUN_SCHEMA_VERSION = "afs.m6.preview_run.v0.2"
TERMINAL_PHASES = {"succeeded", "failed", "cancelled", "confirmed"}
PRUNABLE_PHASES = {"failed", "cancelled", "confirmed"}
MAX_TERMINAL_RUNS_PER_PROJECT = 24
MAX_UNCONFIRMED_RUNS_PER_PROJECT = 8
SERVER_CODEX_SERVICE = "server_codex"
SERVER_CODEX_PROVIDER = "codex_local"
SERVER_CODEX_MODEL = "gpt-5.5"

_EXECUTOR: ThreadPoolExecutor | None = None
_EXECUTOR_LOCK = threading.Lock()
_SUBMITTED: set[str] = set()
_SUBMITTED_LOCK = threading.Lock()


class M6PreviewRunError(ValueError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class M6PreviewRunStore:
    def __init__(self, store: RuntimeStore) -> None:
        self.store = store

    def create_or_load(
        self,
        project_id: str,
        *,
        owner_id: str,
        client_request_id: str,
        source_digest: str,
        expected_graph_version: int,
        remote_llm_enabled: bool,
    ) -> tuple[dict[str, Any], bool]:
        run_id = preview_run_id(owner_id, project_id, client_request_id)
        path = self.run_path(project_id, run_id)
        with exclusive_file_lock(self.run_lock_path(project_id, run_id)):
            if path.is_file():
                run = self._load_path(path, project_id, run_id)
                self._assert_binding(
                    run,
                    owner_id=owner_id,
                    client_request_id=client_request_id,
                    source_digest=source_digest,
                )
                return run, False
            tombstone = self._load_tombstone(project_id, run_id)
            if tombstone is not None:
                if str(tombstone.get("owner_id") or "") != owner_id:
                    raise M6PreviewRunError("preview_run_access_denied", "preview run belongs to a different account")
                if str(tombstone.get("client_request_id") or "") != client_request_id:
                    raise M6PreviewRunError("preview_request_identity_mismatch", "client request identity does not match")
                if str(tombstone.get("source_digest") or "") != source_digest:
                    raise M6PreviewRunError("preview_source_digest_mismatch", "client request id is already bound to different source")
                raise M6PreviewRunError("preview_run_expired", "preview run content expired and cannot be submitted again")
            now = _now()
            provider = {
                "service": SERVER_CODEX_SERVICE if remote_llm_enabled else "local_deterministic",
                "provider": SERVER_CODEX_PROVIDER if remote_llm_enabled else "local_runtime",
                "model": SERVER_CODEX_MODEL if remote_llm_enabled else "deterministic_contract",
            }
            run = {
                "schema_version": RUN_SCHEMA_VERSION,
                "run_id": run_id,
                "project_id": project_id,
                "owner_id": owner_id,
                "client_request_id": client_request_id,
                "source_digest": source_digest,
                "expected_graph_version": int(expected_graph_version),
                "phase": "queued",
                "status": "queued",
                "provider": provider,
                "execution_contract_digest": _execution_contract_digest(provider),
                "dispatch_ordinal": 0,
                "dispatch_count": 0,
                "created_at": now,
                "started_at": None,
                "finished_at": None,
                "updated_at": now,
                "candidate_digest": "",
                "confirmation": None,
                "cancel": {
                    "requested": False,
                    "provider_cancel_supported": False,
                    "in_flight_cancelled": False,
                },
                "cost": {
                    "contract_cost_usd": 0,
                    "reported_external_paid_cost_usd": 0,
                    "actual_usd": None,
                    "billing_state": "unverified",
                },
                "error": None,
                "retention": {
                    "terminal_run_limit": MAX_TERMINAL_RUNS_PER_PROJECT,
                    "unconfirmed_candidate_limit": MAX_UNCONFIRMED_RUNS_PER_PROJECT,
                    "candidate_scope": "authorized_owner_project_only",
                    "raw_provider_output_stored": False,
                },
            }
            self._write(path, run)
        self.prune_runs(project_id, preserve_run_id=run_id)
        return run, True

    def load(self, project_id: str, run_id: str, *, owner_id: str) -> dict[str, Any]:
        with exclusive_file_lock(self.run_lock_path(project_id, run_id)):
            return self._load_under_lock(project_id, run_id, owner_id=owner_id)

    def _load_under_lock(self, project_id: str, run_id: str, *, owner_id: str) -> dict[str, Any]:
        path = self.run_path(project_id, run_id)
        if path.is_file():
            run = self._load_path(path, project_id, run_id)
            self._assert_owner(run, owner_id)
            return run
        tombstone = self._load_tombstone(project_id, run_id)
        if tombstone is None:
            raise M6PreviewRunError("preview_run_not_found", "preview run does not exist")
        self._assert_owner(tombstone, owner_id)
        if str(tombstone.get("phase") or "") == "confirmed":
            return self._run_from_tombstone(tombstone)
        raise M6PreviewRunError("preview_run_expired", "preview run content expired")

    def load_by_client_request(
        self,
        project_id: str,
        client_request_id: str,
        *,
        owner_id: str,
    ) -> dict[str, Any]:
        return self.recover(
            project_id,
            preview_run_id(owner_id, project_id, client_request_id),
            owner_id=owner_id,
        )

    def recover(self, project_id: str, run_id: str, *, owner_id: str) -> dict[str, Any]:
        run = self.load(project_id, run_id, owner_id=owner_id)
        phase = str(run.get("phase") or "")
        if phase not in {"queued", "running", "running_cancel_requested"}:
            return run
        if preview_run_is_active(self.store, project_id, run_id):
            return run
        with exclusive_file_lock(self.run_lock_path(project_id, run_id)):
            run = self._load_path(self.run_path(project_id, run_id), project_id, run_id)
            self._assert_owner(run, owner_id)
            phase = str(run.get("phase") or "")
            if phase == "queued" and int(run.get("dispatch_count") or 0) == 0:
                run["error"] = {
                    "category": "submission_interrupted",
                    "message": "制作方案在文本任务开始前中断；制作事实未改变。",
                }
                return self._transition(run, phase="failed", status="failed_before_dispatch", finished=True)
            if phase in {"running", "running_cancel_requested"}:
                run["error"] = {
                    "category": "dispatch_result_unrecoverable",
                    "message": "文本任务已发送，但服务重启后无法恢复结果；系统不会自动再次提交，制作事实未改变。",
                }
                return self._transition(run, phase="failed", status="failed_after_dispatch", finished=True)
            return run

    def latest(self, project_id: str, *, owner_id: str) -> dict[str, Any] | None:
        runs: list[dict[str, Any]] = []
        for path in self.runs_dir(project_id).glob("*/run.json"):
            try:
                run = self._load_path(path, project_id, path.parent.name)
            except (M6PreviewRunError, OSError, ValueError):
                continue
            if str(run.get("owner_id") or "") == owner_id:
                runs.append(run)
        if not runs:
            return None
        latest = max(runs, key=lambda item: str(item.get("created_at") or ""))
        return self.recover(project_id, str(latest["run_id"]), owner_id=owner_id)

    def begin_dispatch(self, project_id: str, run_id: str, *, owner_id: str) -> dict[str, Any]:
        with exclusive_file_lock(self.run_lock_path(project_id, run_id)):
            run = self._load_path(self.run_path(project_id, run_id), project_id, run_id)
            self._assert_owner(run, owner_id)
            if str(run.get("phase") or "") != "queued":
                return run
            if bool((run.get("cancel") or {}).get("requested")):
                return self._transition(run, phase="cancelled", status="cancelled", finished=True)
            run["phase"] = "running"
            run["status"] = "running"
            run["started_at"] = _now()
            run["updated_at"] = run["started_at"]
            if str((run.get("provider") or {}).get("service") or "") == SERVER_CODEX_SERVICE:
                run["dispatch_ordinal"] = 1
                run["dispatch_count"] = 1
            self._write(self.run_path(project_id, run_id), run)
            return run

    def succeed(self, project_id: str, run_id: str, *, owner_id: str, preview: Mapping[str, Any]) -> dict[str, Any]:
        candidate = preview.get("candidate")
        candidate_digest = str(preview.get("candidate_digest") or "")
        if not isinstance(candidate, Mapping) or not candidate_digest:
            raise M6PreviewRunError("preview_candidate_invalid", "preview candidate is missing")
        if canonical_digest(candidate) != candidate_digest:
            raise M6PreviewRunError("preview_candidate_digest_mismatch", "preview candidate digest does not match")
        candidate_payload = dict(preview)
        reject_unsafe_payload(candidate_payload)
        with exclusive_file_lock(self.run_lock_path(project_id, run_id)):
            run = self._load_path(self.run_path(project_id, run_id), project_id, run_id)
            self._assert_owner(run, owner_id)
            if str(run.get("phase") or "") in TERMINAL_PHASES:
                return run
            provider = _provider_surface(preview, fallback=run.get("provider"))
            expected_provider = dict(run.get("provider") or {})
            if provider != expected_provider:
                raise M6PreviewRunError(
                    "preview_provider_identity_mismatch",
                    "preview provider identity does not match the committed run",
                )
            self.candidate_path(project_id, run_id).parent.mkdir(parents=True, exist_ok=True)
            write_json(self.candidate_path(project_id, run_id), candidate_payload)
            run["candidate_digest"] = candidate_digest
            run["provider"] = provider
            run["cost"] = _cost_surface(preview)
            return self._transition(run, phase="succeeded", status="preview_ready", finished=True)

    def fail(self, project_id: str, run_id: str, *, owner_id: str, error: BaseException) -> dict[str, Any]:
        with exclusive_file_lock(self.run_lock_path(project_id, run_id)):
            run = self._load_path(self.run_path(project_id, run_id), project_id, run_id)
            self._assert_owner(run, owner_id)
            if str(run.get("phase") or "") in TERMINAL_PHASES:
                return run
            category, message = _safe_error(error)
            run["error"] = {"category": category, "message": message}
            return self._transition(run, phase="failed", status="failed", finished=True)

    def cancel(self, project_id: str, run_id: str, *, owner_id: str) -> dict[str, Any]:
        with exclusive_file_lock(self.run_lock_path(project_id, run_id)):
            run = self._load_path(self.run_path(project_id, run_id), project_id, run_id)
            self._assert_owner(run, owner_id)
            phase = str(run.get("phase") or "")
            if phase in {"cancelled", "failed", "confirmed"}:
                return run
            cancel = dict(run.get("cancel") or {})
            cancel["requested"] = True
            run["cancel"] = cancel
            if phase in {"queued", "succeeded"}:
                return self._transition(run, phase="cancelled", status="cancelled", finished=True)
            run["phase"] = "running_cancel_requested"
            run["status"] = "running_cancel_requested"
            run["updated_at"] = _now()
            self._write(self.run_path(project_id, run_id), run)
            return run

    def load_candidate(self, project_id: str, run_id: str, *, owner_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
        with exclusive_file_lock(self.run_lock_path(project_id, run_id)):
            run = self._load_under_lock(project_id, run_id, owner_id=owner_id)
            if str(run.get("phase") or "") not in {"succeeded", "confirmed"}:
                raise M6PreviewRunError("preview_run_not_confirmable", "preview run is not ready for confirmation")
            path = self.candidate_path(project_id, run_id)
            if not path.is_file():
                raise M6PreviewRunError("preview_candidate_missing", "stored preview candidate is unavailable")
            candidate = self._load_candidate_payload(path)
            digest = str(run.get("candidate_digest") or "")
            if digest != str(candidate.get("candidate_digest") or ""):
                raise M6PreviewRunError("preview_candidate_digest_mismatch", "stored preview candidate digest does not match the run")
            return run, candidate

    def confirm_once(
        self,
        project_id: str,
        run_id: str,
        *,
        owner_id: str,
        candidate_digest: str,
        expected_graph_version: int,
        build_response: Callable[[dict[str, Any], dict[str, Any]], Mapping[str, Any]],
    ) -> dict[str, Any]:
        with exclusive_file_lock(self.run_lock_path(project_id, run_id)):
            run = self._load_under_lock(project_id, run_id, owner_id=owner_id)
            if str(run.get("candidate_digest") or "") != candidate_digest:
                raise M6PreviewRunError("preview_candidate_digest_mismatch", "candidate digest does not match the stored preview")
            if int(run.get("expected_graph_version") or 0) != expected_graph_version:
                raise M6PreviewRunError("preview_graph_version_mismatch", "preview expected graph version does not match")
            if str(run.get("phase") or "") == "confirmed":
                return self._load_confirmation_under_lock(project_id, run_id)
            if str(run.get("phase") or "") != "succeeded":
                raise M6PreviewRunError("preview_run_not_confirmable", "preview run is not ready for confirmation")
            path = self.candidate_path(project_id, run_id)
            if not path.is_file():
                raise M6PreviewRunError("preview_candidate_missing", "stored preview candidate is unavailable")
            preview = self._load_candidate_payload(path)
            if candidate_digest != str(preview.get("candidate_digest") or ""):
                raise M6PreviewRunError("preview_candidate_digest_mismatch", "stored preview candidate digest does not match the run")
            response = dict(build_response(run, preview))
            reject_unsafe_payload(response)
            write_json(self.confirmation_path(project_id, run_id), response)
            run["confirmation"] = {
                "status": "confirmed",
                "graph_version": int((response.get("graph") or {}).get("version") or 0),
                "graph_digest": str((response.get("graph") or {}).get("graph_digest") or ""),
                "confirmed_at": _now(),
            }
            run["phase"] = "confirmed"
            run["status"] = "confirmed"
            run["updated_at"] = _now()
            run["finished_at"] = run["updated_at"]
            self._write(self.run_path(project_id, run_id), run)
        self.prune_runs(project_id, preserve_run_id=run_id)
        return response

    def load_confirmation(self, project_id: str, run_id: str, *, owner_id: str) -> dict[str, Any] | None:
        with exclusive_file_lock(self.run_lock_path(project_id, run_id)):
            run = self._load_under_lock(project_id, run_id, owner_id=owner_id)
            if str(run.get("phase") or "") != "confirmed":
                return None
            return self._load_confirmation_under_lock(project_id, run_id)

    def _load_confirmation_under_lock(self, project_id: str, run_id: str) -> dict[str, Any]:
        path = self.confirmation_path(project_id, run_id)
        if path.is_file():
            payload = read_json(path)
            reject_unsafe_payload(payload)
            return payload
        tombstone = self._load_tombstone(project_id, run_id)
        if tombstone is not None and isinstance(tombstone.get("confirmation_response"), Mapping):
            return dict(tombstone["confirmation_response"])
        raise M6PreviewRunError("preview_confirmation_missing", "confirmed preview receipt is unavailable")

    def public(self, run: Mapping[str, Any], *, include_candidate: bool = True) -> dict[str, Any]:
        project_id = str(run.get("project_id") or "")
        run_id = str(run.get("run_id") or "")
        owner_id = str(run.get("owner_id") or "")
        if project_id and run_id and owner_id:
            with exclusive_file_lock(self.run_lock_path(project_id, run_id)):
                current = self._load_under_lock(project_id, run_id, owner_id=owner_id)
                payload = {
                    key: value
                    for key, value in current.items()
                    if key not in {"owner_id"}
                }
                if not include_candidate or str(current.get("phase") or "") not in {"succeeded", "confirmed"}:
                    reject_unsafe_payload(payload)
                    return payload
                path = self.candidate_path(project_id, run_id)
                if path.is_file():
                    candidate = self._load_candidate_payload(path)
                    if str(current.get("candidate_digest") or "") != str(candidate.get("candidate_digest") or ""):
                        raise M6PreviewRunError("preview_candidate_digest_mismatch", "stored preview candidate digest does not match the run")
                    payload["preview"] = candidate
                elif str(current.get("phase") or "") == "succeeded":
                    raise M6PreviewRunError("preview_run_expired", "preview run content expired")
        else:
            payload = {
                key: value
                for key, value in dict(run).items()
                if key not in {"owner_id"}
            }
        reject_unsafe_payload(payload)
        return payload

    def prune_runs(self, project_id: str, *, preserve_run_id: str) -> None:
        terminal: list[tuple[str, str, Path]] = []
        unconfirmed: list[tuple[str, str, Path]] = []
        for path in self.runs_dir(project_id).glob("*/run.json"):
            try:
                run = self._load_path(path, project_id, path.parent.name)
            except (M6PreviewRunError, OSError, ValueError):
                continue
            entry = (
                str(run.get("finished_at") or run.get("updated_at") or ""),
                path.parent.name,
                path.parent,
            )
            phase = str(run.get("phase") or "")
            if phase in PRUNABLE_PHASES:
                terminal.append(entry)
            elif phase == "succeeded":
                unconfirmed.append(entry)
        self._prune_group(
            project_id,
            terminal,
            limit=MAX_TERMINAL_RUNS_PER_PROJECT,
            allowed_phases=PRUNABLE_PHASES,
            preserve_run_id=preserve_run_id,
        )
        self._prune_group(
            project_id,
            unconfirmed,
            limit=MAX_UNCONFIRMED_RUNS_PER_PROJECT,
            allowed_phases={"succeeded"},
            preserve_run_id=preserve_run_id,
        )

    def _prune_group(
        self,
        project_id: str,
        entries: list[tuple[str, str, Path]],
        *,
        limit: int,
        allowed_phases: set[str],
        preserve_run_id: str,
    ) -> None:
        entries.sort(reverse=True)
        keep = {run_id for _, run_id, _ in entries[:limit]}
        keep.add(preserve_run_id)
        for _, run_id, directory in entries:
            if run_id in keep:
                continue
            with exclusive_file_lock(self.run_lock_path(project_id, run_id)):
                path = self.run_path(project_id, run_id)
                if not path.is_file():
                    continue
                run = self._load_path(path, project_id, run_id)
                if str(run.get("phase") or "") in allowed_phases:
                    self._record_tombstone(project_id, run_id, self._build_tombstone(run))
                    try:
                        shutil.rmtree(directory)
                    except OSError as exc:
                        runtime_file_event(
                            "m6_preview",
                            "retention_prune_failed",
                            level="WARNING",
                            project_id=project_id,
                            job_id=run_id,
                            error=type(exc).__name__,
                        )

    def runs_dir(self, project_id: str) -> Path:
        return self.store.projects_dir / safe_id(project_id) / "m6_preview_runs"

    def run_path(self, project_id: str, run_id: str) -> Path:
        return self.runs_dir(project_id) / safe_id(run_id) / "run.json"

    def candidate_path(self, project_id: str, run_id: str) -> Path:
        return self.runs_dir(project_id) / safe_id(run_id) / "candidate.json"

    def confirmation_path(self, project_id: str, run_id: str) -> Path:
        return self.runs_dir(project_id) / safe_id(run_id) / "confirmation.json"

    def run_lock_path(self, project_id: str, run_id: str) -> Path:
        return self.runs_dir(project_id) / "_locks" / f"{safe_id(run_id)}.lock"

    def tombstone_path(self, project_id: str) -> Path:
        return self.runs_dir(project_id) / "_tombstones.json"

    def tombstone_lock_path(self, project_id: str) -> Path:
        return self.runs_dir(project_id) / "_tombstones.lock"

    def _load_tombstone(self, project_id: str, run_id: str) -> dict[str, Any] | None:
        with exclusive_file_lock(self.tombstone_lock_path(project_id)):
            path = self.tombstone_path(project_id)
            if not path.is_file():
                return None
            index = read_json(path)
            reject_unsafe_payload(index)
            if (
                index.get("schema_version") != "afs.m6.preview_tombstones.v0.1"
                or str(index.get("project_id") or "") != project_id
            ):
                raise M6PreviewRunError("preview_tombstone_index_invalid", "preview tombstone index is invalid")
            entry = (index.get("runs") or {}).get(run_id)
            return dict(entry) if isinstance(entry, Mapping) else None

    def _record_tombstone(self, project_id: str, run_id: str, tombstone: Mapping[str, Any]) -> None:
        with exclusive_file_lock(self.tombstone_lock_path(project_id)):
            path = self.tombstone_path(project_id)
            if path.is_file():
                index = read_json(path)
                reject_unsafe_payload(index)
            else:
                index = {
                    "schema_version": "afs.m6.preview_tombstones.v0.1",
                    "project_id": project_id,
                    "runs": {},
                }
            runs = dict(index.get("runs") or {})
            runs[run_id] = dict(tombstone)
            index["runs"] = runs
            self._write(path, index)

    def _build_tombstone(self, run: Mapping[str, Any]) -> dict[str, Any]:
        confirmation = dict(run.get("confirmation") or {})
        confirmation_response = None
        if str(run.get("phase") or "") == "confirmed":
            confirmation_response = {
                "status": "confirmed",
                "run_id": str(run.get("run_id") or ""),
                "candidate_digest": str(run.get("candidate_digest") or ""),
                "graph": {
                    "version": int(confirmation.get("graph_version") or 0),
                    "graph_digest": str(confirmation.get("graph_digest") or ""),
                },
                "projection": {},
                "m6_validation": {},
                "provider_dispatch_count": int(run.get("dispatch_count") or 0),
                "cost": dict(run.get("cost") or {}),
                "cost_usd": (run.get("cost") or {}).get("contract_cost_usd", 0),
            }
        return {
            "schema_version": RUN_SCHEMA_VERSION,
            "run_id": str(run.get("run_id") or ""),
            "project_id": str(run.get("project_id") or ""),
            "owner_id": str(run.get("owner_id") or ""),
            "client_request_id": str(run.get("client_request_id") or ""),
            "source_digest": str(run.get("source_digest") or ""),
            "expected_graph_version": int(run.get("expected_graph_version") or 0),
            "provider": dict(run.get("provider") or {}),
            "execution_contract_digest": str(run.get("execution_contract_digest") or ""),
            "phase": str(run.get("phase") or ""),
            "candidate_digest": str(run.get("candidate_digest") or ""),
            "dispatch_count": int(run.get("dispatch_count") or 0),
            "cost": dict(run.get("cost") or {}),
            "confirmation": confirmation or None,
            "confirmation_response": confirmation_response,
            "pruned_at": _now(),
            "candidate_content_retained": False,
        }

    @staticmethod
    def _run_from_tombstone(tombstone: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": RUN_SCHEMA_VERSION,
            "run_id": str(tombstone.get("run_id") or ""),
            "project_id": str(tombstone.get("project_id") or ""),
            "owner_id": str(tombstone.get("owner_id") or ""),
            "client_request_id": str(tombstone.get("client_request_id") or ""),
            "source_digest": str(tombstone.get("source_digest") or ""),
            "expected_graph_version": int(tombstone.get("expected_graph_version") or 0),
            "phase": "confirmed",
            "status": "confirmed",
            "provider": dict(tombstone.get("provider") or {}),
            "execution_contract_digest": str(tombstone.get("execution_contract_digest") or ""),
            "dispatch_count": int(tombstone.get("dispatch_count") or 0),
            "candidate_digest": str(tombstone.get("candidate_digest") or ""),
            "confirmation": dict(tombstone.get("confirmation") or {}),
            "cost": dict(tombstone.get("cost") or {}),
            "retention": {
                "candidate_content_retained": False,
                "idempotency_binding_retained": True,
            },
        }

    def _transition(self, run: dict[str, Any], *, phase: str, status: str, finished: bool) -> dict[str, Any]:
        run["phase"] = phase
        run["status"] = status
        run["updated_at"] = _now()
        if finished:
            run["finished_at"] = run["updated_at"]
        self._write(self.run_path(str(run["project_id"]), str(run["run_id"])), run)
        if phase in PRUNABLE_PHASES or phase == "succeeded":
            self.prune_runs(str(run["project_id"]), preserve_run_id=str(run["run_id"]))
        return run

    def _load_path(self, path: Path, project_id: str, run_id: str) -> dict[str, Any]:
        payload = read_json(path)
        reject_unsafe_payload(payload)
        if payload.get("schema_version") != RUN_SCHEMA_VERSION:
            raise M6PreviewRunError("preview_run_schema_mismatch", "preview run schema is invalid")
        if str(payload.get("project_id") or "") != project_id or str(payload.get("run_id") or "") != run_id:
            raise M6PreviewRunError("preview_run_identity_mismatch", "preview run storage identity does not match")
        provider = payload.get("provider")
        if not isinstance(provider, Mapping) or str(payload.get("execution_contract_digest") or "") != _execution_contract_digest(provider):
            raise M6PreviewRunError("preview_execution_contract_mismatch", "preview execution contract is invalid")
        return payload

    @staticmethod
    def _load_candidate_payload(path: Path) -> dict[str, Any]:
        payload = read_json(path)
        reject_unsafe_payload(payload)
        candidate = payload.get("candidate")
        digest = str(payload.get("candidate_digest") or "")
        if not isinstance(candidate, Mapping) or not digest or canonical_digest(candidate) != digest:
            raise M6PreviewRunError("preview_candidate_digest_mismatch", "stored preview candidate body is invalid")
        return payload

    def _assert_binding(
        self,
        run: Mapping[str, Any],
        *,
        owner_id: str,
        client_request_id: str,
        source_digest: str,
    ) -> None:
        self._assert_owner(run, owner_id)
        if str(run.get("client_request_id") or "") != client_request_id:
            raise M6PreviewRunError("preview_request_identity_mismatch", "client request identity does not match")
        if str(run.get("source_digest") or "") != source_digest:
            raise M6PreviewRunError("preview_source_digest_mismatch", "client request id is already bound to different source")

    @staticmethod
    def _assert_owner(run: Mapping[str, Any], owner_id: str) -> None:
        if str(run.get("owner_id") or "") != owner_id:
            raise M6PreviewRunError("preview_run_access_denied", "preview run belongs to a different account")

    @staticmethod
    def _write(path: Path, payload: dict[str, Any]) -> None:
        reject_unsafe_payload(payload)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, payload)


def submit_m6_preview_run(
    run_store: M6PreviewRunStore,
    project_id: str,
    run_id: str,
    *,
    owner_id: str,
    body: Mapping[str, Any],
    planner_resolver: Callable[
        [bool],
        Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
    ],
) -> None:
    submission_key = _submission_key(run_store.store, project_id, run_id)
    with _SUBMITTED_LOCK:
        if submission_key in _SUBMITTED:
            return
        run = run_store.load(project_id, run_id, owner_id=owner_id)
        if str(run.get("phase") or "") != "queued":
            return
        committed_remote_llm = preview_run_uses_remote_llm(run)
        _SUBMITTED.add(submission_key)
    _executor().submit(
        _execute_preview_run,
        submission_key,
        run_store,
        project_id,
        run_id,
        owner_id,
        dict(body),
        committed_remote_llm,
        planner_resolver(committed_remote_llm),
    )


def preview_run_id(owner_id: str, project_id: str, client_request_id: str) -> str:
    digest = hashlib.sha256(f"{owner_id}\n{project_id}\n{client_request_id}".encode("utf-8")).hexdigest()[:24]
    return f"m6-preview-{digest}"


def preview_run_is_active(store: RuntimeStore, project_id: str, run_id: str) -> bool:
    with _SUBMITTED_LOCK:
        return _submission_key(store, project_id, run_id) in _SUBMITTED


def preview_run_uses_remote_llm(run: Mapping[str, Any]) -> bool:
    return str((run.get("provider") or {}).get("service") or "") == SERVER_CODEX_SERVICE


def preview_source_digest(body: Mapping[str, Any]) -> str:
    return canonical_digest({
        "schema_version": RUN_SCHEMA_VERSION,
        "source_kind": body.get("source_kind") or "idea",
        "source_text": str(body.get("source_text") or ""),
        "revision_instruction": str(body.get("revision_instruction") or ""),
        "parent_candidate_digest": str(body.get("parent_candidate_digest") or ""),
        "requested_language": str(body.get("requested_language") or "zh-CN"),
    })


def _execute_preview_run(
    submission_key: str,
    run_store: M6PreviewRunStore,
    project_id: str,
    run_id: str,
    owner_id: str,
    body: Mapping[str, Any],
    remote_llm_enabled: bool,
    planner: Callable[[str, Mapping[str, Any]], Mapping[str, Any]],
) -> None:
    try:
        run = run_store.begin_dispatch(
            project_id,
            run_id,
            owner_id=owner_id,
        )
        if str(run.get("phase") or "") != "running":
            return
        runtime_file_event(
            "m6_preview",
            "dispatch_started",
            project_id=project_id,
            client_request_id=str(run.get("client_request_id") or ""),
            job_id=run_id,
            provider_service_id=str((run.get("provider") or {}).get("service") or ""),
            model=str((run.get("provider") or {}).get("model") or ""),
            dispatch_count=int(run.get("dispatch_count") or 0),
        )
        preview = planner(project_id, body)
        run = run_store.succeed(project_id, run_id, owner_id=owner_id, preview=preview)
        runtime_file_event(
            "m6_preview",
            "dispatch_completed",
            project_id=project_id,
            client_request_id=str(run.get("client_request_id") or ""),
            job_id=run_id,
            provider_service_id=str((run.get("provider") or {}).get("service") or ""),
            model=str((run.get("provider") or {}).get("model") or ""),
            dispatch_count=int(run.get("dispatch_count") or 0),
            candidate=str(run.get("candidate_digest") or "")[:16],
            status="succeeded",
        )
    except BaseException as exc:
        try:
            run_store.fail(project_id, run_id, owner_id=owner_id, error=exc)
        finally:
            runtime_file_event(
                "m6_preview",
                "dispatch_failed",
                level="ERROR",
                project_id=project_id,
                job_id=run_id,
                error=type(exc).__name__,
            )
    finally:
        with _SUBMITTED_LOCK:
            _SUBMITTED.discard(submission_key)


def _executor() -> ThreadPoolExecutor:
    global _EXECUTOR
    with _EXECUTOR_LOCK:
        if _EXECUTOR is None:
            _EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="afs-m6-preview")
        return _EXECUTOR


def _submission_key(store: RuntimeStore, project_id: str, run_id: str) -> str:
    return f"{store.root.resolve()}:{project_id}:{run_id}"


def _provider_surface(preview: Mapping[str, Any], *, fallback: Any) -> dict[str, str]:
    lineage = preview.get("provider_lineage")
    if not isinstance(lineage, Mapping):
        lineage = (preview.get("candidate") or {}).get("provider_lineage") if isinstance(preview.get("candidate"), Mapping) else {}
    if not isinstance(lineage, Mapping):
        lineage = {}
    base = dict(fallback) if isinstance(fallback, Mapping) else {}
    return {
        "service": str(lineage.get("service_id") or base.get("service") or "local_deterministic"),
        "provider": str(lineage.get("provider") or base.get("provider") or "local_runtime"),
        "model": str(lineage.get("model") or lineage.get("model_surface") or base.get("model") or "deterministic_contract"),
    }


def _execution_contract_digest(provider: Mapping[str, Any]) -> str:
    return canonical_digest({
        "schema_version": RUN_SCHEMA_VERSION,
        "provider": {
            "service": str(provider.get("service") or ""),
            "provider": str(provider.get("provider") or ""),
            "model": str(provider.get("model") or ""),
        },
    })


def _cost_surface(preview: Mapping[str, Any]) -> dict[str, Any]:
    lineage = preview.get("provider_lineage")
    if not isinstance(lineage, Mapping):
        lineage = (preview.get("candidate") or {}).get("provider_lineage") if isinstance(preview.get("candidate"), Mapping) else {}
    if not isinstance(lineage, Mapping):
        lineage = {}
    reported = lineage.get("external_paid_cost_usd", preview.get("cost_usd", 0))
    try:
        reported_cost = float(reported or 0)
    except (TypeError, ValueError):
        reported_cost = 0
    return {
        "contract_cost_usd": 0,
        "reported_external_paid_cost_usd": reported_cost,
        "actual_usd": None,
        "billing_state": "unverified",
    }


def _safe_error(error: BaseException) -> tuple[str, str]:
    name = type(error).__name__.lower()
    text = str(error).lower()
    if "timeout" in name or "timeout" in text:
        return "timeout", "制作方案处理超时；同一任务已保留，可查看恢复状态。"
    if "cancel" in name or "cancel" in text:
        return "cancelled", "制作方案任务已取消；制作事实未改变。"
    if "planning" in name or "candidate" in text or "contract" in text:
        return "planning_rejected", "制作方案未通过结构校验；制作事实未改变。"
    if "provider" in text or "model" in text:
        return "text_service_failed", "文本规划能力未完成本次任务；制作事实未改变。"
    return "runtime_failed", "制作方案任务未完成；制作事实未改变。"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = (
    "MAX_TERMINAL_RUNS_PER_PROJECT",
    "MAX_UNCONFIRMED_RUNS_PER_PROJECT",
    "M6PreviewRunError",
    "M6PreviewRunStore",
    "preview_run_id",
    "preview_run_uses_remote_llm",
    "preview_source_digest",
    "submit_m6_preview_run",
)
