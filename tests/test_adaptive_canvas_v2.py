from __future__ import annotations

import json
from pathlib import Path

import agentflow_studio.production.adaptive_canvas_v2 as adaptive_canvas

from agentflow_studio.production.adaptive_canvas_v2 import (
    AdaptiveRunOptions,
    ChargeLedger,
    PaidAttemptLimitExceeded,
    build_script_truth_from_profile,
    compile_duration_chunks,
    load_adaptive_workspace,
    run_adaptive_canvas_production,
)
from agentflow_studio.production.real_anime_4shot import alternate_no_provider_profile, real_anime_4shot_paid_profile
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore, read_json
from fastapi.testclient import TestClient


def test_paid_profile_is_a_profile_not_core_constant(tmp_path: Path) -> None:
    profile = real_anime_4shot_paid_profile()
    assert profile.llm_service_id == "server_codex"
    assert profile.script_candidate_id == "script-v2"
    result = run_adaptive_canvas_production(
        AdaptiveRunOptions(
            runtime_root=tmp_path / "runtime",
            project_id="paid-profile-fake",
            run_id="run-001",
            profile=profile,
            mode="fake",
        )
    )

    assert result["status"] == "succeeded"
    assert round(float(result["final_duration_sec"]), 1) == 60.0
    assert result["paid_attempt_count"] == 0

    store = RuntimeStore(tmp_path / "runtime")
    workspace = load_adaptive_workspace(store, project_id="paid-profile-fake", run_id="run-001")
    assert workspace["script"]["shot_count"] == 4
    assert [shot["target_duration_sec"] for shot in workspace["shots"]] == [15.0, 15.0, 15.0, 15.0]
    assert {shot["generation_strategy"] for shot in workspace["shots"]} == {"image_to_video"}
    assert workspace["final_demo"]["duration_sec"] >= 59.0


def test_failed_script_v1_is_preserved_and_script_v2_has_a_new_fingerprint(tmp_path: Path) -> None:
    ledger = ChargeLedger(tmp_path / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)
    old = ledger.reserve(
        stage="script",
        shot_id=None,
        chunk_id=None,
        candidate_id="script-v1",
        capability="llm",
        service_id="prompt_optimizer",
        prompt="same script request",
    )
    ledger.mark_started(old["attempt_id"])
    ledger.mark_failed(old["attempt_id"], RuntimeError("quota blocked"))
    new = ledger.reserve(
        stage="script",
        shot_id=None,
        chunk_id=None,
        candidate_id="script-v2",
        capability="llm",
        service_id="server_codex",
        prompt="same script request",
    )

    payload = read_json(ledger.path)
    assert payload["paid_attempt_count"] == 1
    assert payload["attempts"][0]["status"] == "failed"
    assert payload["attempts"][0]["service_id"] == "prompt_optimizer"
    assert payload["attempts"][1]["status"] == "reserved"
    assert payload["attempts"][1]["provider_calls_started"] is False
    assert new["service_id"] == "server_codex"
    assert new["candidate_id"] == "script-v2"
    assert old["charge_fingerprint"] != new["charge_fingerprint"]


def test_paid_script_route_dispatches_only_to_server_codex(tmp_path: Path) -> None:
    class RecordingRegistry:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []

        def dispatch(self, capability: str, service_id: str, request: object) -> dict[str, object]:
            self.calls.append((capability, service_id))
            return {
                "text": json.dumps(build_script_truth_from_profile(real_anime_4shot_paid_profile())),
                "provider_calls_started": True,
            }

    profile = real_anime_4shot_paid_profile()
    options = AdaptiveRunOptions(
        runtime_root=tmp_path / "runtime",
        project_id="project",
        run_id="run",
        profile=profile,
        mode="real",
    )
    run_root = tmp_path / "run"
    run_root.mkdir()
    ledger = ChargeLedger(run_root / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)
    registry = RecordingRegistry()
    adaptive_canvas._ensure_script(run_root, options, ledger, registry, None)

    assert registry.calls == [("llm", "server_codex")]
    assert ledger.paid_attempt_count == 1
    assert ledger.attempts[0]["service_id"] == "server_codex"
    assert ledger.attempts[0]["candidate_id"] == "script-v2"


def test_zero_provider_counterexample_has_dynamic_shots_durations_and_strategy(tmp_path: Path) -> None:
    profile = alternate_no_provider_profile()
    result = run_adaptive_canvas_production(
        AdaptiveRunOptions(
            runtime_root=tmp_path / "runtime",
            project_id="adaptive-counterexample",
            run_id="run-001",
            profile=profile,
            mode="fake",
        )
    )

    assert result["status"] == "succeeded"
    store = RuntimeStore(tmp_path / "runtime")
    workspace = load_adaptive_workspace(store, project_id="adaptive-counterexample", run_id="run-001")
    durations = [shot["target_duration_sec"] for shot in workspace["shots"]]
    assert len(durations) == 3
    assert durations == [8.0, 12.0, 16.0]
    assert any(duration != 15.0 for duration in durations)
    assert workspace["timeline"]["duration_sec"] == 36.0
    assert workspace["shots"][0]["generation_strategy"] == "text_to_video"
    assert workspace["shots"][1]["generation_strategy"] == "image_to_video"
    assert workspace["shots"][0]["selected_keyframe"] == {"required": False, "status": "not_required"}
    assert workspace["shots"][1]["selected_keyframe"]["status"] == "selected"
    assert workspace["shots"][1]["reference_binding"]["status"] == "selected"

    ledger = read_json(Path(result["ledger_path"]))
    keyframe_shots = {attempt["shot_id"] for attempt in ledger["attempts"] if attempt["stage"] == "keyframe"}
    video_shots = {attempt["shot_id"] for attempt in ledger["attempts"] if attempt["stage"] == "video_chunk"}
    assert "shot-001" not in keyframe_shots
    assert {"shot-001", "shot-002", "shot-003"} <= video_shots
    assert ledger["paid_attempt_count"] == 0


