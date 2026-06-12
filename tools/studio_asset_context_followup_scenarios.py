from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient


PROJECT_ID = "studio-s1-followup-comparisons"
HAIR_LOCK = "keep black short hair; do not change hair color or hairstyle"
SCAR_LOCK = (
    "keep a small subtle natural scar above the tail of the left eyebrow; "
    "do not enlarge it or turn it into a symbol, makeup, tattoo, or painted mark"
)


def prepare_assets(client: TestClient, args: Any) -> dict[str, Any]:
    character_image = _upload_image(client, args.character_reference, "lin-wan-asset", "character_reference")
    scene_image = _upload_image(client, args.scene_reference, "observatory-asset", "scene_reference")
    return {
        "character_image_asset_id": character_image,
        "scene_image_asset_id": scene_image,
        "character_visual_asset": _promote_character(client, character_image),
        "scene_visual_asset": _promote_scene(client, scene_image),
    }


def run_group2(client: TestClient, args: Any, assets: dict[str, Any]) -> dict[str, Any]:
    response = client.post(
        f"/projects/{PROJECT_ID}/generation-comparisons",
        json={
            "node_id": "target-observatory-shot",
            "prompt_text": "林晚在观测站里抬头看着破碎的穹顶。",
            "optimized_prompt": (
                "A cinematic vertical keyframe: Lin Wan stands inside an abandoned observatory, "
                "looking up at the broken dome above the central telescope base. Cold blue moonlight, "
                "subtle rust details, quiet suspense, realistic film still."
            ),
            "target_platform": "short_video",
            "style": "cinematic realism",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "seed": 260613,
            "provider_service_id": args.provider_service_id,
            "context_subgraph": _context_subgraph(
                target_node_id="target-observatory-shot",
                character_asset_id=assets["character_visual_asset"]["asset_id"],
                scene_asset_id=assets["scene_visual_asset"]["asset_id"],
            ),
            "manual_scores": {},
            "generated_at": "2026-06-12T22:00:00+08:00",
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"group2 comparison failed: {response.status_code} {response.text}")
    payload = response.json()
    return {
        "status": payload["report"]["status"],
        "provider_calls_started": payload["provider_calls_started"],
        "job": payload["job"],
        "artifacts": payload["artifacts"],
        "report": _compact_comparison_report(payload["report"]),
    }


def run_group3(client: TestClient, args: Any, assets: dict[str, Any]) -> dict[str, Any]:
    locked = _run_keyframe(
        client,
        args,
        assets,
        node_id="target-lock-conflict-locked",
        optimized_prompt="林晚染了红色长发站在沙漠里，正面中景，电影感真实照片。",
        temporary_lock_overrides=[],
        seed=260614,
    )
    unlocked = _run_keyframe(
        client,
        args,
        assets,
        node_id="target-lock-conflict-unlocked",
        optimized_prompt="林晚染了红色长发站在沙漠里，正面中景，电影感真实照片。",
        temporary_lock_overrides=[
            {
                "asset_id": assets["character_visual_asset"]["asset_id"],
                "lock_text": HAIR_LOCK,
                "reason": "follow-up comparison arm: test one-run temporary hair lock release",
            }
        ],
        seed=260615,
    )
    status = "blocked" if "blocked" in {locked["status"], unlocked["status"]} else "succeeded"
    return {"status": status, "locked": locked, "temporary_unlocked": unlocked}


def _run_keyframe(
    client: TestClient,
    args: Any,
    assets: dict[str, Any],
    *,
    node_id: str,
    optimized_prompt: str,
    temporary_lock_overrides: list[dict[str, str]],
    seed: int,
) -> dict[str, Any]:
    response = client.post(
        f"/projects/{PROJECT_ID}/keyframe-generations",
        json={
            "node_id": node_id,
            "prompt_text": optimized_prompt,
            "optimized_prompt": optimized_prompt,
            "target_platform": "short_video",
            "style": "cinematic realism",
            "aspect_ratio": "9:16",
            "candidate_count": 1,
            "seed": seed,
            "provider_service_id": args.provider_service_id,
            "context_subgraph": _context_subgraph(
                target_node_id=node_id,
                character_asset_id=assets["character_visual_asset"]["asset_id"],
                scene_asset_id="",
            ),
            "temporary_lock_overrides": temporary_lock_overrides,
            "generated_at": "2026-06-12T22:20:00+08:00",
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"group3 keyframe failed: {response.status_code} {response.text}")
    payload = response.json()
    return {
        "status": payload["safe_manifest"]["status"],
        "provider_calls_started": payload["provider_calls_started"],
        "job": payload["job"],
        "artifact_refs": payload.get("artifacts"),
        "candidate_previews": payload.get("candidate_previews"),
        "reusable_image_assets": payload.get("reusable_image_assets"),
        "context_bundle": _compact_bundle(payload.get("context_bundle")),
        "request_plan_artifact": payload.get("artifacts", {}).get("keyframe_request_plan", {}),
    }


def _upload_image(client: TestClient, image_path: str, node_id: str, role: str) -> str:
    path = Path(image_path)
    response = client.post(
        f"/projects/{PROJECT_ID}/image-assets",
        json={
            "node_id": node_id,
            "filename": path.name,
            "mime_type": _mime_type(path),
            "data_base64": base64.b64encode(path.read_bytes()).decode("ascii"),
            "role": role,
            "generated_at": "2026-06-12T21:55:00+08:00",
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"image upload failed: {response.status_code} {response.text}")
    return str(response.json()["asset"]["asset_id"])


def _promote_character(client: TestClient, image_asset_id: str) -> dict[str, Any]:
    response = client.post(
        f"/projects/{PROJECT_ID}/visual-assets/promote",
        json={
            "source_image_asset_refs": [image_asset_id],
            "asset_type": "character",
            "label": "Lin Wan",
            "signature": "黑色短发、红色风衣、左眉尾有淡色细小疤痕的年轻女性",
            "feature_card": {
                "identity": "young woman detective, calm and alert",
                "hair": "black short bob hair",
                "face": "small subtle natural scar above the tail of the left eyebrow, skin texture, not makeup, tattoo, symbol, or painted mark",
                "wardrobe": "red trench coat",
                "palette": "red coat against cool blue night lighting",
            },
            "negative_locks": [HAIR_LOCK, "keep red trench coat", SCAR_LOCK],
            "source_node_id": "lin-wan-asset",
            "review_decision": "fixed",
            "reviewed_at": "2026-06-12T21:56:00+08:00",
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"character promote failed: {response.status_code} {response.text}")
    return response.json()["asset"]


def _promote_scene(client: TestClient, image_asset_id: str) -> dict[str, Any]:
    response = client.post(
        f"/projects/{PROJECT_ID}/visual-assets/promote",
        json={
            "source_image_asset_refs": [image_asset_id],
            "asset_type": "scene",
            "label": "Observatory Ruin",
            "signature": "青蓝色废弃观测站、中央望远镜基座、破碎穹顶",
            "feature_card": {
                "location": "abandoned observatory interior",
                "layout": "central rusted telescope base, cracked dome overhead, broken west windows",
                "props": "fallen metal stairs, old star charts, puddles on the floor",
                "lighting_mood": "cold blue moonlight, quiet suspense, faint water reflections",
                "palette": "cyan blue, desaturated steel gray, small rust orange accents",
            },
            "negative_locks": [
                "keep the central telescope base visible",
                "keep the broken dome and cold blue moonlight",
                "do not add modern electronic screens",
            ],
            "source_node_id": "observatory-asset",
            "review_decision": "fixed",
            "reviewed_at": "2026-06-12T21:57:00+08:00",
        },
    )
    if response.status_code != 200:
        raise RuntimeError(f"scene promote failed: {response.status_code} {response.text}")
    return response.json()["asset"]


def _context_subgraph(*, target_node_id: str, character_asset_id: str, scene_asset_id: str) -> dict[str, Any]:
    nodes = [
        {"id": target_node_id, "type": "image", "title": "Target shot", "prompt": "follow-up comparison target"},
        {"id": "lin-wan-asset", "type": "image", "title": "Lin Wan fixed character", "prompt": "", "visual_asset_ids": [character_asset_id]},
    ]
    edges = [{"id": "edge-character-target", "from": "lin-wan-asset", "to": target_node_id, "relation_type": "reference"}]
    if scene_asset_id:
        nodes.append({"id": "observatory-asset", "type": "image", "title": "Observatory fixed scene", "prompt": "", "visual_asset_ids": [scene_asset_id]})
        edges.append({"id": "edge-scene-target", "from": "observatory-asset", "to": target_node_id, "relation_type": "reference"})
    return {"target_node_id": target_node_id, "runtime_work_mode": "comparison_qa", "nodes": nodes, "edges": edges}


def _compact_comparison_report(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "arm_definitions": report.get("arm_definitions"),
        "arms": [
            {
                "arm_id": item.get("arm_id"),
                "status": item.get("status"),
                "provider_calls_started": item.get("provider_calls_started") is True,
                "fixed_asset_injection": item.get("fixed_asset_injection") is True,
                "result_refs": item.get("result_refs") or [],
                "subject_reference_asset_id": item.get("subject_reference_asset_id"),
                "reference_image_count": len(item.get("reference_images") or []),
                "context_bundle": _compact_bundle(item.get("context_bundle")),
            }
            for item in report.get("arms", [])
        ],
    }


def _compact_bundle(bundle: Any) -> dict[str, Any] | None:
    if not isinstance(bundle, dict):
        return None
    text = bundle.get("text_channel") if isinstance(bundle.get("text_channel"), dict) else {}
    return {
        "mode": bundle.get("mode"),
        "included_assets": [
            {
                "asset_id": item.get("asset_id"),
                "asset_type": item.get("asset_type"),
                "label": item.get("label"),
                "channel": item.get("channel"),
                "hop": item.get("hop"),
                "relation_type": item.get("relation_type"),
            }
            for item in bundle.get("included_assets", [])
            if isinstance(item, dict)
        ],
        "subject_reference_asset_id": bundle.get("subject_reference_asset_id"),
        "reference_image_channel": bundle.get("reference_image_channel") or [],
        "warnings": bundle.get("warnings") or [],
        "temporary_lock_overrides": bundle.get("temporary_lock_overrides") or [],
        "budget": bundle.get("budget"),
        "text_segment_lengths": {key: len(str(text.get(key) or "")) for key in sorted(text)},
    }


def _mime_type(path: Path) -> str:
    if path.suffix.lower() in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "image/png"
