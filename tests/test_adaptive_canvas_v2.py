from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import agentflow_studio.production.adaptive_canvas_v2 as adaptive_canvas
import pytest

from agentflow.harness.json_io import write_json
from agentflow_studio.model_gateway.errors import ModelGatewayError
from agentflow_studio.production.adaptive_canvas_v2 import (
    AdaptiveCanvasError,
    AdaptiveRunOptions,
    ChargeLedger,
    PaidAttemptLimitExceeded,
    ProviderArtifactRetryExceeded,
    build_agent_authored_script_input,
    build_script_truth_from_profile,
    compile_duration_chunks,
    load_adaptive_workspace,
    run_adaptive_canvas_production,
    seed_agent_authored_script_truth,
    _video_safety_text,
)
from agentflow_studio.production.media_operations_review import (
    _classification,
    _prop_locks,
    build_media_operations_command_preview,
    load_media_operations_review,
    media_file_path,
)
from agentflow_studio.production.real_anime_4shot import alternate_no_provider_profile, real_anime_4shot_paid_profile
from apps.api.runtime_service import create_runtime_app
from apps.api.runtime_store import RuntimeStore, read_json
from fastapi.testclient import TestClient


@pytest.fixture
def offline_adaptive_media(monkeypatch: pytest.MonkeyPatch) -> dict[Path, dict[str, object]]:
    metadata: dict[Path, dict[str, object]] = {}

    def key(path: Path) -> Path:
        return Path(path).resolve()

    def record(path: Path, payload: bytes, probe: dict[str, object]) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        metadata[key(target)] = probe

    def video_probe(duration_sec: float) -> dict[str, object]:
        return {
            "streams": [
                {
                    "codec_type": "video",
                    "width": 160,
                    "height": 284,
                    "avg_frame_rate": "12/1",
                    "r_frame_rate": "12/1",
                    "nb_frames": str(int(round(float(duration_sec) * 12))),
                }
            ],
            "format": {"duration": f"{float(duration_sec):.3f}"},
        }

    def fake_png(path: Path, color: str) -> None:
        record(
            path,
            f"offline-png:{color}".encode("utf-8"),
            video_probe(1.0),
        )

    def fake_video(path: Path, *, duration_sec: int, color: str) -> None:
        record(
            path,
            f"offline-mp4:{duration_sec}:{color}".encode("utf-8"),
            video_probe(float(duration_sec)),
        )

    def concat_videos(inputs: list[Path], output: Path, *, duration_sec: float) -> None:
        assert inputs
        for source in inputs:
            assert Path(source).exists()
        record(
            output,
            f"offline-concat:{duration_sec:.3f}".encode("utf-8"),
            video_probe(float(duration_sec)),
        )

    def extract_tail_frame(video: Path, output: Path) -> None:
        if not Path(video).exists():
            raise FileNotFoundError(str(video))
        fake_png(output, "tail-frame")

    def contact_sheet(video: Path, output: Path) -> None:
        if not Path(video).exists():
            raise FileNotFoundError(str(video))
        record(
            output,
            b"offline-contact-sheet",
            video_probe(1.0),
        )

    def probe(path: Path) -> dict[str, object]:
        value = metadata.get(key(path))
        if value is None:
            raise AdaptiveCanvasError(f"offline media fixture has no probe metadata: {Path(path).name}")
        return value

    def decode_check(path: Path) -> dict[str, str]:
        return {"status": "pass" if Path(path).exists() else "failed", "stderr_tail": ""}

    def video_event_scan(path: Path) -> dict[str, object]:
        return {"status": "pass", "black_segments": [], "freeze_events": []}

    monkeypatch.setattr(adaptive_canvas, "_fake_png", fake_png)
    monkeypatch.setattr(adaptive_canvas, "_fake_video", fake_video)
    monkeypatch.setattr(adaptive_canvas, "_concat_videos", concat_videos)
    monkeypatch.setattr(adaptive_canvas, "_extract_tail_frame", extract_tail_frame)
    monkeypatch.setattr(adaptive_canvas, "_contact_sheet", contact_sheet)
    monkeypatch.setattr(adaptive_canvas, "_probe", probe)
    monkeypatch.setattr(adaptive_canvas, "_decode_check", decode_check)
    monkeypatch.setattr(adaptive_canvas, "_video_event_scan", video_event_scan)
    return metadata


def test_missing_ffmpeg_media_tool_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def missing_executable(cmd: list[str], *args: object, **kwargs: object) -> object:
        raise FileNotFoundError(cmd[0])

    monkeypatch.setattr(adaptive_canvas.subprocess, "run", missing_executable)
    with pytest.raises(AdaptiveCanvasError, match="command executable not found: ffmpeg"):
        adaptive_canvas._fake_video(tmp_path / "missing-tool.mp4", duration_sec=5, color="0x000000")


