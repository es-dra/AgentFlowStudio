from __future__ import annotations

import hashlib
import json
import subprocess
import threading
from pathlib import Path

from fastapi.testclient import TestClient

from agentflow_studio.production.vertical_slice import CharacterSeed, DeterministicProductionSlice, ProjectIP
from apps.api import runtime_store as runtime_store_module
from apps.api.runtime_production_models import (
    RepresentativeEpisodeMediaAssemblyRequest,
    RepresentativeEpisodeMediaIntakeRequest,
    canonical_json_digest,
)
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_representative_episode_media_contract_exposes_only_bounded_authenticated_inputs() -> None:
    intake_schema = RepresentativeEpisodeMediaIntakeRequest.model_json_schema()
    assembly_schema = RepresentativeEpisodeMediaAssemblyRequest.model_json_schema()
    assert intake_schema["additionalProperties"] is False
    assert assembly_schema["additionalProperties"] is False
    assert intake_schema["properties"]["assets"]["minItems"] == 25
    assert intake_schema["properties"]["assets"]["maxItems"] == 25
    assert set(intake_schema["properties"]) == {
        "schema_version",
        "idempotency_key",
        "expected_checkpoint_version",
        "expected_binding_digest",
        "expected_episode_version_id",
        "assets",
    }
    assert set(assembly_schema["properties"]) == {
        "schema_version",
        "idempotency_key",
        "expected_checkpoint_version",
        "expected_binding_digest",
        "expected_media_manifest_sha256",
    }


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _registered_client(tmp_path, monkeypatch):
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_AUTH_ALLOW_OPEN_SIGNUP", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    registered = client.post(
        "/auth/register",
        json={
            "email": "creator@example.com",
            "password": "strong-password-123",
            "display_name": "Creator",
        },
    )
    assert registered.status_code == 200, registered.text
    headers = {"Authorization": f"Bearer {registered.json()['session_token']}"}
    created = client.post(
        "/projects",
        json={"project_id": "owned-project", "goal": "Authenticated production lifecycle"},
        headers=headers,
    )
    assert created.status_code == 200, created.text
    return client, headers


def _create_payload() -> dict:
    return {
        "schema_version": "afs_runtime_production_run.v0.1",
        "run_id": "production-run-001",
        "idempotency_key": "create-production-run-001",
        "subject_digest": _digest("project-subject-v1"),
        "candidates": [
            {
                "candidate_id": "candidate-001",
                "canonical_digest": _digest("candidate-one"),
                "parent_job_id": "job-keyframe-001",
                "shot_id": "shot-001",
                "safe_artifact_refs": [
                    {
                        "artifact_id": "artifact-candidate-001",
                        "artifact_type": "candidate-manifest",
                        "role": "candidate_manifest",
                        "media_type": "application/json",
                    }
                ],
            },
            {
                "candidate_id": "candidate-002",
                "canonical_digest": _digest("candidate-two"),
                "parent_job_id": "job-keyframe-001",
                "shot_id": "shot-001",
                "safe_artifact_refs": [],
            },
        ],
    }


