from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from agentflow.memory.video_pipeline_review import (
    build_memory_video_pipeline_review,
    write_memory_video_pipeline_review,
)
from apps.cli.main import app


EXAMPLE_PROTOCOL = Path("examples/agentflow/memory_video_pipeline_protocol.example.json")


def test_review_from_explicit_artifact_manifest_writes_safe_cross_run_evidence(tmp_path) -> None:
    protocol = _protocol()
    artifacts = _artifact_manifest(tmp_path, run_count=2)

    review = build_memory_video_pipeline_review(protocol, artifacts)
    paths = write_memory_video_pipeline_review(review, tmp_path / "review")

    assert review["artifact_type"] == "agentflow_memory_video_pipeline_review"
    assert review["provider_calls_started_by_review"] is False
    assert review["writes_long_term_memory"] is False
    assert review["lane_parity"]["expected_lanes_present"] is True
    assert review["lane_parity"]["same_source_image_sha256"] is True
    assert review["cross_run_stability"]["status"] == "ready_for_human_visual_review"
    assert review["cross_run_stability"]["run_count"] == 2
    assert review["cross_run_stability"]["lane_repeat_counts"] == {
        "baseline": 2,
        "memory_backed": 2,
    }
    assert review["claim_boundaries"]["human_acceptance"] == "not_reviewed"
    assert review["claim_boundaries"]["business_validation"] == "not_validated"
    assert review["claim_boundaries"]["quality_improvement_claim"] == "not_claimed"

    assert {path.name for path in paths} == {
        "memory_video_pipeline_review.json",
        "memory_video_pipeline_review.md",
    }
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert str(tmp_path) not in serialized
    assert "D:\\Projects" not in serialized
    assert "https://" not in serialized
    assert "Bearer " not in serialized
    assert "data:image/" not in serialized
    assert "signed_url" not in serialized


def test_review_requires_every_expected_lane_for_each_run(tmp_path) -> None:
    protocol = _protocol()
    artifacts = _artifact_manifest(tmp_path, run_count=2)
    artifacts["artifacts"] = [
        item
        for item in artifacts["artifacts"]
        if not (item["run_id"] == "recording_016_run_2" and item["lane_id"] == "memory_backed")
    ]

    with pytest.raises(ValueError, match="missing lane artifacts"):
        build_memory_video_pipeline_review(protocol, artifacts)


def test_review_rejects_provider_urls_and_absolute_video_paths(tmp_path) -> None:
    protocol = _protocol()
    artifacts = _artifact_manifest(tmp_path, run_count=1)
    first_manifest = Path(artifacts["artifacts"][0]["i2v_manifest_path"])
    manifest = json.loads(first_manifest.read_text(encoding="utf-8"))
    manifest["outputs"][0]["provider_url"] = "https://provider.example.com/signed.mp4?token=abc"
    first_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="unsafe"):
        build_memory_video_pipeline_review(protocol, artifacts)

    artifacts = _artifact_manifest(tmp_path / "absolute_path_case", run_count=1)
    first_manifest = Path(artifacts["artifacts"][0]["i2v_manifest_path"])
    manifest = json.loads(first_manifest.read_text(encoding="utf-8"))
    manifest["outputs"][0]["video_path"] = "D:\\Projects\\AgentFlowStudio\\data\\processed\\video.mp4"
    first_manifest.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="unsafe"):
        build_memory_video_pipeline_review(protocol, artifacts)


def test_cli_writes_review_from_protocol_and_explicit_artifact_manifest(tmp_path) -> None:
    protocol_path = tmp_path / "protocol.json"
    artifacts_path = tmp_path / "artifacts.json"
    protocol_path.write_text(json.dumps(_protocol(), ensure_ascii=False), encoding="utf-8")
    artifacts_path.write_text(
        json.dumps(_artifact_manifest(tmp_path, run_count=2), ensure_ascii=False),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "memory-video-pipeline-review",
            "--protocol",
            str(protocol_path),
            "--artifacts",
            str(artifacts_path),
            "--output",
            str(tmp_path / "review"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Memory video pipeline review" in result.output
    assert "Runs reviewed: 2" in result.output
    assert "Provider calls: not started" in result.output
    assert str(protocol_path) not in result.output
    assert str(artifacts_path) not in result.output
    assert (tmp_path / "review" / "memory_video_pipeline_review.json").is_file()


def test_cli_accepts_powershell_utf8_bom_json_inputs(tmp_path) -> None:
    protocol_path = tmp_path / "protocol.json"
    artifacts_path = tmp_path / "artifacts.json"
    protocol_path.write_text("\ufeff" + json.dumps(_protocol(), ensure_ascii=False), encoding="utf-8")
    artifacts_path.write_text(
        "\ufeff" + json.dumps(_artifact_manifest(tmp_path, run_count=1), ensure_ascii=False),
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "memory-video-pipeline-review",
            "--protocol",
            str(protocol_path),
            "--artifacts",
            str(artifacts_path),
            "--output",
            str(tmp_path / "review"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Runs reviewed: 1" in result.output


def test_plan_cli_accepts_powershell_utf8_bom_protocol(tmp_path) -> None:
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text("\ufeff" + json.dumps(_protocol(), ensure_ascii=False), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "memory-video-pipeline-plan",
            "--protocol",
            str(protocol_path),
            "--output",
            str(tmp_path / "plan"),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Lanes planned: 2" in result.output
    assert (tmp_path / "plan" / "request_plan.json").is_file()


def _protocol() -> dict:
    return json.loads(EXAMPLE_PROTOCOL.read_text(encoding="utf-8"))


def _artifact_manifest(root: Path, run_count: int) -> dict:
    artifacts = []
    for index in range(1, run_count + 1):
        run_id = f"recording_016_run_{index}"
        for lane_id in ["baseline", "memory_backed"]:
            manifest_path = root / run_id / lane_id / "kling_i2v_smoke_manifest.json"
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            manifest_path.write_text(
                json.dumps(_kling_manifest(run_id, lane_id), ensure_ascii=False),
                encoding="utf-8",
            )
            artifacts.append(
                {
                    "run_id": run_id,
                    "lane_id": lane_id,
                    "i2v_manifest_path": str(manifest_path),
                }
            )
    return {
        "schema_version": "0.1.0",
        "artifact_type": "agentflow_memory_video_pipeline_artifact_manifest",
        "artifacts": artifacts,
    }


def _kling_manifest(run_id: str, lane_id: str) -> dict:
    return {
        "schema_version": "kling_i2v_smoke_manifest.v1",
        "status": "succeeded",
        "service_id": "kling_i2v",
        "provider": "kling",
        "api_family": "i2v",
        "model": "kling-v3",
        "capability": "video",
        "task": {
            "task_id": f"{run_id}_{lane_id}",
            "task_status": "succeed",
        },
        "outputs": [
            {
                "candidate_id": "candidate_001",
                "video_path": "video_candidates/candidate_001.mp4",
                "byte_count": 30_000_000 + len(run_id) + len(lane_id),
                "sha256": f"sha256-{run_id}-{lane_id}",
                "content_type": "video/mp4",
                "provider_url_persisted": False,
            }
        ],
        "input_image": {
            "path_persisted": False,
            "byte_count": 242_694,
            "sha256": "same-source-keyframe-sha256",
        },
    }
