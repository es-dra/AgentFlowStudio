from __future__ import annotations

import hashlib
import shutil
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.model_gateway.image_utils import image_dimensions


JOB_ROOT_DIR = "codex_image_job"
REQUEST_FILENAME = "request.json"
RESULT_FILENAME = "result.json"
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def create_handoff_task(plan: dict[str, Any]) -> dict[str, Any]:
    output_dir = Path(plan["output_dir"]).resolve()
    job_id = f"codex_img_{uuid4().hex[:12]}"
    job_root = output_dir / JOB_ROOT_DIR
    staging_dir = job_root / "_staging" / job_id
    pending_dir = job_root / "pending" / job_id
    references = _copy_reference_images(staging_dir, plan.get("reference_image_paths") or [])
    request_payload = {
        "schema_version": "afs_codex_image_request.v0.1",
        "job_id": job_id,
        "service_id": str(plan["service_id"]),
        "capability": "image",
        "prompt": str(plan["prompt"]),
        "aspect_ratio": str(plan.get("aspect_ratio") or "9:16"),
        "candidate_count": 1,
        "seed": plan.get("seed"),
        "reference_images": references,
        "output": {
            "candidate_id": "candidate_001",
            "image_path": "image_candidates/candidate_001.png",
            "result_path": RESULT_FILENAME,
        },
        "media_bytes_returned_by_api": False,
        "provider_raw_response_stored": False,
        "signed_urls_persisted": False,
    }
    write_json(staging_dir / REQUEST_FILENAME, request_payload)
    pending_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir.rename(pending_dir)
    return {
        "status": "submitted",
        "job_id": job_id,
        "output_dir": str(output_dir),
        "relative_job_root": JOB_ROOT_DIR,
        "provider_calls_started": True,
        "provider_raw_response_stored": False,
    }


def poll_handoff_task(task: dict[str, Any]) -> dict[str, Any]:
    output_dir = Path(str(task.get("output_dir") or "")).resolve()
    job_id = _safe_job_id(str(task.get("job_id") or ""))
    if not job_id:
        raise ModelGatewayError("Codex image handoff task is missing job_id")
    job_root = output_dir / JOB_ROOT_DIR
    located = _locate_job_dir(job_root, job_id)
    if located is None:
        raise ModelGatewayError("Codex image handoff job not found")
    state, job_dir = located
    if state in {"pending", "running"}:
        recovered = _completed_running_candidate(output_dir, job_dir, job_id)
        if recovered:
            return recovered
        return {
            "status": "running",
            "job_id": job_id,
            "provider_calls_started": True,
            "provider_raw_response_stored": False,
            "outputs": [],
        }
    result = _read_result(job_dir)
    if state == "failed":
        return {
            "status": "failed",
            "job_id": job_id,
            "provider_calls_started": True,
            "provider_raw_response_stored": False,
            "blocks": result.get("blocks") or [_worker_failed_block()],
            "outputs": [],
        }
    if state != "completed":
        raise ModelGatewayError("Codex image handoff job has an invalid state")
    outputs = _safe_outputs(output_dir, result)
    return {
        "status": "succeeded",
        "job_id": job_id,
        "provider_calls_started": True,
        "provider_raw_response_stored": False,
        "outputs": outputs,
    }