def test_paid_profile_is_a_profile_not_core_constant(tmp_path: Path, offline_adaptive_media: dict[Path, dict[str, object]]) -> None:
    profile = real_anime_4shot_paid_profile()
    assert profile.llm_service_id == "disabled_agent_authored"
    assert profile.script_candidate_id == "agent-authored-script-v1"
    assert profile.script_contract_id is None
    assert profile.script_source_type == "agent_authored_test_input"
    assert profile.script_decision_source == "OWNER_DECISION_A_AGENT_AUTHORED_SCRIPT_RELEASED"
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
    assert workspace["script"]["provenance"]["source_type"] == "agent_authored_test_input"
    assert workspace["script"]["provenance"]["provider_generated"] is False
    assert workspace["script"]["provenance"]["llm_success"] is False
    assert workspace["script"]["provenance"]["owner_acceptance"] is False
    assert workspace["script"]["provenance"]["purpose"] == "paid_media_vertical_slice"
    assert [shot["target_duration_sec"] for shot in workspace["shots"]] == [15.0, 15.0, 15.0, 15.0]
    assert {shot["generation_strategy"] for shot in workspace["shots"]} == {"image_to_video"}
    assert workspace["final_demo"]["duration_sec"] >= 59.0
    qa = read_json(
        tmp_path
        / "runtime"
        / "projects"
        / "paid-profile-fake"
        / "adaptive_canvas_v2"
        / "run-001"
        / "qa"
        / "technical_qa.json"
    )
    assert qa["media_metrics"]["width"] == 160
    assert qa["media_metrics"]["fps"] == 12.0
    assert qa["media_metrics"]["frame_count"] == 720
    assert qa["media_metrics"]["black_segment_count"] == 0
    assert qa["media_metrics"]["freeze_event_count"] == 0
    assert qa["technical_scores"]["resolution_fps_frame_count"] == 5
    assert qa["technical_scores"]["black_freeze_repeat_anomaly"] == 5


def test_cinematic_media_profile_keeps_adaptive_workspace_contract(
    tmp_path: Path,
    offline_adaptive_media: dict[Path, dict[str, object]],
) -> None:
    profile = replace(
        real_anime_4shot_paid_profile(),
        title="M6.2 cinematic paid media profile",
        media_prompt_style="cinematic_live_action",
        media_aspect_ratio="16:9",
        video_motion="controlled live-action camera movement; preserve continuity",
        media_negative_locks=("no logos", "no readable text", "no smoke"),
    )

    result = run_adaptive_canvas_production(
        AdaptiveRunOptions(
            runtime_root=tmp_path / "runtime",
            project_id="m6-2-cinematic-profile",
            run_id="run-001",
            profile=profile,
            mode="fake",
        )
    )

    store = RuntimeStore(tmp_path / "runtime")
    workspace = load_adaptive_workspace(store, project_id="m6-2-cinematic-profile", run_id="run-001")
    assert result["status"] == "succeeded"
    assert result["paid_attempt_count"] == 0
    assert workspace["script"]["shot_count"] == profile.shot_count
    assert workspace["assets"]["style_bible"] == profile.style_bible
    assert workspace["provider_dispatch_count"] == 0


def test_media_operations_review_is_safe_and_keeps_single_graph_lineage(
    tmp_path: Path,
    offline_adaptive_media: dict[Path, dict[str, object]],
) -> None:
    profile = replace(
        real_anime_4shot_paid_profile(),
        title="M6.3 operations contract profile",
        media_negative_locks=("no logos", "no readable text"),
    )
    run_adaptive_canvas_production(
        AdaptiveRunOptions(
            runtime_root=tmp_path / "runtime",
            project_id="m6-3-ops-profile",
            run_id="run-001",
            profile=profile,
            mode="fake",
        )
    )

    store = RuntimeStore(tmp_path / "runtime")
    review = load_media_operations_review(store, project_id="m6-3-ops-profile", run_id="run-001")
    serialized = json.dumps(review, ensure_ascii=False, sort_keys=True)

    assert review["schema_version"] == "afs.media_operations_review.v0.1"
    assert review["summary"]["shot_count"] == profile.shot_count
    assert review["summary"]["graph_digest"]
    assert review["shots"][0]["keyframe_url"].startswith("/projects/m6-3-ops-profile/adaptive-canvas-v2/media/keyframe/")
    assert review["shots"][0]["video_url"].startswith("/projects/m6-3-ops-profile/adaptive-canvas-v2/media/shot-video/")
    assert review["assets"]["reference_set"]["reference_sheet_url"].endswith("run_id=run-001")
    assert review["provider_boundary"] == {
        "browser_dispatch_count": 0,
        "incremental_cost_usd": 0.0,
        "uses_existing_paid_evidence": True,
        "production_provider_gates_expected_closed": True,
    }
    creator_copy = json.dumps(
        {
            "next_action": review["stage"]["next_action"],
            "journey": review["journey"],
            "continuity_warning": review["assets"]["continuity_warning"],
        },
        ensure_ascii=False,
    )
    assert not any(
        token in creator_copy
        for token in ("M6", "revision2", "Owner", "ReferenceSet", "ProductionGraph")
    )
    assert review["commands"][0]["paid_until_confirmed"] is False
    assert "not_human_creative_acceptance" in review["advanced_evidence"]["non_claims"]
    assert not any(token in serialized.lower() for token in ("/home/", "/tmp/", "/var/", "api_key", "authorization", "bearer", "secret", ".mp4", ".png"))
    preview = build_media_operations_command_preview(
        store,
        project_id="m6-3-ops-profile",
        run_id="run-001",
        action="local_redo_preview",
        shot_id=review["shots"][0]["shot_id"],
    )
    assert preview["schema_version"] == "afs.media_operations_command_preview.v0.1"
    assert preview["will_dispatch_provider_now"] is False
    assert preview["will_mutate_now"] is False
    assert preview["requires_explicit_charge_confirmation"] is True
    assert len(preview["unaffected_shot_digests_preserved"]) == profile.shot_count - 1
    assert preview["idempotency_key"].startswith("m6-3-")
    assert "不会发起生成或产生费用" in preview["human_message"]
    assert "Provider" not in preview["human_message"]


