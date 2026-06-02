from __future__ import annotations

import json


def provider_config() -> dict:
    return {
        "schema_version": "company_provider_secrets.local.v2",
        "accounts": {
            "kling": {
                "auth_type": "jwt_hs256_from_ak_sk",
                "base_url": "https://api-beijing.klingai.com",
                "access_key": "fake-access-key",
                "secret_key": "fake-secret-key",
                "jwt": {"ttl_seconds": 1800, "nbf_skew_seconds": -5},
                "default_models": {"i2v": "kling-v3", "t2v": "kling-v3"},
                "endpoints": {
                    "i2v_create": "/v1/videos/image2video",
                    "i2v_query": "/v1/videos/image2video/{id}",
                    "t2v_create": "/v1/videos/text2video",
                    "t2v_query": "/v1/videos/text2video/{id}",
                },
            },
            "minimax": {
                "auth_type": "api_key",
                "base_url": "https://api.minimaxi.com/anthropic",
                "api_key": "fake-minimax-key",
                "default_models": {"image": "image-01"},
            },
        },
        "services": {
            "minimax_image": {
                "provider": "minimax",
                "account_ref": "minimax",
                "capability": "image",
                "api_family": "t2i",
                "required_gate": "AFS_ALLOW_REMOTE_IMAGE",
            },
            "kling_i2v": {
                "provider": "kling",
                "account_ref": "kling",
                "capability": "video",
                "api_family": "i2v",
                "default_model_ref": "accounts.kling.default_models.i2v",
                "create_endpoint_ref": "accounts.kling.endpoints.i2v_create",
                "query_endpoint_ref": "accounts.kling.endpoints.i2v_query",
                "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
            },
            "kling_t2v": {
                "provider": "kling",
                "account_ref": "kling",
                "capability": "video",
                "api_family": "t2v",
                "default_model_ref": "accounts.kling.default_models.t2v",
                "create_endpoint_ref": "accounts.kling.endpoints.t2v_create",
                "query_endpoint_ref": "accounts.kling.endpoints.t2v_query",
                "required_gate": "AFS_ALLOW_REMOTE_VIDEO",
            },
        },
    }


def write_image_manifest(run_root, lane: str, state_id: str) -> None:
    output_dir = run_root / "live" / lane / state_id / "image"
    image_dir = output_dir / "image_candidates"
    image_dir.mkdir(parents=True, exist_ok=True)
    (image_dir / "candidate_001.png").write_bytes(b"fake-png")
    manifest = {
        "schema_version": "minimax_image_smoke_manifest.v1",
        "status": "succeeded",
        "service_id": "minimax_image",
        "provider": "minimax_image",
        "api_family": "t2i",
        "model": "image-01",
        "outputs": [
            {
                "image_path": "image_candidates/candidate_001.png",
                "byte_count": 8,
                "sha256": f"sha-img-{lane}-{state_id}",
                "provider_url_persisted": False,
            }
        ],
        "claim_boundary": "provider_smoke_only_not_creative_quality",
    }
    (output_dir / "minimax_image_smoke_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def write_i2v_manifest(run_root, lane: str, state_id: str) -> None:
    output_dir = run_root / "live" / lane / state_id / "i2v"
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
        "outputs": [
            {
                "video_path": "video_candidates/candidate_001.mp4",
                "byte_count": 8,
                "sha256": f"sha-vid-{lane}-{state_id}",
                "provider_url_persisted": False,
            }
        ],
        "claim_boundary": "provider_smoke_only_not_creative_quality",
    }
    (output_dir / "kling_i2v_smoke_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
