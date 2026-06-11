from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any
from uuid import uuid4

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.minimax_image_runtime import image_dimensions
from apps.api.runtime_image_assets import public_image_asset
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload, safe_id


def register_generated_image_asset(
    store: RuntimeStore,
    project_id: str,
    *,
    source_node_id: str | None,
    source_job_id: str,
    source_candidate_id: str,
    image_path: Path,
) -> dict[str, Any]:
    root = store.root.resolve()
    resolved = Path(image_path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("generated image asset must stay inside runtime root") from exc
    if not resolved.is_file():
        raise ValueError("generated image asset is missing")

    image_bytes = resolved.read_bytes()
    suffix, mime_type = _image_kind(image_bytes)
    dimensions = image_dimensions(image_bytes)
    if not dimensions:
        raise ValueError("generated image asset dimensions are required")

    asset_id = f"img_{uuid4().hex[:12]}"
    asset_dir = store.projects_dir / safe_id(project_id) / "image_assets" / safe_id(asset_id)
    asset_dir.mkdir(parents=True, exist_ok=True)
    (asset_dir / f"source{suffix}").write_bytes(image_bytes)
    metadata = _generated_metadata(
        project_id=project_id,
        asset_id=asset_id,
        source_node_id=source_node_id,
        source_job_id=source_job_id,
        source_candidate_id=source_candidate_id,
        filename=resolved.name,
        image_bytes=image_bytes,
        mime_type=mime_type,
        dimensions=dimensions,
    )
    metadata_path = asset_dir / "image_asset.json"
    reject_unsafe_payload(metadata)
    write_json(metadata_path, metadata)
    artifact = store.register_artifact(metadata_path, role="image_asset_metadata")
    return {"asset": public_image_asset(metadata), "artifact": artifact}


def _generated_metadata(
    *,
    project_id: str,
    asset_id: str,
    source_node_id: str | None,
    source_job_id: str,
    source_candidate_id: str,
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
        "preview_url": f"/projects/{safe_id(project_id)}/image-assets/{safe_id(asset_id)}/preview",
        "width": dimensions["width"],
        "height": dimensions["height"],
        "aspect_ratio": dimensions["aspect_ratio"],
        "source_kind": "keyframe_candidate",
        "source_job_id": safe_id(source_job_id),
        "source_candidate_id": safe_id(source_candidate_id),
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


__all__ = ("register_generated_image_asset",)