def test_media_recovery_classification_depends_on_ledger_not_project_name() -> None:
    assert _classification({}) == "CLEAN_FULL_CASE"
    assert _classification({"attempts": [], "project_id": "sci_fi_chamber-adversarial"}) == "CLEAN_FULL_CASE"
    assert _classification({
        "attempts": [{"attempt_id": "attempt-1", "stage": "video_chunk", "status": "failed"}],
    }) == "RECOVERY_EVIDENCE_NOT_COUNTED"


def test_media_prop_locks_use_structured_canonical_props_without_name_rules() -> None:
    props = _prop_locks({
        "assets": {
            "props": [
                {
                    "name": "黑曜石钥匙",
                    "classification": "canonical_prop",
                    "continuity": "始终由主角左手持有",
                },
                {
                    "display_name": "折叠星图",
                    "classification": "canonical_prop",
                    "do_not_change": ["保持刻度方向", "保持折痕位置"],
                },
                {
                    "name": "海风色板",
                    "classification": "production_aid",
                },
            ],
        },
    })

    assert [item["name"] for item in props] == ["黑曜石钥匙", "折叠星图"]
    assert props[0]["continuity"] == "始终由主角左手持有"
    assert props[1]["continuity"] == "保持刻度方向；保持折痕位置"
    assert all(item["status"] == "locked" for item in props)


def test_video_prompt_text_preserves_story_terms_without_keyword_rewrites() -> None:
    source = "  红色风筝在旧桥上方掠过，角色面对冲突后放下工具。  "
    assert _video_safety_text(source) == source.strip()


def test_media_operations_preview_route_serves_only_known_runtime_media(
    tmp_path: Path,
    offline_adaptive_media: dict[Path, dict[str, object]],
) -> None:
    profile = real_anime_4shot_paid_profile()
    run_adaptive_canvas_production(
        AdaptiveRunOptions(
            runtime_root=tmp_path / "runtime",
            project_id="m6-3-route-profile",
            run_id="run-001",
            profile=profile,
            mode="fake",
        )
    )
    store = RuntimeStore(tmp_path / "runtime")
    review = load_media_operations_review(store, project_id="m6-3-route-profile", run_id="run-001")
    keyframe, image_type = media_file_path(
        store,
        project_id="m6-3-route-profile",
        run_id="run-001",
        media_kind="keyframe",
        media_id=review["shots"][0]["shot_id"],
    )
    final, video_type = media_file_path(
        store,
        project_id="m6-3-route-profile",
        run_id="run-001",
        media_kind="final-video",
        media_id="primary",
    )

    assert keyframe.is_file()
    assert image_type == "image/png"
    assert final.is_file()
    assert video_type == "video/mp4"
    with pytest.raises(KeyError):
        media_file_path(
            store,
            project_id="m6-3-route-profile",
            run_id="run-001",
            media_kind="keyframe",
            media_id="../../secret",
        )


def test_run_state_clears_current_error_after_recovery_and_preserves_audit_history(tmp_path: Path) -> None:
    path = tmp_path / "run_state.json"
    state = {
        "schema_version": "afs.adaptive_canvas_v2.v0.1",
        "project_id": "project",
        "run_id": "run",
    }
    error = {"type": "RuntimeError", "message": "temporary contract failure"}

    adaptive_canvas._write_state(path, state, status="failed", safe_error=error)
    failed = read_json(path)
    assert failed["status"] == "failed"
    assert failed["safe_error"] == error
    assert failed["error_history"][-1]["safe_error"] == error

    adaptive_canvas._write_state(path, state, status="running")
    running = read_json(path)
    assert running["status"] == "running"
    assert "safe_error" not in running
    assert running["error_history"][-1]["safe_error"] == error

    adaptive_canvas._write_state(path, state, status="succeeded")
    succeeded = read_json(path)
    assert succeeded["status"] == "succeeded"
    assert "safe_error" not in succeeded
    assert [item["safe_error"] for item in succeeded["error_history"]] == [error]


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


def test_charge_ledger_attempt_id_includes_fingerprint_for_prompt_retry(tmp_path: Path) -> None:
    ledger = ChargeLedger(tmp_path / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)
    old = ledger.reserve(
        stage="video_chunk",
        shot_id="shot-005",
        chunk_id="chunk-01",
        candidate_id="candidate-001",
        capability="video",
        service_id="seedance_i2v",
        prompt="risky provider prompt",
    )
    ledger.mark_started(old["attempt_id"])
    ledger.mark_failed(old["attempt_id"], RuntimeError("provider rejected prompt"))

    new = ledger.reserve(
        stage="video_chunk",
        shot_id="shot-005",
        chunk_id="chunk-01",
        candidate_id="candidate-001",
        capability="video",
        service_id="seedance_i2v",
        prompt="safe provider prompt",
    )
    ledger.mark_started(new["attempt_id"])

    payload = read_json(ledger.path)
    assert old["charge_fingerprint"] != new["charge_fingerprint"]
    assert old["attempt_id"] != new["attempt_id"]
    assert payload["attempts"][0]["status"] == "failed"
    assert payload["attempts"][0]["safe_error"]["message"] == "provider rejected prompt"
    assert payload["attempts"][1]["status"] == "started"
    assert payload["attempts"][1].get("safe_error") is None


