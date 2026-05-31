from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
from typing import Any

from narratocut.memory_advantage_demo_015_content import SCENE_ID
from narratocut.utils import write_json


DEMO_ID = "AFS-MEMORY-ADVANTAGE-DEMO-015"
I2V_MANIFEST_NAME = "kling_i2v_smoke_manifest.json"


def build_demo_015_i2v_review(
    package: dict[str, Any],
    run_root: str | Path,
    source_keyframe_path: str | Path,
) -> dict[str, Any]:
    root = Path(run_root)
    videos = [_video_artifact_from_manifest(root, item) for item in package["video_requests"]]
    return {
        "schema_version": "memory_advantage_demo_015_i2v_review.v1",
        "demo_id": DEMO_ID,
        "status": "memory_backed_production_i2v_provider_smoke_succeeded",
        "provider_calls_started": True,
        "writes_long_term_memory": False,
        "source_keyframe": _safe_source_keyframe(source_keyframe_path),
        "same_user_task": _same_user_task(package["generation_projections"]),
        "production_line_contract": {
            "baseline": "stateless generation from the same current task and keyframe",
            "memory_backed": "same current task and keyframe plus asset, scene, and feedback memory reuse",
            "not_a_prompt_length_test": True,
        },
        "video_artifacts": videos,
        "generated_video_count": len(videos),
        "scorecard_rubric": package["scorecard_rubric"],
        "technical_visual_review": "not_reviewed",
        "human_acceptance": "not_reviewed",
        "business_validation": "not_validated",
        "quality_improvement_claim": "not_claimed",
        "decision_rule": package["scorecard_rubric"]["decision_rule"],
        "claim_boundary": "provider_runtime_only_not_creative_quality_or_business_validation",
        "not_claimed": [
            "human_acceptance",
            "creative_quality_validation",
            "business_validation",
            "durable_memory_runtime_behavior",
            "statistically_definitive_memory_advantage",
        ],
    }


def write_demo_015_i2v_review(
    package: dict[str, Any],
    run_root: str | Path,
    source_keyframe_path: str | Path,
) -> tuple[Path, Path]:
    root = Path(run_root)
    review = build_demo_015_i2v_review(package, root, source_keyframe_path)
    review_path = write_json(root / "i2v_review.json", review)
    html_path = root / "i2v_review.html"
    html_path.write_text(render_demo_015_i2v_review_html(review), encoding="utf-8")
    return review_path, html_path


def render_demo_015_i2v_review_html(review: dict[str, Any]) -> str:
    videos = {str(item["lane"]): item for item in review.get("video_artifacts", [])}
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{DEMO_ID} I2V Review</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f7f4; color: #151515; }}
    h1 {{ font-size: 24px; }}
    .boundary {{ padding: 12px; border: 1px solid #bbb; background: #fff; margin-bottom: 20px; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
    .cell {{ background: #fff; border: 1px solid #c9c9c9; padding: 12px; }}
    video {{ width: 100%; max-height: 540px; background: #111; object-fit: contain; }}
    .label {{ font-weight: 700; margin-bottom: 8px; }}
    .path {{ font-size: 12px; color: #555; overflow-wrap: anywhere; }}
  </style>
</head>
<body>
  <h1>{DEMO_ID} Memory-Backed Production I2V Review</h1>
  <div class="boundary">
    <div>Same user task: {_esc(review.get("same_user_task", ""))}</div>
    <div>Provider runtime is not creative quality validation.</div>
    <div>Memory advantage claim: {_esc(review.get("quality_improvement_claim", ""))}</div>
    <div>Human acceptance: {_esc(review.get("human_acceptance", ""))}</div>
    <div>Business validation: {_esc(review.get("business_validation", ""))}</div>
  </div>
  <section class="grid">
    {_lane_cell("Baseline / Stateless", videos.get("baseline", {}))}
    {_lane_cell("Memory-Backed", videos.get("memory_backed", {}))}
  </section>
</body>
</html>
"""


def _video_artifact_from_manifest(root: Path, request: dict[str, Any]) -> dict[str, Any]:
    lane = str(request["lane"])
    manifest_path = root / "live" / lane / SCENE_ID / "i2v" / I2V_MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output = (manifest.get("outputs") or [{}])[0]
    video_ref = str(output.get("video_path") or "")
    return {
        "lane": lane,
        "scene_id": SCENE_ID,
        "production_mode": request["production_mode"],
        "provider": manifest.get("provider"),
        "service_id": manifest.get("service_id"),
        "api_family": manifest.get("api_family"),
        "model": manifest.get("model"),
        "video_path": f"live/{lane}/{SCENE_ID}/i2v/{video_ref}",
        "byte_count": output.get("byte_count"),
        "sha256": output.get("sha256"),
        "provider_url_persisted": output.get("provider_url_persisted") is True,
        "claim_boundary": manifest.get("claim_boundary"),
    }


def _safe_source_keyframe(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    image_bytes = source.read_bytes()
    return {
        "file_name": source.name,
        "path_persisted": False,
        "byte_count": len(image_bytes),
        "sha256": hashlib.sha256(image_bytes).hexdigest(),
    }


def _same_user_task(projections: list[dict[str, Any]]) -> bool:
    return len({str(item.get("user_task") or "") for item in projections}) == 1


def _lane_cell(label: str, video: dict[str, Any]) -> str:
    video_path = str(video.get("video_path") or "")
    video_el = f'<video controls src="{_esc(video_path)}"></video>' if video_path else "<div>Missing video</div>"
    return f"""<div class="cell">
    <div class="label">{_esc(label)}</div>
    {video_el}
    <div class="path">{_esc(video_path)}</div>
  </div>"""


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)
