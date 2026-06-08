from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentflow.contracts.project_manifest import validate_project_manifest
from agentflow.harness.constants import AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
from agentflow.memory.production_loop import SCHEMA_VERSION
from agentflow_studio.utils import write_json


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

    def project_manifest_path(self, project_id: str) -> Path:
        safe = safe_id(project_id)
        return self.projects_dir / safe / "project_manifest.json"

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

    def register_artifact(self, path: Path, *, role: str) -> dict[str, Any]:
        resolved = Path(path).resolve()
        if not resolved.exists():
            raise FileNotFoundError(str(path))
        artifact_id = safe_id(str(resolved.relative_to(self.root.resolve()).with_suffix("")))
        payload = read_json(resolved) if resolved.suffix.lower() == ".json" else None
        artifact_type = str((payload or {}).get("artifact_type") or (payload or {}).get("kind") or "text_artifact")
        entry = {
            "artifact_id": artifact_id,
            "relative_path": resolved.relative_to(self.root.resolve()).as_posix(),
            "filename": resolved.name,
            "artifact_type": artifact_type,
            "role": role,
            "media_type": "application/json" if resolved.suffix.lower() == ".json" else "text/markdown",
        }
        index = read_json(self.index_path)
        index.setdefault("artifacts", {})[artifact_id] = entry
        write_json(self.index_path, index)
        return public_artifact_ref(entry)

    def read_artifact(self, artifact_id: str) -> dict[str, Any]:
        index = read_json(self.index_path)
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
        text = path.read_text(encoding="utf-8")
        reject_unsafe_text(text)
        return {**ref, "text": text}


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"{Path(path).name} must be a JSON object")
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


def runtime_feedback_event(project_id: str, feedback: dict[str, Any], generated_at: str) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_runtime_feedback_event",
        "schema_version": SCHEMA_VERSION,
        "feedback_id": f"runtime-feedback:{project_id}:{uuid4().hex[:12]}",
        "project_id": project_id,
        "generated_at": generated_at,
        "feedback": feedback,
        "feedback_is_memory": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": ["not durable memory", "not human acceptance", "not business validation"],
    }


__all__ = (
    "RuntimeStore",
    "public_job",
    "read_json",
    "runtime_feedback_event",
    "safe_id",
)