def test_charge_ledger_rejects_completed_attempt_resurrection(tmp_path: Path) -> None:
    ledger = ChargeLedger(tmp_path / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)
    attempt = ledger.reserve(
        stage="video_chunk",
        shot_id="shot-005",
        chunk_id="chunk-01",
        candidate_id="candidate-001",
        capability="video",
        service_id="seedance_i2v",
        prompt="provider prompt",
    )
    ledger.mark_started(attempt["attempt_id"])
    ledger.mark_failed(attempt["attempt_id"], RuntimeError("provider rejected prompt"))

    with pytest.raises(AdaptiveCanvasError, match="completed provider attempt cannot be restarted"):
        ledger.mark_started(attempt["attempt_id"])
    with pytest.raises(AdaptiveCanvasError, match="completed provider attempt cannot be marked submitted"):
        ledger.mark_submitted(attempt["attempt_id"], provider_task_id="task-1", provider_poll_task={"task": {"task_id": "task-1"}})
    with pytest.raises(AdaptiveCanvasError, match="failed provider attempt cannot be marked succeeded"):
        ledger.mark_succeeded(attempt["attempt_id"], {"artifact_version_id": "a", "sha256": "b", "kind": "video"})

    payload = read_json(ledger.path)
    assert payload["paid_attempt_count"] == 1
    assert payload["attempts"][0]["status"] == "failed"
    assert payload["attempts"][0]["safe_error"]["message"] == "provider rejected prompt"


def test_charge_ledger_submit_recovery_requires_task_id(tmp_path: Path) -> None:
    ledger = ChargeLedger(tmp_path / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)
    attempt = ledger.reserve(
        stage="video_chunk",
        shot_id="shot-005",
        chunk_id="chunk-01",
        candidate_id="candidate-001",
        capability="video",
        service_id="seedance_i2v",
        prompt="provider prompt",
    )
    ledger.mark_started(attempt["attempt_id"])

    with pytest.raises(AdaptiveCanvasError, match="provider task id is required"):
        ledger.mark_submitted(attempt["attempt_id"], provider_task_id="", provider_poll_task={"task": {"task_id": ""}})

    payload = read_json(ledger.path)
    assert payload["attempts"][0]["status"] == "started"


def _provider_script_v3_profile():
    return replace(
        real_anime_4shot_paid_profile(),
        llm_service_id="server_codex",
        script_candidate_id="script-v3",
        script_contract_id="adaptive_canvas_script_v3",
        script_source_type="provider",
        script_decision_source=None,
    )


def _script_v3_payload() -> dict[str, object]:
    truth = build_script_truth_from_profile(_provider_script_v3_profile())
    shot_fields = (
        "shot_id",
        "summary",
        "location",
        "characters",
        "action",
        "camera",
        "target_duration_sec",
        "generation_strategy",
        "strategy_reason",
        "continuity_in",
        "continuity_out",
    )
    return {
        "title": truth["title"],
        "logline": truth["logline"],
        "style_bible": truth["style_bible"],
        "characters": truth["characters"],
        "scenes": truth["scenes"],
        "shots": [{key: shot[key] for key in shot_fields} for shot in truth["shots"]],
    }


def test_paid_script_v3_route_dispatches_only_to_server_codex_with_schema_digest(tmp_path: Path) -> None:
    class RecordingRegistry:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str]] = []
            self.request: object | None = None

        def dispatch(self, capability: str, service_id: str, request: object) -> dict[str, object]:
            self.calls.append((capability, service_id))
            self.request = request
            return {
                "text": json.dumps(_script_v3_payload()),
                "structured_output": _script_v3_payload(),
                "provider_calls_started": True,
            }

    profile = _provider_script_v3_profile()
    options = AdaptiveRunOptions(tmp_path / "runtime", "project", "run", profile, mode="real")
    run_root = tmp_path / "run"
    run_root.mkdir()
    ledger = ChargeLedger(run_root / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)
    registry = RecordingRegistry()
    adaptive_canvas._ensure_script(run_root, options, ledger, registry, None)

    assert registry.calls == [("llm", "server_codex")]
    assert registry.request.task_type == "adaptive_canvas_script_v3"
    assert registry.request.structured_output_contract_id == "adaptive_canvas_script_v3"
    assert registry.request.structured_output_schema["type"] == "object"
    assert len(registry.request.structured_output_schema_digest) == 64
    assert ledger.paid_attempt_count == 1
    assert ledger.attempts[0]["service_id"] == "server_codex"
    assert ledger.attempts[0]["candidate_id"] == "script-v3"
    assert ledger.attempts[0]["contract_id"] == "adaptive_canvas_script_v3"
    assert ledger.attempts[0]["contract_schema_digest"] == registry.request.structured_output_schema_digest


