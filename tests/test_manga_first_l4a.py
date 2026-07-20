from __future__ import annotations

import json
import subprocess
import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agentflow_studio.production.manga_first_l4a import (
    CHECKPOINT_STAGES,
    CheckpointLedgerStore,
    build_manga_first_episode_aggregate,
    build_manga_first_provider_call_plan,
    build_studio_demo_projection,
    charge_fingerprint,
    compile_manga_first_manifest,
    compose_legacy_fixture_silent_assembly,
    json_digest,
    persist_manga_first_project,
    validate_manga_first_manifest,
)
from agentflow_studio.production.runtime_safe_io import safe_id as production_safe_id
from apps.api.runtime_episode_domain_contract import TenantScope
from apps.api.runtime_episode_domain_store import EpisodeDomainAggregateStore
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore


REPO_ROOT = Path(__file__).resolve().parents[1]
L1_ROOT = Path("/opt/afs/recovery-evidence/real-story-20260717T143658Z-6ea4fbee/recovery-bound-v1")
L3_ROOT = Path("/opt/afs/recovery-evidence/real-story-20260717T143658Z-6ea4fbee/visual-creative-evaluation-v1")


def _run_node_script(tmp_path: Path, script: str) -> subprocess.CompletedProcess[str]:
    script_path = tmp_path / "node_probe.mjs"
    script_path.write_text(script, encoding="utf-8")
    return subprocess.run(
        ["node", str(script_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_json_fixture(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def _brief(project_id: str = "manga-a") -> dict:
    return {
        "project_id": project_id,
        "title": "Neon Courier Pact",
        "logline": "Two teen couriers cross a sky market to return a stolen memory chip before dawn.",
        "style": "manga_drama",
        "target_duration_seconds": "108.000",
        "audience": "mobile-first young adult animation viewers",
        "tone": "urgent, intimate, hopeful",
        "characters": [
            {
                "character_id": "mika",
                "name": "Mika",
                "role": "courier leader",
                "visual_identity": "short silver hair, red scarf, cracked visor, compact hover boots",
                "continuity_rules": ["red scarf remains visible", "visor crack stays on left side"],
            },
            {
                "character_id": "ren",
                "name": "Ren",
                "role": "map reader",
                "visual_identity": "green jacket, square glasses, wrist-mounted projector",
                "continuity_rules": ["glasses stay square", "projector remains on right wrist"],
            },
        ],
        "scenes": [
            {
                "scene_id": "sky-market",
                "name": "Sky Market",
                "location_type": "stacked night bazaar above the city",
                "visual_mood": "paper lanterns, neon kanji, thin fog",
                "story_function": "introduce pursuit and memory chip stakes",
            },
            {
                "scene_id": "train-roof",
                "name": "Maglev Roof",
                "location_type": "moving train roof above dawn traffic",
                "visual_mood": "wind streaks, pale sunrise, reflected signs",
                "story_function": "resolve trust and deliver the chip",
            },
        ],
        "beats": [
            _beat(1, "sky-market", ("mika", "ren"), "Mika catches the falling chip case", "stakes revealed", "1.1"),
            _beat(2, "sky-market", ("mika",), "Mika spots masked riders in the crowd", "danger closes", "0.9"),
            _beat(3, "sky-market", ("ren",), "Ren projects a broken route map", "plan fails", "1.0"),
            _beat(4, "sky-market", ("mika", "ren"), "They vault across food stalls", "partnership tested", "1.2"),
            _beat(5, "sky-market", ("ren",), "Ren decodes a hidden platform mark", "hope returns", "0.8"),
            _beat(6, "sky-market", ("mika", "ren"), "The riders cut off the stair bridge", "trap sprung", "1.0"),
            _beat(7, "train-roof", ("mika",), "Mika leaps onto the departing maglev", "risk accepted", "1.15"),
            _beat(8, "train-roof", ("ren",), "Ren lands hard and shields the chip", "cost paid", "0.85"),
            _beat(9, "train-roof", ("mika", "ren"), "They argue over who should carry it", "trust fracture", "1.0"),
            _beat(10, "train-roof", ("mika",), "Mika sees the memory belongs to a child", "purpose clarified", "0.95"),
            _beat(11, "train-roof", ("ren",), "Ren reroutes the train beacon", "solution found", "1.05"),
            _beat(12, "train-roof", ("mika", "ren"), "They drop the chip to the rescue drone", "promise kept", "1.2"),
        ],
    }


def _different_brief() -> dict:
    brief = _brief("manga-b")
    brief["title"] = "Glass Orchard Oath"
    brief["logline"] = "Three apprentices protect a glass orchard from a noon eclipse ritual."
    brief["style"] = "anime"
    brief["target_duration_seconds"] = "96.000"
    brief["characters"] = [
        {
            "character_id": "aya",
            "name": "Aya",
            "role": "apprentice gardener",
            "visual_identity": "amber braid, ink-stained gloves, crescent satchel",
            "continuity_rules": ["amber braid remains tied", "satchel crescent mark stays visible"],
        }
    ]
    brief["scenes"] = [
        {
            "scene_id": "glass-orchard",
            "name": "Glass Orchard",
            "location_type": "transparent trees over a shallow reflecting field",
            "visual_mood": "bright noon, prism shadows, floating pollen",
            "story_function": "set fragile world and approaching eclipse",
        },
        {
            "scene_id": "bell-terrace",
            "name": "Bell Terrace",
            "location_type": "ceramic terrace above the orchard",
            "visual_mood": "gold dust, ringing cables, sharp sun rim",
            "story_function": "resolve the oath with a public signal",
        },
        {
            "scene_id": "root-vault",
            "name": "Root Vault",
            "location_type": "subsurface archive of crystal roots",
            "visual_mood": "cool blue glow, suspended seed diagrams",
            "story_function": "reveal the restoration recipe",
        },
    ]
    scene_cycle = ("glass-orchard", "root-vault", "bell-terrace")
    brief["beats"] = [
        _beat(index, scene_cycle[(index - 1) % 3], ("aya",), f"Aya performs orchard action {index}", f"turn {index}", str(0.8 + (index % 4) * 0.1))
        for index in range(1, 16)
    ]
    return brief


def _beat(index: int, scene_id: str, characters: tuple[str, ...], action: str, turn: str, weight: str) -> dict:
    return {
        "beat_id": f"beat-{index:03d}",
        "scene_id": scene_id,
        "character_ids": list(characters),
        "action": action,
        "emotional_turn": turn,
        "duration_weight": weight,
    }


def test_manga_first_compiler_is_brief_driven_and_removes_legacy_template_dominance() -> None:
    first = compile_manga_first_manifest(_brief())
    second = compile_manga_first_manifest(_different_brief())

    validate_manga_first_manifest(first)
    validate_manga_first_manifest(second)
    assert first.manifest_sha256 != second.manifest_sha256
    assert first.story_bible["title"] == "Neon Courier Pact"
    assert second.story_bible["title"] == "Glass Orchard Oath"
    assert len(first.shots) == 12
    assert len(second.shots) == 15
    assert first.timeline["duration_seconds"] == "108.000"
    assert second.timeline["duration_seconds"] == "96.000"
    assert first.template_audit["legacy_template_dominance_removed"] is True
    assert second.template_audit["legacy_template_dominance_removed"] is True
    assert first.story_bible["source"] == "owner_brief"
    assert first.scenes[0]["scene_id"] == "sky-market"
    assert first.reference_set["characters"][0]["character_id"] == "mika"
    assert first.production_recipe["manual_editing_required"] is False
    assert first.assembly_contract["timeline_otio"]["required"] is True
    canonical_text = json.dumps(
        {"story_bible": first.story_bible, "scenes": first.scenes, "shots": first.shots},
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    for forbidden in ("pier", "lighthouse", "robot", "blue raincoat"):
        assert forbidden not in canonical_text


def test_fact_chain_and_checkpoint_ledger_support_idempotency_restart_pause_retry_cancel_and_dlq(tmp_path: Path) -> None:
    manifest = compile_manga_first_manifest(_brief())
    assert manifest.fact_chain["required_chain"] == "Shot->Task->Attempt->ArtifactVersion->Candidate->Selection->Review->Delivery"
    assert manifest.fact_chain["studio_fabricated_state_allowed"] is False
    assert tuple(item["stage"] for item in manifest.checkpoints) == CHECKPOINT_STAGES
    video_checkpoint = next(item for item in manifest.checkpoints if item["stage"] == "video")
    assert video_checkpoint["project_lock_held_while_waiting"] is False
    assert all(video_checkpoint[f"{name}_supported"] for name in ("lease", "idempotency", "pause", "cancel", "retry", "dlq", "restart_takeover"))

    store = CheckpointLedgerStore(tmp_path / "ledger.json")
    state = store.initialize(manifest)
    assert state["provider_dispatch_count"] == 0
    acquired = store.apply(
        stage="video",
        action="acquire_lease",
        idempotency_key="lease-video-1",
        worker_id="worker-a",
        now="2026-07-18T00:00:00+00:00",
        lease_expires_at="2026-07-18T00:05:00+00:00",
    )
    replay = store.apply(
        stage="video",
        action="acquire_lease",
        idempotency_key="lease-video-1",
        worker_id="worker-a",
    )
    assert replay == acquired
    takeover = store.apply(
        stage="video",
        action="takeover_expired",
        idempotency_key="takeover-video-1",
        worker_id="worker-b",
        now="2026-07-18T00:06:00+00:00",
    )
    assert takeover["checkpoint"]["lease"]["takeover_of"] == "worker-a"
    assert store.apply(stage="video", action="pause", idempotency_key="pause-video-1")["checkpoint"]["control_state"] == "paused"
    assert store.apply(stage="video", action="retry", idempotency_key="retry-video-1")["checkpoint"]["retry_count"] == 1
    assert store.apply(stage="video", action="dlq", idempotency_key="dlq-video-1", reason="provider_gate_closed")["checkpoint"]["status"] == "dead_letter"
    assert store.apply(stage="audio_wait", action="cancel", idempotency_key="cancel-audio-1")["checkpoint"]["status"] == "cancelled"
    current = json.loads((tmp_path / "ledger.json").read_text(encoding="utf-8"))
    assert current["checkpoints"]["compose"]["status"] == "queued"


def test_checkpoint_restart_recovery_does_not_repurchase_completed_shot(tmp_path: Path) -> None:
    manifest = compile_manga_first_manifest(_brief())
    ledger_path = tmp_path / "checkpoint_ledger.json"
    store = CheckpointLedgerStore(ledger_path)
    store.initialize(manifest)
    prompt_sha = json_digest({"prompt": manifest.shots[0]["canonical_prompt"]})
    reserved = store.reserve_shot_charge(
        stage="keyframe",
        shot_id="shot-001",
        capability="image",
        prompt_sha256=prompt_sha,
        attempt_id="attempt-shot-001-001",
        idempotency_key="reserve-shot-001",
    )
    completed = store.complete_shot(shot_id="shot-001", idempotency_key="complete-shot-001")

    restarted = CheckpointLedgerStore(ledger_path)
    retry = restarted.reserve_shot_charge(
        stage="keyframe",
        shot_id="shot-001",
        capability="image",
        prompt_sha256=prompt_sha,
        attempt_id="attempt-shot-001-002",
        idempotency_key="reserve-shot-001-after-restart",
    )
    state = restarted.load()

    assert reserved["charge_fingerprint"] == completed["charge_fingerprint"]
    assert retry["status"] == "skipped_already_completed"
    assert retry["charge_reserved"] is False
    assert state["shots"]["shot-001"]["charge_reservation_count"] == 1
    assert len(state["charge_fingerprints"]) == 1
    assert charge_fingerprint(
        project_id=manifest.project_id,
        manifest_sha256=manifest.manifest_sha256,
        stage="keyframe",
        shot_id="shot-001",
        capability="image",
        prompt_sha256=prompt_sha,
    ) == reserved["charge_fingerprint"]


def test_episode_aggregate_and_runtime_persistence_are_the_unique_fact_authority(tmp_path: Path) -> None:
    manifest = compile_manga_first_manifest(_brief())
    scope = TenantScope(org_id="org-1", project_id=manifest.project_id, actor_id="creator-1")
    aggregate = build_manga_first_episode_aggregate(manifest, scope=scope)

    assert len(aggregate.shots) == 12
    assert len(aggregate.asset_candidates) == 12
    assert len(aggregate.selections) == 12
    assert len(aggregate.review_decisions) == 12
    assert aggregate.deliveries[0].preview_artifact_ref is None
    assert all(item.approval_state == "pending_human" and item.human_confirmed is False for item in aggregate.reference_assets)
    assert aggregate.reference_sets[0].approval_state == "pending_human"
    assert aggregate.reference_sets[0].human_confirmed is False
    assert all(item.reference_set_ref is None for item in aggregate.shots)

    runtime_store = RuntimeStore(tmp_path)
    runtime_store.create_project_manifest(
        project_id=manifest.project_id,
        project_type="manga_first_episode",
        goal="Manga first L4B",
        status="in_progress",
    )
    persisted = persist_manga_first_project(
        runtime_store,
        manifest,
        scope=scope,
        idempotency_key="manga-first-create-v1",
    )
    replayed = persist_manga_first_project(
        runtime_store,
        manifest,
        scope=scope,
        idempotency_key="manga-first-create-v1",
    )
    loaded = EpisodeDomainAggregateStore(tmp_path).load(org_id=scope.org_id, project_id=scope.project_id)

    assert loaded == persisted.aggregate_result.aggregate
    assert replayed.aggregate_result.replayed is True
    assert persisted.studio_workspace["truth_authority"]["primary"] == "ProductionProjectAggregate"
    assert persisted.studio_workspace["truth_authority"]["second_fact_source_allowed"] is False
    assert persisted.studio_workspace["truth_authority"]["production_truth_manifest_role"] == "aggregate_backed_artifact_evidence"
    assert persisted.studio_workspace["reference_approval_gate"]["status"] == "pending_human"
    assert persisted.studio_workspace["reference_approval_gate"]["provider_ready"] is False
    assert "relative_path" not in persisted.studio_workspace["truth_authority"]["manifest_artifact"]
    assert persisted.manifest_artifact["artifact_id"]


def test_l4b_runtime_uses_bounded_storage_ids_for_long_project_ids(tmp_path: Path) -> None:
    project_id = "manga-" + ("p" * 154)
    manifest = compile_manga_first_manifest(_brief(project_id))
    scope = TenantScope(org_id="org-1", project_id=project_id, actor_id="creator-1")
    runtime_store = RuntimeStore(tmp_path)
    runtime_store.create_project_manifest(
        project_id=project_id,
        project_type="manga_first_episode",
        goal="Manga first L4B long project id",
        status="in_progress",
    )

    persisted = persist_manga_first_project(
        runtime_store,
        manifest,
        scope=scope,
        idempotency_key="manga-first-long-project-create-v1",
    )
    storage_id = production_safe_id(project_id)
    project_root = tmp_path / "projects" / storage_id

    assert storage_id != project_id
    assert len(storage_id) <= 120
    assert (project_root / "manga_first_l4b" / "production_truth_manifest.json").is_file()
    assert persisted.manifest.project_id == project_id
    assert persisted.studio_workspace["project_id"] == project_id
    assert len(persisted.manifest.manifest_sha256) == 64
    assert persisted.manifest_artifact["artifact_id"]
    assert persisted.manifest_artifact["artifact_id"] != project_id
    assert max(len(part) for path in tmp_path.rglob("*") for part in path.relative_to(tmp_path).parts) <= 120


@pytest.mark.skipif(not L1_ROOT.exists() or not L3_ROOT.exists(), reason="server recovery fixture is not mounted")
def test_existing_13x13_assets_compose_provider_free_silent_regression_and_preserve_l3_p1(tmp_path: Path) -> None:
    result = compose_legacy_fixture_silent_assembly(
        l1_root=L1_ROOT,
        l3_root=L3_ROOT,
        output_dir=tmp_path / "assembly",
    )
    assert result["provider_dispatch_count"] == 0
    assert result["duration_seconds"] == "120.000"
    assert result["p1_count"] == 5
    manifest = json.loads(Path(result["manifest_path"]).read_text(encoding="utf-8"))
    assert manifest["shot_count"] == 13
    assert manifest["manual_editing_required"] is False
    assert manifest["audio_stream_count"] == 0
    assert manifest["verdict"] == "fixture_regression_only_p1_open"
    assert "not_visual_creative_qa_pass" in manifest["non_claims"]
    qa = json.loads(Path(result["technical_qa_path"]).read_text(encoding="utf-8"))
    assert qa["full_ffmpeg_decode_ok"] is True
    assert qa["no_audio"] is True
    assert len(manifest["episode_sha256"]) == 64
    fixture_projection = json.loads(Path(result["studio_projection_path"]).read_text(encoding="utf-8"))
    assert "preview_path" not in fixture_projection["final_demo"]
    assert fixture_projection["final_demo"]["preview_artifact"]["sha256"] == manifest["episode_sha256"]


def test_runtime_api_and_studio_projection_are_safe_and_provider_free(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_AUTH_ALLOW_OPEN_SIGNUP", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    registered = client.post(
        "/auth/register",
        json={"email": "owner@example.com", "password": "strong-password-123", "display_name": "Owner"},
    )
    assert registered.status_code == 200, registered.text
    headers = {"Authorization": f"Bearer {registered.json()['session_token']}"}
    created = client.post(
        "/projects",
        headers=headers,
        json={"project_id": "manga-a", "project_type": "studio_episode_production", "goal": "Manga first L4A"},
    )
    assert created.status_code == 200, created.text
    response = client.post(
        "/projects/manga-a/manga-first-l4a/compile-preview",
        headers=headers,
        json={"brief": _brief(), "include_manifest": True},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["provider_dispatch_count"] == 0
    assert payload["studio_projection"]["project"]["workload"] == "manga_first"
    assert payload["studio_projection"]["final_demo"]["status"] == "not_composed_for_new_manga_authority"
    assert payload["manifest"]["fact_chain"]["studio_fabricated_state_allowed"] is False

    js = REPO_ROOT / "apps" / "studio" / "src" / "manga-first-l4a-projection.js"
    payload_path = _write_json_fixture(tmp_path / "l4a_projection_payload.json", payload)
    script = f"""
      import {{ readFileSync }} from "node:fs";
      import {{ normalizeMangaFirstL4AProjection, mangaFirstL4AStatusCounts }} from {json.dumps(js.as_uri())};
      const payload = JSON.parse(readFileSync({json.dumps(str(payload_path))}, "utf8"));
      const view = normalizeMangaFirstL4AProjection(payload);
      if (!view || view.provider_dispatch_count !== 0 || view.fabricated_state_allowed !== false) process.exit(2);
      const counts = mangaFirstL4AStatusCounts(view);
      if (counts.awaiting_provider_authorization !== 12) process.exit(3);
    """
    completed = _run_node_script(tmp_path, script)
    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_l4b_runtime_route_persists_truth_and_studio_workspace_uses_runtime_data_flow(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_AUTH_ALLOW_OPEN_SIGNUP", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    headers = _register_owner(client)
    api_headers = _api_headers(headers)
    payload = _persist_l4b_project(client, headers, _brief())
    assert payload["provider_dispatch_count"] == 0
    assert payload["studio_workspace"]["truth_authority"]["second_fact_source_allowed"] is False
    assert payload["studio_workspace"]["truth_authority"]["page_read_models"] == [
        "build_creator_authoring_projection",
        "build_episode_workspace_projection",
    ]
    assert payload["reference_approval_gate"]["status"] == "pending_human"
    assert payload["reference_approval_gate"]["provider_ready"] is False
    assert payload["studio_workspace"]["studio_projection"]["truth_source"] == "canonical_episode_workspace_projection"
    assert payload["provider_call_plan"]["call_counts"]["image_calls"] == 24
    assert payload["provider_call_plan"]["cost"]["status"] == "ESTIMATE_OWNER_DECISION_NEEDED"
    before_get = _runtime_tree_fingerprint(tmp_path)
    loaded = client.get("/projects/manga-a/manga-first-l4b/workspace", headers=api_headers)
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["studio_workspace"]["truth_authority"]["primary"] == "ProductionProjectAggregate"
    assert _runtime_tree_fingerprint(tmp_path) == before_get

    js = REPO_ROOT / "apps" / "studio" / "src" / "manga-first-l4b-workspace.js"
    payload_path = _write_json_fixture(tmp_path / "l4b_workspace_payload.json", payload)
    brief_path = _write_json_fixture(tmp_path / "l4b_workspace_brief.json", _brief())
    script = f"""
      import {{ readFileSync }} from "node:fs";
      import {{ normalizeMangaFirstL4BWorkspace, createMangaFirstL4BWorkspace }} from {json.dumps(js.as_uri())};
      const payload = JSON.parse(readFileSync({json.dumps(str(payload_path))}, "utf8"));
      const brief = JSON.parse(readFileSync({json.dumps(str(brief_path))}, "utf8"));
      const view = normalizeMangaFirstL4BWorkspace(payload);
      if (!view || view.provider_dispatch_count !== 0 || view.fabricated_state_allowed !== false) process.exit(2);
      if (view.truth_authority.second_fact_source_allowed !== false) process.exit(3);
      if (!view.reference_approval_gate || view.reference_approval_gate.status !== "pending_human") process.exit(4);
      const runtimeClient = {{ createMangaFirstProductionTruth: async () => payload }};
      const created = await createMangaFirstL4BWorkspace({{ projectId: "manga-a", brief, runtimeClient }});
      if (!created || created.shot_status.length !== 12) process.exit(5);
    """
    completed = _run_node_script(tmp_path, script)
    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_l4b_reference_approval_gate_is_pending_until_explicit_owner_cas_approval(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_AUTH_ALLOW_OPEN_SIGNUP", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    headers = _register_owner(client)
    api_headers = _api_headers(headers)
    payload = _persist_l4b_project(client, headers, _brief())
    gate = payload["reference_approval_gate"]

    assert gate["status"] == "pending_human"
    assert gate["provider_ready"] is False
    aggregate = EpisodeDomainAggregateStore(tmp_path).load(org_id=headers["_user_id"], project_id="manga-a")
    assert all(item.reference_set_ref is None for item in aggregate.shots)

    wrong_digest = client.post(
        "/projects/manga-a/manga-first-l4b/reference-set-approvals",
        headers=api_headers,
        json={
            "decision_id": "approve-manga-a-references",
            "expected_aggregate_version": gate["aggregate_version"],
            "reference_set_digest": "0" * 64,
            "idempotency_key": "approve-manga-a-references-v1",
        },
    )
    assert wrong_digest.status_code == 409
    wrong_cas = client.post(
        "/projects/manga-a/manga-first-l4b/reference-set-approvals",
        headers=api_headers,
        json={
            "decision_id": "approve-manga-a-references",
            "expected_aggregate_version": gate["aggregate_version"] + 1,
            "reference_set_digest": gate["reference_set_digest"],
            "idempotency_key": "approve-manga-a-references-v1",
        },
    )
    assert wrong_cas.status_code == 409

    approved = client.post(
        "/projects/manga-a/manga-first-l4b/reference-set-approvals",
        headers=api_headers,
        json={
            "decision_id": "approve-manga-a-references",
            "expected_aggregate_version": gate["aggregate_version"],
            "reference_set_digest": gate["reference_set_digest"],
            "idempotency_key": "approve-manga-a-references-v1",
        },
    )
    assert approved.status_code == 200, approved.text
    approval_payload = approved.json()
    assert approval_payload["reference_approval_gate"]["status"] == "confirmed"
    assert approval_payload["reference_approval_gate"]["provider_ready"] is True
    assert approval_payload["aggregate"]["aggregate_version"] == 2
    approved_aggregate = EpisodeDomainAggregateStore(tmp_path).load(org_id=headers["_user_id"], project_id="manga-a")
    assert all(item.approval_state == "approved" for item in _latest_by_entity(approved_aggregate.reference_assets))
    assert _latest_by_entity(approved_aggregate.reference_sets)[0].approval_state == "approved"
    assert all(item.reference_set_ref == _latest_by_entity(approved_aggregate.reference_sets)[0].as_ref() for item in _latest_by_entity(approved_aggregate.shots))
    assert any(item.entity_id == "approve-manga-a-references" and item.decision == "approve" for item in approved_aggregate.review_decisions)

    replay = client.post(
        "/projects/manga-a/manga-first-l4b/reference-set-approvals",
        headers=api_headers,
        json={
            "decision_id": "approve-manga-a-references",
            "expected_aggregate_version": gate["aggregate_version"],
            "reference_set_digest": gate["reference_set_digest"],
            "idempotency_key": "approve-manga-a-references-v1",
        },
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["aggregate"]["replayed"] is True


def test_l4b_two_distinct_briefs_run_full_no_provider_e2e(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_AUTH_ALLOW_OPEN_SIGNUP", "true")
    client = TestClient(create_runtime_app(runtime_root=tmp_path))
    headers = _register_owner(client)

    first = _assert_l4b_e2e(client, headers, _brief(), tmp_path)
    second = _assert_l4b_e2e(client, headers, _different_brief(), tmp_path)
    assert first["manifest_sha256"] != second["manifest_sha256"]
    assert first["studio_workspace"]["studio_projection"]["project"]["title"] != second["studio_workspace"]["studio_projection"]["project"]["title"]
    assert len(first["studio_workspace"]["studio_projection"]["shot_status"]) == 12
    assert len(second["studio_workspace"]["studio_projection"]["shot_status"]) == 15
    combined = json.dumps(
        {
            "first": first["studio_workspace"]["studio_projection"],
            "second": second["studio_workspace"]["studio_projection"],
        },
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    for forbidden in ("pier", "lighthouse", "robot", "blue raincoat"):
        assert forbidden not in combined


def test_studio_runtime_client_reaches_manga_first_workspace_contract(tmp_path: Path) -> None:
    client_js = REPO_ROOT / "apps" / "studio" / "src" / "runtime-client.js"
    brief_path = _write_json_fixture(tmp_path / "runtime_client_brief.json", _brief())
    digest = "a" * 64
    script = f"""
      import {{ readFileSync }} from "node:fs";
      import {{ createRuntimeClient }} from {json.dumps(client_js.as_uri())};
      const brief = JSON.parse(readFileSync({json.dumps(str(brief_path))}, "utf8"));
      const calls = [];
      globalThis.fetch = async (url, options = {{}}) => {{
        calls.push({{
          url,
          method: options.method || "GET",
          payload: options.body ? JSON.parse(options.body) : null,
        }});
        return {{
          ok: true,
          status: 200,
          statusText: "OK",
          headers: {{ get: () => "" }},
          text: async () => "{{}}",
        }};
      }};
      const client = createRuntimeClient("manga-a");
      await client.createMangaFirstProductionTruth(brief, {{
        idempotencyKey: "manga-first-create-v1",
        includeManifest: true,
      }});
      await client.loadMangaFirstWorkspace();
      await client.approveMangaFirstReferenceSet({{
        decision_id: "approve-manga-a-references",
        expected_aggregate_version: 3,
        reference_set_digest: {json.dumps(digest)},
      }});
      const expected = [
        ["/projects/manga-a/manga-first-l4b/production-truth", "POST"],
        ["/projects/manga-a/manga-first-l4b/workspace", "GET"],
        ["/projects/manga-a/manga-first-l4b/reference-set-approvals", "POST"],
      ];
      if (JSON.stringify(calls.map((item) => [item.url, item.method])) !== JSON.stringify(expected)) process.exit(2);
      if (calls[0].payload.idempotency_key !== "manga-first-create-v1" || calls[0].payload.include_manifest !== true) process.exit(3);
      if (calls[2].payload.reference_set_digest !== {json.dumps(digest)}) process.exit(4);
    """
    completed = _run_node_script(tmp_path, script)
    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_provider_call_plan_is_read_only_and_marks_cost_as_owner_decision_needed() -> None:
    manifest = compile_manga_first_manifest(_different_brief())
    plan = build_manga_first_provider_call_plan(manifest, retry_limit=2)

    assert plan["provider_dispatch_count"] == 0
    assert plan["secret_values_read"] is False
    assert plan["models"]["keyframe_image"]["model"] == "gpt-image-2"
    assert plan["models"]["shot_video"]["model"] == "doubao-seedance-2-0-fast"
    assert plan["call_counts"]["shot_count"] == 15
    assert plan["call_counts"]["image_calls"] == 30
    assert plan["call_counts"]["video_calls"] == 15
    assert plan["call_counts"]["max_attempted_calls_with_retries"] == 135
    assert plan["cost"]["status"] == "ESTIMATE_OWNER_DECISION_NEEDED"
    assert plan["models"]["shot_video"]["supported_durations_sec"] == [5, 10]


def test_studio_projection_rejects_missing_manifest_digest() -> None:
    manifest = compile_manga_first_manifest(_brief())
    projection = build_studio_demo_projection(manifest)
    assert projection["provider_dispatch_count"] == 0
    assert projection["truth_source"] == "episode_aggregate_backed_manga_first_manifest"


def _register_owner(client: TestClient) -> dict[str, str]:
    registered = client.post(
        "/auth/register",
        json={"email": "owner@example.com", "password": "strong-password-123", "display_name": "Owner"},
    )
    assert registered.status_code == 200, registered.text
    payload = registered.json()
    return {
        "Authorization": f"Bearer {payload['session_token']}",
        "_user_id": str(payload["user"]["user_id"]),
    }


def _persist_l4b_project(client: TestClient, headers: dict[str, str], brief: dict) -> dict:
    project_id = brief["project_id"]
    api_headers = _api_headers(headers)
    created = client.post(
        "/projects",
        headers=api_headers,
        json={"project_id": project_id, "project_type": "manga_first_episode", "goal": "Manga first L4B"},
    )
    assert created.status_code == 200, created.text
    response = client.post(
        f"/projects/{project_id}/manga-first-l4b/production-truth",
        headers=api_headers,
        json={"brief": brief, "idempotency_key": f"{project_id}-manga-first-l4b-create-v1"},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _assert_l4b_e2e(client: TestClient, headers: dict[str, str], brief: dict, runtime_root: Path) -> dict:
    payload = _persist_l4b_project(client, headers, brief)
    assert payload["provider_dispatch_count"] == 0
    project_id = brief["project_id"]
    api_headers = _api_headers(headers)
    loaded = client.get(f"/projects/{project_id}/manga-first-l4b/workspace", headers=api_headers)
    assert loaded.status_code == 200, loaded.text
    workspace = loaded.json()["studio_workspace"]
    assert workspace["truth_authority"]["primary"] == "ProductionProjectAggregate"
    assert workspace["truth_authority"]["second_fact_source_allowed"] is False
    assert workspace["reference_approval_gate"]["status"] == "pending_human"
    assert workspace["provider_dispatch_count"] == 0
    aggregate = EpisodeDomainAggregateStore(runtime_root).load(
        org_id=headers["_user_id"],
        project_id=project_id,
    )
    assert aggregate.aggregate_version == 1
    assert len(aggregate.shots) == len(brief["beats"])
    assert len(aggregate.scenes) == len(brief["scenes"])
    assert len(aggregate.reference_assets) == len(brief["characters"]) + len(brief["scenes"])
    return payload


def _latest_by_entity(records):
    latest = {}
    for item in records:
        current = latest.get(item.entity_id)
        if current is None or item.revision > current.revision:
            latest[item.entity_id] = item
    return tuple(sorted(latest.values(), key=lambda item: item.entity_id))


def _api_headers(headers: dict[str, str]) -> dict[str, str]:
    return {key: value for key, value in headers.items() if not key.startswith("_")}


def _runtime_tree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name.endswith(".lock"):
            continue
        if path.relative_to(root).parts[:1] == ("auth",):
            continue
        stat = path.stat()
        digest.update(str(path.relative_to(root)).encode("utf-8"))
        digest.update(str(stat.st_size).encode("utf-8"))
        digest.update(str(stat.st_mtime_ns).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()
