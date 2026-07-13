from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.image_utils import image_dimensions
from apps.api.runtime_image_assets import public_reusable_image_asset
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


SAFE_SOURCE_JOB_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
SAFE_SOURCE_CANDIDATE_ID = re.compile(r"^candidate_\d{3}$")
REUSABLE_IMAGE_ASSET_STATUSES = frozenset({"succeeded", "failed", "retryable"})


def register_generated_image_asset(
    store: RuntimeStore,
    project_id: str,
    *,
    source_node_id: str | None,
    source_job_id: str,
    source_candidate_id: str,
    image_path: Path,
    source_candidate_digest: str | None = None,
    source_candidate_status: str = "succeeded",
) -> dict[str, Any]:
    root = store.root.resolve()
    resolved = Path(image_path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("generated image asset must stay inside runtime root") from exc
    if not resolved.is_file():
        raise ValueError("generated image asset is missing")

    normalized_job_id = _source_job_id(source_job_id)
    normalized_candidate_id = _source_candidate_id(source_candidate_id)
    normalized_status = str(source_candidate_status or "").strip().lower()
    if normalized_status not in REUSABLE_IMAGE_ASSET_STATUSES:
        raise ValueError("generated image asset status is invalid")
    if normalized_status != "succeeded":
        raise ValueError("only succeeded generated image assets are reusable")

    image_bytes = resolved.read_bytes()
    suffix, mime_type = _image_kind(image_bytes)
    dimensions = image_dimensions(image_bytes)
    if not dimensions:
        raise ValueError("generated image asset dimensions are required")
    candidate_digest = hashlib.sha256(image_bytes).hexdigest()
    if source_candidate_digest is not None and source_candidate_digest != candidate_digest:
        raise ValueError("source candidate digest does not match generated image bytes")

    existing = _existing_generated_asset(
        store,
        project_id,
        source_job_id=normalized_job_id,
        source_candidate_id=normalized_candidate_id,
    )
    if existing:
        metadata, metadata_path = existing
        if metadata.get("sha256") != candidate_digest:
            raise ValueError("existing generated image asset digest does not match candidate bytes")
        expected_authority = {
            "status": normalized_status,
            "source_candidate_digest": candidate_digest,
        }
        for field, expected in expected_authority.items():
            existing_value = metadata.get(field)
            if existing_value not in {None, expected}:
                raise ValueError(f"existing generated image asset {field} is inconsistent")
            metadata[field] = expected
        reject_unsafe_payload(metadata)
        write_json(metadata_path, metadata)
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
        status=normalized_status,
        filename=resolved.name,
        image_bytes=image_bytes,
        mime_type=mime_type,
        dimensions=dimensions,
    )
    metadata_path = asset_dir / "image_asset.json"
    reject_unsafe_payload(metadata)
    write_json(metadata_path, metadata)
    artifact = store.register_artifact(metadata_path, role="image_asset_metadata")
    return {"asset": public_reusable_image_asset(metadata), "artifact": artifact}


def _existing_generated_asset(
    store: RuntimeStore,
    project_id: str,
    *,
    source_job_id: str,
    source_candidate_id: str,
) -> tuple[dict[str, Any], Path] | None:
    image_assets_dir = store.projects_dir / safe_id(project_id) / "image_assets"
    if not image_assets_dir.is_dir():
        return None
    expected_job_id = safe_id(source_job_id)
    expected_candidate_id = safe_id(source_candidate_id)
    for metadata_path in sorted(image_assets_dir.glob("*/image_asset.json")):
        metadata = read_json(metadata_path)
        if metadata.get("source_kind") != "keyframe_candidate":
            continue
        if metadata.get("source_job_id") != expected_job_id:
            continue
        if metadata.get("source_candidate_id") != expected_candidate_id:
            continue
        reject_unsafe_payload(metadata)
        return metadata, metadata_path
    return None


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


__all__ = ("register_generated_image_asset",)