@pytest.mark.parametrize(
    "reason",
    [
        "markdown fence final rejected",
        "preface or suffix final rejected",
        "empty final rejected",
        "Codex CLI nonzero exit",
    ],
)
def test_script_v3_provider_failure_paths_mark_attempt_failed(tmp_path: Path, reason: str) -> None:
    class InvalidRegistry:
        def dispatch(self, capability: str, service_id: str, request: object) -> dict[str, object]:
            raise ModelGatewayError(reason)

    profile = _provider_script_v3_profile()
    options = AdaptiveRunOptions(tmp_path / "runtime", "project", "run", profile, mode="real")
    run_root = tmp_path / "run"
    run_root.mkdir()
    ledger = ChargeLedger(run_root / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)

    with pytest.raises(ModelGatewayError, match=reason):
        adaptive_canvas._ensure_script(run_root, options, ledger, InvalidRegistry(), None)

    assert ledger.paid_attempt_count == 1
    assert ledger.attempts[0]["status"] == "failed"
    assert ledger.attempts[0]["provider_calls_started"] is True
    assert ledger.attempts[0]["service_id"] == "server_codex"
    assert ledger.attempts[0]["candidate_id"] == "script-v3"
    assert ledger.attempts[0]["attempt_index"] == 1
    assert ledger.attempts[0]["safe_error"]["type"] == "ModelGatewayError"


def test_script_v3_schema_invalid_final_marks_attempt_failed(tmp_path: Path) -> None:
    class InvalidRegistry:
        def dispatch(self, capability: str, service_id: str, request: object) -> dict[str, object]:
            payload = _script_v3_payload()
            payload["title"] = "robot"
            return {
                "text": json.dumps(payload),
                "structured_output": payload,
                "provider_calls_started": True,
            }

    profile = _provider_script_v3_profile()
    options = AdaptiveRunOptions(tmp_path / "runtime", "project", "run", profile, mode="real")
    run_root = tmp_path / "run"
    run_root.mkdir()
    ledger = ChargeLedger(run_root / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)

    with pytest.raises(AdaptiveCanvasError, match="forbidden fixed template leaked into script"):
        adaptive_canvas._ensure_script(run_root, options, ledger, InvalidRegistry(), None)

    assert ledger.attempts[0]["status"] == "failed"
    assert ledger.attempts[0]["safe_error"]["type"] == "AdaptiveCanvasError"


def test_script_v3_profile_contract_mismatch_marks_attempt_failed(tmp_path: Path) -> None:
    class InvalidRegistry:
        def dispatch(self, capability: str, service_id: str, request: object) -> dict[str, object]:
            payload = _script_v3_payload()
            payload["shots"][0]["target_duration_sec"] = 99.0
            return {
                "text": json.dumps(payload),
                "structured_output": payload,
                "provider_calls_started": True,
            }

    profile = _provider_script_v3_profile()
    options = AdaptiveRunOptions(tmp_path / "runtime", "project", "run", profile, mode="real")
    run_root = tmp_path / "run"
    run_root.mkdir()
    ledger = ChargeLedger(run_root / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)

    with pytest.raises(AdaptiveCanvasError, match="structured script duration must match profile"):
        adaptive_canvas._ensure_script(run_root, options, ledger, InvalidRegistry(), None)

    assert ledger.attempts[0]["status"] == "failed"
    assert ledger.attempts[0]["safe_error"]["type"] == "AdaptiveCanvasError"


def test_script_v3_schema_digest_changes_charge_fingerprint(tmp_path: Path) -> None:
    ledger = ChargeLedger(tmp_path / "ledger.json", project_id="project", run_id="run", max_paid_attempts=20)
    first = ledger.fingerprint(
        stage="script",
        shot_id=None,
        chunk_id=None,
        candidate_id="script-v3",
        prompt="prompt",
        contract_id="adaptive_canvas_script_v3",
        contract_schema_digest="a" * 64,
    )
    second = ledger.fingerprint(
        stage="script",
        shot_id=None,
        chunk_id=None,
        candidate_id="script-v3",
        prompt="prompt",
        contract_id="adaptive_canvas_script_v3",
        contract_schema_digest="b" * 64,
    )

    assert first != second


