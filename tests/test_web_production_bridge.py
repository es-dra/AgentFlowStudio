from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from apps.web_bridge.bridge import (
    bridge_health,
    create_workflow_plan,
    inspect_workflow_input,
    list_workflows,
    refresh_run_review,
    run_workflow,
    run_status,
    start_workflow_run,
)
from apps.web_bridge.server import serve
from apps.web_bridge.workflow_profiles import workflow_web_profile
from narratocut.workflow_engine import load_workflow


def test_bridge_health_reports_local_runtime_without_secrets() -> None:
    health = bridge_health()
    serialized = json.dumps(health, ensure_ascii=False)

    assert health["service"] == "narratocut_web_bridge"
    assert health["status"] in {"ready", "degraded"}
    assert health["python"]["version"]
    assert "ffmpeg" in health["media"]
    assert "local_asr" in health
    assert health["local_asr"]["provider"] == "faster_whisper"
    assert health["local_asr"]["status"] in {"ready", "missing_optional_dependency"}
    assert "workspace" in health
    assert "OPENAI_API_KEY" not in serialized
    assert "NARRATOCUT_OPENAI_API_KEY" not in serialized
    assert "api_key" not in serialized.lower()


def test_bridge_exposes_standalone_server_entrypoint() -> None:
    assert callable(serve)


def test_web_bridge_cli_command_starts_local_bridge(monkeypatch) -> None:
    calls = []

    def fake_serve(*, host: str, port: int) -> None:
        calls.append({"host": host, "port": port})

    monkeypatch.setattr("apps.cli.main.serve_web_bridge", fake_serve)

    result = CliRunner().invoke(app, ["web-bridge", "--host", "127.0.0.1", "--port", "8799"])

    assert result.exit_code == 0, result.output
    assert calls == [{"host": "127.0.0.1", "port": 8799}]


def test_bridge_lists_workflows_from_yaml_metadata() -> None:
    workflows = list_workflows()
    names = {workflow["name"] for workflow in workflows}

    assert "mock_roi_to_script" in names
    assert "video_to_finished_package_local_asr" in names
    product = next(workflow for workflow in workflows if workflow["name"] == "video_to_finished_package_local_asr")
    assert product["path"] == "workflows/video_to_finished_package_local_asr.yaml"
    assert product["metadata"]["kind"] == "product"
    assert product["metadata"]["status"] == "recommended"
    assert product["step_count"] > 10
    assert product["inputs"]
    assert product["outputs"]


def test_bridge_marks_demo_and_product_workflow_profiles() -> None:
    workflows = list_workflows()
    demo = next(workflow for workflow in workflows if workflow["name"] == "mock_text_to_slices")
    product = next(workflow for workflow in workflows if workflow["name"] == "video_to_finished_package_local_asr")

    assert demo["web_profile"]["kind"] == "demo"
    assert demo["web_profile"]["quick_start"] is True
    assert demo["web_profile"]["recommended_input"] == "examples/demo_text/story.txt"
    assert demo["web_profile"]["requirements"] == []
    assert "无需媒体" in demo["web_profile"]["summary"]

    assert product["web_profile"]["kind"] == "product"
    assert product["web_profile"]["quick_start"] is False
    assert product["web_profile"]["recommended_input"].endswith("video_to_finished_package_local_asr_input.example.json")
    assert {"local_media", "ffmpeg", "local_asr"} <= set(product["web_profile"]["requirements"])
    assert "完整成品" in product["web_profile"]["summary"]
    assert demo["web_profile"]["display_name"] == "本机演示：文本到切片"
    assert product["web_profile"]["display_name"] == "完整成品包：本地 ASR"


def test_bridge_workflow_profiles_include_readiness_guidance() -> None:
    workflows = list_workflows()
    product = next(workflow for workflow in workflows if workflow["name"] == "video_to_finished_package_local_asr")
    demo = next(workflow for workflow in workflows if workflow["name"] == "mock_text_to_slices")

    assert demo["web_profile"]["next_step_hint"] == "可直接生成计划并运行本机演示；成功后刷新验收报告。"
    assert product["web_profile"]["next_step_hint"] == "先补齐本地视频、BGM、FFmpeg/FFprobe 和 local ASR 依赖，再生成计划。"
    assert product["web_profile"]["review_focus"] == ["final_video", "subtitles", "cover", "bgm", "delivery_package"]


def test_bridge_video_script_profile_points_to_local_alpha_0_4_scenario() -> None:
    workflows = list_workflows()
    product = next(workflow for workflow in workflows if workflow["name"] == "video_script_to_finished_package_local_asr")
    profile = product["web_profile"]

    assert profile["scenario_id"] == "local_alpha_0_4"
    assert profile["recommended_input"] == "data/processed/local_alpha_0_4/video_script_local_asr_input.json"
    assert profile["runbook"] == "docs/local_alpha_0_4_scenario_package.md"
    assert profile["local_setup_blockers"] == [
        "data/raw/demo_real_video/input.mp4",
        "data/raw/demo_bgm/bgm.wav",
        "data/models/faster-whisper/",
        "data/processed/local_alpha_0_4/video_script_local_asr_input.json",
    ]
    assert "Local Alpha 0.4" in profile["next_step_hint"]


