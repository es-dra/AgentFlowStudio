from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agentflow_studio.production.representative_episode_media import (
    RepresentativeEpisodeMediaError,
    _validate_probe,
    assemble_authoritative_episode,
    derive_authoritative_inventory,
    safe_media_projection,
)
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore
from tools.afs_representative_episode_media import (
    build_provider_free_media_admissions,
    prepare_provider_free_media_delivery,
)
from tools.studio_production_delivery_browser_qa import (
    QA_EMAIL,
    QA_PASSWORD,
    _qa_environment,
    prepare_provider_free_delivery_qa,
)


MEDIA_TOOLS_READY = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
requires_media_tools = pytest.mark.skipif(
    not MEDIA_TOOLS_READY,
    reason="ffmpeg and ffprobe are required for controlled media integration evidence",
)


def _login(client: TestClient) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": QA_EMAIL, "password": QA_PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['session_token']}"}


def _media_request(run: dict, assets: list[dict]) -> dict:
    binding = run["representative_episode_binding"]
    return {
        "schema_version": "afs_representative_episode_media_intake.v0.1",
        "idempotency_key": "canonical-media-intake-001",
        "expected_checkpoint_version": run["checkpoint"]["version"],
        "expected_binding_digest": binding["binding_digest"],
        "expected_episode_version_id": binding["episode_version_id"],
        "assets": assets,
    }


def test_inventory_is_server_derived_exact_v2_and_caller_cannot_reorder(tmp_path: Path) -> None:
    seed = prepare_provider_free_delivery_qa(tmp_path)
    store = RuntimeStore(tmp_path)
    run = store.load_production_run(seed["project_id"], seed["run_id"])
    binding = run["representative_episode_binding"]
    inventory = derive_authoritative_inventory(binding)

    assert len(inventory) == 25
    assert [item["category"] for item in inventory] == ["character"] * 3 + ["scene"] * 3 + ["shot"] * 15 + ["audio"] * 4
    assert [item["shot_number"] for item in inventory if item["category"] == "shot"] == list(range(1, 16))
    assert inventory[10]["asset_id"] == "asset-shot-005-motion"
    stale = copy.deepcopy(binding)
    stale["episode_version_id"] = "ep-rainlight-001-v1"
    with pytest.raises(RepresentativeEpisodeMediaError, match="exact propagated v2"):
        derive_authoritative_inventory(stale)