def _completed_running_candidate(output_dir: Path, job_dir: Path, job_id: str) -> dict[str, Any] | None:
    candidate = _running_candidate_path(job_dir)
    if not candidate or time.time() - candidate.stat().st_mtime < 5:
        return None
    target = candidate_output_path(output_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    if candidate.resolve() != target.resolve():
        shutil.copyfile(candidate, target)
    result = completed_result_payload(job_id=job_id, output_dir=output_dir, candidate_path=target)
    write_json(job_dir / RESULT_FILENAME, result)
    return {
        "status": "succeeded",
        "job_id": job_id,
        "provider_calls_started": True,
        "provider_raw_response_stored": False,
        "outputs": _safe_outputs(output_dir, result),
    }


def _running_candidate_path(job_dir: Path) -> Path | None:
    for candidate in (job_dir / "candidate_001.png", job_dir / "image_candidates" / "candidate_001.png"):
        if candidate.is_file() and candidate.stat().st_size > 0:
            return candidate
    return None


def completed_result_payload(*, job_id: str, output_dir: Path, candidate_path: Path) -> dict[str, Any]:
    output_dir = Path(output_dir).resolve()
    candidate_path = Path(candidate_path).resolve()
    image_bytes = candidate_path.read_bytes()
    try:
        image_ref = candidate_path.relative_to(output_dir).as_posix()
    except ValueError as exc:
        raise ModelGatewayError("Codex image candidate escaped output directory") from exc
    return {
        "schema_version": "afs_codex_image_result.v0.1",
        "job_id": _safe_job_id(job_id),
        "status": "succeeded",
        "provider_calls_started": True,
        "provider_raw_response_stored": False,
        "signed_urls_persisted": False,
        "outputs": [
            {
                "candidate_id": "candidate_001",
                "image_path": image_ref,
                "byte_count": len(image_bytes),
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
                **image_dimensions(image_bytes),
                "provider_url_persisted": False,
            }
        ],
    }


def failed_result_payload(*, job_id: str, reason: str) -> dict[str, Any]:
    return {
        "schema_version": "afs_codex_image_result.v0.1",
        "job_id": _safe_job_id(job_id),
        "status": "failed",
        "provider_calls_started": True,
        "provider_raw_response_stored": False,
        "signed_urls_persisted": False,
        "blocks": [_worker_failed_block(reason)],
        "outputs": [],
    }


def candidate_output_path(output_dir: Path) -> Path:
    return Path(output_dir).resolve() / "image_candidates" / "candidate_001.png"


def _copy_reference_images(staging_dir: Path, reference_paths: Any) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    refs_dir = staging_dir / "references"
    for index, raw_path in enumerate(list(reference_paths or [])[:8], start=1):
        source = Path(raw_path).resolve()
        if not source.is_file():
            continue
        suffix = source.suffix.lower()
        if suffix not in IMAGE_SUFFIXES:
            continue
        image_bytes = source.read_bytes()
        target_name = f"reference_{index:03d}{suffix}"
        target = refs_dir / target_name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied.append(
            {
                "ref_id": f"reference_{index:03d}",
                "path": f"references/{target_name}",
                "byte_count": len(image_bytes),
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
            }
        )
    return copied


def _safe_outputs(output_dir: Path, result: dict[str, Any]) -> list[dict[str, Any]]:
    outputs: list[dict[str, Any]] = []
    root = output_dir.resolve()
    for item in result.get("outputs") or []:
        if not isinstance(item, dict):
            continue
        candidate_id = str(item.get("candidate_id") or "")
        if candidate_id != "candidate_001":
            continue
        image_ref = str(item.get("image_path") or "")
        path = (root / image_ref).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        image_bytes = path.read_bytes()
        outputs.append(
            {
                "candidate_id": candidate_id,
                "image_path": path.relative_to(root).as_posix(),
                "byte_count": len(image_bytes),
                "sha256": hashlib.sha256(image_bytes).hexdigest(),
                **image_dimensions(image_bytes),
                "provider_url_persisted": False,
            }
        )
    return outputs


def _locate_job_dir(job_root: Path, job_id: str) -> tuple[str, Path] | None:
    for state in ("completed", "failed", "running", "pending"):
        path = job_root / state / job_id
        if path.is_dir():
            return state, path
    return None


def _read_result(job_dir: Path) -> dict[str, Any]:
    path = job_dir / RESULT_FILENAME
    if not path.is_file():
        raise ModelGatewayError("Codex image handoff result is missing")
    import json

    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ModelGatewayError("Codex image handoff result must be a JSON object")
    return payload


def _safe_job_id(value: str) -> str:
    return "".join(ch for ch in value if ch.isalnum() or ch in {"_", "-"})[:64]


def _worker_failed_block(reason: str = "Image generation worker failed.") -> dict[str, str]:
    return {
        "block_id": "remote_image_provider_not_ready",
        "reason": _safe_error(reason),
        "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
    }


def _safe_error(value: str) -> str:
    lowered = value.lower()
    if any(term in lowered for term in ("api", "key", "secret", "token", "authorization", "cookie")):
        return "Image generation worker configuration is not ready."
    if any(term in lowered for term in ("codex", "handoff", "request.json", "candidate_001")):
        return "Image generation worker failed."
    return " ".join(value.split())[:160] or "Image generation worker failed."


__all__ = (
    "JOB_ROOT_DIR",
    "RESULT_FILENAME",
    "REQUEST_FILENAME",
    "candidate_output_path",
    "completed_result_payload",
    "create_handoff_task",
    "failed_result_payload",
    "poll_handoff_task",
)