def test_video_attempt_resumes_submitted_task_without_second_provider_start(tmp_path: Path) -> None:
    class ResumeRegistry:
        def __init__(self) -> None:
            self.submit_calls = 0
            self.poll_calls = 0

        def submit(self, capability: str, service_id: str, request: object) -> dict[str, object]:
            self.submit_calls += 1
            raise AssertionError("resumed video jobs must not submit a second provider request")

        def poll(self, capability: str, service_id: str, task: dict[str, object]) -> dict[str, object]:
            self.poll_calls += 1
            assert capability == "video"
            assert service_id == "seedance_i2v"
            assert (task.get("task") or {}).get("task_id") == "task-123"
            return {
                "status": "succeeded",
                "provider_calls_started": True,
                "outputs": [{"candidate_id": "candidate_001", "video_path": "video_candidates/candidate_001.mp4"}],
            }

    profile = real_anime_4shot_paid_profile()
    options = AdaptiveRunOptions(tmp_path / "runtime", "project", "run", profile, mode="real")
    ledger = ChargeLedger(tmp_path / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)
    prompt = "safe video prompt"
    attempt = ledger.reserve(
        stage="video_chunk",
        shot_id="shot-001",
        chunk_id="chunk-01",
        candidate_id="candidate-001",
        capability="video",
        service_id="seedance_i2v",
        prompt=prompt,
    )
    ledger.mark_started(attempt["attempt_id"])
    ledger.mark_submitted(
        attempt["attempt_id"],
        provider_task_id="task-123",
        provider_poll_task={
            "service_id": "seedance_i2v",
            "capability": "video",
            "task": {
                "status": "submitted",
                "task_id": "task-123",
                "query_url_template": "https://provider.example/tasks/{id}",
                "timeout_sec": 5.0,
                "download_timeout_sec": 5.0,
                "allowed_url_hosts": (".example",),
                "output_dir": tmp_path / "provider_outputs",
            },
        },
    )

    registry = ResumeRegistry()
    result = adaptive_canvas._real_video_attempt(
        options,
        ledger,
        registry,
        shot_id="shot-001",
        chunk_id="chunk-01",
        prompt=prompt,
        first_frame=tmp_path / "first.png",
        duration_sec=5,
        output_dir=tmp_path / "provider_outputs",
    )

    assert result["status"] == "succeeded"
    assert registry.submit_calls == 0
    assert registry.poll_calls == 1
    assert ledger.paid_attempt_count == 1


def test_script_v3_parser_exception_marks_attempt_failed(tmp_path: Path, monkeypatch) -> None:
    class Registry:
        def dispatch(self, capability: str, service_id: str, request: object) -> dict[str, object]:
            return {
                "text": json.dumps(_script_v3_payload()),
                "structured_output": _script_v3_payload(),
                "provider_calls_started": True,
            }

    def parser_failure(payload: dict[str, object], profile: object) -> dict[str, object]:
        raise RuntimeError("parser failed")

    monkeypatch.setattr(adaptive_canvas, "_parse_script_payload", parser_failure)
    profile = _provider_script_v3_profile()
    options = AdaptiveRunOptions(tmp_path / "runtime", "project", "run", profile, mode="real")
    run_root = tmp_path / "run"
    run_root.mkdir()
    ledger = ChargeLedger(run_root / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)

    with pytest.raises(RuntimeError, match="parser failed"):
        adaptive_canvas._ensure_script(run_root, options, ledger, Registry(), None)

    assert ledger.attempts[0]["status"] == "failed"
    assert ledger.attempts[0]["safe_error"]["type"] == "RuntimeError"


def test_script_v3_recovery_after_one_failure_does_not_dispatch_again(tmp_path: Path) -> None:
    class InvalidRegistry:
        def __init__(self) -> None:
            self.calls = 0

        def dispatch(self, capability: str, service_id: str, request: object) -> dict[str, object]:
            self.calls += 1
            raise ModelGatewayError("invalid structured final")

    profile = _provider_script_v3_profile()
    options = AdaptiveRunOptions(tmp_path / "runtime", "project", "run", profile, mode="real")
    run_root = tmp_path / "run"
    run_root.mkdir()
    ledger = ChargeLedger(run_root / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)
    registry = InvalidRegistry()

    with pytest.raises(ModelGatewayError, match="invalid structured final"):
        adaptive_canvas._ensure_script(run_root, options, ledger, registry, None)
    before = json.loads(json.dumps(ledger.attempts))
    with pytest.raises(ProviderArtifactRetryExceeded):
        adaptive_canvas._ensure_script(run_root, options, ledger, registry, None)

    assert registry.calls == 1
    assert ledger.paid_attempt_count == 1
    assert ledger.attempts == before
    assert ledger.attempts[0]["status"] == "failed"
    assert ledger.attempts[0]["attempt_index"] == 1



def _record_four_failed_script_attempts(ledger: ChargeLedger) -> None:
    history = (
        ("prompt_optimizer", "script-v1", None, None),
        ("server_codex", "script-v2", None, None),
        ("server_codex", "script-v2", None, None),
        ("server_codex", "script-v3", "adaptive_canvas_script_v3", "a" * 64),
    )
    for service_id, candidate_id, contract_id, schema_digest in history:
        attempt = ledger.reserve(
            stage="script",
            shot_id=None,
            chunk_id=None,
            candidate_id=candidate_id,
            capability="llm",
            service_id=service_id,
            prompt=f"frozen-{candidate_id}",
            contract_id=contract_id,
            contract_schema_digest=schema_digest,
            max_provider_starts=2,
        )
        ledger.mark_started(attempt["attempt_id"])
        ledger.mark_failed(attempt["attempt_id"], AdaptiveCanvasError("historical script failure"))


