from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from apps.api.runtime_episode_domain_contract import (
    AssetCandidateVersion,
    EpisodeVersion,
    ProductionProjectAggregate,
    ProjectDataPolicy,
    ProjectVersion,
    SafeArtifactRef,
    SceneVersion,
    SeriesVersion,
    ShotVersion,
    TenantScope,
)
from apps.api.runtime_episode_domain_store import EpisodeDomainAggregateStore
from apps.api.runtime_episode_workspace_projection import (
    WorkspaceProjectionReferenceError,
    WorkspaceProjectionStateError,
    build_episode_workspace_projection,
)
from apps.api.runtime_service import create_runtime_app


BASE_TIME = "2026-07-15T08:00:00+00:00"
LATER_TIME = "2026-07-15T08:01:00+00:00"
PROJECT_ID = "project-1"


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def _common(
    scope: TenantScope,
    entity_id: str,
    *,
    version_id: str | None = None,
    revision: int = 1,
    parent_version_id: str | None = None,
    created_at: str = BASE_TIME,
    content_digest: str | None = None,
) -> dict[str, object]:
    return {
        "entity_id": entity_id,
        "version_id": version_id or f"{entity_id}.v{revision}",
        "revision": revision,
        "parent_version_id": parent_version_id,
        "lifecycle_state": "draft",
        "review_state": "not_requested",
        "content_digest": content_digest or _digest(entity_id),
        "scope": scope,
        "created_at": created_at,
    }


def _aggregate(
    *,
    scope: TenantScope | None = None,
    shot_count: int = 3,
    include_missing_candidate: bool = False,
    project_title: str = "雨夜追光",
) -> ProductionProjectAggregate:
    scope = scope or TenantScope(
        org_id="org-1", project_id=PROJECT_ID, actor_id="creator-1"
    )
    project = ProjectVersion(
        **_common(scope, PROJECT_ID),
        title=project_title,
        data_policy=ProjectDataPolicy(),
    )
    series = SeriesVersion(
        **_common(scope, "series-1"), project_ref=project.as_ref(), title="第一季"
    )
    episode = EpisodeVersion(
        **_common(scope, "episode-1"), series_ref=series.as_ref(), title="第一集"
    )
    scene = SceneVersion(
        **_common(scope, "scene-1"),
        episode_ref=episode.as_ref(),
        sequence=1,
        title="巷口",
    )
    shots = tuple(
        ShotVersion(
            **_common(scope, f"shot-{sequence}"),
            scene_ref=scene.as_ref(),
            sequence=sequence,
            duration_seconds=3,
        )
        for sequence in range(1, shot_count + 1)
    )
    candidates: tuple[AssetCandidateVersion, ...] = ()
    if include_missing_candidate:
        candidates = (
            AssetCandidateVersion(
                **_common(scope, "candidate-1"),
                target_ref=shots[0].as_ref(),
                job_id="job-1",
                job_state="queued",
            ),
        )
    return ProductionProjectAggregate(
        aggregate_version=1,
        evaluated_at=BASE_TIME,
        scope=scope,
        projects=(project,),
        series=(series,),
        episodes=(episode,),
        scenes=(scene,),
        shots=shots,
        asset_candidates=candidates,
    )


def _projection(aggregate: ProductionProjectAggregate) -> dict[str, Any]:
    return build_episode_workspace_projection(
        aggregate, episode_ref=aggregate.episodes[-1].as_ref()
    )


