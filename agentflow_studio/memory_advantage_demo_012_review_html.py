from __future__ import annotations

import html
from typing import Any


def render_image_review_html(package: dict[str, Any], review: dict[str, Any]) -> str:
    keyframes = {(item["lane"], item["scene_id"]): item for item in review.get("keyframe_artifacts", [])}
    rows = "\n".join(_scene_row(scene, keyframes) for scene in package["scene_stress_tests"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{_esc(package["demo_id"])} I2I Review</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f7f4; color: #151515; }}
    h1 {{ font-size: 24px; }}
    .boundary {{ padding: 12px; border: 1px solid #bbb; background: #fff; margin-bottom: 20px; }}
    .scene {{ display: grid; grid-template-columns: 160px 1fr 1fr; gap: 16px; margin-bottom: 20px; }}
    .cell {{ background: #fff; border: 1px solid #c9c9c9; padding: 12px; }}
    img {{ width: 100%; max-height: 520px; background: #111; object-fit: contain; }}
    .label {{ font-weight: 700; margin-bottom: 8px; }}
    .path {{ font-size: 12px; color: #555; overflow-wrap: anywhere; }}
    .note {{ font-size: 13px; color: #444; }}
  </style>
</head>
<body>
  <h1>{_esc(package["demo_id"])} I2I Keyframe Review</h1>
  <div class="boundary">
    <div>3 scenes x 2 lanes = 6 keyframes.</div>
    <div>Provider smoke is not creative quality validation.</div>
    <div>Memory advantage claim: {_esc(review.get("quality_improvement_claim", ""))}</div>
    <div>Human acceptance: {_esc(review.get("human_acceptance", ""))}</div>
    <div>Business validation: {_esc(review.get("business_validation", ""))}</div>
    <div>Video route: {_esc(review.get("video_route_status", ""))}</div>
  </div>
  {rows}
</body>
</html>
"""


def render_i2v_review_html(package: dict[str, Any], review: dict[str, Any]) -> str:
    keyframes = {(item["lane"], item["scene_id"]): item for item in review.get("keyframe_artifacts", [])}
    videos = {(item["lane"], item["scene_id"]): item for item in review.get("video_artifacts", [])}
    rows = "\n".join(_i2v_scene_row(scene, keyframes, videos) for scene in package["scene_stress_tests"])
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{_esc(package["demo_id"])} I2V Review</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 24px; background: #f7f7f4; color: #151515; }}
    h1 {{ font-size: 24px; }}
    .boundary {{ padding: 12px; border: 1px solid #bbb; background: #fff; margin-bottom: 20px; }}
    .scene {{ display: grid; grid-template-columns: 160px 1fr 1fr; gap: 16px; margin-bottom: 20px; }}
    .cell {{ background: #fff; border: 1px solid #c9c9c9; padding: 12px; }}
    .media {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    img, video {{ width: 100%; max-height: 440px; background: #111; object-fit: contain; }}
    .label {{ font-weight: 700; margin-bottom: 8px; }}
    .path {{ font-size: 12px; color: #555; overflow-wrap: anywhere; }}
    .note {{ font-size: 13px; color: #444; }}
  </style>
</head>
<body>
  <h1>{_esc(package["demo_id"])} I2V Storyboard Review</h1>
  <div class="boundary">
    <div>3 scenes x 2 lanes = 6 videos.</div>
    <div>Provider smoke is not creative quality validation.</div>
    <div>Memory advantage claim: {_esc(review.get("quality_improvement_claim", ""))}</div>
    <div>Human acceptance: {_esc(review.get("human_acceptance", ""))}</div>
    <div>Business validation: {_esc(review.get("business_validation", ""))}</div>
  </div>
  {rows}
</body>
</html>
"""


def _scene_row(scene: dict[str, Any], keyframes: dict[tuple[str, str], dict[str, Any]]) -> str:
    scene_id = str(scene["scene_id"])
    baseline = keyframes.get(("baseline", scene_id), {})
    memory = keyframes.get(("memory_assisted", scene_id), {})
    physics = "; ".join(str(item) for item in scene.get("physics_targets", []))
    return f"""<section class="scene">
  <div class="cell">
    <div class="label">{_esc(scene_id)}</div>
    <div>{_esc(str(scene.get("stressor", "")))}</div>
    <p class="note">{_esc(str(scene.get("source_script_summary", "")))}</p>
    <p class="note">{_esc(physics)}</p>
  </div>
  {_image_cell("Baseline", baseline)}
  {_image_cell("Memory Assisted", memory)}
</section>"""


def _i2v_scene_row(
    scene: dict[str, Any],
    keyframes: dict[tuple[str, str], dict[str, Any]],
    videos: dict[tuple[str, str], dict[str, Any]],
) -> str:
    scene_id = str(scene["scene_id"])
    baseline_keyframe = keyframes.get(("baseline", scene_id), {})
    baseline_video = videos.get(("baseline", scene_id), {})
    memory_keyframe = keyframes.get(("memory_assisted", scene_id), {})
    memory_video = videos.get(("memory_assisted", scene_id), {})
    physics = "; ".join(str(item) for item in scene.get("physics_targets", []))
    return f"""<section class="scene">
  <div class="cell">
    <div class="label">{_esc(scene_id)}</div>
    <div>{_esc(str(scene.get("stressor", "")))}</div>
    <p class="note">{_esc(str(scene.get("source_script_summary", "")))}</p>
    <p class="note">{_esc(physics)}</p>
  </div>
  {_video_cell("Baseline", baseline_keyframe, baseline_video)}
  {_video_cell("Memory Assisted", memory_keyframe, memory_video)}
</section>"""


def _image_cell(label: str, artifact: dict[str, Any]) -> str:
    path = str(artifact.get("image_path") or "")
    image = f'<img src="{_esc(path)}" alt="{_esc(label)} keyframe">' if path else "<div>Missing keyframe</div>"
    return f"""<div class="cell">
    <div class="label">{_esc(label)}</div>
    {image}
    <div class="path">{_esc(path)}</div>
  </div>"""


def _video_cell(label: str, keyframe: dict[str, Any], video: dict[str, Any]) -> str:
    image_path = str(keyframe.get("image_path") or "")
    video_path = str(video.get("video_path") or "")
    image = f'<img src="{_esc(image_path)}" alt="{_esc(label)} keyframe">' if image_path else "<div>Missing keyframe</div>"
    video_el = f'<video controls src="{_esc(video_path)}"></video>' if video_path else "<div>Missing video</div>"
    return f"""<div class="cell">
    <div class="label">{_esc(label)}</div>
    <div class="media">{image}{video_el}</div>
    <div class="path">{_esc(image_path)}</div>
    <div class="path">{_esc(video_path)}</div>
  </div>"""


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)
