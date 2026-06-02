from __future__ import annotations

import json
from pathlib import PureWindowsPath

from agentflow_studio.schemas import ROISettings, Transcript


EXAMPLE_ROOT = "examples/demo_highlight"


def test_script_input_example_declares_script_only_contract() -> None:
    payload = _read_json(f"{EXAMPLE_ROOT}/script_input.example.json")

    assert payload["input_mode"] == "script_only"
    assert payload["script_path"] == f"{EXAMPLE_ROOT}/script.txt"
    assert payload["roi_config_path"] == f"{EXAMPLE_ROOT}/roi_config.json"
    assert payload["output_dir"] == "data/processed/runs/demo_highlight_script"
    assert "video_path" not in payload
    assert _all_paths_are_relative(payload)


def test_transcript_input_example_declares_timestamped_contract() -> None:
    payload = _read_json(f"{EXAMPLE_ROOT}/transcript_input.example.json")

    assert payload["input_mode"] == "timestamped_transcript"
    assert payload["transcript_path"] == f"{EXAMPLE_ROOT}/transcript.json"
    assert payload["roi_config_path"] == f"{EXAMPLE_ROOT}/roi_config.json"
    assert payload["output_dir"] == "data/processed/runs/demo_highlight_transcript"
    assert _all_paths_are_relative(payload)


def test_demo_transcript_example_matches_schema() -> None:
    payload = _read_json(f"{EXAMPLE_ROOT}/transcript.json")
    transcript = Transcript.model_validate(payload)

    assert transcript.transcript_id == "demo_transcript_001"
    assert transcript.segments[0].segment_id == "seg_001"
    assert transcript.segments[0].start_time == 0.0
    assert transcript.segments[0].end_time > transcript.segments[0].start_time


def test_demo_roi_config_matches_phase_9_roi_schema() -> None:
    payload = _read_json(f"{EXAMPLE_ROOT}/roi_config.json")
    settings = ROISettings.model_validate(payload)

    assert settings.target_platform == "douyin"
    assert settings.validation_policy == "advisory"
    assert "hook_strength" in settings.priority


def test_script_text_has_no_fake_timestamps() -> None:
    text = _read_text(f"{EXAMPLE_ROOT}/script.txt")

    assert "start_time" not in text
    assert "end_time" not in text
    assert "很多人以为努力就一定会成功" in text


def _read_json(path: str) -> dict[str, object]:
    with open(path, encoding="utf-8") as file:
        payload = json.load(file)
    assert isinstance(payload, dict)
    return payload


def _read_text(path: str) -> str:
    with open(path, encoding="utf-8") as file:
        return file.read()


def _all_paths_are_relative(payload: dict[str, object]) -> bool:
    for key, value in payload.items():
        if not key.endswith(("_path", "_dir")) or not isinstance(value, str):
            continue
        if PureWindowsPath(value).is_absolute() or value.startswith("/"):
            return False
    return True