@requires_media_tools
def test_authenticated_media_intake_is_atomic_idempotent_reload_safe_and_isolated(tmp_path: Path, monkeypatch) -> None:
    seed = prepare_provider_free_delivery_qa(tmp_path)
    route = f"/projects/{seed['project_id']}/production-runs/{seed['run_id']}"
    with _qa_environment():
        monkeypatch.setenv("AFS_INVITE_CODES", "delivery-qa-invite,media-other-invite")
        with TestClient(create_runtime_app(runtime_root=tmp_path)) as client:
            headers = _login(client)
            run = client.get(route, headers=headers).json()["production_run"]
            admissions = build_provider_free_media_admissions(run["representative_episode_binding"])
            request = _media_request(run, admissions)

            stale = copy.deepcopy(request)
            stale["idempotency_key"] = "canonical-media-stale-checkpoint"
            stale["expected_checkpoint_version"] -= 1
            assert client.post(f"{route}/representative-episode-media/intake", headers=headers, json=stale).status_code == 409
            omitted = copy.deepcopy(request)
            omitted["assets"].pop()
            assert client.post(f"{route}/representative-episode-media/intake", headers=headers, json=omitted).status_code == 422
            duplicated = copy.deepcopy(request)
            duplicated["assets"][-1] = copy.deepcopy(duplicated["assets"][0])
            assert client.post(f"{route}/representative-episode-media/intake", headers=headers, json=duplicated).status_code == 422
            premature_assembly = client.post(
                f"{route}/representative-episode-media/assemble",
                headers=headers,
                json={
                    "schema_version": "afs_representative_episode_media_assembly.v0.1",
                    "idempotency_key": "premature-assembly",
                    "expected_checkpoint_version": run["checkpoint"]["version"],
                    "expected_binding_digest": run["representative_episode_binding"]["binding_digest"],
                    "expected_media_manifest_sha256": "1" * 64,
                },
            )
            assert premature_assembly.status_code == 409

            reordered = copy.deepcopy(request)
            reordered["idempotency_key"] = "canonical-media-reordered"
            reordered["assets"][0], reordered["assets"][1] = reordered["assets"][1], reordered["assets"][0]
            rejected = client.post(f"{route}/representative-episode-media/intake", headers=headers, json=reordered)
            assert rejected.status_code == 409
            assert client.get(f"{route}/representative-episode-media", headers=headers).status_code == 404

            bad_hash = copy.deepcopy(request)
            bad_hash["idempotency_key"] = "canonical-media-bad-hash"
            bad_hash["assets"][0]["sha256"] = "0" * 64
            rejected = client.post(f"{route}/representative-episode-media/intake", headers=headers, json=bad_hash)
            assert rejected.status_code == 409
            assert client.get(f"{route}/representative-episode-media", headers=headers).status_code == 404

            admitted = client.post(f"{route}/representative-episode-media/intake", headers=headers, json=request)
            assert admitted.status_code == 200, admitted.text
            run_after = admitted.json()["production_run"]
            media = run_after["representative_episode_media"]
            assert media["accepted_count"] == 25
            assert len(media["assets"]) == 25
            assert media["continuity_status"] == "structural_checked"
            assert "relative_ref" not in json.dumps(media)
            assert "probe" not in json.dumps(media)
            assert "data_base64" not in json.dumps(media)

            replay = client.post(f"{route}/representative-episode-media/intake", headers=headers, json=request)
            assert replay.status_code == 200, replay.text
            assert replay.json()["idempotent_replay"] is True
            assert replay.json()["production_run"]["checkpoint"] == run_after["checkpoint"]

            first = media["assets"][0]
            preview_url = first["safe_preview"]["preview_url"]
            assert client.get(preview_url).status_code == 401
            preview = client.get(preview_url, headers=headers)
            assert preview.status_code == 200
            assert preview.headers["content-type"].startswith("image/png")
            assert preview.headers["cache-control"] == "private, no-store"
            assert preview.headers["x-content-type-options"] == "nosniff"
            assert preview.headers["content-disposition"].startswith("inline;")

            reloaded = TestClient(create_runtime_app(runtime_root=tmp_path)).get(route, headers=headers)
            assert reloaded.status_code == 200, reloaded.text
            assert reloaded.json()["production_run"]["representative_episode_media"] == media

            other = client.post(
                "/auth/register",
                json={
                    "email": "media-other@local.test",
                    "password": "Local-QA-Media-Other-2026!",
                    "display_name": "Media Other",
                    "invite_code": "media-other-invite",
                },
            )
            assert other.status_code == 200, other.text
            other_headers = {"Authorization": f"Bearer {other.json()['session_token']}"}
            assert client.get(route, headers=other_headers).status_code == 403
            assert client.get(preview_url, headers=other_headers).status_code == 403


@requires_media_tools
def test_media_hash_tamper_fails_closed_on_reload(tmp_path: Path) -> None:
    seed = prepare_provider_free_media_delivery(tmp_path, assemble=False)
    store = RuntimeStore(tmp_path)
    run = store.load_production_run(seed["project_id"], seed["run_id"])
    internal = run["representative_episode_media"]
    first = internal["assets"][0]
    media_root = store.production_run_path(seed["project_id"], seed["run_id"]).parent / "representative_episode_media"
    path = media_root / first["relative_ref"]
    path.write_bytes(path.read_bytes() + b"tamper")
    with _qa_environment(), TestClient(create_runtime_app(runtime_root=tmp_path)) as client:
        response = client.get(
            f"/projects/{seed['project_id']}/production-runs/{seed['run_id']}",
            headers=_login(client),
        )
        assert response.status_code == 409
        assert "hash revalidation" in response.text


