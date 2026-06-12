from __future__ import annotations

import base64
import hashlib
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.minimax_image_runtime import image_dimensions
from apps.api.runtime_models import ImageAssetUploadRequest
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


MAX_UPLOAD_BYTES = 8 * 1024 * 1024
IMAGE_SUFFIX_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def register_runtime_image_asset_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.get("/projects/{project_id}/image-assets", include_in_schema=False)
    def list_project_image_assets(project_id: str) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        return {"project_id": project_id, "assets": list_image_assets(store, project_id)}

    @app.post("/projects/{project_id}/image-assets", include_in_schema=False)
    def upload_image_asset(project_id: str, request: ImageAssetUploadRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        try:
            image_bytes = _decode_image(request.data_base64)
            suffix, mime_type = _image_kind(image_bytes, request.mime_type)
            dimensions = image_dimensions(image_bytes)
            if not dimensions:
                raise ValueError("image dimensions are required")
            asset_id = f"img_{uuid4().hex[:12]}"
            asset_dir = _asset_dir(store, project_id, asset_id)
            asset_dir.mkdir(parents=True, exist_ok=True)
            image_path = asset_dir / f"source{suffix}"
            image_path.write_bytes(image_bytes)
            metadata = _asset_metadata(
                project_id=project_id,
                request=request,
                asset_id=asset_id,
                image_bytes=image_bytes,
                mime_type=mime_type,
                dimensions=dimensions,
            )
            metadata_path = asset_dir / "image_asset.json"
            reject_unsafe_payload(metadata)
            write_json(metadata_path, metadata)
            artifact = store.register_artifact(metadata_path, role="image_asset_metadata")
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {
            "asset": public_image_asset(metadata),
            "artifact": artifact,
            "media_bytes_returned": False,
            "provider_raw_response_stored": False,
        }

    @app.get("/projects/{project_id}/image-assets/{asset_id}/preview", include_in_schema=False)
    def image_asset_preview(project_id: str, asset_id: str) -> FileResponse:
        try:
            path = image_asset_file_path(store, project_id, asset_id)
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=404, detail="image asset not found") from exc
        return FileResponse(
            path,
            media_type=IMAGE_SUFFIX_TYPES[path.suffix.lower()],
            headers={"Cache-Control": "no-store"},
        )


def image_asset_file_path(store: RuntimeStore, project_id: str, asset_id: str) -> Path:
    metadata = image_asset_metadata(store, project_id, asset_id)
    suffix = str(metadata.get("file_suffix") or "")
    if suffix not in IMAGE_SUFFIX_TYPES:
        raise KeyError(asset_id)
    path = (_asset_dir(store, project_id, asset_id) / f"source{suffix}").resolve()
    root = store.root.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("image asset path escapes runtime root") from exc
    if not path.is_file():
        raise KeyError(asset_id)
    return path


def image_asset_metadata(store: RuntimeStore, project_id: str, asset_id: str) -> dict[str, Any]:
    path = (_asset_dir(store, project_id, asset_id) / "image_asset.json").resolve()
    root = store.root.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("image asset metadata escapes runtime root") from exc
    if not path.is_file():
        raise KeyError(asset_id)
    metadata = read_json(path)
    reject_unsafe_payload(metadata)
    return metadata


def list_image_assets(store: RuntimeStore, project_id: str) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    root = store.root.resolve()
    image_assets_dir = (store.projects_dir / safe_id(project_id) / "image_assets").resolve()
    try:
        image_assets_dir.relative_to(root)
    except ValueError as exc:
        raise ValueError("image assets path escapes runtime root") from exc
    if not image_assets_dir.is_dir():
        return []
    for path in sorted(image_assets_dir.glob("*/image_asset.json")):
        metadata = read_json(path)
        reject_unsafe_payload(metadata)
        assets.append(public_image_asset(metadata))
    return assets


def public_image_asset(metadata: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "asset_id": metadata["asset_id"],
        "source_node_id": metadata.get("source_node_id"),
        "role": metadata.get("role"),
        "filename": metadata.get("filename"),
        "mime_type": metadata.get("mime_type"),
        "byte_count": metadata.get("byte_count"),
        "sha256": metadata.get("sha256"),
        "width": metadata.get("width"),
        "height": metadata.get("height"),
        "aspect_ratio": metadata.get("aspect_ratio"),
        "preview_url": metadata.get("preview_url"),
    }
    if metadata.get("source_kind"):
        payload["source_kind"] = metadata.get("source_kind")
    if metadata.get("source_job_id"):
        payload["source_job_id"] = metadata.get("source_job_id")
    if metadata.get("source_candidate_id"):
        payload["source_candidate_id"] = metadata.get("source_candidate_id")
    return payload


