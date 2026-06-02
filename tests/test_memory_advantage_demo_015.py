from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from agentflow_studio.memory_advantage_demo_015 import (
    DEMO_ID,
    build_demo_015_package,
    run_demo_015_i2v_protocol,
    write_demo_015_package,
)
from agentflow_studio.memory_advantage_demo_015_content import MAX_KLING_PROMPT_CHARS
from agentflow_studio.memory_advantage_demo_015_review import (
    build_demo_015_i2v_review,
    render_demo_015_i2v_review_html,
)
from agentflow_studio.model_gateway.company_secrets import load_company_provider_secrets
from tests.provider_smoke_helpers import provider_config


def test_demo_015_package_defines_memory_backed_protocol_without_provider_calls(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)

    package = build_demo_015_package(_store(tmp_path), source_keyframe_ref="candidate_001.jpg")

    assert package["schema_version"] == "memory_advantage_demo_015_package.v1"
    assert package["demo_id"] == DEMO_ID
    assert package["provider_calls_started"] is False
    assert package["writes_long_term_memory"] is False
    assert package["protocol_card"]["not_a_prompt_length_test"] is True
    assert package["source_keyframe"]["role"] == "same_existing_keyframe_for_both_lanes"
    assert package["source_keyframe"]["path_persisted"] is False
    assert [item["lane"] for item in package["generation_projections"]] == ["baseline", "memory_backed"]
    assert len({item["user_task"] for item in package["generation_projections"]}) == 1
    assert len(package["video_requests"]) == 2
    assert {item["provider_plan"]["api_family"] for item in package["video_requests"]} == {"i2v"}
    assert package["claim_boundaries"]["quality_improvement_claim"] == "not_claimed"

    serialized = json.dumps(package, ensure_ascii=False)
    assert "fake-access-key" not in serialized
    assert "fake-secret-key" not in serialized
    assert "Bearer " not in serialized
    assert "data:image/" not in serialized
    assert str(tmp_path) not in serialized


