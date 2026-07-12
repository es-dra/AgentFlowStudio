from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from agentflow.algorithms.fixed_asset_memory import (
    VISUAL_ASSET_SCHEMA_VERSION,
    build_visual_asset_record,
    clean_feature_card,
    clean_locks,
    clean_refs,
    fixed_context_assets,
    public_review,
    public_visual_asset as project_visual_asset,
    public_visual_asset_detail as project_visual_asset_detail,
)
from agentflow.harness.json_io import write_json
from apps.api.runtime_errors import safe_error_detail
from apps.api.runtime_image_assets import image_asset_metadata
from apps.api.runtime_models import VisualAssetPromoteRequest, VisualAssetRetireRequest
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


VISUAL_ASSET_STATUSES = {"fixed", "rejected", "retired"}


def register_runtime_visual_asset_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/visual-assets/promote")
    def promote_visual_asset(project_id: str, request: VisualAssetPromoteRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        try:
            record, warnings = create_visual_asset(store, project_id, request)
            artifact = store.register_artifact(_visual_asset_path(store, project_id, record["asset_id"]), role="visual_asset")
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_visual_asset")) from exc
        return {"asset": public_visual_asset(record), "warnings": warnings, "artifact": artifact}

    @app.post("/projects/{project_id}/visual-assets/{asset_id}/retire")
    def retire_visual_asset(project_id: str, asset_id: str, request: VisualAssetRetireRequest) -> dict[str, Any]:
        try:
            record = retire_fixed_visual_asset(store, project_id, asset_id, request)
            artifact = store.register_artifact(_visual_asset_path(store, project_id, asset_id), role="visual_asset")
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_visual_asset")) from exc
        return {"asset": public_visual_asset(record), "artifact": artifact}

    @app.get("/projects/{project_id}/visual-assets")
    def get_visual_assets(project_id: str, status: str = "fixed") -> dict[str, Any]:
        if status not in VISUAL_ASSET_STATUSES:
            raise HTTPException(status_code=422, detail="status must be fixed, rejected, or retired")
        assets = [public_visual_asset(item) for item in list_visual_assets(store, project_id, status=status)]
        return {"project_id": project_id, "status": status, "assets": assets}

    @app.get("/projects/{project_id}/visual-assets/{asset_id}")
    def get_visual_asset(project_id: str, asset_id: str) -> dict[str, Any]:
        try:
            record = visual_asset_record(store, project_id, asset_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="visual asset not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=safe_error_detail("invalid_visual_asset")) from exc
        return {"project_id": project_id, "asset": public_visual_asset_detail(record)}


def create_visual_asset(
    store: RuntimeStore,
    project_id: str,
    request: VisualAssetPromoteRequest,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    _validate_promote_request(store, project_id, request)
    duplicates = _matching_fixed_visual_assets(store, project_id, request.asset_type, request.label)
    warnings = _duplicate_label_warnings(duplicates, request.asset_type, request.label, request.reuse_intent)
    if request.review_decision == "fixed" and request.reuse_intent == "link_existing":
        linked_id = str(request.link_existing_asset_id or "").strip()
        linked = next((item for item in duplicates if str(item.get("asset_id") or "") == linked_id), None)
        if not linked:
            raise ValueError("link_existing_asset_id must match an existing fixed asset")
        return linked, warnings
    asset_id = f"vas_{uuid4().hex[:12]}"
    record = build_visual_asset_record(
        project_id=project_id,
        asset_id=asset_id,
        request=request,
        created_at=_server_now(),
        server_recorded_at=_server_now(),
    )
    reject_unsafe_payload(record)
    path = _visual_asset_path(store, project_id, asset_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, record)
    return record, warnings


def retire_fixed_visual_asset(
    store: RuntimeStore,
    project_id: str,
    asset_id: str,
    request: VisualAssetRetireRequest,
) -> dict[str, Any]:
    record = visual_asset_record(store, project_id, asset_id)
    if record.get("status") != "fixed":
        raise ValueError("only fixed visual assets can be retired")
    record["status"] = "retired"
    record["retirement_review"] = {
        "reason": request.reason.strip(),
        "retired_at": request.retired_at,
        "server_recorded_at": _server_now(),
    }
    reject_unsafe_payload(record)
    write_json(_visual_asset_path(store, project_id, asset_id), record)
    return record


def list_visual_assets(store: RuntimeStore, project_id: str, *, status: str = "fixed") -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []
    for path in sorted(_visual_assets_dir(store, project_id).glob("*/visual_asset.json")):
        record = read_json(path)
        reject_unsafe_payload(record)
        if record.get("status") == status:
            assets.append(record)
    return assets


def visual_asset_record(store: RuntimeStore, project_id: str, asset_id: str) -> dict[str, Any]:
    path = _visual_asset_path(store, project_id, asset_id).resolve()
    root = store.root.resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("visual asset path escapes runtime root") from exc
    if not path.is_file():
        raise KeyError(asset_id)
    record = read_json(path)
    reject_unsafe_payload(record)
    return record


def fixed_visual_assets_by_id(store: RuntimeStore, project_id: str) -> dict[str, dict[str, Any]]:
    return fixed_context_assets({str(item["asset_id"]): item for item in list_visual_assets(store, project_id, status="fixed")})


def public_visual_asset(record: dict[str, Any]) -> dict[str, Any]:
    return project_visual_asset(record)


def public_visual_asset_detail(record: dict[str, Any]) -> dict[str, Any]:
    return project_visual_asset_detail(record)


def _public_review(value: Any) -> dict[str, Any] | None:
    return public_review(value)


def _validate_promote_request(store: RuntimeStore, project_id: str, request: VisualAssetPromoteRequest) -> None:
    if not request.signature.strip():
        raise ValueError("signature is required")
    if not clean_feature_card(request.feature_card):
        raise ValueError("feature_card must contain at least one item")
    refs = clean_refs(request.source_image_asset_refs)
    if not refs:
        raise ValueError("source_image_asset_refs is required")
    for asset_id in refs:
        image_asset_metadata(store, project_id, asset_id)
    if request.supersedes_asset_id:
        visual_asset_record(store, project_id, request.supersedes_asset_id.strip())
    if request.link_existing_asset_id:
        visual_asset_record(store, project_id, request.link_existing_asset_id.strip())
    if request.review_decision != "fixed":
        return
    duplicates = _matching_fixed_visual_assets(store, project_id, request.asset_type, request.label)
    if not duplicates:
        return
    if request.reuse_intent not in {"link_existing", "replace", "create_new"}:
        raise ValueError("reuse_intent is required when a fixed visual asset duplicate exists")
    duplicate_ids = {str(item.get("asset_id") or "") for item in duplicates}
    if request.reuse_intent == "link_existing" and str(request.link_existing_asset_id or "").strip() not in duplicate_ids:
        raise ValueError("link_existing_asset_id must match an existing fixed asset duplicate")
    if request.reuse_intent == "replace" and str(request.supersedes_asset_id or "").strip() not in duplicate_ids:
        raise ValueError("supersedes_asset_id must match an existing fixed asset duplicate")


def _matching_fixed_visual_assets(
    store: RuntimeStore,
    project_id: str,
    asset_type: str,
    label: str,
) -> list[dict[str, Any]]:
    return [
        item
        for item in list_visual_assets(store, project_id, status="fixed")
        if item.get("asset_type") == asset_type and str(item.get("label") or "").casefold() == label.strip().casefold()
    ]


def _duplicate_label_warnings(
    duplicates: list[dict[str, Any]],
    asset_type: str,
    label: str,
    reuse_intent: str | None = None,
) -> list[dict[str, Any]]:
    if not duplicates:
        return []
    return [
        {
            "warning_id": "duplicate_visual_asset_label",
            "warning_code": "fixed_asset_reuse_intent_recorded" if reuse_intent else "fixed_asset_reuse_intent_required",
            "asset_type": asset_type,
            "label": label.strip(),
            "existing_asset_ids": ",".join(str(item.get("asset_id")) for item in duplicates),
            "existing_assets": [
                {
                    "asset_id": str(item.get("asset_id") or ""),
                    "asset_type": str(item.get("asset_type") or ""),
                    "label": str(item.get("label") or ""),
                    "status": str(item.get("status") or ""),
                }
                for item in duplicates[:8]
            ],
            "required_intents": ["link_existing", "replace", "create_new"],
            "reuse_intent": reuse_intent or "",
        }
    ]


def _clean_refs(values: list[str]) -> list[str]:
    return clean_refs(values)


def _clean_feature_card(value: dict[str, Any]) -> dict[str, Any]:
    return clean_feature_card(value)


def _clean_locks(values: list[str]) -> list[str]:
    return clean_locks(values)


def _server_now() -> str:
    return datetime.now(UTC).isoformat()


def _visual_assets_dir(store: RuntimeStore, project_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "visual_assets"


def _visual_asset_path(store: RuntimeStore, project_id: str, asset_id: str) -> Path:
    return _visual_assets_dir(store, project_id) / safe_id(asset_id) / "visual_asset.json"


__all__ = (
    "fixed_visual_assets_by_id",
    "list_visual_assets",
    "public_visual_asset",
    "public_visual_asset_detail",
    "register_runtime_visual_asset_routes",
    "visual_asset_record",
)
