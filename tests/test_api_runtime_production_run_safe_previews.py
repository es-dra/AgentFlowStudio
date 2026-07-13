from __future__ import annotations

import binascii
import hashlib
import json
import struct
import zlib
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agentflow.harness.json_io import write_json
from apps.api.runtime_generated_image_assets import register_generated_image_asset
from apps.api.runtime_production_models import checkpoint_digest
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore


PROJECT_ID = "safe-preview-project"
RUN_ID = "safe-preview-run"
OWNER_EMAIL = "safe-preview-owner@example.test"
OWNER_PASSWORD = "safe-preview-owner-password"


def _digest(value: bytes | str) -> str:
    payload = value if isinstance(value, bytes) else value.encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _png(width: int = 2, height: int = 2) -> bytes:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        checksum = binascii.crc32(kind + payload) & 0xFFFFFFFF
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)

    rows = b"".join(b"\x00" + bytes((40, 90, 150)) * width for _ in range(height))
    header = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    return b"\x89PNG\r\n\x1a\n" + header + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def _registered_client(runtime_root: Path, monkeypatch) -> tuple[TestClient, dict[str, str]]:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_AUTH_ALLOW_OPEN_SIGNUP", "true")
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    registered = client.post(
        "/auth/register",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD, "display_name": "Preview Owner"},
    )
    assert registered.status_code == 200, registered.text
    headers = {"Authorization": f"Bearer {registered.json()['session_token']}"}
    created = client.post(
        "/projects",
        json={"project_id": PROJECT_ID, "goal": "Authoritative safe preview projection"},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    return client, headers


def _candidate(candidate_id: str, digest: str, parent_job_id: str) -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
        "canonical_digest": digest,
        "parent_job_id": parent_job_id,
        "parent_candidate_id": None,
        "parent_revision_id": None,
        "shot_id": "shot-001",
        "safe_artifact_refs": [],
    }


