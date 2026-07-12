from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentflow.contracts.project_manifest import validate_project_manifest
from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.harness.json_io import system_path, write_json


SAFE_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_.-]+")


class RuntimeStore:
    def __init__(self, runtime_root: Path) -> None:
        self.root = Path(runtime_root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.projects_dir = self.root / "projects"
        self.runs_dir = self.root / "runs"
        self.jobs_dir = self.root / "jobs"
        self.feedback_dir = self.root / "feedback"
        for path in (self.projects_dir, self.runs_dir, self.jobs_dir, self.feedback_dir):
            path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "artifact_index.json"
        if not self.index_path.exists():
            write_json(self.index_path, {"artifacts": {}})
        else:
            write_json(self.index_path, self._artifact_index())

    def project_manifest_path(self, project_id: str) -> Path:
        safe = safe_id(project_id)
        return self.projects_dir / safe / "project_manifest.json"

    def project_deleted_marker_path(self, project_id: str) -> Path:
        safe = safe_id(project_id)
        return self.projects_dir / safe / "project_deleted.json"

    def is_project_deleted(self, project_id: str) -> bool:
        return self.project_deleted_marker_path(project_id).is_file()

    def create_project_manifest(
        self,
        *,
        project_id: str,
        project_type: str,
        goal: str,
        status: str,
    ) -> dict[str, Any]:
        payload = {
            "artifact_type": "agentflow_project_manifest",
            "schema_version": "0.1.0",
            "project_id": project_id,
            "project_type": project_type,
            "goal": goal,
            "source_assets": [],
            "content_cards": [],
            "runs": [],
            "packages": [],
            "feedback_refs": [],
            "profile_version_refs": [],
            "status": status,
            "does_not_store_secrets": True,
            "does_not_store_private_asset_bytes": True,
            "does_not_auto_sync": True,
        }
        validate_project_manifest(payload)
        path = self.project_manifest_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        marker = self.project_deleted_marker_path(project_id)
        if marker.exists():
            marker.unlink()
        write_json(path, payload)
        return payload

    def ensure_project_manifest(self, project_id: str) -> dict[str, Any]:
        path = self.project_manifest_path(project_id)
        if not path.exists():
            return self.create_project_manifest(
                project_id=project_id,
                project_type="short_video_campaign",
                goal="Runtime service project",
                status="in_progress",
            )
        payload = read_json(path)
        validate_project_manifest(payload)
        return payload

    def import_project_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        payload = dict(manifest)
        reject_unsafe_payload(payload)
        validate_project_manifest(payload)
        project_id = str(payload["project_id"])
        path = self.project_manifest_path(project_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, payload)
        return payload

    def list_project_summaries(self) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        for path in sorted(self.projects_dir.glob("*/project_manifest.json")):
            if (path.parent / "project_deleted.json").is_file():
                continue
            manifest = read_json(path)
            validate_project_manifest(manifest)
            artifact = self.register_artifact(path, role="project_manifest")
            summaries.append(project_summary(manifest, artifact))
        return summaries

    def soft_delete_project(self, project_id: str, *, deleted_by: str = "", reason: str = "user_requested") -> dict[str, Any]:
        path = self.project_manifest_path(project_id)
        if not path.exists():
            raise KeyError(project_id)
        manifest = read_json(path)
        validate_project_manifest(manifest)
        marker = {
            "schema_version": "0.1.0",
            "project_id": str(manifest.get("project_id") or project_id),
            "deleted": True,
            "delete_mode": "soft_delete",
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "deleted_by": str(deleted_by or ""),
            "reason": str(reason or "user_requested"),
            "does_not_delete_project_bytes": True,
        }
        marker_path = self.project_deleted_marker_path(project_id)
        marker_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(marker_path, marker)
        return marker

    def update_project_manifest(self, project_id: str, updates: dict[str, list[dict[str, Any]]], status: str) -> dict[str, Any]:
        manifest = self.ensure_project_manifest(project_id)
        for field, refs in updates.items():
            existing = list(manifest.get(field, []))
            for ref in refs:
                if ref not in existing:
                    existing.append(ref)
            manifest[field] = existing
        manifest["status"] = status
        validate_project_manifest(manifest)
        write_json(self.project_manifest_path(project_id), manifest)
        return manifest

    def add_source_asset(self, project_id: str, asset_ref: dict[str, Any]) -> dict[str, Any]:
        reject_unsafe_payload(asset_ref)
        return self.update_project_manifest(project_id, {"source_assets": [asset_ref]}, status="in_progress")

    def add_content_card(self, project_id: str, content_card: dict[str, Any]) -> dict[str, Any]:
        reject_unsafe_payload(content_card)
        return self.update_project_manifest(project_id, {"content_cards": [content_card]}, status="in_progress")

    def update_content_card(self, project_id: str, card_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        manifest = self.ensure_project_manifest(project_id)
        cards = list(manifest.get("content_cards", []))
        for index, item in enumerate(cards):
            if isinstance(item, dict) and item.get("card_id") == card_id:
                merged = {**item, **updates}
                reject_unsafe_payload(merged)
                cards[index] = merged
                manifest["content_cards"] = cards
                manifest["status"] = "in_progress"
                validate_project_manifest(manifest)
                write_json(self.project_manifest_path(project_id), manifest)
                return manifest
        raise ValueError("content card not found")

    def new_job_id(self, action: str, project_id: str) -> str:
        return f"{safe_id(project_id)}-{safe_id(action)}-{uuid4().hex[:12]}"

    def run_dir(self, project_id: str, job_id: str) -> Path:
        return self.runs_dir / safe_id(project_id) / safe_id(job_id)

    def write_job(self, job: dict[str, Any]) -> dict[str, Any]:
        write_json(self.jobs_dir / f"{safe_id(str(job['job_id']))}.json", job)
        return public_job(job)

    def load_job(self, job_id: str) -> dict[str, Any]:
        path = self.jobs_dir / f"{safe_id(job_id)}.json"
        if not path.exists():
            raise KeyError(job_id)
        return read_json(path)

    def list_project_jobs(self, project_id: str) -> list[dict[str, Any]]:
        jobs: list[dict[str, Any]] = []
        for path in sorted(self.jobs_dir.glob("*.json"), key=lambda item: item.stat().st_mtime):
            job = read_json(path)
            if job.get("project_id") == project_id:
                jobs.append(public_job(job))
        return jobs

    def register_artifact(self, path: Path, *, role: str) -> dict[str, Any]:
        resolved = Path(path).resolve()
        if not _path_exists(resolved):
            raise FileNotFoundError(str(path))
        relative_path = resolved.relative_to(self.root.resolve()).as_posix()
        artifact_id = safe_id(str(resolved.relative_to(self.root.resolve()).with_suffix("")))
        payload = read_json(resolved) if resolved.suffix.lower() == ".json" else None
        artifact_type = str((payload or {}).get("artifact_type") or (payload or {}).get("kind") or "text_artifact")
        entry = {
            "artifact_id": artifact_id,
            "relative_path": relative_path,
            "filename": resolved.name,
            "artifact_type": artifact_type,
            "role": role,
            "media_type": "application/json" if resolved.suffix.lower() == ".json" else "text/markdown",
        }
        project_id = _project_id_from_artifact_relative_path(relative_path)
        if project_id:
            entry["project_id"] = project_id
        index = self._artifact_index()
        index.setdefault("artifacts", {})[artifact_id] = entry
        write_json(self.index_path, index)
        return public_artifact_ref(entry)

    def artifact_project_id(self, artifact_id: str) -> str:
        index = self._artifact_index()
        entry = dict(index.get("artifacts", {}).get(artifact_id) or {})
        if not entry:
            raise KeyError(artifact_id)
        return str(entry.get("project_id") or _project_id_from_artifact_relative_path(str(entry.get("relative_path") or "")))

    def read_artifact(self, artifact_id: str) -> dict[str, Any]:
        index = self._artifact_index()
        entry = dict(index.get("artifacts", {}).get(artifact_id) or {})
        if not entry:
            raise KeyError(artifact_id)
        path = (self.root / str(entry["relative_path"])).resolve()
        if not _is_within(path, self.root.resolve()):
            raise ValueError("artifact path escapes runtime root")
        ref = public_artifact_ref(entry)
        if entry["media_type"] == "application/json":
            payload = read_json(path)
            reject_unsafe_payload(payload)
            return {**ref, "payload": payload}
        text = _read_text(path, encoding="utf-8")
        reject_unsafe_text(text)
        return {**ref, "text": text}

    def _artifact_index(self) -> dict[str, Any]:
        try:
            index = read_json(self.index_path)
        except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
            index = {}
        artifacts = index.get("artifacts")
        if not isinstance(artifacts, dict):
            index["artifacts"] = {}
        return index


def read_json(path: Path) -> dict[str, Any]:
    json_path = Path(path)
    payload = json.loads(_read_text(json_path, encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{json_path.name} must be a JSON object")
    return payload


def public_job(job: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in job.items() if not key.startswith("_")}


def public_artifact_ref(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_id": entry["artifact_id"],
        "artifact_type": entry["artifact_type"],
        "filename": entry["filename"],
        "role": entry["role"],
        "media_type": entry["media_type"],
    }


def project_summary(manifest: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    return {
        "project_id": manifest["project_id"],
        "project_type": manifest["project_type"],
        "goal": manifest["goal"],
        "status": manifest["status"],
        "run_count": len(manifest.get("runs", [])),
        "package_count": len(manifest.get("packages", [])),
        "feedback_count": len(manifest.get("feedback_refs", [])),
        "profile_version_count": len(manifest.get("profile_version_refs", [])),
        "content_card_count": len(manifest.get("content_cards", [])) if isinstance(manifest.get("content_cards"), list) else 0,
        "artifact": artifact,
    }


def safe_id(value: str) -> str:
    cleaned = SAFE_ID_PATTERN.sub("-", str(value).strip()).strip("-._")
    return cleaned or "item"


def reject_unsafe_payload(payload: dict[str, Any]) -> None:
    reject_unsafe_text(json.dumps(payload, ensure_ascii=False))


def reject_unsafe_text(value: str) -> None:
    lowered = value.lower()
    for fragment in AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS:
        if fragment.lower() in lowered:
            raise ValueError("artifact contains private path, media ref, or secret-like fragment")


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _path_exists(path: Path) -> bool:
    return os.path.exists(system_path(path))


def _read_text(path: Path, *, encoding: str) -> str:
    with open(system_path(path), encoding=encoding) as handle:
        return handle.read()


def _project_id_from_artifact_relative_path(relative_path: str) -> str:
    parts = [part for part in str(relative_path or "").replace("\\", "/").split("/") if part]
    if len(parts) >= 2 and parts[0] in {"projects", "runs", "feedback"}:
        return safe_id(parts[1])
    return ""


__all__ = (
    "RuntimeStore",
    "project_summary",
    "public_job",
    "read_json",
    "safe_id",
)
