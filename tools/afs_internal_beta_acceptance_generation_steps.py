from __future__ import annotations

from typing import Any

from tools.afs_internal_beta_acceptance_config import AcceptanceConfig
from tools.afs_internal_beta_acceptance_scope_steps import add_step


def vision_gate_step(client, steps: list[dict[str, Any]], alpha_headers: dict[str, str], image_asset_id: str, config: AcceptanceConfig) -> None:
    response = client.post(
        f"/projects/{config.project_id}/asset-card-drafts",
        json={
            "asset_type": "character",
            "source_image_asset_refs": [image_asset_id],
            "node_id": "image_1",
            "prompt_text": "Summarize the character from this reference image for future continuity.",
            "provider_service_id": "vision_image",
            "generated_at": config.generated_at,
        },
        headers=alpha_headers,
    )
    payload = response.json()
    manifest = payload.get("safe_manifest") or {}
    add_step(
        steps,
        "vision_draft_gate_closed",
        "expected_blocked" if _vision_blocked(payload, manifest, response.status_code) else "failed",
        {"http_status": response.status_code, "job_status": (payload.get("job") or {}).get("status"), "failure_class": manifest.get("failure_class")},
        provider_calls_started=bool(payload.get("provider_calls_started")),
    )


def fixed_assets_not_polluted_step(client, steps: list[dict[str, Any]], alpha_headers: dict[str, str], config: AcceptanceConfig) -> None:
    response = client.get(f"/projects/{config.project_id}/visual-assets", headers=alpha_headers)
    assets = response.json().get("assets") if response.status_code == 200 else []
    add_step(
        steps,
        "fixed_assets_not_polluted",
        "passed" if response.status_code == 200 and assets == [] else "failed",
        {"http_status": response.status_code, "fixed_asset_count": len(assets or [])},
    )


def asset_confirmation_step(client, steps: list[dict[str, Any]], alpha_headers: dict[str, str], image_asset_id: str, config: AcceptanceConfig) -> str:
    response = client.post(
        f"/projects/{config.project_id}/visual-assets/promote",
        json={
            "source_image_asset_refs": [image_asset_id],
            "asset_type": "character",
            "label": "Acceptance Character",
            "signature": "single reference continuity character",
            "feature_card": {"appearance": "minimal deterministic reference"},
            "negative_locks": ["do not change identity"],
            "source_node_id": "image_1",
            "review_decision": "fixed",
            "reviewed_at": config.generated_at,
        },
        headers=alpha_headers,
    )
    payload = response.json()
    asset = payload.get("asset") or {}
    asset_id = str(asset.get("asset_id") or "")
    add_step(
        steps,
        "asset_confirmation",
        "passed" if response.status_code == 200 and asset.get("status") == "fixed" and asset_id else "failed",
        {"http_status": response.status_code, "asset_status": asset.get("status"), "asset_type": asset.get("asset_type")},
    )
    return asset_id


def fixed_asset_context_reuse_step(client, steps: list[dict[str, Any]], alpha_headers: dict[str, str], visual_asset_id: str, config: AcceptanceConfig) -> None:
    response = client.post(
        f"/projects/{config.project_id}/keyframe-generations",
        json={
            "node_id": "keyframe_1",
            "prompt_text": "Create a keyframe preserving the confirmed character identity.",
            "provider_service_id": "codex_image",
            "candidate_count": 1,
            "context_subgraph": {
                "target_node_id": "keyframe_1",
                "nodes": [
                    {"id": "asset_node", "type": "image", "title": "Confirmed character", "visual_asset_ids": [visual_asset_id]},
                    {"id": "keyframe_1", "type": "image", "title": "Generated keyframe"},
                ],
                "edges": [{"from": "asset_node", "to": "keyframe_1", "relation_type": "reference"}],
            },
            "generated_at": config.generated_at,
        },
        headers=alpha_headers,
    )
    payload = response.json()
    included_assets = (payload.get("context_bundle") or {}).get("included_assets") or []
    add_step(steps, "fixed_asset_context_reuse", "passed" if _context_reuse_ok(response.status_code, payload, included_assets) else "failed", {
        "http_status": response.status_code,
        "provider_calls_started": bool(payload.get("provider_calls_started")),
        "included_asset_count": len(included_assets),
        "job_status": (payload.get("job") or {}).get("status"),
    }, provider_calls_started=bool(payload.get("provider_calls_started")))


def feedback_step(client, steps: list[dict[str, Any]], alpha_headers: dict[str, str], config: AcceptanceConfig) -> str:
    response = client.post(
        "/feedback",
        json={"project_id": config.project_id, "feedback": {"rating": 4, "notes": "Use as raw evidence only for the next revision."}, "generated_at": config.generated_at},
        headers=alpha_headers,
    )
    payload = response.json()
    artifact_id = str(payload["artifact"]["artifact_id"])
    add_step(
        steps,
        "feedback_raw_evidence",
        "passed" if _feedback_ok(response.status_code, payload) else "failed",
        {"http_status": response.status_code, "job_action": (payload.get("job") or {}).get("action")},
    )
    return artifact_id


def video_gate_step(client, steps: list[dict[str, Any]], alpha_headers: dict[str, str], health: dict[str, Any], image_asset_id: str, config: AcceptanceConfig) -> None:
    preflight = client.post(
        f"/projects/{config.project_id}/video-generations/preflight",
        json={
            "node_id": "video_1",
            "prompt_text": "Create a short motion test from the confirmed first frame.",
            "provider_service_id": "seedance_i2v",
            "first_frame_image_asset_id": image_asset_id,
            "duration_sec": 5,
            "resolution": "720p",
            "aspect_ratio": "9:16",
            "generated_at": config.generated_at,
        },
        headers=alpha_headers,
    )
    payload = preflight.json()
    video_gate_open = bool((health.get("provider_gates") or {}).get("video"))
    add_step(steps, "video_gate_closed", "passed" if _video_gate_ok(preflight.status_code, payload, video_gate_open) else "failed", {
        "preflight_http_status": preflight.status_code,
        "provider_calls_started": bool(payload.get("provider_calls_started")),
        "video_gate_open": video_gate_open,
    }, provider_calls_started=bool(payload.get("provider_calls_started")))


def _vision_blocked(payload: dict[str, Any], manifest: dict[str, Any], status_code: int) -> bool:
    return status_code == 200 and payload.get("provider_calls_started") is False and payload.get("draft") is None and manifest.get("failure_class") == "remote_vision_gate_closed"


def _context_reuse_ok(status_code: int, payload: dict[str, Any], included_assets: list[Any]) -> bool:
    return status_code == 200 and payload.get("provider_calls_started") is False and len(included_assets) == 1


def _feedback_ok(status_code: int, payload: dict[str, Any]) -> bool:
    return status_code == 200 and (payload.get("job") or {}).get("action") == "record_feedback" and (payload.get("feedback_event") or {}).get("writes_long_term_memory") is not True


def _video_gate_ok(status_code: int, payload: dict[str, Any], video_gate_open: bool) -> bool:
    return status_code == 200 and payload.get("provider_calls_started") is False and video_gate_open is False
