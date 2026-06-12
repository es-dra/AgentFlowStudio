from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from agentflow.harness.json_io import write_json
from apps.api.runtime_image_assets import image_asset_metadata
from apps.api.runtime_models import VisualAssetPromoteRequest, VisualAssetRetireRequest
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


VISUAL_ASSET_SCHEMA_VERSION = "0.2.0"
VISUAL_ASSET_STATUSES = {"fixed", "rejected", "retired"}


def register_runtime_visual_asset_routes(app: FastAPI, store: RuntimeStore) -> None:
    @app.post("/projects/{project_id}/visual-assets/promote")
    def promote_visual_asset(project_id: str, request: VisualAssetPromoteRequest) -> dict[str, Any]:
        store.ensure_project_manifest(project_id)
        try:
            record, warnings = create_visual_asset(store, project_id, request)
            artifact = store.register_artifact(_visual_asset_path(store, project_id, record["asset_id"]), role="visual_asset")
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"asset": public_visual_asset(record), "warnings": warnings, "artifact": artifact}

    @app.post("/projects/{project_id}/visual-assets/{asset_id}/retire")
    def retire_visual_asset(project_id: str, asset_id: str, request: VisualAssetRetireRequest) -> dict[str, Any]:
        try:
            record = retire_fixed_visual_asset(store, project_id, asset_id, request)
            artifact = store.register_artifact(_visual_asset_path(store, project_id, asset_id), role="visual_asset")
        except (KeyError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"asset": public_visual_asset(record), "artifact": artifact}

    @app.get("/projects/{project_id}/visual-assets")
    def get_visual_assets(project_id: str, status: str = "fixed") -> dict[str, Any]:
        if status not in VISUAL_ASSET_STATUSES:
            raise HTTPException(status_code=422, detail="status must be fixed, rejected, or retired")
        assets = [public_visual_asset(item) for item in list_visual_assets(store, project_id, status=status)]
        return {"project_id": project_id, "status": status, "assets": assets}


def create_visual_asset(
    store: RuntimeStore,
    project_id: str,
    request: VisualAssetPromoteRequest,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    _validate_promote_request(store, project_id, request)
    warnings = _duplicate_label_warnings(store, project_id, request.asset_type, request.label)
    asset_id = f"vas_{uuid4().hex[:12]}"
    record = {
        "artifact_type": "agentflow_visual_asset",
        "schema_version": VISUAL_ASSET_SCHEMA_VERSION,
        "project_id": project_id,
        "asset_id": asset_id,
        "asset_type": request.asset_type,
        "label": request.label.strip(),
        "status": request.review_decision,
        "version": 1,
        "source_node_id": request.source_node_id,
        "supersedes_asset_id": request.supersedes_asset_id.strip() if request.supersedes_asset_id else None,
        "created_at": _server_now(),
        "image_asset_refs": _clean_refs(request.source_image_asset_refs),
        "signature": request.signature.strip(),
        "feature_card": _clean_feature_card(request.feature_card),
        "negative_locks": _clean_locks(request.negative_locks),
        "promotion_review": {
            "action": request.review_decision,
            "reviewed_at": request.reviewed_at,
            "server_recorded_at": _server_now(),
            "human_confirmed": True,
            "claim_boundary": "operator_review_record_not_human_acceptance",
        },
        "claim_boundary": "fixed_asset_runtime_contract_not_provider_validation",
        "safe_fields_only": True,
        "media_bytes_returned_by_api": False,
        "provider_raw_response_stored": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
    }
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
    return {str(item["asset_id"]): item for item in list_visual_assets(store, project_id, status="fixed")}


def public_visual_asset(record: dict[str, Any]) -> dict[str, Any]:
    review = record.get("promotion_review") if isinstance(record.get("promotion_review"), dict) else {}
    retirement = record.get("retirement_review") if isinstance(record.get("retirement_review"), dict) else {}
    payload = {
        "asset_id": record.get("asset_id"),
        "asset_type": record.get("asset_type"),
        "label": record.get("label"),
        "status": record.get("status"),
        "version": record.get("version"),
        "signature": record.get("signature"),
        "image_asset_refs": list(record.get("image_asset_refs") or []),
        "source_node_id": record.get("source_node_id"),
        "supersedes_asset_id": record.get("supersedes_asset_id"),
        "created_at": record.get("created_at"),
        "reviewed_at": review.get("reviewed_at"),
        "server_recorded_at": review.get("server_recorded_at"),
    }
    if retirement:
        payload["retired_at"] = retirement.get("retired_at")
        payload["retirement_server_recorded_at"] = retirement.get("server_recorded_at")
    return payload


def _validate_promote_request(store: RuntimeStore, project_id: str, request: VisualAssetPromoteRequest) -> None:
    if not request.signature.strip():
        raise ValueError("signature is required")
    if not _clean_feature_card(request.feature_card):
        raise ValueError("feature_card must contain at least one item")
    refs = _clean_refs(request.source_image_asset_refs)
    if not refs:
        raise ValueError("source_image_asset_refs is required")
    for asset_id in refs:
        image_asset_metadata(store, project_id, asset_id)
    if request.supersedes_asset_id:
        visual_asset_record(store, project_id, request.supersedes_asset_id.strip())


def _duplicate_label_warnings(
    store: RuntimeStore,
    project_id: str,
    asset_type: str,
    label: str,
) -> list[dict[str, str]]:
    duplicates = [
        item
        for item in list_visual_assets(store, project_id, status="fixed")
        if item.get("asset_type") == asset_type and str(item.get("label") or "").casefold() == label.strip().casefold()
    ]
    if not duplicates:
        return []
    return [
        {
            "warning_id": "duplicate_visual_asset_label",
            "asset_type": asset_type,
            "label": label.strip(),
            "existing_asset_ids": ",".join(str(item.get("asset_id")) for item in duplicates),
        }
    ]


def _clean_refs(values: list[str]) -> list[str]:
    refs: list[str] = []
    for value in values:
        ref = str(value or "").strip()
        if ref and ref not in refs:
            refs.append(ref)
    return refs


def _clean_feature_card(value: dict[str, Any]) -> dict[str, Any]:
    return {str(key): item for key, item in value.items() if str(key).strip() and item not in (None, "", [], {})}


def _clean_locks(values: list[str]) -> list[str]:
    locks: list[str] = []
    for value in values:
        lock = str(value or "").strip()
        if lock and lock not in locks:
            locks.append(lock)
    return locks[:24]


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
    "register_runtime_visual_asset_routes",
    "visual_asset_record",
)