def test_bridge_workflow_profile_logic_is_split_from_bridge_module() -> None:
    bridge_source = Path("apps/web_bridge/bridge.py").read_text(encoding="utf-8")
    profile_source = Path("apps/web_bridge/workflow_profiles.py").read_text(encoding="utf-8")
    workflow = load_workflow(Path("workflows/mock_text_to_slices.yaml"))
    profile = workflow_web_profile(workflow, Path("workflows/mock_text_to_slices.yaml"))

    assert "workflow_web_profile" in bridge_source
    assert "_default_web_profile" not in bridge_source
    assert "完整成品包：本地 ASR" not in bridge_source
    assert "完整成品包：本地 ASR" in profile_source
    assert profile["display_name"] == "本机演示：文本到切片"


def test_bridge_plan_generation_does_not_execute_workflow(tmp_path: Path) -> None:
    output_dir = tmp_path / "plans"

    plan = create_workflow_plan(
        workflow_path=Path("workflows/mock_roi_to_script.yaml"),
        input_path=Path("examples/demo_text/story.txt"),
        output_dir=output_dir,
    )

    assert plan["status"] == "draft"
    assert plan["plan_path"].endswith("workflow_plan.json")
    assert Path(plan["plan_path"]).is_file()
    assert not (output_dir / "manifest.json").exists()
    assert not (output_dir / "run_manifest.json").exists()
    assert all(step["execution_status"] == "not_started" for step in plan["steps"])
    assert plan["input_check"]["status"] == "pass"


def test_bridge_reports_missing_files_referenced_by_input_bundle(tmp_path: Path) -> None:
    input_bundle = tmp_path / "input.json"
    input_bundle.write_text(
        json.dumps(
            {
                "video_path": str(tmp_path / "missing.mp4"),
                "roi_config_path": "examples/demo_highlight/roi_config.json",
                "max_clips": 4,
            }
        ),
        encoding="utf-8",
    )

    check = inspect_workflow_input(input_bundle)

    assert check["status"] == "fail"
    assert str(tmp_path / "missing.mp4").replace("\\", "/") in check["missing"]
    assert check["warnings"]
    assert check["summary"] == "存在 1 个缺失引用"
    assert check["categories"]["local_media"] == [str(tmp_path / "missing.mp4").replace("\\", "/")]
    assert check["next_action"] == "修正 input bundle 中的本地文件路径。"


def test_bridge_runs_workflow_and_reports_step_status(tmp_path: Path) -> None:
    output_dir = tmp_path / "runs" / "bridge_mock_run"

    run = run_workflow(
        workflow_path=Path("workflows/mock_roi_to_script.yaml"),
        input_path=Path("examples/demo_text/story.txt"),
        output_dir=output_dir,
    )
    status = run_status(output_dir)

    assert run["status"] == "success"
    assert run["run_id"] == "bridge_mock_run"
    assert run["run_dir"] == str(output_dir).replace("\\", "/")
    assert len(run["steps"]) == 2
    assert {step["status"] for step in run["steps"]} == {"success"}
    assert (output_dir / "manifest.json").is_file()
    assert status["status"] == "success"
    assert status["artifact_index"]["manifest"]["exists"] is True
    assert "run_manifest.json" in status["files"]
    assert status["next_actions"]


def test_bridge_starts_workflow_as_background_run_with_progress_file(tmp_path: Path) -> None:
    output_dir = tmp_path / "runs" / "bridge_background_run"

    started = start_workflow_run(
        workflow_path=Path("workflows/mock_roi_to_script.yaml"),
        input_path=Path("examples/demo_text/story.txt"),
        output_dir=output_dir,
    )
    status = run_status(output_dir)

    assert started["accepted"] is True
    assert started["status"] in {"pending", "running", "success"}
    assert started["status_url"].endswith(str(output_dir).replace("\\", "/"))
    assert (output_dir / "bridge_status.json").is_file()
    assert status["steps"]
    assert {step["status"] for step in status["steps"]} <= {"pending", "running", "success", "failed"}
    assert status["bridge_status_path"].endswith("bridge_status.json")


def test_bridge_refreshes_review_artifacts_after_run(tmp_path: Path) -> None:
    output_dir = tmp_path / "runs" / "bridge_review_run"
    run_workflow(
        workflow_path=Path("workflows/mock_text_to_slices.yaml"),
        input_path=Path("examples/demo_text/story.txt"),
        output_dir=output_dir,
    )

    review = refresh_run_review(output_dir)

    assert review["run_id"] == "bridge_review_run"
    assert review["quality"]["status"] == "pass"
    assert review["review"]["status"] in {"passed", "warning"}
    assert (output_dir / "quality_report.json").is_file()
    assert (output_dir / "review_report.json").is_file()
    assert review["artifacts"]["quality_report"].endswith("quality_report.json")
    assert review["artifacts"]["review_report"].endswith("review_report.json")
