from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.image_utils import image_dimensions
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


SAFE_SOURCE_JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SAFE_SOURCE_CANDIDATE_ID = re.compile(r"^candidate_\d{3}$")
REUSABLE_IMAGE_ASSET_STATUSES = frozenset({"succeeded", "failed", "retryable"})
CANDIDATE_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")


def register_generated_image_asset(
    store: RuntimeStore,
    project_id: str,
    *,
    source_node_id: str | None,
    source_job_id: str,
    source_candidate_id: str,
    image_path: Path,
    source_candidate_digest: str | None = None,
    source_candidate_status: str | None = None,
) -> dict[str, Any]:
    authority = resolve_generated_candidate_authority(
        store,
        project_id,
        source_job_id=source_job_id,
        source_candidate_id=source_candidate_id,
        authority_records=[
            {
                "candidate_id": source_candidate_id,
                "status": source_candidate_status,
                "source_candidate_digest": source_candidate_digest,
            }
        ],
        image_path=image_path,
    )
    normalized_job_id = authority["source_job_id"]
    normalized_candidate_id = authority["source_candidate_id"]
    candidate_digest = authority["sha256"]
    image_bytes = authority["image_bytes"]
    dimensions = authority["dimensions"]
    resolved = authority["candidate_path"]
    suffix, mime_type = _image_kind(image_bytes)
    existing = authority.get("existing")
    if existing:
        metadata, metadata_path = existing
        from apps.api.runtime_image_assets import public_reusable_image_asset

        artifact = store.register_artifact(metadata_path, role="image_asset_metadata")
        return {"asset": public_reusable_image_asset(metadata), "artifact": artifact}

    asset_id = _generated_asset_id(normalized_job_id, normalized_candidate_id)
    asset_dir = store.projects_dir / safe_id(project_id) / "image_assets" / safe_id(asset_id)
    asset_dir.mkdir(parents=True, exist_ok=True)
    (asset_dir / f"source{suffix}").write_bytes(image_bytes)
    metadata = _generated_metadata(
        project_id=project_id,
        asset_id=asset_id,
        source_node_id=source_node_id,
        source_job_id=normalized_job_id,
        source_candidate_id=normalized_candidate_id,
        source_candidate_digest=candidate_digest,
        status="succeeded",
        filename=resolved.name,
        image_bytes=image_bytes,
        mime_type=mime_type,
        dimensions=dimensions,
    )
    metadata_path = asset_dir / "image_asset.json"
    reject_unsafe_payload(metadata)
    write_json(metadata_path, metadata)
    authority = resolve_generated_candidate_authority(
        store,
        project_id,
        source_job_id=normalized_job_id,
        source_candidate_id=normalized_candidate_id,
        require_existing_asset=True,
    )
    metadata, metadata_path = authority["existing"]
    from apps.api.runtime_image_assets import public_reusable_image_asset

    artifact = store.register_artifact(metadata_path, role="image_asset_metadata")
    return {"asset": public_reusable_image_asset(metadata), "artifact": artifact}


