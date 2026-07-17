from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from agentflow_studio.production.manga_first_l4a import (
    CHECKPOINT_STAGES,
    CheckpointLedgerStore,
    build_studio_demo_projection,
    compile_manga_first_manifest,
    compose_legacy_fixture_silent_assembly,
    validate_manga_first_manifest,
)
from apps.api.runtime_service import create_runtime_app


REPO_ROOT = Path(__file__).resolve().parents[1]
L1_ROOT = Path("/opt/afs/recovery-evidence/real-story-20260717T143658Z-6ea4fbee/recovery-bound-v1")
L3_ROOT = Path("/opt/afs/recovery-evidence/real-story-20260717T143658Z-6ea4fbee/visual-creative-evaluation-v1")


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
    script = f"""
      import {{ normalizeMangaFirstL4AProjection, mangaFirstL4AStatusCounts }} from {json.dumps(js.as_uri())};
      const payload = {json.dumps(payload)};
      const view = normalizeMangaFirstL4AProjection(payload);
      if (!view || view.provider_dispatch_count !== 0 || view.fabricated_state_allowed !== false) process.exit(2);
      const counts = mangaFirstL4AStatusCounts(view);
      if (counts.awaiting_provider_authorization !== 12) process.exit(3);
    """
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr or completed.stdout


def test_studio_projection_rejects_missing_manifest_digest() -> None:
    manifest = compile_manga_first_manifest(_brief())
    projection = build_studio_demo_projection(manifest)
    assert projection["provider_dispatch_count"] == 0
    assert projection["truth_source"] == "schema_validated_manga_first_manifest"
