from __future__ import annotations

import json
from pathlib import Path

from agentflow_studio.model_gateway.company_secrets import load_company_provider_secrets
from tests.provider_smoke_helpers import provider_config


def write_i2i_manifest(run_root: Path, lane: str, scene_id: str) -> None:
    output_dir = run_root / "live" / lane / scene_id / "image"
    image_dir = output_dir / "image_candidates"
    image_dir.mkdir(parents=True, exist_ok=True)
    (image_dir / "candidate_001.png").write_bytes(b"fake-png")
    manifest = {
        "schema_version": "minimax_image_smoke_manifest.v1",
        "status": "succeeded",
        "service_id": "minimax_image",
        "provider": "minimax_image",
        "api_family": "i2i",
        "model": "image-01",
        "input_image": {
            "path_persisted": False,
            "byte_count": 8,
            "sha256": "sha256:fake",
            "mime_type": "image/png",
        },
        "outputs": [
            {
                "image_path": "image_candidates/candidate_001.png",
                "byte_count": 8,
                "sha256": f"sha-img-{lane}-{scene_id}",
                "provider_url_persisted": False,
            }
        ],
        "claim_boundary": "provider_smoke_only_not_creative_quality",
    }
    (output_dir / "minimax_image_smoke_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def write_i2v_manifest(run_root: Path, lane: str, scene_id: str) -> None:
    output_dir = run_root / "live" / lane / scene_id / "i2v"
    video_dir = output_dir / "video_candidates"
    video_dir.mkdir(parents=True, exist_ok=True)
    (video_dir / "candidate_001.mp4").write_bytes(b"fake-mp4")
    manifest = {
        "schema_version": "kling_i2v_smoke_manifest.v1",
        "status": "succeeded",
        "service_id": "kling_i2v",
        "provider": "kling",
        "api_family": "i2v",
        "model": "kling-v3",
        "input_image": {
            "path_persisted": False,
            "byte_count": 8,
            "sha256": "sha256:fake",
        },
        "outputs": [
            {
                "video_path": "video_candidates/candidate_001.mp4",
                "byte_count": 8,
                "sha256": f"sha-vid-{lane}-{scene_id}",
                "provider_url_persisted": False,
            }
        ],
        "claim_boundary": "provider_smoke_only_not_creative_quality",
    }
    (output_dir / "kling_i2v_smoke_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def demo_012_store(tmp_path: Path):
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(provider_config()), encoding="utf-8")
    return load_company_provider_secrets(config_path)
