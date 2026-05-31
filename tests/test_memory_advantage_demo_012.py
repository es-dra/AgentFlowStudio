from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from narratocut.memory_advantage_demo_012 import (
    DEMO_ID,
    build_demo_012_package,
    run_demo_012_i2v_storyboards,
    run_demo_012_i2i_keyframes,
    write_demo_012_package,
)
from narratocut.memory_advantage_demo_012_review import build_i2v_review, render_i2v_review_html
from narratocut.memory_advantage_demo_012_content import MAX_T2I_PROMPT_CHARS
from tests.memory_advantage_demo_012_helpers import demo_012_store as _store
from tests.memory_advantage_demo_012_helpers import write_i2i_manifest as _write_i2i_manifest
from tests.memory_advantage_demo_012_helpers import write_i2v_manifest as _write_i2v_manifest
from tests.provider_smoke_helpers import provider_config


def test_demo_012_package_locks_six_image_i2i_experiment_without_provider_calls(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", raising=False)
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_VIDEO", raising=False)

    package = build_demo_012_package(_store(tmp_path), subject_reference_image_ref="yiqi_front.png")

    assert package["schema_version"] == "memory_advantage_demo_012_package.v1"
    assert package["demo_id"] == DEMO_ID
    assert package["provider_calls_started"] is False
    assert package["writes_long_term_memory"] is False
    assert package["image_budget"]["total_keyframes"] == 6
    assert package["image_budget"]["scene_count"] == 3
    assert package["image_budget"]["lanes"] == ["baseline", "memory_assisted"]
    assert [scene["scene_id"] for scene in package["scene_stress_tests"]] == [
        "desert_wind_walk",
        "neon_rain_turn",
        "combat_dodge_motion",
    ]
    assert len(package["image_requests"]) == 6
    assert {request["provider_plan"]["api_family"] for request in package["image_requests"]} == {"i2i"}
    assert {
        request["provider_plan"]["subject_reference"]["image_ref"]
        for request in package["image_requests"]
    } == {"yiqi_front.png"}
    assert _request(package, "baseline", "desert_wind_walk")["seed"] == _request(
        package, "memory_assisted", "desert_wind_walk"
    )["seed"]
    assert package["claim_boundaries"]["quality_improvement_claim"] == "not_claimed"

    serialized = json.dumps(package, ensure_ascii=False)
    assert "fake-minimax-key" not in serialized
    assert "fake-secret-key" not in serialized
    assert "Bearer " not in serialized
    assert "data:image/" not in serialized
    assert str(tmp_path) not in serialized


def test_demo_012_prompts_keep_baseline_fair_and_memory_structured(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", raising=False)
    package = build_demo_012_package(_store(tmp_path), subject_reference_image_ref="yiqi_front.png")

    baseline = _request(package, "baseline", "neon_rain_turn")
    memory = _request(package, "memory_assisted", "neon_rain_turn")

    assert baseline["subject_reference_role"] == "same_fixed_character_reference_image"
    assert memory["subject_reference_role"] == "same_fixed_character_reference_image"
    assert "Visual Memory Asset Card" not in baseline["image_prompt"]
    assert "normal professional character-consistency prompt" in baseline["method_note"]
    assert "Visual Memory Asset Card Yiqi v1" in memory["image_prompt"]
    assert "identity lock" in memory["image_prompt"]
    assert "wardrobe lock" in memory["image_prompt"]
    assert "T-shirt hem covers the waist" in memory["image_prompt"]
    assert "no crop top" in memory["image_prompt"]
    assert "no hair accessories" in memory["image_prompt"]
    assert len(memory["continuity_anchors"]) > len(baseline["continuity_anchors"])
    assert package["experiment_card"]["baseline"] != package["experiment_card"]["change"]


def test_demo_012_image_prompts_fit_minimax_limit(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", raising=False)
    package = build_demo_012_package(_store(tmp_path), subject_reference_image_ref="yiqi_front.png")

    for request in package["image_requests"]:
        assert len(request["image_prompt"]) <= MAX_T2I_PROMPT_CHARS, request["request_id"]


def test_demo_012_writer_outputs_six_image_run_package(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", raising=False)
    package = build_demo_012_package(_store(tmp_path), subject_reference_image_ref="yiqi_front.png")

    paths = write_demo_012_package(package, tmp_path / "plan")

    assert {path.name for path in paths} == {
        "accepted_character_asset.json",
        "visual_memory_asset_card.json",
        "scene_stress_tests.json",
        "image_requests.json",
        "evaluation_rubric.json",
        "run_plan.json",
        "demo_012_report.md",
    }
    assert all(path.is_file() for path in paths)
    run_plan = json.loads((tmp_path / "plan" / "run_plan.json").read_text(encoding="utf-8"))
    assert run_plan["image_budget"]["total_keyframes"] == 6
    report = (tmp_path / "plan" / "demo_012_report.md").read_text(encoding="utf-8")
    assert "3 scenes x 2 lanes = 6 keyframes" in report
    assert "Provider calls started: false" in report
    assert "Do not claim memory advantage" in report
    serialized = "".join(path.read_text(encoding="utf-8") for path in paths)
    assert "fake-minimax-key" not in serialized
    assert "data:image/" not in serialized


def test_demo_012_cli_writes_no_call_package(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", raising=False)
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(provider_config()), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "memory-advantage-demo-012-plan",
            "--provider-config",
            str(config_path),
            "--subject-reference-image-ref",
            "yiqi_front.png",
            "--output",
            str(tmp_path / "plan"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "AFS-MEMORY-ADVANTAGE-DEMO-012" in result.output
    assert "Provider calls: not started" in result.output
    assert "Images planned: 6" in result.output
    assert (tmp_path / "plan" / "image_requests.json").is_file()
    assert str(config_path) not in result.output
    assert "fake-minimax-key" not in result.output


def test_demo_012_i2v_cli_exposes_runtime_command() -> None:
    result = CliRunner().invoke(app, ["memory-advantage-demo-012-i2v-runtime", "--help"])

    assert result.exit_code == 0, result.output
    assert "Run gated DEMO-012 Kling I2V storyboards" in result.output
    assert "--run-dir" in result.output
    assert "--transport" in result.output


def test_demo_012_i2i_runtime_uses_same_reference_and_six_calls(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", raising=False)
    reference_path = tmp_path / "yiqi_front.png"
    reference_path.write_bytes(b"fake-png")
    calls = []

    def fake_runner(store, **kwargs):
        output_dir = Path(kwargs["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        lane = output_dir.parent.parent.name
        scene_id = output_dir.parent.name
        _write_i2i_manifest(tmp_path / "run", lane, scene_id)
        calls.append(kwargs)
        return {"status": "succeeded", "outputs": [{"image_path": "image_candidates/candidate_001.png"}]}

    summary = run_demo_012_i2i_keyframes(
        _store(tmp_path),
        tmp_path / "run",
        subject_reference_image_path=reference_path,
        image_runner=fake_runner,
    )

    assert len(calls) == 6
    assert {call["subject_reference_image_path"] for call in calls} == {reference_path}
    assert {call["aspect_ratio"] for call in calls} == {"9:16"}
    assert {call["candidate_count"] for call in calls} == {1}
    assert {call["model_name_override"] for call in calls} == {"image-01"}
    assert len({call["seed"] for call in calls}) == 3
    assert all("Visual Memory Asset Card" not in call["prompt"] for call in calls[:3])
    assert all("Visual Memory Asset Card Yiqi v1" in call["prompt"] for call in calls[3:])
    assert summary["generated_image_count"] == 6
    assert summary["generated_video_count"] == 0
    assert (tmp_path / "run" / "image_review.json").is_file()
    assert (tmp_path / "run" / "image_review.html").is_file()
    assert (tmp_path / "run" / "image_runtime_summary.json").is_file()


def test_demo_012_i2v_runtime_uses_existing_keyframes_and_six_calls(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_VIDEO", raising=False)
    package = build_demo_012_package(_store(tmp_path), subject_reference_image_ref="yiqi_front.png")
    run_root = tmp_path / "run"
    calls = []
    for request in package["image_requests"]:
        _write_i2i_manifest(run_root, request["lane"], request["scene_id"])

    def fake_video_runner(store, **kwargs):
        image_path = Path(kwargs["image_path"])
        output_dir = Path(kwargs["output_dir"])
        assert image_path.is_file()
        lane = output_dir.parent.parent.name
        scene_id = output_dir.parent.name
        _write_i2v_manifest(run_root, lane, scene_id)
        calls.append(kwargs)
        return {"status": "succeeded", "outputs": [{"video_path": "video_candidates/candidate_001.mp4"}]}

    summary = run_demo_012_i2v_storyboards(
        _store(tmp_path),
        run_root,
        video_runner=fake_video_runner,
    )

    assert len(calls) == 6
    assert {call["service_id"] for call in calls} == {"kling_i2v"}
    assert {call["duration"] for call in calls} == {"5"}
    assert {call["mode"] for call in calls} == {"pro"}
    assert all("Visual Memory Asset Card" not in call["prompt"] for call in calls[:3])
    assert all("Visual Memory Asset Card Yiqi v1" in call["prompt"] for call in calls[3:])
    assert all("provider-secret-url" not in json.dumps(call, ensure_ascii=False, default=str) for call in calls)
    assert summary["generated_image_count"] == 6
    assert summary["generated_video_count"] == 6
    assert summary["claim_boundary"] == "provider_smoke_only_not_creative_quality"
    assert (run_root / "i2v_review.json").is_file()
    assert (run_root / "i2v_review.html").is_file()
    assert (run_root / "i2v_runtime_summary.json").is_file()


def test_demo_012_i2v_review_summarizes_side_by_side_videos_without_claim(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("NARRATOCUT_ALLOW_REMOTE_VIDEO", raising=False)
    package = build_demo_012_package(_store(tmp_path), subject_reference_image_ref="yiqi_front.png")
    run_root = tmp_path / "run"
    for request in package["image_requests"]:
        _write_i2i_manifest(run_root, request["lane"], request["scene_id"])
        _write_i2v_manifest(run_root, request["lane"], request["scene_id"])

    review = build_i2v_review(package, run_root)
    html = render_i2v_review_html(package, review)

    assert review["schema_version"] == "memory_advantage_demo_012_i2v_review.v1"
    assert review["status"] == "i2v_storyboard_provider_smoke_succeeded"
    assert review["generated_image_count"] == 6
    assert review["generated_video_count"] == 6
    assert review["creative_quality_review"] == "not_reviewed"
    assert review["human_acceptance"] == "not_reviewed"
    assert review["business_validation"] == "not_validated"
    assert review["quality_improvement_claim"] == "not_claimed"
    assert {(item["lane"], item["scene_id"]) for item in review["video_artifacts"]} == {
        ("baseline", "desert_wind_walk"),
        ("baseline", "neon_rain_turn"),
        ("baseline", "combat_dodge_motion"),
        ("memory_assisted", "desert_wind_walk"),
        ("memory_assisted", "neon_rain_turn"),
        ("memory_assisted", "combat_dodge_motion"),
    }
    assert "Baseline" in html
    assert "Memory Assisted" in html
    assert "live/baseline/desert_wind_walk/i2v/video_candidates/candidate_001.mp4" in html
    assert "Provider smoke is not creative quality validation." in html
    serialized = json.dumps(review, ensure_ascii=False) + html
    assert "Bearer " not in serialized
    assert "fake-secret-key" not in serialized
    assert "http" not in serialized


def test_demo_012_i2v_review_html_escapes_dynamic_values(monkeypatch, tmp_path) -> None:
    package = build_demo_012_package(_store(tmp_path), subject_reference_image_ref="yiqi_front.png")
    package["scene_stress_tests"][0]["stressor"] = "<script>alert(1)</script>"
    review = {
        "quality_improvement_claim": "not_claimed",
        "human_acceptance": "not_reviewed",
        "business_validation": "not_validated",
        "video_artifacts": [
            {
                "lane": "baseline",
                "scene_id": "desert_wind_walk",
                "video_path": 'x" onerror="alert(1).mp4',
            }
        ],
        "keyframe_artifacts": [
            {
                "lane": "baseline",
                "scene_id": "desert_wind_walk",
                "image_path": "<script>alert(2)</script>.jpg",
            }
        ],
    }

    html = render_i2v_review_html(package, review)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert 'x" onerror="alert(1).mp4' not in html
    assert 'x&quot; onerror=&quot;alert(1).mp4' in html
    assert "<script>alert(2)</script>" not in html


def _request(package: dict, lane: str, scene_id: str) -> dict:
    for request in package["image_requests"]:
        if request["lane"] == lane and request["scene_id"] == scene_id:
            return request
    raise AssertionError(f"request not found: {lane}/{scene_id}")
