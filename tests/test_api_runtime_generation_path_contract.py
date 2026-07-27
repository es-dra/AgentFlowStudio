from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api import runtime_video_routes
from apps.api.generation_path_contract import generation_path_contracts, video_generation_path_id
from apps.api.runtime_models import VideoGenerationRequest
from apps.api.runtime_service import create_runtime_app


INITIAL_GENERATION_PATHS = {
    "t2v",
    "reference_images",
    "i2v_first_frame",
    "i2v_first_last",
    "reference_video",
    "director_to_keyframe",
    "director_to_video",
}


def test_generation_path_contract_v1_defines_initial_paths() -> None:
    contracts = generation_path_contracts()

    assert set(contracts) == INITIAL_GENERATION_PATHS
    for path_id, contract in contracts.items():
        assert contract["schema_version"] == "afs_generation_path_contract.v1"
        assert contract["path_id"] == path_id
        assert contract["required_inputs"]
        assert contract["allowed_media_families"]["output"] in {"image", "video"}
        assert contract["provider_capability"]
        assert contract["adoption_state"] in {"supported", "planned", "blocked"}
        assert contract["safety_preflight"]["provider_calls_started"] is False
        assert contract["safety_preflight"]["media_bytes_required_by_preflight"] is False

    assert contracts["t2v"]["required_inputs"] == ["prompt_text"]
    assert "first_frame_image_asset_id" not in contracts["t2v"]["required_inputs"]
    assert contracts["i2v_first_frame"]["required_inputs"] == ["prompt_text", "first_frame_image_asset_id"]
    assert contracts["reference_images"]["required_inputs"] == [
        "prompt_text",
        "reference_image_asset_ids",
    ]
    assert contracts["reference_images"]["adoption_state"] == "supported"
    assert contracts["i2v_first_last"]["required_inputs"] == [
        "prompt_text",
        "first_frame_image_asset_id",
        "last_frame_image_asset_id",
    ]


def test_video_generation_request_keeps_legacy_i2v_required_inputs() -> None:
    with pytest.raises(ValidationError) as missing_first:
        VideoGenerationRequest(
            prompt_text="A controlled legacy image-to-video request.",
            generated_at="2026-07-11T00:00:00+00:00",
        )

    assert "first_frame_image_asset_id" in str(missing_first.value)

    with pytest.raises(ValidationError) as missing_last:
        VideoGenerationRequest(
            generation_path="i2v_first_last",
            prompt_text="Move from the first frame to the last frame.",
            first_frame_image_asset_id="img_first",
            generated_at="2026-07-11T00:00:00+00:00",
        )

    assert "last_frame_image_asset_id" in str(missing_last.value)

    legacy = VideoGenerationRequest(
        prompt_text="A controlled legacy image-to-video request.",
        first_frame_image_asset_id="img_first",
        generated_at="2026-07-11T00:00:00+00:00",
    )
    first_last = VideoGenerationRequest(
        prompt_text="A controlled legacy image-to-video request.",
        first_frame_image_asset_id="img_first",
        last_frame_image_asset_id="img_last",
        generated_at="2026-07-11T00:00:00+00:00",
    )

    assert video_generation_path_id(legacy) == "i2v_first_frame"
    assert video_generation_path_id(first_last) == "i2v_first_last"

    reference_conditioned = VideoGenerationRequest(
        generation_path="reference_images",
        prompt_text="Use approved references for identity continuity.",
        reference_image_asset_ids=["character-ref", "scene-ref"],
        generated_at="2026-07-27T00:00:00+00:00",
    )
    assert reference_conditioned.first_frame_image_asset_id is None
    assert video_generation_path_id(reference_conditioned) == "reference_images"
    with pytest.raises(ValidationError) as missing_references:
        VideoGenerationRequest(
            generation_path="reference_images",
            prompt_text="No references supplied.",
            generated_at="2026-07-27T00:00:00+00:00",
        )
    assert "reference_image_asset_ids" in str(missing_references.value)