def resolve_generated_candidate_authority(
    store: RuntimeStore,
    project_id: str,
    *,
    source_job_id: str,
    source_candidate_id: str,
    authority_records: list[dict[str, Any]] | None = None,
    image_path: Path | None = None,
    require_existing_asset: bool = False,
) -> dict[str, Any]:
    if safe_id(project_id) != project_id:
        raise ValueError("project id must already be normalized")
    normalized_job_id = _source_job_id(source_job_id)
    normalized_candidate_id = _source_candidate_id(source_candidate_id)
    output_dir = store.run_dir(project_id, normalized_job_id).resolve()
    root = store.root.resolve()
    try:
        output_dir.relative_to(root)
    except ValueError as exc:
        raise ValueError("candidate output directory escapes runtime root") from exc
    candidate_paths = [
        path.resolve()
        for suffix in CANDIDATE_IMAGE_SUFFIXES
        if (path := output_dir / "image_candidates" / f"{normalized_candidate_id}{suffix}").is_file()
    ]
    if len(candidate_paths) != 1:
        raise ValueError("candidate authority requires one canonical candidate file")
    candidate_path = candidate_paths[0]
    candidate_path.relative_to(root)
    if image_path is not None and Path(image_path).resolve() != candidate_path:
        raise ValueError("generated image path is not the canonical candidate path")
    image_bytes = candidate_path.read_bytes()
    suffix, mime_type = _image_kind(image_bytes)
    dimensions = image_dimensions(image_bytes)
    if not dimensions:
        raise ValueError("generated image asset dimensions are required")
    candidate_digest = hashlib.sha256(image_bytes).hexdigest()

    existing_matches = _matching_generated_assets(
        store,
        project_id,
        source_job_id=normalized_job_id,
        source_candidate_id=normalized_candidate_id,
    )
    if len(existing_matches) > 1:
        raise ValueError("generated candidate authority metadata must be unique")
    if require_existing_asset and len(existing_matches) != 1:
        raise ValueError("generated candidate authority metadata is missing")
    existing = existing_matches[0] if existing_matches else None

    if authority_records is not None:
        matching_records = [
            item
            for item in authority_records
            if isinstance(item, dict) and item.get("candidate_id") == normalized_candidate_id
        ]
        if len(matching_records) != 1:
            raise ValueError("candidate authority record must be unique")
        candidate_status = matching_records[0].get("status")
        declared_digest = matching_records[0].get("source_candidate_digest")
    elif existing:
        candidate_status = existing[0].get("status")
        declared_digest = existing[0].get("source_candidate_digest")
    else:
        raise ValueError("candidate authority record is missing")
    if not isinstance(candidate_status, str) or candidate_status not in REUSABLE_IMAGE_ASSET_STATUSES:
        raise ValueError("generated image asset status is invalid")
    if candidate_status != "succeeded":
        raise ValueError("only succeeded generated image assets are reusable")
    if declared_digest is not None:
        if not isinstance(declared_digest, str) or not re.fullmatch(r"[a-f0-9]{64}", declared_digest):
            raise ValueError("source candidate digest is invalid")
        if declared_digest != candidate_digest:
            raise ValueError("source candidate digest does not match generated image bytes")

    stored_path = None
    if existing:
        stored_path = _validate_existing_authority(
            store,
            project_id,
            normalized_job_id,
            normalized_candidate_id,
            candidate_digest,
            existing,
        )
    return {
        "project_id": project_id,
        "source_job_id": normalized_job_id,
        "source_candidate_id": normalized_candidate_id,
        "status": "succeeded",
        "candidate_path": candidate_path,
        "stored_path": stored_path,
        "image_bytes": image_bytes,
        "sha256": candidate_digest,
        "mime_type": mime_type,
        "suffix": suffix,
        "dimensions": dimensions,
        "existing": existing,
    }


def _matching_generated_assets(
    store: RuntimeStore,
    project_id: str,
    *,
    source_job_id: str,
    source_candidate_id: str,
) -> list[tuple[dict[str, Any], Path]]:
    image_assets_dir = store.projects_dir / safe_id(project_id) / "image_assets"
    if not image_assets_dir.is_dir():
        return []
    matches: list[tuple[dict[str, Any], Path]] = []
    for metadata_path in sorted(image_assets_dir.glob("*/image_asset.json")):
        metadata = read_json(metadata_path)
        if metadata.get("source_kind") != "keyframe_candidate":
            continue
        if metadata.get("source_job_id") != source_job_id:
            continue
        if metadata.get("source_candidate_id") != source_candidate_id:
            continue
        reject_unsafe_payload(metadata)
        matches.append((metadata, metadata_path))
    return matches


