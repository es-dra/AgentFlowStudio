from __future__ import annotations

from typing import Any


RETRYABLE_ITEM_STATES = ("failed", "timed_out", "blocked", "skipped")
ACTIVE_RUNTIME_STATES = {"submitted", "pending", "running", "retrying"}
COMPLETE_RUNTIME_STATES = {"succeeded", "success", "complete", "completed"}
FAILED_RUNTIME_STATES = {"failed", "poll_failed", "timed_out", "timeout", "cancelled", "cancelled_local_only"}


def annotate_blocks(blocks: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for block in blocks or []:
        if not isinstance(block, dict):
            continue
        item = dict(block)
        item.setdefault("failure_class", failure_class_for_block(item))
        annotated.append(item)
    return annotated


def recovery_manifest_fields(
    *,
    status: str,
    requested_count: int,
    output_count: int,
    blocks: list[dict[str, Any]] | None,
    provider_calls_started: bool,
    retry_count: int = 0,
    stage: str = "",
    capability: str = "",
) -> dict[str, Any]:
    safe_blocks = annotate_blocks(blocks)
    items = batch_items(requested_count=max(1, requested_count), completed_count=max(0, output_count), blocks=safe_blocks)
    batch_status = public_batch_status(
        status=status,
        requested_count=max(1, requested_count),
        output_count=max(0, output_count),
        blocks=safe_blocks,
        provider_calls_started=provider_calls_started,
        retry_count=retry_count,
    )
    return {
        "batch_status": batch_status,
        "stage": stage or stage_for_status(status),
        "failure_class": first_failure_class(safe_blocks, batch_status=batch_status),
        "batch_summary": {
            "requested_count": max(1, requested_count),
            "complete_count": sum(1 for item in items if item["state"] == "complete"),
            "retryable_count": sum(1 for item in items if item["state"] in RETRYABLE_ITEM_STATES),
            "needs_attention_count": sum(1 for item in items if item["state"] != "complete"),
        },
        "retry": retry_metadata(items, retry_count=retry_count),
        "provenance": {
            "capability": capability,
            "raw_response_stored": False,
            "generated_media_bytes_returned": False,
            "safe_artifact_pointers_only": True,
        },
    }


def runtime_recovery_envelope(
    *,
    project_id: str,
    job_id: str,
    capability: str,
    status: str,
    requested_count: int,
    output_count: int,
    blocks: list[dict[str, Any]] | None,
    provider_gate: dict[str, Any],
    provider_calls_started: bool,
    retry_count: int = 0,
    artifacts: dict[str, Any] | None = None,
    candidate_previews: list[dict[str, Any]] | None = None,
    reusable_assets: list[dict[str, Any]] | None = None,
    stage: str = "",
    non_claims: list[str] | None = None,
) -> dict[str, Any]:
    fields = recovery_manifest_fields(
        status=status,
        requested_count=requested_count,
        output_count=output_count,
        blocks=blocks,
        provider_calls_started=provider_calls_started,
        retry_count=retry_count,
        stage=stage,
        capability=capability,
    )
    completed_ids = [str(item.get("candidate_id") or "") for item in candidate_previews or [] if isinstance(item, dict)]
    safe_outputs = reviewable_outputs(
        items=batch_items(
            requested_count=requested_count,
            completed_count=output_count,
            blocks=annotate_blocks(blocks),
            completed_ids=completed_ids,
        ),
        candidate_previews=candidate_previews or [],
        reusable_assets=reusable_assets or [],
    )
    return {
        "schema_version": "afs_runtime_recovery_contract.v0.1",
        "project_id": project_id,
        "job_id": job_id,
        "capability": capability,
        "status": fields["batch_status"],
        "stage": fields["stage"],
        "provider_gate": provider_gate,
        "provider_calls_started": provider_calls_started,
        "safe_artifact_pointers": safe_artifact_pointers(artifacts or {}),
        "outputs": safe_outputs,
        "provenance": fields["provenance"],
        "retry": fields["retry"],
        "review": {
            "state": "partial_result" if fields["batch_status"] == "partially_complete" else "ready_for_review" if fields["batch_status"] == "complete" else "needs_attention",
            "copy": copy_concepts(fields["batch_status"]),
        },
        "non_claims": list(non_claims or []),
    }


def public_batch_status(
    *,
    status: str,
    requested_count: int,
    output_count: int,
    blocks: list[dict[str, Any]] | None,
    provider_calls_started: bool,
    retry_count: int = 0,
) -> str:
    normalized = _normalize_status(status)
    if normalized in ACTIVE_RUNTIME_STATES:
        return "retrying"
    if output_count > 0:
        if normalized in COMPLETE_RUNTIME_STATES and output_count >= requested_count and not blocks:
            return "complete"
        return "partially_complete"
    if normalized in COMPLETE_RUNTIME_STATES and output_count >= requested_count:
        return "complete"
    if normalized == "needs_attention":
        return "needs_attention"
    if normalized == "blocked" and not provider_calls_started:
        return "needs_attention"
    if normalized in FAILED_RUNTIME_STATES or provider_calls_started:
        return "failed"
    if retry_count:
        return "retrying"
    return "needs_attention"


def batch_items(*, requested_count: int, completed_count: int, blocks: list[dict[str, Any]] | None, completed_ids: list[str] | None = None) -> list[dict[str, Any]]:
    requested = max(1, requested_count)
    complete = min(max(0, completed_count), requested)
    completed = {item for item in completed_ids or [] if item}
    fallback_state = item_failure_state(blocks or [])
    items: list[dict[str, Any]] = []
    for index in range(1, requested + 1):
        item_id = f"candidate_{index:03d}"
        state = "complete" if (item_id in completed if completed else index <= complete) else fallback_state
        item: dict[str, Any] = {
            "item_id": item_id,
            "state": state,
            "preserved": state == "complete",
        }
        if state != "complete":
            item["failure_class"] = first_failure_class(blocks or [], batch_status="failed")
        items.append(item)
    return items


def retry_metadata(items: list[dict[str, Any]], *, retry_count: int = 0) -> dict[str, Any]:
    retryable = [item["item_id"] for item in items if item.get("state") in RETRYABLE_ITEM_STATES]
    preserved = [item["item_id"] for item in items if item.get("state") == "complete"]
    return {
        "retry_count": retry_count,
        "default_scope": "failed_items_only",
        "retryable_item_states": list(RETRYABLE_ITEM_STATES),
        "retryable_item_ids": retryable,
        "preserved_item_ids": preserved,
        "preserve_successful_outputs": True,
        "full_batch_rerun": {
            "default": False,
            "requires_explicit_advanced_destructive_option": True,
            "provider_quota_may_be_used": True,
        },
    }


def reviewable_outputs(*, items: list[dict[str, Any]], candidate_previews: list[dict[str, Any]], reusable_assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previews = {str(item.get("candidate_id") or ""): item for item in candidate_previews if isinstance(item, dict)}
    assets = {str(item.get("source_candidate_id") or ""): item for item in reusable_assets if isinstance(item, dict)}
    outputs: list[dict[str, Any]] = []
    for item in items:
        candidate_id = str(item["item_id"])
        payload = dict(item)
        preview = previews.get(candidate_id)
        asset = assets.get(candidate_id)
        if preview:
            payload["preview_url"] = preview.get("preview_url")
            payload["byte_count"] = preview.get("byte_count")
            payload["sha256"] = preview.get("sha256")
        if asset:
            payload["image_asset_id"] = asset.get("asset_id")
            payload["image_asset_preview_url"] = asset.get("preview_url")
        outputs.append(payload)
    return outputs


def safe_artifact_pointers(artifacts: dict[str, Any]) -> list[dict[str, Any]]:
    pointers: list[dict[str, Any]] = []
    for role, artifact in sorted(artifacts.items()):
        if not isinstance(artifact, dict):
            continue
        pointers.append(
            {
                "role": str(role),
                "artifact_id": artifact.get("artifact_id"),
                "artifact_type": artifact.get("artifact_type"),
                "media_type": artifact.get("media_type"),
            }
        )
    return pointers


def failure_class_for_block(block: dict[str, Any]) -> str:
    block_id = str(block.get("block_id") or "").lower()
    reason = str(block.get("reason") or "").lower()
    if "policy" in block_id or "copyright" in reason:
        return "provider_policy_block"
    if "timeout" in block_id or "timed out" in reason or "timeout" in reason:
        return "provider_timeout"
    if "gate_closed" in block_id:
        return "provider_gate_closed"
    if "unsupported" in block_id or "invalid" in block_id or "validation" in block_id:
        return "validation_block"
    if "skipped" in block_id:
        return "skipped"
    if "not_ready" in block_id or "service_not_found" in block_id or "auth_not_ready" in block_id:
        return "provider_not_ready"
    if "missing" in block_id:
        return "provider_output_missing"
    return "provider_failed"


def item_failure_state(blocks: list[dict[str, Any]]) -> str:
    failure_class = first_failure_class(blocks, batch_status="failed")
    if failure_class == "provider_timeout":
        return "timed_out"
    if failure_class in {"provider_gate_closed", "validation_block", "provider_policy_block"}:
        return "blocked"
    if failure_class == "skipped":
        return "skipped"
    return "failed"


def first_failure_class(blocks: list[dict[str, Any]] | None, *, batch_status: str) -> str:
    for block in blocks or []:
        if isinstance(block, dict):
            value = str(block.get("failure_class") or failure_class_for_block(block))
            if value:
                return value
    return "" if batch_status == "complete" else "unknown"


def stage_for_status(status: str) -> str:
    normalized = _normalize_status(status)
    if normalized in ACTIVE_RUNTIME_STATES:
        return "provider_task"
    if normalized in COMPLETE_RUNTIME_STATES:
        return "review"
    if normalized == "blocked":
        return "provider_gate"
    if normalized in FAILED_RUNTIME_STATES:
        return "provider_result"
    return normalized or "unknown"


def copy_concepts(batch_status: str) -> list[str]:
    if batch_status == "complete":
        return ["ready for review", "preserved outputs", "not yet accepted"]
    if batch_status == "partially_complete":
        return ["partial result", "retry failed items", "preserved outputs", "provider quota may be used", "not yet accepted"]
    if batch_status == "retrying":
        return ["retry failed items", "preserved outputs", "provider quota may be used"]
    return ["needs attention", "retry failed items", "provider quota may be used"]


def _normalize_status(status: str) -> str:
    return str(status or "").strip().lower().replace("-", "_")
