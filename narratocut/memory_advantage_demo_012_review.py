from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from narratocut.memory_advantage_demo_012_content import ASPECT_RATIO, MODEL_NAME
from narratocut.memory_advantage_demo_012_review_html import render_i2v_review_html, render_image_review_html
from narratocut.model_gateway.company_secrets import CompanyProviderSecrets
from narratocut.model_gateway.kling_video_smoke import run_kling_i2v_smoke
from narratocut.model_gateway.minimax_image_smoke import run_minimax_image_smoke
from narratocut.utils import write_json


IMAGE_MANIFEST_NAME = "minimax_image_smoke_manifest.json"
I2V_MANIFEST_NAME = "kling_i2v_smoke_manifest.json"
ImageRunner = Callable[..., dict[str, Any]]
VideoRunner = Callable[..., dict[str, Any]]


def run_i2i_keyframes(
    store: CompanyProviderSecrets,
    package: dict[str, Any],
    run_root: str | Path,
    *,
    subject_reference_image_path: str | Path,
    image_runner: ImageRunner = run_minimax_image_smoke,
    image_service_id: str = "minimax_image",
) -> dict[str, Any]:
    root = Path(run_root)
    reference_path = Path(subject_reference_image_path)
    for request in package["image_requests"]:
        output_dir = root / "live" / str(request["lane"]) / str(request["scene_id"]) / "image"
        image_runner(
            store,
            service_id=image_service_id,
            prompt=str(request["image_prompt"]),
            output_dir=output_dir,
            aspect_ratio=ASPECT_RATIO,
            candidate_count=1,
            model_name_override=MODEL_NAME,
            subject_reference_image_path=reference_path,
            seed=request["seed"],
        )
    review_path, html_path = write_image_review(package, root)
    summary = {
        "schema_version": "memory_advantage_demo_012_image_runtime_summary.v1",
        "demo_id": package["demo_id"],
        "status": "i2i_keyframe_provider_smoke_succeeded",
        "provider_calls_started": True,
        "writes_long_term_memory": False,
        "generated_image_count": len(package["image_requests"]),
        "generated_video_count": 0,
        "review_path": _display_ref(root, review_path),
        "html_path": _display_ref(root, html_path),
        "claim_boundary": "provider_smoke_only_not_creative_quality",
    }
    write_json(root / "image_runtime_summary.json", summary)
    return summary


def build_image_review(package: dict[str, Any], run_root: str | Path) -> dict[str, Any]:
    root = Path(run_root)
    keyframes = [_keyframe_artifact_from_manifest(root, item) for item in package["image_requests"]]
    return {
        "schema_version": "memory_advantage_demo_012_image_review.v1",
        "demo_id": package["demo_id"],
        "status": "i2i_keyframe_provider_smoke_succeeded",
        "provider_calls_started": True,
        "writes_long_term_memory": False,
        "generated_image_count": len(keyframes),
        "generated_video_count": 0,
        "video_route_status": "not_started",
        "keyframe_artifacts": keyframes,
        "creative_quality_review": "not_reviewed",
        "human_acceptance": "asset_reference_only_scene_outputs_not_reviewed",
        "business_validation": "not_validated",
        "quality_improvement_claim": "not_claimed",
        "decision_rule": package["evaluation_rubric"]["decision_rule"],
        "claim_boundary": "provider_smoke_only_not_creative_quality",
    }


def write_image_review(package: dict[str, Any], run_root: str | Path) -> tuple[Path, Path]:
    root = Path(run_root)
    review = build_image_review(package, root)
    review_path = write_json(root / "image_review.json", review)
    html_path = root / "image_review.html"
    html_path.write_text(render_image_review_html(package, review), encoding="utf-8")
    return review_path, html_path


