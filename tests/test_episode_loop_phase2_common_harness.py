from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / "experiments" / "episode-loop-phase2" / "common"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(name: str) -> dict:
    return json.loads((COMMON / name).read_text(encoding="utf-8"))


def test_manifest_freezes_contract_research_protocol_and_fixtures() -> None:
    manifest = load_json("fixture-manifest.json")

    assert manifest["base_commit"] == "7f74f2280dca8d4a8d86b9aefda017e5b2e5f62a"
    assert manifest["domain_contract_commit"] == "c3ff529940538d42ac95d9c575b605a866e2e42b"
    for entry in (
        manifest["evidence_matrix"],
        manifest["evaluation_protocol"],
        *manifest["fixtures"],
    ):
        path = ROOT / entry["path"]
        assert path.is_file(), entry["path"]
        assert sha256(path) == entry["sha256"]

    assert manifest["provider_dispatch_allowed"] is False
    assert manifest["expected_missing_assets"] == 25
    assert manifest["expected_provider_dispatch_count"] == 0


def test_scenario_is_variant_neutral_and_preserves_truth_constraints() -> None:
    scenario = load_json("scenario.json")
    overlays = {item["target"]: item for item in scenario["overlays"]}

    assert scenario["truth_constraints"] == {
        "shot_count": 15,
        "duration_seconds": 135,
        "missing_asset_count": 25,
        "provider_dispatch_count": 0,
        "playable_preview_available": False,
    }
    assert overlays["shot-006"]["expected_scene"] == "scene-archive-tower"
    assert overlays["shot-007"]["kind"] == "continuity_conflict"
    assert overlays["shot-008"]["expected_action"] == "leave_unchanged"
    assert scenario["revision_task"]["target"] == "shot-011"
    assert scenario["revision_task"]["unchanged_shot_count"] == 14
    assert scenario["revision_task"]["reload_after_reconfirmed_count"] == 3
    assert scenario["revision_task"]["expected_final_reconfirmed_count"] == 8
    assert len(scenario["tasks"]) == 5
    assert not any(key in json.dumps(scenario).lower() for key in ("guided", "storyboard-first", "hybrid"))


def test_variant_roots_are_isolated_from_production_and_each_other() -> None:
    manifest = load_json("fixture-manifest.json")
    roots = list(manifest["variants"].values())

    assert len(roots) == len(set(roots)) == 3
    assert all(path.startswith("experiments/episode-loop-phase2/prototypes/") for path in roots)
    assert not any(path.startswith("apps/") for path in roots)
    runtime_service = (ROOT / "apps" / "api" / "runtime_service.py").read_text(encoding="utf-8")
    assert "experiments/episode-loop-phase2" not in runtime_service


