from __future__ import annotations

import re
from typing import Any, Callable

from apps.api.runtime_store import safe_id


SAFE_GENERATION_PARAM_KEYS = {
    "progressPercent",
    "jobProgress",
    "terminalProgress",
    "candidatePreviewUrls",
}

AUTHORITY_SCHEMA_VERSION = "afs_studio_reusable_asset_authority.v0.1"
SAFE_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$")
SAFE_CANDIDATE_ID_PATTERN = re.compile(r"^candidate_\d{3}$")
SAFE_SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
CANDIDATE_PREVIEW_ROUTE_PATTERN = re.compile(
    r"^/projects/([A-Za-z0-9_.-]+)/keyframe-generations/([A-Za-z0-9_.-]+)/"
    r"candidates/(candidate_\d{3})/preview$"
)
CANDIDATE_PREVIEW_ALIASES = (
    "preview_url",
    "url",
    "previewUrl",
    "image_asset_preview_url",
    "imageAssetPreviewUrl",
)


def sanitize_generation_param(
    key: str,
    value: Any,
    *,
    project_id: str | None,
    preview_url: Callable[..., str],
    text: Callable[[Any, str, int], str],
    number: Callable[[Any, float], float],
) -> Any:
    if key == "progressPercent":
        return max(0, min(100, number(value, 0)))
    if key in {"jobProgress", "terminalProgress"}:
        return _job_progress(value, text=text, number=number)
    if key == "candidatePreviewUrls":
        return _candidate_preview_urls(value, project_id=project_id, preview_url=preview_url, text=text, number=number)
    return None


def _job_progress(
    value: Any,
    *,
    text: Callable[[Any, str, int], str],
    number: Callable[[Any, float], float],
) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {
        "percent": max(0, min(100, number(value.get("percent"), 0))),
        "terminal": bool(value.get("terminal")),
    }
    for key, limit in (("label", 160), ("hint", 240), ("status", 40)):
        safe_text = text(value.get(key), "", limit)
        if safe_text:
            result[key] = safe_text
    return result


def _candidate_preview_urls(
    value: Any,
    *,
    project_id: str | None,
    preview_url: Callable[..., str],
    text: Callable[[Any, str, int], str],
    number: Callable[[Any, float], float],
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    result: list[dict[str, Any]] = []
    for item in value[:12]:
        if isinstance(item, str):
            url = preview_url(item, project_id=project_id)
            if url:
                result.append({"url": url, "preview_url": url})
            continue
        if not isinstance(item, dict):
            continue
        url = preview_url(item.get("url") or item.get("preview_url"), project_id=project_id)
        if not url:
            continue
        preview: dict[str, Any] = {"url": url, "preview_url": url}
        for size_key in ("width", "height"):
            value_number = number(item.get(size_key), 0)
            if value_number > 0:
                preview[size_key] = value_number
        aspect_ratio = text(item.get("aspect_ratio"), "", 20)
        if aspect_ratio:
            preview["aspect_ratio"] = aspect_ratio
        artifact_id = text(item.get("artifact_id"), "", 120)
        if artifact_id:
            preview["artifact_id"] = safe_id(artifact_id)
        candidate_contract = _validated_candidate_contract(
            item,
            url=url,
            project_id=project_id,
            preview_url=preview_url,
        )
        if candidate_contract:
            preview.update(candidate_contract)
        result.append(preview)
    return result


def _validated_candidate_contract(
    item: dict[str, Any],
    *,
    url: str,
    project_id: str | None,
    preview_url: Callable[..., str],
) -> dict[str, Any] | None:
    if not isinstance(project_id, str) or not SAFE_IDENTIFIER_PATTERN.fullmatch(project_id):
        return None
    supplied_routes: list[str] = []
    for alias in CANDIDATE_PREVIEW_ALIASES:
        value = item.get(alias)
        if value is None or value == "":
            continue
        try:
            supplied_route = preview_url(value, project_id=project_id)
        except (TypeError, ValueError):
            return None
        if not supplied_route:
            return None
        supplied_routes.append(supplied_route)
    if not supplied_routes or any(route != url for route in supplied_routes):
        return None
    route = CANDIDATE_PREVIEW_ROUTE_PATTERN.fullmatch(url)
    if not route:
        return None
    route_project_id, route_job_id, route_candidate_id = route.groups()
    candidate_id = _exact_match(item.get("candidate_id"), SAFE_CANDIDATE_ID_PATTERN)
    parent_job_id = _exact_match(item.get("parent_job_id"), SAFE_IDENTIFIER_PATTERN)
    candidate_project_id = _exact_match(item.get("project_id"), SAFE_IDENTIFIER_PATTERN)
    canonical_digest = _exact_match(item.get("canonical_digest"), SAFE_SHA256_PATTERN)
    if (
        candidate_project_id != project_id
        or route_project_id != project_id
        or parent_job_id != route_job_id
        or candidate_id != route_candidate_id
        or not canonical_digest
    ):
        return None

    authority = item.get("reusable_asset_authority")
    if not isinstance(authority, dict):
        return None
    if "schema_version" in authority and authority.get("schema_version") != AUTHORITY_SCHEMA_VERSION:
        return None
    asset_id = _exact_match(authority.get("asset_id"), SAFE_IDENTIFIER_PATTERN)
    source_job_id = _exact_match(authority.get("source_job_id"), SAFE_IDENTIFIER_PATTERN)
    source_candidate_id = _exact_match(authority.get("source_candidate_id"), SAFE_CANDIDATE_ID_PATTERN)
    source_candidate_digest = _exact_match(authority.get("source_candidate_digest"), SAFE_SHA256_PATTERN)
    sha256 = _exact_match(authority.get("sha256"), SAFE_SHA256_PATTERN)
    if (
        not asset_id
        or authority.get("role") != "generated_keyframe_reference"
        or authority.get("source_kind") != "keyframe_candidate"
        or authority.get("status") != "succeeded"
        or source_job_id != parent_job_id
        or source_candidate_id != candidate_id
        or source_candidate_digest != canonical_digest
        or sha256 != canonical_digest
    ):
        return None

    return {
        "candidate_id": candidate_id,
        "canonical_digest": canonical_digest,
        "parent_job_id": parent_job_id,
        "project_id": candidate_project_id,
        "reusable_asset_authority": {
            "schema_version": AUTHORITY_SCHEMA_VERSION,
            "asset_id": asset_id,
            "role": "generated_keyframe_reference",
            "source_kind": "keyframe_candidate",
            "status": "succeeded",
            "source_job_id": source_job_id,
            "source_candidate_id": source_candidate_id,
            "source_candidate_digest": source_candidate_digest,
            "sha256": sha256,
        },
    }


def _exact_match(value: Any, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not pattern.fullmatch(value):
        return ""
    return value