def _register(client: TestClient, invite_code: str, email: str) -> dict[str, Any]:
    response = client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "strong-password-123",
            "display_name": email.split("@", 1)[0],
            "invite_code": invite_code,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def _headers(user: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {user['session_token']}"}


def _auth_client(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "owner-invite,other-invite")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    owner = _register(client, "owner-invite", "owner@example.com")
    other = _register(client, "other-invite", "other@example.com")
    created = client.post(
        "/projects",
        headers=_headers(owner),
        json={"project_id": PROJECT_ID, "goal": "Produce one episode"},
    )
    assert created.status_code == 200, created.text
    return client, owner, other


def _store_aggregate(tmp_path: Path, aggregate: ProductionProjectAggregate) -> None:
    EpisodeDomainAggregateStore(tmp_path).save(
        aggregate,
        expected_aggregate_version=0,
        idempotency_key="workspace-fixture",
        payload_digest=_digest(aggregate.model_dump(mode="json")),
    )


def _route() -> str:
    return (
        f"/projects/{PROJECT_ID}/episodes/episode-1/versions/episode-1.v1/workspace"
    )


def _error(response) -> str:
    return str(response.json().get("detail", {}).get("error") or "")


def test_projection_is_deterministic_and_uses_only_latest_exact_facts() -> None:
    aggregate = _aggregate(include_missing_candidate=True)
    candidate_v1 = aggregate.asset_candidates[0]
    candidate_v2 = candidate_v1.model_copy(
        update={
            "version_id": "candidate-1.v2",
            "revision": 2,
            "parent_version_id": candidate_v1.version_id,
            "created_at": LATER_TIME,
            "artifact_ref": SafeArtifactRef(
                artifact_id="artifact-1",
                artifact_type="image",
                content_digest=_digest("artifact-1"),
            ),
            "job_state": "succeeded",
        }
    )
    updated = ProductionProjectAggregate.model_validate(
        {
            **aggregate.model_dump(mode="python"),
            "evaluated_at": LATER_TIME,
            "asset_candidates": (candidate_v1, candidate_v2),
        }
    )
    reordered = ProductionProjectAggregate.model_validate(
        {
            **updated.model_dump(mode="python"),
            "shots": tuple(reversed(updated.shots)),
            "asset_candidates": tuple(reversed(updated.asset_candidates)),
        }
    )

    first = _projection(updated)
    second = _projection(reordered)

    assert first == second
    assert first["workspace"]["shots"][0]["candidates"] == [
        {
            "ref": candidate_v2.as_ref().model_dump(mode="json"),
            "label": "候选 1",
            "status_label": "候选",
            "summary": None,
            "artifact_present": True,
            "job_state": "succeeded",
        }
    ]
    assert first["workspace"]["truth"]["missing_asset_count"] == 0


def test_empty_episode_is_truthful_and_does_not_invent_recovery_or_progress() -> None:
    aggregate = _aggregate(shot_count=0)

    projection = _projection(aggregate)

    workspace = projection["workspace"]
    assert workspace["shots"] == []
    assert workspace["next_action"] is None
    assert workspace["recovery"] is None
    assert workspace["truth"] == {
        "scene_count": 1,
        "shot_count": 0,
        "duration_seconds": 0,
        "missing_asset_count": 0,
        "generation_dispatch_count": 0,
        "playable_preview_available": False,
    }
    assert "progress" not in workspace
    assert workspace["delivery"]["blockers"] == ["delivery_not_frozen"]


def test_sixty_shots_remain_exact_without_fixture_defaults_or_media_claims() -> None:
    projection = _projection(_aggregate(shot_count=60))

    workspace = projection["workspace"]
    assert len(workspace["shots"]) == 60
    assert [item["sequence"] for item in workspace["shots"]] == list(range(1, 61))
    assert workspace["truth"]["shot_count"] == 60
    assert workspace["truth"]["duration_seconds"] == 180
    assert workspace["truth"]["missing_asset_count"] == 0
    assert workspace["truth"]["generation_dispatch_count"] == 0
    assert workspace["truth"]["playable_preview_available"] is False
    assert workspace["recovery"] is None
    assert all(item["script"] is None for item in workspace["shots"])
    assert all(item["thumbnail_url"] is None for item in workspace["shots"])


def test_known_missing_candidate_counts_one_not_rainlight_fixture_default() -> None:
    projection = _projection(_aggregate(include_missing_candidate=True))

    assert projection["workspace"]["truth"]["missing_asset_count"] == 1
    assert projection["workspace"]["delivery"]["missing_asset_count"] == 1


def test_stale_episode_ref_and_ambiguous_sequence_fail_closed() -> None:
    aggregate = _aggregate(shot_count=2)
    episode_v1 = aggregate.episodes[0]
    episode_v2 = episode_v1.model_copy(
        update={
            "version_id": "episode-1.v2",
            "revision": 2,
            "parent_version_id": episode_v1.version_id,
            "created_at": LATER_TIME,
        }
    )
    revised = ProductionProjectAggregate.model_validate(
        {
            **aggregate.model_dump(mode="python"),
            "evaluated_at": LATER_TIME,
            "episodes": (episode_v1, episode_v2),
        }
    )
    duplicate_sequence = aggregate.shots[1].model_copy(update={"sequence": 1})
    ambiguous = ProductionProjectAggregate.model_validate(
        {
            **aggregate.model_dump(mode="python"),
            "shots": (aggregate.shots[0], duplicate_sequence),
        }
    )
    duplicate_scene = aggregate.scenes[0].model_copy(
        update={"entity_id": "scene-2", "version_id": "scene-2.v1"}
    )
    ambiguous_scenes = ProductionProjectAggregate.model_validate(
        {
            **aggregate.model_dump(mode="python"),
            "scenes": (*aggregate.scenes, duplicate_scene),
        }
    )

    with pytest.raises(WorkspaceProjectionReferenceError, match="stale"):
        build_episode_workspace_projection(revised, episode_ref=episode_v1.as_ref())
    with pytest.raises(WorkspaceProjectionStateError, match="ambiguous"):
        _projection(ambiguous)
    with pytest.raises(WorkspaceProjectionStateError, match="ambiguous"):
        _projection(ambiguous_scenes)


def test_actor_scope_drift_fails_closed() -> None:
    aggregate = _aggregate()
    foreign_scope = aggregate.scope.model_copy(update={"actor_id": "other-creator"})
    foreign_shot = aggregate.shots[0].model_copy(update={"scope": foreign_scope})
    cross_scope = aggregate.model_copy(
        update={"shots": (foreign_shot, *aggregate.shots[1:])}
    )
    with pytest.raises(WorkspaceProjectionStateError, match="exact tenant"):
        _projection(cross_scope)


@pytest.mark.parametrize(
    "unsafe_text",
    (
        r"D:\private\snapshot.json",
        "%44%3A%5Cprivate%5Csnapshot.json",
        "file:///home/afs/private/episode.json",
        "https://cdn.example/shot.png?X-Amz-%53ignature=secret",
        "https%3A%2F%2Fcdn.example%2Fshot.png%3Faccess_token%3Dsecret",
    ),
)
def test_unsafe_visible_text_fails_closed(unsafe_text: str) -> None:
    unsafe = _aggregate(project_title=unsafe_text)

    with pytest.raises(WorkspaceProjectionStateError, match="signed credential"):
        _projection(unsafe)


def test_ordinary_creator_text_and_unsigned_url_are_preserved() -> None:
    title = "参考 https://example.com/storyboard-guide 的镜头说明"
    projection = _projection(_aggregate(project_title=title))

    assert projection["aggregate"]["projects"][0]["title"] == title


def test_authenticated_workspace_route_enforces_owner_and_exact_episode_ref(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, owner, other = _auth_client(tmp_path, monkeypatch)
    owner_id = owner["user"]["user_id"]
    aggregate = _aggregate(
        scope=TenantScope(org_id=owner_id, project_id=PROJECT_ID, actor_id=owner_id)
    )
    _store_aggregate(tmp_path, aggregate)

    anonymous = client.get(_route())
    denied = client.get(_route(), headers=_headers(other))
    loaded = client.get(_route(), headers=_headers(owner))
    stale = client.get(
        _route().replace("episode-1.v1", "episode-1.unknown"),
        headers=_headers(owner),
    )

    assert anonymous.status_code == 401
    assert denied.status_code == 403
    assert _error(denied) == "project_access_denied"
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["workspace"]["episode_ref"] == aggregate.episodes[0].as_ref().model_dump(
        mode="json"
    )
    assert stale.status_code == 409
    assert _error(stale) == "episode_workspace_reference_conflict"
    assert stale.json()["detail"]["retryable"] is True

    restarted = TestClient(create_runtime_app(runtime_root=tmp_path))
    recovered = restarted.get(_route(), headers=_headers(owner))
    assert recovered.status_code == 200, recovered.text
    assert recovered.json() == loaded.json()


def test_route_fails_closed_on_corrupt_snapshot_without_leaking_storage_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    client, owner, _ = _auth_client(tmp_path, monkeypatch)
    owner_id = owner["user"]["user_id"]
    aggregate = _aggregate(
        scope=TenantScope(org_id=owner_id, project_id=PROJECT_ID, actor_id=owner_id)
    )
    _store_aggregate(tmp_path, aggregate)
    path = EpisodeDomainAggregateStore(tmp_path).snapshot_path(
        org_id=owner_id, project_id=PROJECT_ID
    )
    envelope = json.loads(path.read_text(encoding="utf-8"))
    envelope["aggregate"]["projects"][0]["title"] = r"D:\private\snapshot.json"
    path.write_text(json.dumps(envelope), encoding="utf-8")

    response = client.get(_route(), headers=_headers(owner))

    assert response.status_code == 500
    assert _error(response) == "episode_workspace_integrity_failed"
    lowered = response.text.lower()
    assert "episode_aggregates" not in lowered
    assert "snapshot.json" not in lowered
    assert "d:\\private" not in lowered


def test_runtime_openapi_contains_workspace_get_without_mutation_route(tmp_path: Path) -> None:
    client = TestClient(create_runtime_app(runtime_root=tmp_path))

    schema = client.get("/openapi.json").json()
    route = (
        "/projects/{project_id}/episodes/{episode_id}/versions/"
        "{episode_version_id}/workspace"
    )

    assert set(schema["paths"][route]) == {"get"}
    assert (
        schema["paths"][route]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"]
        == "#/components/schemas/EpisodeWorkspaceReadResponse"
    )