def test_common_javascript_has_an_independent_syntax_gate() -> None:
    result = subprocess.run(
        ["node", "tools/check-phase2-prototype-js.mjs"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "3 files" in result.stdout


def test_protocol_consumes_research_and_has_human_evidence_boundary() -> None:
    protocol = (ROOT / "docs" / "AFS_EPISODE_LOOP_PHASE2_EVALUATION_PROTOCOL.md").read_text(
        encoding="utf-8"
    )

    assert "research/AFS_PHASE1_EVIDENCE_MATRIX.md" in protocol
    assert "same-task" in protocol.lower()
    assert "six valid sessions" in protocol.lower()
    assert "cannot\nclaim human acceptance" in protocol
    assert "decision_needed" in protocol


def test_neutral_tokens_provide_accessibility_basics_without_layout_choice() -> None:
    css = (COMMON / "neutral-tokens.css").read_text(encoding="utf-8")

    assert "min-height: 44px" in css
    assert ":focus-visible" in css
    assert "display: grid" not in css
    assert "display: flex" not in css


def run_node_module(script: str) -> dict:
    result = subprocess.run(
        ["node", "--input-type=module", "--eval", script],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def test_store_rejects_contradictory_or_drifted_recovery_envelopes() -> None:
    result = run_node_module(
        """
        import { createInitialState, FIXTURE_SHA256 } from './experiments/episode-loop-phase2/common/prototype-contract.js';
        import { createEnvelope, loadEnvelope, saveEnvelope } from './experiments/episode-loop-phase2/common/prototype-store.js';
        import scenario from './experiments/episode-loop-phase2/common/scenario.json' with { type: 'json' };
        const values = new Map();
        const storage = {
          getItem: (key) => values.get(key) ?? null,
          setItem: (key, value) => values.set(key, value),
          removeItem: (key) => values.delete(key),
        };
        const state = createInitialState({ variant: 'guided', scenario });
        state.checkpoint.completed_reconfirmations = 3;
        const envelope = createEnvelope({
          variant: 'guided', fixtureSha256: FIXTURE_SHA256, sessionId: 'session-1', state, eventLog: [],
        });
        saveEnvelope(storage, envelope);
        const valid = loadEnvelope(storage, { variant: 'guided', fixtureSha256: FIXTURE_SHA256 });
        const key = 'afs:episode-loop:phase2:guided:v1';
        const wrongVariant = structuredClone(envelope);
        wrongVariant.state.variant = 'hybrid';
        storage.setItem(key, JSON.stringify(wrongVariant));
        const variantRejected = loadEnvelope(storage, { variant: 'guided', fixtureSha256: FIXTURE_SHA256 }) === null;
        const falseDelivery = structuredClone(envelope);
        falseDelivery.state.delivery.missing_asset_count = 0;
        storage.setItem(key, JSON.stringify(falseDelivery));
        const deliveryRejected = loadEnvelope(storage, { variant: 'guided', fixtureSha256: FIXTURE_SHA256 }) === null;
        const splitCheckpoint = structuredClone(envelope);
        splitCheckpoint.checkpoint = { completed_reconfirmations: 8 };
        storage.setItem(key, JSON.stringify(splitCheckpoint));
        const splitCheckpointRejected = loadEnvelope(
          storage, { variant: 'guided', fixtureSha256: FIXTURE_SHA256 },
        ) === null;
        const foreignSession = structuredClone(envelope);
        foreignSession.event_log = [{
          sequence: 1, variant: 'guided', session_id: 'foreign-session', elapsed_ms: 1,
        }];
        storage.setItem(key, JSON.stringify(foreignSession));
        const foreignSessionRejected = loadEnvelope(
          storage, { variant: 'guided', fixtureSha256: FIXTURE_SHA256 },
        ) === null;
        const skippedReload = structuredClone(envelope);
        skippedReload.state.checkpoint.completed_reconfirmations = 8;
        skippedReload.state.checkpoint.reload_observed = false;
        storage.setItem(key, JSON.stringify(skippedReload));
        const skippedReloadRejected = loadEnvelope(
          storage, { variant: 'guided', fixtureSha256: FIXTURE_SHA256 },
        ) === null;
        console.log(JSON.stringify({
          valid: valid !== null, variantRejected, deliveryRejected, splitCheckpointRejected,
          foreignSessionRejected, skippedReloadRejected,
        }));
        """
    )

    assert result == {
        "valid": True,
        "variantRejected": True,
        "deliveryRejected": True,
        "splitCheckpointRejected": True,
        "foreignSessionRejected": True,
        "skippedReloadRejected": True,
    }


def test_event_log_deduplicates_activation_and_resumes_sequence_and_time() -> None:
    result = run_node_module(
        """
        import { createEventLogger, summarizeEvents } from './experiments/episode-loop-phase2/common/event-log.js';
        let clockValue = 1000;
        const first = createEventLogger({ variant: 'guided', sessionId: 'session-1', clock: () => clockValue });
        clockValue = 1010;
        first.record({
          task: 'repair_scene_split', action: 'confirm', objectType: 'shot', objectKey: 'shot-006',
          fromView: 'breakdown', toView: 'scene_editor', inputMethod: 'keyboard', stateSummary: 'repaired',
          activationId: 'repair-shot-006',
        });
        clockValue = 1011;
        first.record({
          task: 'repair_scene_split', action: 'confirm', objectType: 'shot', objectKey: 'shot-006',
          fromView: 'breakdown', toView: 'scene_editor', inputMethod: 'mouse', stateSummary: 'synthetic-click',
          activationId: 'repair-shot-006',
        });
        const saved = first.snapshot();
        clockValue = 5;
        const resumed = createEventLogger({
          variant: 'guided', sessionId: 'session-1', clock: () => clockValue, existingEvents: saved,
        });
        clockValue = 15;
        resumed.record({
          task: 'resolve_continuity', action: 'open', objectType: 'shot', objectKey: 'shot-007',
          fromView: 'scene_editor', toView: 'continuity', inputMethod: 'keyboard', stateSummary: 'conflict-open',
          activationId: 'open-shot-007',
        });
        const events = resumed.snapshot();
        console.log(JSON.stringify({
          sequences: events.map((event) => event.sequence),
          elapsed: events.map((event) => event.elapsed_ms),
          meaningful: events.map((event) => event.meaningful_activation),
          transitions: events.map((event) => event.screen_transition),
          summary: summarizeEvents(events),
        }));
        """
    )

    assert result["sequences"] == [1, 2, 3]
    assert result["elapsed"] == [10, 11, 21]
    assert result["meaningful"] == [True, False, True]
    assert result["transitions"] == [True, False, True]
    assert result["summary"] == {
        "meaningful_activations": 2,
        "context_transitions": 2,
        "elapsed_ms": 21,
    }