def test_agent_authored_seed_preserves_failed_history_and_explicit_lineage(tmp_path: Path) -> None:
    runtime_root = tmp_path / "runtime"
    run_root = runtime_root / "projects" / "project" / "adaptive_canvas_v2" / "run"
    run_root.mkdir(parents=True)
    ledger = ChargeLedger(run_root / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)
    _record_four_failed_script_attempts(ledger)
    ledger_before = ledger.path.read_bytes()

    result = seed_agent_authored_script_truth(
        runtime_root=runtime_root,
        project_id="project",
        run_id="run",
        profile=real_anime_4shot_paid_profile(),
    )

    assert result["status"] == "seeded"
    assert result["paid_attempt_count"] == 4
    assert result["attempt_count"] == 4
    assert result["ledger_mutated"] is False
    assert result["provider_dispatch_count"] == 0
    assert ledger.path.read_bytes() == ledger_before
    script = read_json(run_root / "script_truth.json")
    lineage = script["provenance"]
    assert lineage == read_json(run_root / "agent_authored_script_input.json")["lineage"]
    assert lineage["source_type"] == "agent_authored_test_input"
    assert lineage["author_type"] == "agent"
    assert lineage["provider_generated"] is False
    assert lineage["llm_success"] is False
    assert lineage["owner_acceptance"] is False
    assert lineage["purpose"] == "paid_media_vertical_slice"
    assert lineage["decision_source"] == "OWNER_DECISION_A_AGENT_AUTHORED_SCRIPT_RELEASED"
    assert len(lineage["script_body_sha256"]) == 64
    assert [shot["order"] for shot in script["shots"]] == [1, 2, 3, 4]
    assert [shot["target_duration_sec"] for shot in script["shots"]] == [15.0, 15.0, 15.0, 15.0]
    assert all(shot["character_ids"] == ["aoi", "nori"] for shot in script["shots"])
    assert {shot["scene_id"] for shot in script["shots"]} == {
        "rooftop-lantern-garden",
        "dawn-observatory-bridge",
    }

    truth_before = (run_root / "script_truth.json").read_bytes()
    replay = seed_agent_authored_script_truth(
        runtime_root=runtime_root,
        project_id="project",
        run_id="run",
        profile=real_anime_4shot_paid_profile(),
    )
    assert replay["status"] == "reused"
    assert (run_root / "script_truth.json").read_bytes() == truth_before
    assert ledger.path.read_bytes() == ledger_before


def test_agent_authored_recovery_never_dispatches_or_adds_script_ledger(tmp_path: Path) -> None:
    class NoDispatchRegistry:
        def __init__(self) -> None:
            self.calls = 0

        def dispatch(self, capability: str, service_id: str, request: object) -> dict[str, object]:
            self.calls += 1
            raise AssertionError("agent-authored recovery must not dispatch")

    profile = real_anime_4shot_paid_profile()
    options = AdaptiveRunOptions(tmp_path / "runtime", "project", "run", profile, mode="real")
    run_root = tmp_path / "run"
    run_root.mkdir()
    ledger = ChargeLedger(run_root / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)
    _record_four_failed_script_attempts(ledger)
    before = ledger.path.read_bytes()
    registry = NoDispatchRegistry()

    first = adaptive_canvas._ensure_script(run_root, options, ledger, registry, None)
    truth_before = (run_root / "script_truth.json").read_bytes()
    second = adaptive_canvas._ensure_script(run_root, options, ledger, registry, None)

    assert first == second
    assert registry.calls == 0
    assert ledger.path.read_bytes() == before
    assert ledger.paid_attempt_count == 4
    assert (run_root / "script_truth.json").read_bytes() == truth_before