@requires_media_tools
def test_complete_media_assembles_only_after_25_of_25_and_preserves_nonclaims(tmp_path: Path) -> None:
    result = prepare_provider_free_media_delivery(tmp_path)
    assert result["media_accepted_count"] == 25
    assert result["assembly_complete"] is True
    assert result["provider_calls_started"] is False
    assert result["evidence_label"] == "canonical_media_delivery_bridge_pass"
    assert result["representative_content_proof"] == "not_started"

    with _qa_environment(), TestClient(create_runtime_app(runtime_root=tmp_path)) as client:
        headers = _login(client)
        route = f"/projects/{result['project_id']}/production-runs/{result['run_id']}"
        run = client.get(route, headers=headers).json()["production_run"]
        assert run["exports"] == []
        media = run["representative_episode_media"]
        assert media["assembly_status"] == "technical_qa_passed"
        assert media["representative_content_proof"] == "not_started"
        preview = client.get(media["delivery_preview_url"], headers=headers)
        assert preview.status_code == 200
        assert preview.headers["content-type"].startswith("video/mp4")
        assert preview.headers["cache-control"] == "private, no-store"
        assert preview.headers["x-content-type-options"] == "nosniff"
        assert preview.headers["content-disposition"].startswith("inline;")
        assert len(preview.content) > 1000

        projection = safe_media_projection(RuntimeStore(tmp_path).load_production_run(
            result["project_id"], result["run_id"]
        )["representative_episode_media"])
        assert projection == {
            "status": "media_ready",
            "accepted_count": 25,
            "required_count": 25,
            "visual_count": 21,
            "audio_count": 4,
            "continuity_status": "structural_checked",
            "continuity_checks": [
                {"label": "规范版本一致", "status": "structural_checked"},
                {"label": "十五镜时间线", "status": "structural_checked"},
                {"label": "角色场景与镜头素材", "status": "structural_checked"},
                {"label": "对白音乐音效与母版", "status": "structural_checked"},
            ],
            "assembly_status": "technical_qa_passed",
            "delivery_preview_url": media["delivery_preview_url"],
            "duration_seconds": 135,
            "shot_count": 15,
            "representative_content_proof": "not_started",
            "creative_media_quality": "not_evaluated",
            "human_acceptance": "not_evaluated",
        }


def test_declared_video_and_audio_mime_require_matching_probed_containers() -> None:
    with pytest.raises(RepresentativeEpisodeMediaError, match="video MIME and probed container"):
        _validate_probe(
            {},
            "video",
            "video/mp4",
            {
                "format": {"format_name": "mpegts", "duration": "9"},
                "streams": [{"codec_type": "video", "codec_name": "h264", "width": 640, "height": 360}],
            },
        )
    with pytest.raises(RepresentativeEpisodeMediaError, match="audio MIME and probed container"):
        _validate_probe(
            {},
            "audio",
            "audio/wav",
            {
                "format": {"format_name": "aiff", "duration": "135"},
                "streams": [
                    {"codec_type": "audio", "codec_name": "pcm_s16le", "sample_rate": "48000", "channels": 1}
                ],
            },
        )


@requires_media_tools
def test_assembly_removes_partial_delivery_when_technical_qa_raises(tmp_path: Path, monkeypatch) -> None:
    seed = prepare_provider_free_media_delivery(tmp_path, assemble=False)
    store = RuntimeStore(tmp_path)
    run = store.load_production_run(seed["project_id"], seed["run_id"])
    media_root = store.production_run_path(seed["project_id"], seed["run_id"]).parent / "representative_episode_media"

    def fail_qa(*_args, **_kwargs):
        raise RepresentativeEpisodeMediaError("transient technical QA failure")

    monkeypatch.setattr(
        "agentflow_studio.production.representative_episode_media._run_technical_qa_utf8",
        fail_qa,
    )
    with pytest.raises(RepresentativeEpisodeMediaError, match="transient technical QA failure"):
        assemble_authoritative_episode(run["representative_episode_binding"], run["representative_episode_media"], media_root)
    assert not (media_root / "delivery").exists()