def test_duration_compiler_uses_provider_durations_and_continuity_anchor() -> None:
    assert compile_duration_chunks(15.0, (10, 5)) == [
        {
            "chunk_id": "chunk-01",
            "provider_duration_sec": 10,
            "timeline_in_sec": 0.0,
            "timeline_out_sec": 10.0,
            "used_duration_sec": 10.0,
            "requires_continuity_anchor": False,
        },
        {
            "chunk_id": "chunk-02",
            "provider_duration_sec": 5,
            "timeline_in_sec": 10.0,
            "timeline_out_sec": 15.0,
            "used_duration_sec": 5.0,
            "requires_continuity_anchor": True,
        },
    ]
    assert compile_duration_chunks(12.0, (10, 5))[-1] == {
        "chunk_id": "chunk-02",
        "provider_duration_sec": 5,
        "timeline_in_sec": 10.0,
        "timeline_out_sec": 12.0,
        "used_duration_sec": 2.0,
        "requires_continuity_anchor": True,
    }
    assert compile_duration_chunks(8.0, (10, 5)) == [
        {
            "chunk_id": "chunk-01",
            "provider_duration_sec": 10,
            "timeline_in_sec": 0.0,
            "timeline_out_sec": 8.0,
            "used_duration_sec": 8.0,
            "requires_continuity_anchor": False,
        }
    ]


def test_image_to_video_and_text_to_video_lineage_in_script_truth() -> None:
    script = build_script_truth_from_profile(alternate_no_provider_profile())
    shot_1, shot_2, shot_3 = script["shots"]

    assert shot_1["generation_strategy"] == "text_to_video"
    assert shot_1["strategy_reason"]
    assert shot_1["chunk_plan"][0]["provider_duration_sec"] == 10
    assert shot_2["generation_strategy"] == "image_to_video"
    assert shot_2["chunk_plan"][-1]["requires_continuity_anchor"] is True
    assert shot_3["target_duration_sec"] == 16.0


def test_charge_ledger_separates_stage_chunk_candidate_and_attempt(tmp_path: Path) -> None:
    ledger = ChargeLedger(tmp_path / "ledger.json", project_id="p", run_id="r", max_paid_attempts=2)
    image = ledger.reserve(
        stage="keyframe",
        shot_id="shot-001",
        chunk_id=None,
        candidate_id="candidate-001",
        capability="image",
        service_id="image_relay",
        prompt="same shot prompt",
    )
    video = ledger.reserve(
        stage="video_chunk",
        shot_id="shot-001",
        chunk_id="chunk-01",
        candidate_id="candidate-001",
        capability="video",
        service_id="seedance_i2v",
        prompt="same shot prompt",
    )
    assert image["charge_fingerprint"] != video["charge_fingerprint"]
    ledger.mark_started(image["attempt_id"])
    ledger.mark_started(video["attempt_id"])

    try:
        extra = ledger.reserve(
            stage="video_chunk",
            shot_id="shot-002",
            chunk_id="chunk-01",
            candidate_id="candidate-001",
            capability="video",
            service_id="seedance_i2v",
            prompt="extra",
        )
        ledger.mark_started(extra["attempt_id"])
    except PaidAttemptLimitExceeded:
        pass
    else:  # pragma: no cover
        raise AssertionError("third paid attempt must be blocked")


def test_runtime_workspace_api_exposes_safe_projection(tmp_path: Path) -> None:
    profile = alternate_no_provider_profile()
    run_adaptive_canvas_production(
        AdaptiveRunOptions(
            runtime_root=tmp_path / "runtime",
            project_id="api-counterexample",
            run_id="run-001",
            profile=profile,
            mode="fake",
        )
    )

    client = TestClient(create_runtime_app(runtime_root=tmp_path / "runtime"))
    response = client.get("/projects/api-counterexample/adaptive-canvas-v2/workspace?run_id=run-001")
    assert response.status_code == 200
    payload = response.json()
    assert payload["script"]["shot_count"] == 3
    assert payload["shots"][0]["generation_strategy"] == "text_to_video"
    assert payload["shots"][0]["reference_binding"]["status"] == "not_required"
    assert payload["shots"][1]["selected_keyframe"]["status"] == "selected"
    assert payload["shots"][1]["chunk_plan"][-1]["requires_continuity_anchor"] is True
    raw = response.text
    assert "/tmp/" not in raw
    assert "/var/" not in raw
    assert ".mp4" not in raw