def test_t2v_preflight_does_not_require_first_frame_and_blocks_provider_submit(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")

    def fail_submit(*_args, **_kwargs):
        raise AssertionError("planned t2v path must block before video provider submit")

    monkeypatch.setattr(runtime_video_routes, "submit_video_generation", fail_submit)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "generation-path-t2v"
    client.post("/projects", json={"project_id": project_id, "goal": "T2V path contract"}).raise_for_status()
    request = {
        "generation_path": "t2v",
        "prompt_text": "A text-only camera move through a quiet train station.",
        "duration_sec": 5,
        "resolution": "720p",
        "aspect_ratio": "9:16",
        "generated_at": "2026-07-11T00:00:00+00:00",
    }

    preflight = client.post(f"/projects/{project_id}/video-generations/preflight", json=request)
    submitted = client.post(f"/projects/{project_id}/video-generations", json=request)

    assert preflight.status_code == 200
    payload = preflight.json()
    assert payload["provider_calls_started"] is False
    assert payload["generation_path"] == "t2v"
    assert payload["input_mode"] == "text_only"
    assert payload["input_source"] == {"source_mode": "text_prompt", "role": "prompt_only"}
    assert payload["generation_path_contract"]["adoption_state"] == "planned"
    assert payload["generation_path_contract"]["safety_preflight"]["provider_submit_allowed"] is False
    assert payload["preflight_blocked"] is True
    assert payload["blocked_unsupported_combinations"][0]["error"] == "generation_path_not_supported"

    assert submitted.status_code == 422
    detail = submitted.json()["detail"]
    assert detail["error"] == "unsupported_generation_path"
    assert detail["stage"] == "generation_path_preflight"
    assert detail["details"]["provider_calls_started"] is False
    assert detail["details"]["generation_path"] == "t2v"


def test_unknown_generation_path_rejects_before_preflight(tmp_path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "generation-path-unknown"
    client.post("/projects", json={"project_id": project_id, "goal": "Unknown path"}).raise_for_status()

    response = client.post(
        f"/projects/{project_id}/video-generations/preflight",
        json={
            "generation_path": "unknown_path",
            "prompt_text": "A request with an unknown path.",
            "generated_at": "2026-07-11T00:00:00+00:00",
        },
    )

    assert response.status_code == 422
    assert "generation_path" in response.text


def test_planned_and_blocked_paths_do_not_call_video_provider(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_ALLOW_REMOTE_VIDEO", "true")

    def fail_submit(*_args, **_kwargs):
        raise AssertionError("planned or blocked generation paths must stop before provider submit")

    monkeypatch.setattr(runtime_video_routes, "submit_video_generation", fail_submit)
    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    project_id = "generation-path-provider-closed"
    client.post("/projects", json={"project_id": project_id, "goal": "Provider-closed paths"}).raise_for_status()

    director_response = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "generation_path": "director_to_video",
            "prompt_text": "Use the director setup to create a video.",
            "director_setup": {"view": "top_down_2d", "composition": "wide establishing shot"},
            "generated_at": "2026-07-11T00:00:00+00:00",
        },
    )
    reference_response = client.post(
        f"/projects/{project_id}/video-generations",
        json={
            "generation_path": "reference_video",
            "prompt_text": "Use the reference video as temporal input.",
            "reference_video_artifact_id": "artifact_reference_video",
            "generated_at": "2026-07-11T00:00:00+00:00",
        },
    )

    assert director_response.status_code == 422
    assert director_response.json()["detail"]["details"]["generation_path"] == "director_to_video"
    assert director_response.json()["detail"]["details"]["adoption_state"] == "planned"
    assert director_response.json()["detail"]["details"]["provider_calls_started"] is False

    assert reference_response.status_code == 422
    assert reference_response.json()["detail"]["details"]["generation_path"] == "reference_video"
    assert reference_response.json()["detail"]["details"]["adoption_state"] == "blocked"
    assert reference_response.json()["detail"]["details"]["provider_calls_started"] is False
