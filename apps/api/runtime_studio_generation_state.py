from __future__ import annotations

from typing import Any, Callable

from apps.api.runtime_store import safe_id


SAFE_GENERATION_PARAM_KEYS = {
    "progressPercent",
    "jobProgress",
    "terminalProgress",
    "candidatePreviewUrls",
}


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
        result.append(preview)
    return result