def safe_reference_image(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "asset_id": metadata["asset_id"],
        "source_node_id": metadata.get("source_node_id"),
        "role": metadata.get("role"),
        "mime_type": metadata.get("mime_type"),
        "byte_count": metadata.get("byte_count"),
        "sha256": metadata.get("sha256"),
        "width": metadata.get("width"),
        "height": metadata.get("height"),
        "aspect_ratio": metadata.get("aspect_ratio"),
    }


def resolve_reference_images(
    store: RuntimeStore,
    project_id: str,
    asset_refs: list[str],
    *,
    limit: int = 4,
) -> list[dict[str, Any]]:
    images: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_ref in asset_refs:
        asset_id = str(raw_ref or "").strip()
        if not asset_id or asset_id in seen:
            continue
        seen.add(asset_id)
        try:
            metadata = image_asset_metadata(store, project_id, asset_id)
            path = image_asset_file_path(store, project_id, asset_id)
        except (KeyError, ValueError):
            continue
        images.append({"path": path, "public": safe_reference_image(metadata)})
        if len(images) >= limit:
            break
    return images


def _asset_metadata(
    *,
    project_id: str,
    request: ImageAssetUploadRequest,
    asset_id: str,
    image_bytes: bytes,
    mime_type: str,
    dimensions: dict[str, Any],
) -> dict[str, Any]:
    return _image_asset_metadata(
        project_id=project_id,
        asset_id=asset_id,
        source_node_id=request.node_id,
        role=request.role,
        filename=Path(request.filename).name or "upload",
        image_bytes=image_bytes,
        mime_type=mime_type,
        dimensions=dimensions,
        artifact_type="agentflow_uploaded_image_asset",
    )


def _image_asset_metadata(
    *,
    project_id: str,
    asset_id: str,
    source_node_id: str | None,
    role: str,
    filename: str,
    image_bytes: bytes,
    mime_type: str,
    dimensions: dict[str, Any],
    artifact_type: str,
) -> dict[str, Any]:
    return {
        "artifact_type": artifact_type,
        "schema_version": "0.1.0",
        "project_id": project_id,
        "asset_id": asset_id,
        "source_node_id": source_node_id,
        "role": safe_id(role or "reference_image"),
        "filename": Path(filename).name or "image",
        "mime_type": mime_type,
        "file_suffix": _suffix_for_mime(mime_type),
        "byte_count": len(image_bytes),
        "sha256": hashlib.sha256(image_bytes).hexdigest(),
        "preview_url": (
            f"/projects/{safe_id(project_id)}/image-assets/"
            f"{safe_id(asset_id)}/preview"
        ),
        "width": dimensions["width"],
        "height": dimensions["height"],
        "aspect_ratio": dimensions["aspect_ratio"],
        "media_bytes_returned_by_api": False,
        "provider_raw_response_stored": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }


def _decode_image(value: str) -> bytes:
    try:
        image_bytes = base64.b64decode(str(value or ""), validate=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("image upload must be valid base64") from exc
    if not image_bytes:
        raise ValueError("image upload is empty")
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("image upload exceeds the 8MB limit")
    return image_bytes


def _image_kind(image_bytes: bytes, declared_mime: str) -> tuple[str, str]:
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png", "image/png"
    if image_bytes.startswith(b"\xff\xd8"):
        return ".jpg", "image/jpeg"
    if declared_mime.lower() in {"image/png", "image/jpeg", "image/jpg"}:
        raise ValueError("image bytes do not match the declared MIME type")
    raise ValueError("image upload must be PNG or JPEG")


def _suffix_for_mime(mime_type: str) -> str:
    return ".png" if mime_type == "image/png" else ".jpg"


def _asset_dir(store: RuntimeStore, project_id: str, asset_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "image_assets" / safe_id(asset_id)


__all__ = (
    "image_asset_file_path",
    "image_asset_metadata",
    "list_image_assets",
    "public_image_asset",
    "register_runtime_image_asset_routes",
    "resolve_reference_images",
    "safe_reference_image",
)