def test_agent_authored_profile_mismatch_fails_before_any_provider(tmp_path: Path) -> None:
    class NoDispatchRegistry:
        def __init__(self) -> None:
            self.calls = 0

        def dispatch(self, capability: str, service_id: str, request: object) -> dict[str, object]:
            self.calls += 1
            raise AssertionError("invalid canonical input must fail before Provider")

    profile = real_anime_4shot_paid_profile()
    options = AdaptiveRunOptions(tmp_path / "runtime", "project", "run", profile, mode="real")
    run_root = tmp_path / "run"
    run_root.mkdir()
    payload = build_agent_authored_script_input(profile)
    payload["script"]["shots"][0]["target_duration_sec"] = 99.0
    payload["lineage"]["script_body_sha256"] = adaptive_canvas.sha256_text(
        json.dumps(payload["script"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    write_json(run_root / "agent_authored_script_input.json", payload)
    ledger = ChargeLedger(run_root / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)
    registry = NoDispatchRegistry()

    with pytest.raises(AdaptiveCanvasError, match="shot duration must match profile"):
        adaptive_canvas._ensure_script(run_root, options, ledger, registry, None)

    assert registry.calls == 0
    assert ledger.paid_attempt_count == 0
    assert ledger.attempts == []
    assert not (run_root / "script_truth.json").exists()




def test_reference_output_contract_failure_marks_attempt_failed(tmp_path: Path) -> None:
    class InvalidImageRegistry:
        def dispatch(self, capability: str, service_id: str, request: object) -> dict[str, object]:
            return {"outputs": [{"image_path": "missing.png"}], "provider_calls_started": True}

    profile = real_anime_4shot_paid_profile()
    options = AdaptiveRunOptions(tmp_path / "runtime", "project", "run", profile, mode="real")
    run_root = tmp_path / "run"
    run_root.mkdir()
    ledger = ChargeLedger(run_root / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)

    with pytest.raises(FileNotFoundError):
        adaptive_canvas._ensure_reference_sheet(
            run_root,
            options,
            ledger,
            InvalidImageRegistry(),
            build_script_truth_from_profile(profile),
            None,
        )

    assert ledger.attempts[0]["stage"] == "reference_sheet"
    assert ledger.attempts[0]["status"] == "failed"
    assert ledger.attempts[0]["provider_calls_started"] is True
    assert ledger.attempts[0]["safe_error"]["type"] == "FileNotFoundError"


def test_keyframe_output_contract_failure_marks_attempt_failed(tmp_path: Path) -> None:
    class InvalidImageRegistry:
        def dispatch(self, capability: str, service_id: str, request: object) -> dict[str, object]:
            return {"outputs": [{"image_path": "missing.png"}], "provider_calls_started": True}

    profile = real_anime_4shot_paid_profile()
    options = AdaptiveRunOptions(tmp_path / "runtime", "project", "run", profile, mode="real")
    run_root = tmp_path / "run"
    run_root.mkdir()
    reference = run_root / "reference.png"
    reference.write_bytes(b"reference")
    ledger = ChargeLedger(run_root / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)

    with pytest.raises(FileNotFoundError):
        adaptive_canvas._ensure_keyframes(
            run_root,
            options,
            ledger,
            InvalidImageRegistry(),
            build_script_truth_from_profile(profile),
            {"path": str(reference)},
            None,
        )

    assert ledger.attempts[0]["stage"] == "keyframe"
    assert ledger.attempts[0]["status"] == "failed"
    assert ledger.attempts[0]["provider_calls_started"] is True


def test_video_output_contract_failure_marks_attempt_failed(tmp_path: Path) -> None:
    class InvalidVideoRegistry:
        def submit(self, capability: str, service_id: str, request: object) -> dict[str, object]:
            return {"task": {"task_id": "task"}}

        def poll(self, capability: str, service_id: str, submitted: object) -> dict[str, object]:
            return {"status": "succeeded", "outputs": [{"video_path": "missing.mp4"}]}

    profile = real_anime_4shot_paid_profile()
    options = AdaptiveRunOptions(
        tmp_path / "runtime",
        "project",
        "run",
        profile,
        mode="real",
        video_poll_interval_sec=0.01,
    )
    run_root = tmp_path / "run"
    run_root.mkdir()
    keyframe = run_root / "keyframe.png"
    keyframe.write_bytes(b"keyframe")
    ledger = ChargeLedger(run_root / "charge_ledger.json", project_id="project", run_id="run", max_paid_attempts=20)

    with pytest.raises(FileNotFoundError):
        adaptive_canvas._ensure_video_chunks(
            run_root,
            options,
            ledger,
            InvalidVideoRegistry(),
            build_script_truth_from_profile(profile),
            {"shot-001": {"path": str(keyframe)}},
            None,
        )

    assert ledger.attempts[0]["stage"] == "video_chunk"
    assert ledger.attempts[0]["status"] == "failed"
    assert ledger.attempts[0]["provider_calls_started"] is True


def test_zero_provider_counterexample_has_dynamic_shots_durations_and_strategy(
    tmp_path: Path,
    offline_adaptive_media: dict[Path, dict[str, object]],
) -> None:
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


def test_runtime_workspace_api_exposes_safe_projection(
    tmp_path: Path,
    offline_adaptive_media: dict[Path, dict[str, object]],
) -> None:
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


def test_runtime_workspace_api_requires_authenticated_project_owner(
    tmp_path: Path,
    monkeypatch,
    offline_adaptive_media: dict[Path, dict[str, object]],
) -> None:
    monkeypatch.setenv("AFS_AUTH_ENABLED", "true")
    monkeypatch.setenv("AFS_INVITE_CODES", "adaptive-owner,adaptive-other")
    runtime_root = tmp_path / "runtime"
    client = TestClient(create_runtime_app(runtime_root=runtime_root))
    path = "/projects/auth-adaptive/adaptive-canvas-v2/workspace?run_id=run-001"
    assert client.get(path).status_code == 401

    owner = client.post(
        "/auth/register",
        json={
            "email": "adaptive-owner@example.com",
            "password": "strong-password-123",
            "display_name": "owner",
            "invite_code": "adaptive-owner",
        },
    )
    assert owner.status_code == 200, owner.text
    owner_headers = {"Authorization": f"Bearer {owner.json()['session_token']}"}
    created = client.post(
        "/projects",
        headers=owner_headers,
        json={"project_id": "auth-adaptive", "goal": "auth contract"},
    )
    assert created.status_code == 200, created.text

    run_adaptive_canvas_production(
        AdaptiveRunOptions(
            runtime_root=runtime_root,
            project_id="auth-adaptive",
            run_id="run-001",
            profile=alternate_no_provider_profile(),
            mode="fake",
        )
    )
    allowed = client.get(path, headers=owner_headers)
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["schema_version"] == "afs.adaptive_canvas_v2.workspace.v0.1"
    assert allowed.json()["provider_dispatch_count"] == 0

    other = client.post(
        "/auth/register",
        json={
            "email": "adaptive-other@example.com",
            "password": "strong-password-123",
            "display_name": "other",
            "invite_code": "adaptive-other",
        },
    )
    assert other.status_code == 200, other.text
    other_headers = {"Authorization": f"Bearer {other.json()['session_token']}"}
    assert client.get(path, headers=other_headers).status_code == 403