def _create_run(
    client: TestClient,
    headers: dict[str, str],
    candidates: list[dict[str, object]],
    *,
    run_id: str = RUN_ID,
) -> dict[str, object]:
    response = client.post(
        f"/projects/{PROJECT_ID}/production-runs",
        json={
            "schema_version": "afs_runtime_production_run.v0.1",
            "run_id": run_id,
            "idempotency_key": f"create-{run_id}",
            "subject_digest": _digest(f"subject-{run_id}"),
            "candidates": candidates,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["production_run"]


def _write_image_authority(store: RuntimeStore, job_id: str, candidate_id: str) -> str:
    image_bytes = _png()
    candidate_dir = store.run_dir(PROJECT_ID, job_id) / "image_candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    path = candidate_dir / f"{candidate_id}.png"
    path.write_bytes(image_bytes)
    digest = _digest(image_bytes)
    register_generated_image_asset(
        store,
        PROJECT_ID,
        source_node_id="art-node-001",
        source_job_id=job_id,
        source_candidate_id=candidate_id,
        image_path=path,
        source_candidate_digest=digest,
        source_candidate_status="succeeded",
    )
    return digest


def _write_video_candidate(store: RuntimeStore, job_id: str, candidate_id: str, suffix: str = ".mp4") -> str:
    payload = b"provider-free-video-fixture-v1"
    candidate_dir = store.run_dir(PROJECT_ID, job_id) / "video_candidates"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    (candidate_dir / f"{candidate_id}{suffix}").write_bytes(payload)
    return _digest(payload)


def _candidate_projection(response: dict[str, object]) -> list[dict[str, object]]:
    run = response["production_run"]
    assert isinstance(run, dict)
    candidates = run["candidates"]
    assert isinstance(candidates, list)
    return candidates


def test_safe_preview_projects_authoritative_image_and_video_for_list_detail_and_reload(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    store = RuntimeStore(tmp_path)
    image_job_id = "image-job-001"
    video_job_id = "video-job-001"
    store.write_job(
        {"job_id": image_job_id, "project_id": PROJECT_ID, "action": "keyframe_generation", "status": "succeeded"}
    )
    store.write_job(
        {"job_id": video_job_id, "project_id": PROJECT_ID, "action": "video_generation", "status": "succeeded"}
    )
    image_digest = _write_image_authority(store, image_job_id, "candidate_001")
    video_digest = _write_video_candidate(store, video_job_id, "candidate_002")
    created = _create_run(
        client,
        headers,
        [
            _candidate("candidate_001", image_digest, image_job_id),
            _candidate("candidate_002", video_digest, video_job_id),
        ],
    )
    assert all("safe_preview" not in item for item in created["candidates"])
    stored_path = store.production_run_path(PROJECT_ID, RUN_ID)
    stored_before = stored_path.read_bytes()

    detail = client.get(f"/projects/{PROJECT_ID}/production-runs/{RUN_ID}", headers=headers)
    listed = client.get(f"/projects/{PROJECT_ID}/production-runs", headers=headers)
    assert detail.status_code == listed.status_code == 200
    detail_candidates = _candidate_projection(detail.json())
    list_candidates = listed.json()["production_runs"][0]["candidates"]
    assert list_candidates == detail_candidates
    assert detail_candidates[0]["safe_preview"] == {
        "media_kind": "image",
        "preview_url": (
            f"/projects/{PROJECT_ID}/keyframe-generations/{image_job_id}/"
            "candidates/candidate_001/preview"
        ),
    }
    assert detail_candidates[1]["safe_preview"] == {
        "media_kind": "video",
        "preview_url": f"/projects/{PROJECT_ID}/video-generations/{video_job_id}/candidates/candidate_002/preview",
    }
    assert set(detail_candidates[0]["safe_preview"]) == {"media_kind", "preview_url"}
    assert set(detail_candidates[1]["safe_preview"]) == {"media_kind", "preview_url"}
    for descriptor in (detail_candidates[0]["safe_preview"], detail_candidates[1]["safe_preview"]):
        assert descriptor["preview_url"].startswith(f"/projects/{PROJECT_ID}/")
        assert "://" not in descriptor["preview_url"]
        serialized = json.dumps(descriptor).lower()
        assert all(term not in serialized for term in ("provider", "signed", "filesystem", "account"))

    image_preview = client.get(detail_candidates[0]["safe_preview"]["preview_url"], headers=headers)
    video_preview = client.get(detail_candidates[1]["safe_preview"]["preview_url"], headers=headers)
    assert image_preview.status_code == video_preview.status_code == 200
    assert image_preview.content == _png()
    assert video_preview.content == b"provider-free-video-fixture-v1"
    assert stored_path.read_bytes() == stored_before
    assert b"safe_preview" not in stored_before

    with TestClient(create_runtime_app(runtime_root=tmp_path)) as reloaded:
        loaded = reloaded.get(f"/projects/{PROJECT_ID}/production-runs/{RUN_ID}", headers=headers)
    assert loaded.status_code == 200, loaded.text
    assert _candidate_projection(loaded.json()) == detail_candidates
    assert stored_path.read_bytes() == stored_before


def test_safe_preview_read_and_media_routes_keep_auth_and_project_isolation(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    store = RuntimeStore(tmp_path)
    job_id = "image-job-auth"
    store.write_job(
        {"job_id": job_id, "project_id": PROJECT_ID, "action": "keyframe_generation", "status": "succeeded"}
    )
    digest = _write_image_authority(store, job_id, "candidate_001")
    _create_run(client, headers, [_candidate("candidate_001", digest, job_id)])
    detail_url = f"/projects/{PROJECT_ID}/production-runs/{RUN_ID}"
    preview_url = (
        f"/projects/{PROJECT_ID}/keyframe-generations/{job_id}/candidates/candidate_001/preview"
    )

    other = client.post(
        "/auth/register",
        json={
            "email": "foreign-preview@example.test",
            "password": "foreign-preview-password",
            "display_name": "Foreign",
        },
    )
    assert other.status_code == 200
    foreign_headers = {"Authorization": f"Bearer {other.json()['session_token']}"}
    assert client.get(detail_url).status_code == 401
    assert client.get(preview_url).status_code == 401
    assert client.get(detail_url, headers=foreign_headers).status_code == 403
    assert client.get(preview_url, headers=foreign_headers).status_code == 403
    assert client.get(preview_url, headers=headers).status_code == 200


@pytest.mark.parametrize(
    ("case", "action", "candidate_id", "artifact_kind", "digest_mode"),
    [
        ("missing_job", None, "candidate_001", "none", "matching"),
        ("foreign_job", "keyframe_generation", "candidate_001", "image", "matching"),
        ("job_identity_conflict", "keyframe_generation", "candidate_001", "image", "matching"),
        ("pending_job", "keyframe_generation", "candidate_001", "image", "matching"),
        ("wrong_action", "prompt_optimization", "candidate_001", "image", "matching"),
        ("image_digest_mismatch", "keyframe_generation", "candidate_001", "image", "mismatch"),
        ("image_asset_missing", "keyframe_generation", "candidate_001", "image_without_asset", "matching"),
        ("image_conflict", "keyframe_generation", "candidate_001", "image_conflict", "matching"),
        ("video_digest_mismatch", "video_generation", "candidate_001", "video", "mismatch"),
        ("video_conflict", "video_generation", "candidate_001", "video_conflict", "matching"),
        ("video_unsupported", "video_generation", "candidate_001", "video_unsupported", "matching"),
        ("unsafe_alias", "video_generation", "candidate-video", "video", "matching"),
    ],
)
def test_safe_preview_omits_stale_foreign_conflicting_unsafe_and_unsupported_authority(
    tmp_path,
    monkeypatch,
    case: str,
    action: str | None,
    candidate_id: str,
    artifact_kind: str,
    digest_mode: str,
) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    store = RuntimeStore(tmp_path)
    job_id = f"job-{case}"
    project_id = "foreign-project" if case == "foreign_job" else PROJECT_ID
    if action:
        status = "pending" if case == "pending_job" else "succeeded"
        if case == "job_identity_conflict":
            write_json(
                store.jobs_dir / f"{job_id}.json",
                {"job_id": "different-job", "project_id": project_id, "action": action, "status": status},
            )
        else:
            store.write_job({"job_id": job_id, "project_id": project_id, "action": action, "status": status})

    digest = _digest(f"no-authority-{case}")
    if artifact_kind.startswith("image"):
        candidate_dir = store.run_dir(PROJECT_ID, job_id) / "image_candidates"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        image_path = candidate_dir / f"{candidate_id}.png"
        image_path.write_bytes(_png())
        digest = _digest(image_path.read_bytes())
        if artifact_kind != "image_without_asset":
            register_generated_image_asset(
                store,
                PROJECT_ID,
                source_node_id="art-node-negative",
                source_job_id=job_id,
                source_candidate_id=candidate_id,
                image_path=image_path,
                source_candidate_digest=digest,
                source_candidate_status="succeeded",
            )
        if artifact_kind == "image_conflict":
            (candidate_dir / f"{candidate_id}.jpg").write_bytes(b"\xff\xd8conflict")
    elif artifact_kind.startswith("video"):
        suffix = ".avi" if artifact_kind == "video_unsupported" else ".mp4"
        digest = _write_video_candidate(store, job_id, candidate_id, suffix)
        if artifact_kind == "video_conflict":
            _write_video_candidate(store, job_id, candidate_id, ".webm")
    if digest_mode == "mismatch":
        digest = _digest(f"stale-{case}")

    _create_run(client, headers, [_candidate(candidate_id, digest, job_id)])
    response = client.get(f"/projects/{PROJECT_ID}/production-runs/{RUN_ID}", headers=headers)
    assert response.status_code == 200, response.text
    assert "safe_preview" not in _candidate_projection(response.json())[0]


def test_safe_preview_discards_stored_descriptor_and_does_not_change_checkpoint(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    store = RuntimeStore(tmp_path)
    _create_run(client, headers, [_candidate("candidate_001", _digest("missing"), "missing-job")])
    path = store.production_run_path(PROJECT_ID, RUN_ID)
    stored = json.loads(path.read_text(encoding="utf-8"))
    stored["candidates"][0]["safe_preview"] = {
        "media_kind": "video",
        "preview_url": f"/projects/{PROJECT_ID}/video-generations/stale-job/candidates/candidate_001/preview",
        "stale_client_hint": True,
    }
    stored["checkpoint"]["state_digest"] = checkpoint_digest(stored)
    write_json(path, stored)
    before = deepcopy(stored)

    detail = client.get(f"/projects/{PROJECT_ID}/production-runs/{RUN_ID}", headers=headers)
    listed = client.get(f"/projects/{PROJECT_ID}/production-runs", headers=headers)
    assert detail.status_code == listed.status_code == 200
    assert "safe_preview" not in _candidate_projection(detail.json())[0]
    assert "safe_preview" not in listed.json()["production_runs"][0]["candidates"][0]
    assert json.loads(path.read_text(encoding="utf-8")) == before
    assert before["checkpoint"]["state_digest"] == checkpoint_digest(before)