def _validate_existing_authority(
    store: RuntimeStore,
    project_id: str,
    source_job_id: str,
    source_candidate_id: str,
    candidate_digest: str,
    existing: tuple[dict[str, Any], Path],
) -> Path:
    metadata, metadata_path = existing
    asset_id = metadata.get("asset_id")
    if not isinstance(asset_id, str) or safe_id(asset_id) != asset_id or metadata_path.parent.name != asset_id:
        raise ValueError("existing generated image asset id is inconsistent")
    if asset_id != _generated_asset_id(source_job_id, source_candidate_id):
        raise ValueError("existing generated image asset id is not deterministic")
    expected = {
        "project_id": project_id,
        "source_kind": "keyframe_candidate",
        "source_job_id": source_job_id,
        "source_candidate_id": source_candidate_id,
        "status": "succeeded",
        "source_candidate_digest": candidate_digest,
        "sha256": candidate_digest,
    }
    for field, value in expected.items():
        if metadata.get(field) != value:
            raise ValueError(f"existing generated image asset {field} is inconsistent")
    suffix = metadata.get("file_suffix")
    if suffix not in {".png", ".jpg"}:
        raise ValueError("existing generated image asset suffix is invalid")
    stored_path = (metadata_path.parent / f"source{suffix}").resolve()
    root = store.root.resolve()
    try:
        stored_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("existing generated image asset path escapes runtime root") from exc
    if not stored_path.is_file():
        raise ValueError("existing generated image asset stored bytes are missing")
    stored_bytes = stored_path.read_bytes()
    if hashlib.sha256(stored_bytes).hexdigest() != candidate_digest:
        raise ValueError("existing generated image asset stored bytes do not match candidate authority")
    if metadata.get("byte_count") != len(stored_bytes):
        raise ValueError("existing generated image asset byte count is inconsistent")
    return stored_path


def _generated_asset_id(source_job_id: str, source_candidate_id: str) -> str:
    seed = f"{source_job_id}:{source_candidate_id}".encode("utf-8")
    return f"img_gen_{hashlib.sha256(seed).hexdigest()[:16]}"


def _generated_metadata(
    *,
    project_id: str,
    asset_id: str,
    source_node_id: str | None,
    source_job_id: str,
    source_candidate_id: str,
    source_candidate_digest: str,
    status: str,
    filename: str,
    image_bytes: bytes,
    mime_type: str,
    dimensions: dict[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_type": "agentflow_generated_image_asset",
        "schema_version": "0.1.0",
        "project_id": project_id,
        "asset_id": asset_id,
        "source_node_id": source_node_id,
        "role": "generated_keyframe_reference",
        "filename": Path(filename).name or "candidate.png",
        "mime_type": mime_type,
        "file_suffix": ".png" if mime_type == "image/png" else ".jpg",
        "byte_count": len(image_bytes),
        "sha256": hashlib.sha256(image_bytes).hexdigest(),
        "source_candidate_digest": source_candidate_digest,
        "status": status,
        "preview_url": f"/projects/{safe_id(project_id)}/image-assets/{safe_id(asset_id)}/preview",
        "width": dimensions["width"],
        "height": dimensions["height"],
        "aspect_ratio": dimensions["aspect_ratio"],
        "source_kind": "keyframe_candidate",
        "source_job_id": source_job_id,
        "source_candidate_id": source_candidate_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "media_bytes_returned_by_api": False,
        "provider_raw_response_stored": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _image_kind(image_bytes: bytes) -> tuple[str, str]:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if image_bytes.startswith(b"\xff\xd8"):
        return ".jpg", "image/jpeg"
    raise ValueError("generated image asset must be PNG or JPEG")


def _source_job_id(value: str) -> str:
    if not isinstance(value, str) or not SAFE_SOURCE_JOB_ID.fullmatch(value):
        raise ValueError("source job id must be a safe runtime identifier")
    if safe_id(value) != value:
        raise ValueError("source job id must already be normalized")
    return value


def _source_candidate_id(value: str) -> str:
    if not isinstance(value, str) or not SAFE_SOURCE_CANDIDATE_ID.fullmatch(value):
        raise ValueError("source candidate id must match candidate_NNN")
    return value


__all__ = ("register_generated_image_asset", "resolve_generated_candidate_authority")