def test_demo_015_prompts_are_projection_of_memory_not_prompt_length_bait(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    package = build_demo_015_package(_store(tmp_path), source_keyframe_ref="candidate_001.jpg")

    baseline = _request(package, "baseline")
    memory = _request(package, "memory_backed")

    assert baseline["user_task"] == memory["user_task"]
    assert baseline["memory_sources_loaded"] == []
    assert memory["memory_sources_loaded"] == [
        "character_memory_card",
        "scene_memory_card",
        "feedback_memory_patch",
    ]
    assert "Character memory:" not in baseline["video_prompt"]
    assert "Feedback memory patch:" not in baseline["video_prompt"]
    assert "Character memory:" in memory["video_prompt"]
    assert "Scene memory:" in memory["video_prompt"]
    assert "Feedback memory patch:" in memory["video_prompt"]
    assert "better than baseline" not in memory["video_prompt"].lower()
    assert len(baseline["video_prompt"]) <= MAX_KLING_PROMPT_CHARS
    assert len(memory["video_prompt"]) <= MAX_KLING_PROMPT_CHARS


def test_demo_015_writer_outputs_protocol_package(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    package = build_demo_015_package(_store(tmp_path), source_keyframe_ref="candidate_001.jpg")

    paths = write_demo_015_package(package, tmp_path / "plan")

    assert {path.name for path in paths} == {
        "protocol_card.json",
        "memory_inputs.json",
        "generation_projections.json",
        "video_requests.json",
        "scorecard_rubric.json",
        "run_plan.json",
        "demo_015_report.md",
    }
    assert all(path.is_file() for path in paths)
    report = (tmp_path / "plan" / "demo_015_report.md").read_text(encoding="utf-8")
    assert "Do not present this as a prompt-length test." in report
    serialized = "".join(path.read_text(encoding="utf-8") for path in paths)
    assert "fake-secret-key" not in serialized
    assert "Bearer " not in serialized


def test_demo_015_cli_writes_no_call_package(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(provider_config()), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "memory-advantage-demo-015-plan",
            "--provider-config",
            str(config_path),
            "--source-keyframe-ref",
            "candidate_001.jpg",
            "--output",
            str(tmp_path / "plan"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "AFS-MEMORY-ADVANTAGE-DEMO-015" in result.output
    assert "Provider calls: not started" in result.output
    assert "Video requests planned: 2" in result.output
    assert (tmp_path / "plan" / "generation_projections.json").is_file()
    assert str(config_path) not in result.output
    assert "fake-secret-key" not in result.output


def test_demo_015_i2v_runtime_uses_same_keyframe_and_two_video_calls(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    source = tmp_path / "candidate_001.jpg"
    source.write_bytes(b"fake-jpg")
    calls = []

    def fake_video_runner(store, **kwargs):
        image_path = Path(kwargs["image_path"])
        output_dir = Path(kwargs["output_dir"])
        assert image_path == source
        lane = output_dir.parent.parent.name
        _write_i2v_manifest(tmp_path / "run", lane)
        calls.append(kwargs)
        return {"status": "succeeded", "outputs": [{"video_path": "video_candidates/candidate_001.mp4"}]}

    summary = run_demo_015_i2v_protocol(
        _store(tmp_path),
        tmp_path / "run",
        source_keyframe_path=source,
        video_runner=fake_video_runner,
    )

    assert len(calls) == 2
    assert {call["service_id"] for call in calls} == {"kling_i2v"}
    assert {call["image_path"] for call in calls} == {source}
    assert {call["duration"] for call in calls} == {"15"}
    assert {call["mode"] for call in calls} == {"pro"}
    assert "Character memory:" not in calls[0]["prompt"]
    assert "Character memory:" in calls[1]["prompt"]
    assert summary["generated_video_count"] == 2
    assert summary["claim_boundary"] == "provider_runtime_only_not_creative_quality_or_business_validation"
    assert (tmp_path / "run" / "i2v_review.json").is_file()
    assert (tmp_path / "run" / "i2v_review.html").is_file()
    assert (tmp_path / "run" / "i2v_runtime_summary.json").is_file()
    serialized = json.dumps(json.loads((tmp_path / "run" / "i2v_review.json").read_text(encoding="utf-8")))
    assert str(source) not in serialized
    assert "fake-secret-key" not in serialized


def test_demo_015_i2v_review_summarizes_without_claim(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AFS_ALLOW_REMOTE_VIDEO", raising=False)
    source = tmp_path / "candidate_001.jpg"
    source.write_bytes(b"fake-jpg")
    package = build_demo_015_package(_store(tmp_path), source_keyframe_ref=source.name)
    run_root = tmp_path / "run"
    for lane in ["baseline", "memory_backed"]:
        _write_i2v_manifest(run_root, lane)

    review = build_demo_015_i2v_review(package, run_root, source)
    html = render_demo_015_i2v_review_html(review)

    assert review["schema_version"] == "memory_advantage_demo_015_i2v_review.v1"
    assert review["same_user_task"] is True
    assert review["production_line_contract"]["not_a_prompt_length_test"] is True
    assert review["generated_video_count"] == 2
    assert review["technical_visual_review"] == "not_reviewed"
    assert review["human_acceptance"] == "not_reviewed"
    assert review["business_validation"] == "not_validated"
    assert review["quality_improvement_claim"] == "not_claimed"
    assert {(item["lane"], item["video_path"]) for item in review["video_artifacts"]} == {
        ("baseline", "live/baseline/desert_occlusion_recovery/i2v/video_candidates/candidate_001.mp4"),
        ("memory_backed", "live/memory_backed/desert_occlusion_recovery/i2v/video_candidates/candidate_001.mp4"),
    }
    assert "Provider runtime is not creative quality validation." in html
    serialized = json.dumps(review, ensure_ascii=False) + html
    assert "Bearer " not in serialized
    assert "fake-secret-key" not in serialized
    assert "http" not in serialized
    assert str(source) not in serialized


def test_demo_015_i2v_review_html_escapes_dynamic_values(monkeypatch, tmp_path) -> None:
    source = tmp_path / "candidate_001.jpg"
    source.write_bytes(b"fake-jpg")
    package = build_demo_015_package(_store(tmp_path), source_keyframe_ref=source.name)
    review = {
        "same_user_task": '<script>alert("task")</script>',
        "quality_improvement_claim": "not_claimed",
        "human_acceptance": "not_reviewed",
        "business_validation": "not_validated",
        "video_artifacts": [
            {"lane": "baseline", "video_path": 'x" onerror="alert(1).mp4'},
        ],
    }

    html = render_demo_015_i2v_review_html(review)

    assert "<script>" not in html
    assert "&lt;script&gt;alert(&quot;task&quot;)&lt;/script&gt;" in html
    assert 'x" onerror="alert(1).mp4' not in html
    assert 'x&quot; onerror=&quot;alert(1).mp4' in html


def _request(package: dict, lane: str) -> dict:
    for request in package["video_requests"]:
        if request["lane"] == lane:
            return request
    raise AssertionError(f"request not found: {lane}")


def _write_i2v_manifest(run_root: Path, lane: str) -> None:
    output_dir = run_root / "live" / lane / "desert_occlusion_recovery" / "i2v"
    video_dir = output_dir / "video_candidates"
    video_dir.mkdir(parents=True, exist_ok=True)
    (video_dir / "candidate_001.mp4").write_bytes(b"fake-mp4")
    manifest = {
        "schema_version": "kling_i2v_smoke_manifest.v1",
        "status": "succeeded",
        "service_id": "kling_i2v",
        "provider": "kling",
        "api_family": "i2v",
        "model": "kling-v3",
        "outputs": [
            {
                "video_path": "video_candidates/candidate_001.mp4",
                "byte_count": 8,
                "sha256": f"sha-vid-{lane}",
                "provider_url_persisted": False,
            }
        ],
        "claim_boundary": "provider_smoke_only_not_creative_quality",
    }
    (output_dir / "kling_i2v_smoke_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def _store(tmp_path):
    config_path = tmp_path / "providers.local.json"
    config_path.write_text(json.dumps(provider_config()), encoding="utf-8")
    return load_company_provider_secrets(config_path)