def run_i2v_storyboards(
    store: CompanyProviderSecrets,
    package: dict[str, Any],
    run_root: str | Path,
    *,
    video_runner: VideoRunner = run_kling_i2v_smoke,
    i2v_service_id: str = "kling_i2v",
    duration: str = "5",
    mode: str = "pro",
    poll_interval_sec: float = 5.0,
    max_polls: int = 120,
    transport: str = "httpx",
) -> dict[str, Any]:
    root = Path(run_root)
    for request in package["image_requests"]:
        lane = str(request["lane"])
        scene_id = str(request["scene_id"])
        image_path = root / _keyframe_artifact_from_manifest(root, request)["image_path"]
        output_dir = root / "live" / lane / scene_id / "i2v"
        video_runner(
            store,
            service_id=i2v_service_id,
            prompt=str(_i2v_prompt(request)),
            image_path=image_path,
            output_dir=output_dir,
            duration=duration,
            mode=mode,
            poll_interval_sec=poll_interval_sec,
            max_polls=max_polls,
            transport=transport,
        )
    review_path, html_path = write_i2v_review(package, root)
    summary = {
        "schema_version": "memory_advantage_demo_012_i2v_runtime_summary.v1",
        "demo_id": package["demo_id"],
        "status": "i2v_storyboard_provider_smoke_succeeded",
        "provider_calls_started": True,
        "writes_long_term_memory": False,
        "generated_image_count": len(package["image_requests"]),
        "generated_video_count": len(package["image_requests"]),
        "review_path": _display_ref(root, review_path),
        "html_path": _display_ref(root, html_path),
        "claim_boundary": "provider_smoke_only_not_creative_quality",
    }
    write_json(root / "i2v_runtime_summary.json", summary)
    return summary


def build_i2v_review(package: dict[str, Any], run_root: str | Path) -> dict[str, Any]:
    root = Path(run_root)
    keyframes = [_keyframe_artifact_from_manifest(root, item) for item in package["image_requests"]]
    videos = [_video_artifact_from_manifest(root, item) for item in package["image_requests"]]
    return {
        "schema_version": "memory_advantage_demo_012_i2v_review.v1",
        "demo_id": package["demo_id"],
        "status": "i2v_storyboard_provider_smoke_succeeded",
        "provider_calls_started": True,
        "writes_long_term_memory": False,
        "generated_image_count": len(keyframes),
        "generated_video_count": len(videos),
        "video_route_status": "succeeded",
        "keyframe_artifacts": keyframes,
        "video_artifacts": videos,
        "creative_quality_review": "not_reviewed",
        "human_acceptance": "not_reviewed",
        "business_validation": "not_validated",
        "quality_improvement_claim": "not_claimed",
        "decision_rule": package["evaluation_rubric"]["decision_rule"],
        "claim_boundary": "provider_smoke_only_not_creative_quality",
    }


def write_i2v_review(package: dict[str, Any], run_root: str | Path) -> tuple[Path, Path]:
    root = Path(run_root)
    review = build_i2v_review(package, root)
    review_path = write_json(root / "i2v_review.json", review)
    html_path = root / "i2v_review.html"
    html_path.write_text(render_i2v_review_html(package, review), encoding="utf-8")
    return review_path, html_path


def _keyframe_artifact_from_manifest(root: Path, request: dict[str, Any]) -> dict[str, Any]:
    lane = str(request["lane"])
    scene_id = str(request["scene_id"])
    manifest_path = root / "live" / lane / scene_id / "image" / IMAGE_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output = (manifest.get("outputs") or [{}])[0]
    image_ref = str(output.get("image_path") or "")
    return {
        "lane": lane,
        "scene_id": scene_id,
        "provider": manifest.get("provider"),
        "service_id": manifest.get("service_id"),
        "api_family": manifest.get("api_family"),
        "model": manifest.get("model"),
        "seed": request["seed"],
        "image_path": f"live/{lane}/{scene_id}/image/{image_ref}",
        "byte_count": output.get("byte_count"),
        "sha256": output.get("sha256"),
        "provider_url_persisted": output.get("provider_url_persisted") is True,
        "claim_boundary": manifest.get("claim_boundary"),
    }


def _video_artifact_from_manifest(root: Path, request: dict[str, Any]) -> dict[str, Any]:
    lane = str(request["lane"])
    scene_id = str(request["scene_id"])
    manifest_path = root / "live" / lane / scene_id / "i2v" / I2V_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output = (manifest.get("outputs") or [{}])[0]
    video_ref = str(output.get("video_path") or "")
    return {
        "lane": lane,
        "scene_id": scene_id,
        "provider": manifest.get("provider"),
        "service_id": manifest.get("service_id"),
        "api_family": manifest.get("api_family"),
        "model": manifest.get("model"),
        "video_path": f"live/{lane}/{scene_id}/i2v/{video_ref}",
        "byte_count": output.get("byte_count"),
        "sha256": output.get("sha256"),
        "provider_url_persisted": output.get("provider_url_persisted") is True,
        "claim_boundary": manifest.get("claim_boundary"),
    }


def _i2v_prompt(request: dict[str, Any]) -> str:
    return (
        "Animate this keyframe as a 5 second vertical cinematic shot. "
        f"{request['image_prompt']} Keep identity, wardrobe, hair, and physical motion stable."
    )


def _display_ref(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