def _create_run(client: TestClient, headers: dict[str, str]) -> dict:
    response = client.post(
        "/projects/owned-project/production-runs",
        json=_create_payload(),
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["production_run"]


def _creator_decision(run: dict, **updates) -> dict:
    candidate = run["candidates"][0]
    payload = {
        "schema_version": "afs_creator_decision.v0.1",
        "decision_id": "decision-001",
        "idempotency_key": "creator-decision-001",
        "expected_checkpoint_version": run["checkpoint"]["version"],
        "subject_digest": run["subject_digest"],
        "decision": "select",
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["canonical_digest"],
        "parent_revision_id": None,
        "revision_intent": "Select the clarity-first treatment without content changes.",
    }
    return {**payload, **updates}


def _episode_binding_payload(run: dict, **updates) -> dict:
    package_path = REPO_ROOT / "examples" / "representative_episode" / "episode_package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    arbitration = package["domain_crew_execution_plan"]["creator_arbitration"]
    character_versions = {
        item["character_id"]: item["current_version_id"] for item in package["characters"]
    }
    scene_versions = {
        item["scene_id"]: item["current_version_id"] for item in package["scenes"]
    }
    assets = {item["asset_id"]: item for item in package["asset_manifest"]}

    def asset_ref(asset_id: str) -> dict:
        item = assets[asset_id]
        return {
            "asset_id": item["asset_id"],
            "current_revision_id": item["current_revision_id"],
            "status": item["status"],
            "provider_needed": item["provider_needed"],
        }

    audio = package["audio_plan"]
    payload = {
        "schema_version": "afs_representative_episode_binding.v0.1",
        "idempotency_key": "bind-rainlight-episode-v1",
        "expected_checkpoint_version": run["checkpoint"]["version"],
        "expected_subject_digest": run["subject_digest"],
        "expected_package_sha256": None,
        "package_sha256": hashlib.sha256(package_path.read_bytes()).hexdigest(),
        "package_project_id": package["project"]["project_id"],
        "episode_id": package["project"]["episode_id"],
        "episode_version_id": package["project"]["current_version_id"],
        "character_refs": [
            {
                "entity_id": item["character_id"],
                "current_approved_version_id": item["current_version_id"],
            }
            for item in package["characters"]
        ],
        "scene_refs": [
            {
                "entity_id": item["scene_id"],
                "current_approved_version_id": item["current_version_id"],
            }
            for item in package["scenes"]
        ],
        "shot_refs": [
            {
                "entity_id": item["shot_id"],
                "current_approved_version_id": item["current_version_id"],
            }
            for item in package["shots"]
        ],
        "asset_refs": [
            asset_ref(item["asset_id"])
            for item in package["asset_manifest"]
        ],
        "episode_canon": {
            "episode_title": package["project"]["title"],
            "episode_version_id": package["project"]["current_version_id"],
            "duration_seconds": package["project"]["duration_seconds"],
            "characters": [
                {
                    "entity_id": item["character_id"],
                    "current_approved_version_id": item["current_version_id"],
                    "name": item["name"],
                    "appearance": item["appearance"],
                    "continuity_constraints": item["continuity_constraints"],
                }
                for item in package["characters"]
            ],
            "scenes": [
                {
                    "entity_id": item["scene_id"],
                    "current_approved_version_id": item["current_version_id"],
                    "name": item["name"],
                    "description": item["description"],
                    "style_constraints": item["style_constraints"],
                }
                for item in package["scenes"]
            ],
            "shots": [
                {
                    "ordinal": index,
                    "entity_id": item["shot_id"],
                    "current_approved_version_id": item["current_version_id"],
                    "start_seconds": item["start_seconds"],
                    "end_seconds": item["end_seconds"],
                    "scene_ref": {
                        "entity_id": item["scene_id"],
                        "current_approved_version_id": scene_versions[item["scene_id"]],
                    },
                    "character_refs": [
                        {
                            "entity_id": character_id,
                            "current_approved_version_id": character_versions[character_id],
                        }
                        for character_id in item["character_refs"]
                    ],
                    "required_asset_ids": item["required_asset_ids"],
                    "visual_action": item["script"]["visual_action"],
                    "dialogue": item["script"]["dialogue"],
                    "camera": item["camera"],
                    "motion": item["motion"],
                    "continuity_note": item["continuity_note"],
                    "quality_target": item["quality_target"],
                }
                for index, item in enumerate(package["shots"], start=1)
            ],
            "audio": {
                "coverage_shot_refs": audio["coverage_shot_refs"],
                "dialogue_asset_ref": asset_ref(audio["dialogue_asset_id"]),
                "music_asset_ref": asset_ref(audio["music_asset_id"]),
                "sfx_asset_ref": asset_ref(audio["sfx_asset_id"]),
                "master_asset_ref": asset_ref(audio["master_asset_id"]),
                "dialogue_direction": audio["dialogue_direction"],
                "music_direction": audio["music_direction"],
                "sfx_direction": audio["sfx_direction"],
                "mix_requirements": audio["mix_requirements"],
            },
        },
        "pending_media_count": sum(item["status"] == "missing" for item in package["asset_manifest"]),
        "creator_decision_ref": arbitration["creator_decision_ref"],
        "authoritative_affected_task_refs": arbitration["authoritative_affected_task_refs"],
        "downstream_reconfirmations": package["domain_crew_execution_plan"]["downstream_reconfirmations"],
    }
    return {**payload, **updates}


def test_production_run_requires_authenticated_project_owner(tmp_path, monkeypatch) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    client.post("/projects", json={"project_id": "local-project", "goal": "Local dev project"})

    response = client.post("/projects/local-project/production-runs", json=_create_payload())

    assert response.status_code == 403
    assert "runtime auth" in response.text

    owner_client, owner_headers = _registered_client(tmp_path / "authenticated", monkeypatch)
    other = owner_client.post(
        "/auth/register",
        json={
            "email": "other@example.com",
            "password": "strong-password-456",
            "display_name": "Other",
        },
    )
    other_headers = {"Authorization": f"Bearer {other.json()['session_token']}"}

    created = owner_client.post(
        "/projects/owned-project/production-runs",
        json=_create_payload(),
        headers=owner_headers,
    )
    denied = owner_client.get(
        "/projects/owned-project/production-runs/production-run-001",
        headers=other_headers,
    )

    assert created.status_code == 200, created.text
    assert denied.status_code == 403


def test_representative_episode_package_binding_is_authenticated_persisted_and_studio_visible(
    tmp_path,
    monkeypatch,
) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    project_id = "afs-rainlight-project"
    created_project = client.post(
        "/projects",
        json={"project_id": project_id, "goal": "Representative episode production"},
        headers=headers,
    )
    assert created_project.status_code == 200, created_project.text
    created_run = client.post(
        f"/projects/{project_id}/production-runs",
        json=_create_payload(),
        headers=headers,
    )
    assert created_run.status_code == 200, created_run.text
    run = created_run.json()["production_run"]
    route = f"/projects/{project_id}/production-runs/{run['run_id']}/representative-episode-binding"
    payload = _episode_binding_payload(run)

    bound = client.put(route, json=payload, headers=headers)
    replayed = client.put(route, json=payload, headers=headers)
    conflicting_replay_payload = _episode_binding_payload(run)
    conflicting_replay_payload["episode_canon"]["shots"][0]["continuity_note"] = "冲突的连续性要求"
    conflicting_replay = client.put(route, json=conflicting_replay_payload, headers=headers)
    loaded = client.get(route, headers=headers)

    assert bound.status_code == 200, bound.text
    assert bound.json()["idempotent_replay"] is False
    binding = bound.json()["production_run"]["representative_episode_binding"]
    assert binding["package_sha256"] == payload["package_sha256"]
    assert binding["episode_id"] == "ep-rainlight-001"
    assert binding["episode_version_id"] == "ep-rainlight-001-v1"
    assert binding["counts"] == {"characters": 3, "scenes": 3, "shots": 15, "assets": 25, "audio_items": 4}
    assert binding["asset_readiness"] == {
        "ready_count": 0,
        "pending_media_count": 25,
        "provider_needed_count": 25,
        "all_assets_ready": False,
    }
    assert len(binding["character_refs"]) == 3
    assert len(binding["scene_refs"]) == 3
    assert len(binding["shot_refs"]) == 15
    assert all(ref["current_approved_version_id"].endswith("-v1") for ref in binding["shot_refs"])
    assert binding["subject_digest"] == run["subject_digest"]
    assert len(binding["canon_digest"]) == 64
    canon = binding["episode_canon"]
    assert canon["episode_title"] == "《雨灯失窃案》第一集：最后一盏引魂灯"
    assert canon["duration_seconds"] == 135
    assert [item["entity_id"] for item in canon["shots"]] == [f"shot-{index:03d}" for index in range(1, 16)]
    assert [(item["start_seconds"], item["end_seconds"]) for item in canon["shots"]] == [
        ((index - 1) * 9, index * 9) for index in range(1, 16)
    ]
    assert all(item["audio_coverage"]["covered"] is True for item in canon["shots"])
    assert all(item["audio_coverage"]["status"] == "pending" for item in canon["shots"])
    assert canon["audio"]["readiness"] == {
        "asset_count": 4,
        "ready_count": 0,
        "pending_count": 4,
        "all_audio_ready": False,
    }
    assert binding["creator_decision_ref"] == "creator-decision-episode-v1"
    assert len(binding["authoritative_affected_task_refs"]) == 8
    assert len(binding["downstream_reconfirmations"]) == 8
    assert binding["propagation_complete"] is False
    assert len(binding["binding_digest"]) == 64
    assert replayed.status_code == 200
    assert replayed.json()["idempotent_replay"] is True
    assert conflicting_replay.status_code == 409
    assert "idempotency conflict" in conflicting_replay.text
    assert loaded.status_code == 200
    assert loaded.json()["representative_episode_binding"] == binding
    assert loaded.json()["checkpoint"] == bound.json()["production_run"]["checkpoint"]
    studio_episode = bound.json()["studio_binding"]["representative_episode"]
    assert studio_episode == {
        "authoritative_source": "runtime_production_run_checkpoint",
        "package_sha256": payload["package_sha256"],
        "binding_digest": binding["binding_digest"],
        "canon_digest": binding["canon_digest"],
        "episode_id": "ep-rainlight-001",
        "episode_title": "《雨灯失窃案》第一集：最后一盏引魂灯",
        "episode_version_id": "ep-rainlight-001-v1",
        "duration_seconds": 135,
        "character_count": 3,
        "scene_count": 3,
        "shot_count": 15,
        "asset_count": 25,
        "audio_item_count": 4,
        "pending_media_count": 25,
        "provider_needed_count": 25,
        "all_assets_ready": False,
        "creator_decision_ref": "creator-decision-episode-v1",
        "propagation_complete": False,
        "lineage": binding["lineage"],
    }

    reloaded_client = TestClient(create_runtime_app(runtime_root=tmp_path))
    reloaded = reloaded_client.get(route, headers=headers)
    assert reloaded.status_code == 200, reloaded.text
    assert reloaded.json()["representative_episode_binding"] == binding


def test_representative_episode_binding_rejects_stale_checkpoint_digest_and_foreign_project(
    tmp_path,
    monkeypatch,
) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    for project_id in ("afs-rainlight-project", "foreign-project"):
        created = client.post(
            "/projects",
            json={"project_id": project_id, "goal": "Episode binding isolation"},
            headers=headers,
        )
        assert created.status_code == 200, created.text
        run_response = client.post(
            f"/projects/{project_id}/production-runs",
            json={**_create_payload(), "run_id": f"run-{project_id}", "idempotency_key": f"create-{project_id}"},
            headers=headers,
        )
        assert run_response.status_code == 200, run_response.text

    route = "/projects/afs-rainlight-project/production-runs/run-afs-rainlight-project/representative-episode-binding"
    run = client.get(
        "/projects/afs-rainlight-project/production-runs/run-afs-rainlight-project",
        headers=headers,
    ).json()["production_run"]
    stale_checkpoint = client.put(
        route,
        json=_episode_binding_payload(run, expected_checkpoint_version=run["checkpoint"]["version"] + 1),
        headers=headers,
    )
    assert stale_checkpoint.status_code == 409
    assert stale_checkpoint.json()["detail"]["error"] == "stale_production_checkpoint"

    changed_subject = client.put(
        route,
        json=_episode_binding_payload(
            run,
            idempotency_key="bind-subject-conflict",
            expected_subject_digest=_digest("another-run-subject"),
        ),
        headers=headers,
    )
    assert changed_subject.status_code == 409
    assert changed_subject.json()["detail"]["error"] == "representative_episode_subject_conflict"

    bound = client.put(route, json=_episode_binding_payload(run), headers=headers)
    assert bound.status_code == 200, bound.text
    current = bound.json()["production_run"]
    stale_package = client.put(
        route,
        json=_episode_binding_payload(
            current,
            idempotency_key="bind-rainlight-episode-v2",
            expected_package_sha256=_digest("stale-package"),
        ),
        headers=headers,
    )
    assert stale_package.status_code == 409
    assert stale_package.json()["detail"]["error"] == "stale_representative_episode_package"

    foreign_route = "/projects/foreign-project/production-runs/run-foreign-project/representative-episode-binding"
    foreign_run = client.get(
        "/projects/foreign-project/production-runs/run-foreign-project",
        headers=headers,
    ).json()["production_run"]
    foreign = client.put(foreign_route, json=_episode_binding_payload(foreign_run), headers=headers)
    assert foreign.status_code == 409
    assert "another project" in foreign.text

    other = client.post(
        "/auth/register",
        json={"email": "episode-other@example.com", "password": "strong-password-789", "display_name": "Other"},
    )
    other_headers = {"Authorization": f"Bearer {other.json()['session_token']}"}
    denied = client.get(route, headers=other_headers)
    assert denied.status_code == 403


def test_representative_episode_binding_rejects_incomplete_or_inconsistent_inventory(
    tmp_path,
    monkeypatch,
) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    project_id = "afs-rainlight-project"
    client.post("/projects", json={"project_id": project_id, "goal": "Inventory validation"}, headers=headers)
    run = client.post(
        f"/projects/{project_id}/production-runs",
        json=_create_payload(),
        headers=headers,
    ).json()["production_run"]
    route = f"/projects/{project_id}/production-runs/{run['run_id']}/representative-episode-binding"
    incomplete = _episode_binding_payload(run)
    incomplete["shot_refs"] = incomplete["shot_refs"][:-1]
    mismatched = _episode_binding_payload(run, idempotency_key="bind-readiness-mismatch")
    mismatched["pending_media_count"] = 24
    missing_reconfirmation = _episode_binding_payload(run, idempotency_key="bind-reconfirmation-missing")
    missing_reconfirmation["downstream_reconfirmations"] = missing_reconfirmation["downstream_reconfirmations"][:-1]
    unsafe_task_ref = _episode_binding_payload(run, idempotency_key="bind-unsafe-task-ref")
    unsafe_task_ref["authoritative_affected_task_refs"][0] = "../foreign-task"
    reordered = _episode_binding_payload(run, idempotency_key="bind-reordered-shots")
    reordered["episode_canon"]["shots"][0], reordered["episode_canon"]["shots"][1] = (
        reordered["episode_canon"]["shots"][1],
        reordered["episode_canon"]["shots"][0],
    )
    timeline_gap = _episode_binding_payload(run, idempotency_key="bind-timeline-gap")
    timeline_gap["episode_canon"]["shots"][1]["start_seconds"] = 10
    duplicate_shot = _episode_binding_payload(run, idempotency_key="bind-duplicate-shot")
    duplicate_shot["episode_canon"]["shots"][1]["entity_id"] = "shot-001"
    stale_version = _episode_binding_payload(run, idempotency_key="bind-stale-version")
    stale_version["episode_canon"]["shots"][0]["current_approved_version_id"] = "shot-001-v2"
    foreign_scene = _episode_binding_payload(run, idempotency_key="bind-foreign-scene")
    foreign_scene["episode_canon"]["shots"][0]["scene_ref"] = {
        "entity_id": "scene-foreign",
        "current_approved_version_id": "scene-foreign-v1",
    }
    incomplete_audio = _episode_binding_payload(run, idempotency_key="bind-incomplete-audio")
    incomplete_audio["episode_canon"]["audio"]["coverage_shot_refs"].pop()
    foreign_asset = _episode_binding_payload(run, idempotency_key="bind-foreign-asset")
    foreign_asset["episode_canon"]["shots"][0]["required_asset_ids"][0] = "asset-foreign"

    for invalid in (
        incomplete,
        mismatched,
        missing_reconfirmation,
        unsafe_task_ref,
        reordered,
        timeline_gap,
        duplicate_shot,
        stale_version,
        foreign_scene,
        incomplete_audio,
        foreign_asset,
    ):
        assert client.put(route, json=invalid, headers=headers).status_code == 422
    unchanged = client.get(f"/projects/{project_id}/production-runs/{run['run_id']}", headers=headers)
    assert unchanged.status_code == 200
    assert unchanged.json()["production_run"]["checkpoint"] == run["checkpoint"]
    assert unchanged.json()["production_run"]["representative_episode_binding"] is None


def test_create_list_get_and_idempotent_replay_persist_checkpoint(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    payload = _create_payload()

    created = client.post(
        "/projects/owned-project/production-runs",
        json=payload,
        headers=headers,
    )
    replayed = client.post(
        "/projects/owned-project/production-runs",
        json=payload,
        headers=headers,
    )
    listed = client.get("/projects/owned-project/production-runs", headers=headers)
    loaded = client.get(
        "/projects/owned-project/production-runs/production-run-001",
        headers=headers,
    )

    assert created.status_code == 200, created.text
    assert created.json()["idempotent_replay"] is False
    run = created.json()["production_run"]
    assert run["project_id"] == "owned-project"
    assert run["run_id"] == "production-run-001"
    assert run["status"] == "candidates_ready"
    assert run["subject_digest"] == payload["subject_digest"]
    assert run["candidates"][0]["canonical_digest"] == payload["candidates"][0]["canonical_digest"]
    assert run["selected_revision"] is None
    assert run["checkpoint"]["schema_version"] == "afs_runtime_production_checkpoint.v0.1"
    assert run["checkpoint"]["version"] == 1
    assert len(run["checkpoint"]["state_digest"]) == 64
    assert created.json()["studio_binding"] == {
        "schema_version": "afs_studio_production_binding.v0.1",
        "authoritative_source": "runtime_production_run",
        "compatibility_mode": "backend_authoritative_summary_only",
        "active_run_id": "production-run-001",
        "checkpoint_version": 1,
        "checkpoint_digest": run["checkpoint"]["state_digest"],
        "subject_digest": run["subject_digest"],
    }
    assert replayed.status_code == 200
    assert replayed.json()["idempotent_replay"] is True
    assert replayed.json()["production_run"] == run
    assert [item["run_id"] for item in listed.json()["production_runs"]] == ["production-run-001"]
    assert loaded.json()["production_run"] == run

    persisted = json.loads(
        (tmp_path / "projects" / "owned-project" / "production_runs" / "production-run-001" / "production_run.json")
        .read_text(encoding="utf-8")
    )
    assert persisted == run
    manifest = json.loads(
        (tmp_path / "projects" / "owned-project" / "project_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["runs"] == [
        {
            "run_id": "production-run-001",
            "artifact_type": "afs_runtime_production_run",
            "schema_version": "afs_runtime_production_run.v0.1",
            "status": "candidates_ready",
        }
    ]


def test_create_idempotency_key_rejects_changed_subject(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    payload = _create_payload()
    assert client.post(
        "/projects/owned-project/production-runs",
        json=payload,
        headers=headers,
    ).status_code == 200
    payload["subject_digest"] = _digest("changed-subject")

    conflict = client.post(
        "/projects/owned-project/production-runs",
        json=payload,
        headers=headers,
    )

    assert conflict.status_code == 409
    assert "idempotency conflict" in conflict.text


def test_creator_decision_enforces_checkpoint_subject_candidate_and_idempotency(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    run = _create_run(client, headers)
    route = "/projects/owned-project/production-runs/production-run-001/creator-decisions"

    stale = client.post(route, json=_creator_decision(run, expected_checkpoint_version=2), headers=headers)
    changed_subject = client.post(route, json=_creator_decision(run, subject_digest=_digest("changed")), headers=headers)
    changed_candidate = client.post(route, json=_creator_decision(run, candidate_digest=_digest("changed")), headers=headers)
    selected = client.post(route, json=_creator_decision(run), headers=headers)
    replayed = client.post(route, json=_creator_decision(run), headers=headers)
    idempotency_conflict = client.post(
        route,
        json=_creator_decision(run, revision_intent="A changed request with a reused key."),
        headers=headers,
    )

    assert stale.status_code == 409
    assert stale.json()["detail"]["error"] == "stale_production_checkpoint"
    assert changed_subject.status_code == 409
    assert "subject digest changed" in changed_subject.text
    assert changed_candidate.status_code == 409
    assert "candidate digest changed" in changed_candidate.text
    assert selected.status_code == 200, selected.text
    selected_run = selected.json()["production_run"]
    revision = selected_run["selected_revision"]
    assert selected_run["checkpoint"]["version"] == 2
    assert selected_run["checkpoint"]["previous_digest"] == run["checkpoint"]["state_digest"]
    assert revision["candidate_id"] == run["candidates"][0]["candidate_id"]
    assert revision["candidate_digest"] == run["candidates"][0]["canonical_digest"]
    assert revision["creator_decision_id"] == "decision-001"
    assert revision["parent_job_id"] == "job-keyframe-001"
    assert len(revision["canonical_digest"]) == 64
    assert len(revision["subject_digest"]) == 64
    assert replayed.status_code == 200
    assert replayed.json()["idempotent_replay"] is True
    assert replayed.json()["production_run"] == selected_run
    assert idempotency_conflict.status_code == 409
    assert "idempotency conflict" in idempotency_conflict.text


def test_selected_revision_lineage_supports_creator_revision_and_reload_recovery(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    run = _create_run(client, headers)
    route = "/projects/owned-project/production-runs/production-run-001/creator-decisions"
    selected = client.post(route, json=_creator_decision(run), headers=headers).json()["production_run"]
    first_revision = selected["selected_revision"]
    revised_payload = _creator_decision(
        selected,
        decision_id="decision-002",
        idempotency_key="creator-decision-002",
        decision="revise",
        parent_revision_id=first_revision["revision_id"],
        revision_intent="Keep the chosen composition and strengthen the character reaction.",
    )

    revised_response = client.post(route, json=revised_payload, headers=headers)

    assert revised_response.status_code == 200, revised_response.text
    revised = revised_response.json()["production_run"]
    second_revision = revised["selected_revision"]
    assert revised["checkpoint"]["version"] == 3
    assert second_revision["parent_revision_id"] == first_revision["revision_id"]
    assert second_revision["revision_id"] != first_revision["revision_id"]
    assert {
        "source_ref": first_revision["revision_id"],
        "target_ref": second_revision["revision_id"],
        "relation": "revision_revised_to_revision",
    } in revised["lineage"]

    restarted_client = TestClient(create_runtime_app(runtime_root=tmp_path))
    recovered = restarted_client.get(
        "/projects/owned-project/production-runs/production-run-001",
        headers=headers,
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["production_run"] == revised


def test_quality_review_and_export_bind_selected_revision_with_hash_readback(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    created = _create_run(client, headers)
    decision_route = "/projects/owned-project/production-runs/production-run-001/creator-decisions"
    selected = client.post(decision_route, json=_creator_decision(created), headers=headers).json()["production_run"]
    revision = selected["selected_revision"]
    review_payload = {
        "schema_version": "afs_production_quality_review.v0.1",
        "review_id": "quality-review-001",
        "idempotency_key": "quality-review-001",
        "expected_checkpoint_version": selected["checkpoint"]["version"],
        "reviewed_subject_digest": revision["subject_digest"],
        "selected_revision_id": revision["revision_id"],
        "selected_revision_digest": revision["canonical_digest"],
        "decision": "approve",
        "checklist": {
            "story_intent_preserved": True,
            "character_continuity_checked": True,
            "shot_coverage_checked": True,
            "revision_addressed": True,
        },
        "note": "Deterministic contract review only; not human acceptance.",
    }
    review_route = "/projects/owned-project/production-runs/production-run-001/quality-reviews"
    reviewed_response = client.post(review_route, json=review_payload, headers=headers)
    assert reviewed_response.status_code == 200, reviewed_response.text
    reviewed = reviewed_response.json()["production_run"]
    assert reviewed["checkpoint"]["version"] == 3
    assert reviewed["quality_reviews"][-1]["human_acceptance_claimed"] is False

    export_payload = {
        "schema_version": "afs_production_export.v0.1",
        "export_id": "export-001",
        "idempotency_key": "export-001",
        "expected_checkpoint_version": reviewed["checkpoint"]["version"],
        "selected_revision_id": revision["revision_id"],
        "selected_revision_digest": revision["canonical_digest"],
    }
    export_route = "/projects/owned-project/production-runs/production-run-001/exports"
    changed_export = client.post(
        export_route,
        json={**export_payload, "selected_revision_digest": _digest("changed")},
        headers=headers,
    )
    exported_response = client.post(export_route, json=export_payload, headers=headers)
    replayed = client.post(export_route, json=export_payload, headers=headers)

    assert changed_export.status_code == 409
    assert exported_response.status_code == 200, exported_response.text
    exported = exported_response.json()
    run = exported["production_run"]
    export = exported["export"]
    assert run["status"] == "exported"
    assert run["checkpoint"]["version"] == 4
    assert export["selected_revision_id"] == revision["revision_id"]
    assert export["selected_revision_digest"] == revision["canonical_digest"]
    assert len(export["delivery_sha256"]) == 64
    assert exported["studio_binding"]["last_export_id"] == "export-001"
    assert exported["studio_binding"]["selected_revision_id"] == revision["revision_id"]
    assert replayed.status_code == 200
    assert replayed.json()["idempotent_replay"] is True
    assert replayed.json()["export"] == export

    artifact = client.get(f"/artifacts/{export['artifact']['artifact_id']}", headers=headers)
    assert artifact.status_code == 200, artifact.text
    delivery = artifact.json()["payload"]
    assert delivery["selected_revision"]["revision_id"] == revision["revision_id"]
    assert delivery["selected_revision"]["canonical_digest"] == revision["canonical_digest"]
    assert delivery["quality_review_ref"] == "quality-review-001"
    delivery_path = (
        tmp_path
        / "projects"
        / "owned-project"
        / "production_runs"
        / "production-run-001"
        / "exports"
        / "export-001"
        / "production_delivery.json"
    )
    assert hashlib.sha256(delivery_path.read_bytes()).hexdigest() == export["delivery_sha256"]

    restarted_client = TestClient(create_runtime_app(runtime_root=tmp_path))
    recovered = restarted_client.get(
        "/projects/owned-project/production-runs/production-run-001",
        headers=headers,
    )
    assert recovered.status_code == 200, recovered.text
    assert recovered.json()["production_run"]["exports"] == [export]

    delivery_path.write_text(json.dumps({**delivery, "quality_review_ref": "tampered"}), encoding="utf-8")
    tampered_readback = restarted_client.get(
        "/projects/owned-project/production-runs/production-run-001",
        headers=headers,
    )
    assert tampered_readback.status_code == 409
    assert "export artifact integrity mismatch" in tampered_readback.text


def test_authenticated_multi_candidate_creator_flow_restores_and_exports_selected_revision_lineage(
    tmp_path, monkeypatch
) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    created_response = client.post(
        "/projects/owned-project/production-runs",
        json=_create_payload(),
        headers=headers,
    )
    assert created_response.status_code == 200, created_response.text
    created = created_response.json()["production_run"]
    candidate = created["candidates"][1]
    decision_route = "/projects/owned-project/production-runs/production-run-001/creator-decisions"

    selected_response = client.post(
        decision_route,
        json=_creator_decision(
            created,
            decision_id="decision-select-candidate-002",
            idempotency_key="decision-select-candidate-002",
            candidate_id=candidate["candidate_id"],
            candidate_digest=candidate["canonical_digest"],
        ),
        headers=headers,
    )
    assert selected_response.status_code == 200, selected_response.text
    selected = selected_response.json()["production_run"]
    selected_revision = selected["selected_revision"]

    refreshed = client.get(
        "/projects/owned-project/production-runs/production-run-001",
        headers=headers,
    )
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["studio_binding"]["selected_candidate_id"] == "candidate-002"
    assert refreshed.json()["studio_binding"]["selected_revision_id"] == selected_revision["revision_id"]

    revised_response = client.post(
        decision_route,
        json=_creator_decision(
            selected,
            decision_id="decision-revise-candidate-002",
            idempotency_key="decision-revise-candidate-002",
            decision="revise",
            candidate_id=candidate["candidate_id"],
            candidate_digest=candidate["canonical_digest"],
            parent_revision_id=selected_revision["revision_id"],
            revision_intent="Keep the selected composition and refine the key light.",
        ),
        headers=headers,
    )
    assert revised_response.status_code == 200, revised_response.text
    revised = revised_response.json()["production_run"]
    revision = revised["selected_revision"]
    assert revision["candidate_id"] == "candidate-002"
    assert revision["parent_revision_id"] == selected_revision["revision_id"]

    review_payload = {
        "schema_version": "afs_production_quality_review.v0.1",
        "review_id": "quality-review-selected-revision",
        "idempotency_key": "quality-review-selected-revision",
        "expected_checkpoint_version": revised["checkpoint"]["version"],
        "reviewed_subject_digest": revision["subject_digest"],
        "selected_revision_id": revision["revision_id"],
        "selected_revision_digest": revision["canonical_digest"],
        "decision": "approve",
        "checklist": {
            "story_intent_preserved": True,
            "character_continuity_checked": True,
            "shot_coverage_checked": True,
            "revision_addressed": True,
        },
        "note": "Automated contract review only; not human acceptance.",
    }
    reviewed_response = client.post(
        "/projects/owned-project/production-runs/production-run-001/quality-reviews",
        json=review_payload,
        headers=headers,
    )
    assert reviewed_response.status_code == 200, reviewed_response.text
    reviewed = reviewed_response.json()["production_run"]

    export_response = client.post(
        "/projects/owned-project/production-runs/production-run-001/exports",
        json={
            "schema_version": "afs_production_export.v0.1",
            "export_id": "export-selected-revision",
            "idempotency_key": "export-selected-revision",
            "expected_checkpoint_version": reviewed["checkpoint"]["version"],
            "selected_revision_id": revision["revision_id"],
            "selected_revision_digest": revision["canonical_digest"],
        },
        headers=headers,
    )
    assert export_response.status_code == 200, export_response.text
    exported = export_response.json()
    assert exported["studio_binding"]["last_export_id"] == "export-selected-revision"
    artifact = client.get(f"/artifacts/{exported['export']['artifact']['artifact_id']}", headers=headers)
    assert artifact.status_code == 200, artifact.text
    delivery = artifact.json()["payload"]
    assert delivery["selected_revision"]["revision_id"] == revision["revision_id"]
    assert {item["relation"] for item in delivery["lineage"]} >= {
        "candidate_received_creator_decision",
        "candidate_selected_as_revision",
        "creator_decision_defined_revision",
        "revision_revised_to_revision",
        "selected_revision_quality_reviewed",
    }


def test_checkpoint_tampering_fails_closed_on_readback(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    _create_run(client, headers)
    state_path = (
        tmp_path / "projects" / "owned-project" / "production_runs" / "production-run-001" / "production_run.json"
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["subject_digest"] = _digest("tampered")
    state_path.write_text(json.dumps(state), encoding="utf-8")

    response = client.get(
        "/projects/owned-project/production-runs/production-run-001",
        headers=headers,
    )

    assert response.status_code == 409
    assert "checkpoint integrity mismatch" in response.text


def test_checkpoint_version_tampering_with_unchanged_digest_fails_closed(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    run = _create_run(client, headers)
    state_path = (
        tmp_path / "projects" / "owned-project" / "production_runs" / "production-run-001" / "production_run.json"
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    original_digest = state["checkpoint"]["state_digest"]
    state["checkpoint"]["version"] = 99
    state_path.write_text(json.dumps(state), encoding="utf-8")

    readback = client.get(
        "/projects/owned-project/production-runs/production-run-001",
        headers=headers,
    )
    mutation = client.post(
        "/projects/owned-project/production-runs/production-run-001/creator-decisions",
        json=_creator_decision(run, expected_checkpoint_version=99),
        headers=headers,
    )

    assert state["checkpoint"]["state_digest"] == original_digest
    assert readback.status_code == 409
    assert "checkpoint integrity mismatch" in readback.text
    assert mutation.status_code == 409
    assert "checkpoint integrity mismatch" in mutation.text


def test_pr127_deterministic_candidates_bridge_into_authenticated_project_run(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path / "runtime", monkeypatch)
    project = ProjectIP(
        project_id="owned-project",
        title="Deterministic bridge",
        premise="A creator compares governed shot treatments.",
        audience="internal creator",
        format="short-form storyboard",
        tone="cinematic",
        characters=[
            CharacterSeed(
                character_id="hero-001",
                name="Hero",
                role="lead",
                visual_anchor="red scarf and dark jacket",
            )
        ],
    )
    deterministic = DeterministicProductionSlice(project, tmp_path / "deterministic")
    deterministic.advance_to_candidates()
    candidates = deterministic.state["artifacts"]["candidates"]
    payload = {
        "schema_version": "afs_runtime_production_run.v0.1",
        "run_id": "production-run-pr127-bridge",
        "idempotency_key": "create-pr127-bridge",
        "subject_digest": canonical_json_digest(project.model_dump(mode="json")),
        "candidates": [
            {
                "candidate_id": item["candidate_id"],
                "canonical_digest": canonical_json_digest(item),
                "parent_job_id": deterministic.state["run_id"],
                "shot_id": item["shot_id"],
                "safe_artifact_refs": [],
            }
            for item in candidates
        ],
    }

    created = client.post(
        "/projects/owned-project/production-runs",
        json=payload,
        headers=headers,
    )

    assert created.status_code == 200, created.text
    run = created.json()["production_run"]
    assert len(run["candidates"]) == 6
    assert {item["shot_id"] for item in run["candidates"]} == {"shot_001", "shot_002", "shot_003"}
    assert all(item["parent_job_id"] == deterministic.state["run_id"] for item in run["candidates"])


def test_studio_state_resolves_production_binding_from_authenticated_ledger(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    run = _create_run(client, headers)
    forged_digest = _digest("forged-binding")

    response = client.put(
        "/projects/owned-project/studio-state",
        json={
            "state": {
                "production": {
                    "schema_version": "client-invented-version",
                    "authoritative_source": "client",
                    "compatibility_mode": "client_can_overwrite",
                    "active_run_id": "forged-run",
                    "checkpoint_version": 99,
                    "checkpoint_digest": forged_digest,
                    "subject_digest": forged_digest,
                    "selected_candidate_id": "forged-candidate",
                    "selected_candidate_digest": forged_digest,
                    "selected_revision_id": "forged-revision",
                    "selected_revision_digest": forged_digest,
                    "last_export_id": "forged-export",
                    "provider_response": "must not persist",
                }
            }
        },
        headers=headers,
    )

    assert response.status_code == 200, response.text
    binding = response.json()["state"]["production"]
    assert binding == {
        "schema_version": "afs_studio_production_binding.v0.1",
        "authoritative_source": "runtime_production_run",
        "compatibility_mode": "backend_authoritative_summary_only",
        "active_run_id": "production-run-001",
        "checkpoint_version": 1,
        "checkpoint_digest": run["checkpoint"]["state_digest"],
        "subject_digest": run["subject_digest"],
    }
    assert "provider_response" not in json.dumps(binding)
    assert "forged" not in json.dumps(binding)

    restored = client.get("/projects/owned-project/studio-state", headers=headers)
    assert restored.status_code == 200
    assert restored.json()["state"]["production"] == binding

    persisted = json.loads(
        (tmp_path / "projects" / "owned-project" / "studio_state.json").read_text(encoding="utf-8")
    )
    assert persisted["state"]["production"] == binding


def test_artifact_index_registration_is_transactional_across_threads(tmp_path, monkeypatch) -> None:
    stores = [RuntimeStore(tmp_path), RuntimeStore(tmp_path)]
    paths = [tmp_path / "runs" / f"thread-{index}" / "artifact.json" for index in range(2)]
    for index, path in enumerate(paths):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"artifact_type": f"thread-artifact-{index}"}), encoding="utf-8")

    read_barrier = threading.Barrier(2)
    for store in stores:
        original_artifact_index = store._artifact_index

        def synchronized_artifact_index(original=original_artifact_index):
            index = original()
            try:
                read_barrier.wait(timeout=0.2)
            except threading.BrokenBarrierError:
                pass
            return index

        monkeypatch.setattr(store, "_artifact_index", synchronized_artifact_index)
    errors: list[BaseException] = []

    def register(store: RuntimeStore, path: Path) -> None:
        try:
            store.register_artifact(path, role="production_export")
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    threads = [threading.Thread(target=register, args=(store, path)) for store, path in zip(stores, paths)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert not errors
    assert all(not thread.is_alive() for thread in threads)
    index = json.loads(stores[0].index_path.read_text(encoding="utf-8"))
    assert set(index["artifacts"]) == {"runs-thread-0-artifact", "runs-thread-1-artifact"}


def test_artifact_index_constructor_cannot_overwrite_concurrent_registration(tmp_path, monkeypatch) -> None:
    registration_store = RuntimeStore(tmp_path)
    artifact_path = tmp_path / "runs" / "constructor-race" / "artifact.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_path.write_text(json.dumps({"artifact_type": "constructor-race-artifact"}), encoding="utf-8")

    constructor_read = threading.Event()
    allow_constructor_write = threading.Event()
    registration_lock_attempted = threading.Event()
    original_artifact_index = RuntimeStore._artifact_index
    original_exclusive_file_lock = runtime_store_module.exclusive_file_lock
    transaction_lock = threading.Lock()

    class ControlledTransactionLock:
        def __enter__(self):
            if threading.current_thread().name == "artifact-registration":
                registration_lock_attempted.set()
            transaction_lock.acquire()

        def __exit__(self, exc_type, exc_value, traceback):
            transaction_lock.release()

    def controlled_exclusive_file_lock(path: Path):
        if Path(path) == registration_store.index_transaction_lock_path:
            return ControlledTransactionLock()
        return original_exclusive_file_lock(path)

    def pause_constructor_after_read(store: RuntimeStore):
        index = original_artifact_index(store)
        if threading.current_thread().name == "runtime-store-constructor":
            constructor_read.set()
            if not allow_constructor_write.wait(timeout=2):
                raise TimeoutError("constructor write was not released")
        return index

    monkeypatch.setattr(RuntimeStore, "_artifact_index", pause_constructor_after_read)
    monkeypatch.setattr(runtime_store_module, "exclusive_file_lock", controlled_exclusive_file_lock)
    errors: list[BaseException] = []

    def construct_store() -> None:
        try:
            RuntimeStore(tmp_path)
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    def register_artifact() -> None:
        try:
            registration_store.register_artifact(artifact_path, role="production_export")
        except BaseException as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    constructor_thread = threading.Thread(target=construct_store, name="runtime-store-constructor")
    constructor_thread.start()
    assert constructor_read.wait(timeout=2)
    constructor_holds_transaction_lock = transaction_lock.locked()

    registration_thread = threading.Thread(target=register_artifact, name="artifact-registration")
    registration_thread.start()
    assert registration_lock_attempted.wait(timeout=2)
    allow_constructor_write.set()
    constructor_thread.join(timeout=2)
    registration_thread.join(timeout=2)

    assert not errors
    assert not constructor_thread.is_alive()
    assert not registration_thread.is_alive()
    assert constructor_holds_transaction_lock
    index = json.loads(registration_store.index_path.read_text(encoding="utf-8"))
    assert set(index["artifacts"]) == {"runs-constructor-race-artifact"}


def test_soft_deleted_project_rejects_new_production_run(tmp_path, monkeypatch) -> None:
    client, headers = _registered_client(tmp_path, monkeypatch)
    deleted = client.delete("/projects/owned-project", headers=headers)
    created = client.post(
        "/projects/owned-project/production-runs",
        json=_create_payload(),
        headers=headers,
    )

    assert deleted.status_code == 200, deleted.text
    assert created.status_code == 404
    assert "project not found" in created.text


def test_studio_client_and_store_expose_frozen_production_contract() -> None:
    runtime_client = (REPO_ROOT / "apps" / "studio" / "src" / "runtime-client.js").read_text(encoding="utf-8")
    store_state = (REPO_ROOT / "apps" / "studio" / "src" / "store-state.js").read_text(encoding="utf-8")

    for method in (
        "createProductionRun",
        "listProductionRuns",
        "getProductionRun",
        "submitCreatorDecision",
        "recordProductionQualityReview",
        "exportProductionRun",
    ):
        assert f"{method}(" in runtime_client
    assert 'authoritative_source: "runtime_production_run"' in store_state
    assert "stripProductionAuthority: true" in store_state

    script = r"""
import { initialState, normalizeSnapshot, snapshotStudioState } from "./apps/studio/src/store-state.js";
const binding = {
  schema_version: "afs_studio_production_binding.v0.1",
  authoritative_source: "runtime_production_run",
  compatibility_mode: "backend_authoritative_summary_only",
  active_run_id: "production-run-001",
  checkpoint_version: 7,
  checkpoint_digest: "a".repeat(64),
  subject_digest: "b".repeat(64),
};
const hydrated = normalizeSnapshot({ ...initialState("owned-project"), production: binding });
const persisted = snapshotStudioState({ ...initialState("owned-project"), production: binding });
process.stdout.write(JSON.stringify({ hydrated: hydrated.production, persisted: persisted.production }));
"""
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    result = json.loads(completed.stdout)
    assert result["hydrated"]["active_run_id"] == "production-run-001"
    assert result["hydrated"]["checkpoint_version"] == 7
    assert result["persisted"] == {}
    assert 'compatibility_mode: "backend_authoritative_summary_only"' in store_state
