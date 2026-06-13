from __future__ import annotations

from pathlib import Path

import pytest


LEGACY_TEST_FILE_PREFIXES = (
    "test_agentflow_production_",
    "test_asr_",
    "test_audio_",
    "test_candidate_",
    "test_clip_plan_",
    "test_highlight_",
    "test_ocr_",
    "test_posterflow_",
    "test_production_memory_",
    "test_video_to_",
    "test_workflow_",
)

LEGACY_TEST_FILES = {
    "test_agentflow_asset_memory_validator.py",
    "test_ffmpeg_cli.py",
    "test_ffmpeg_probe.py",
    "test_memory_review_cli.py",
    "test_mock_slicer.py",
    "test_phase2_roi.py",
    "test_real_slicer.py",
    "test_real_slicer_contract.py",
    "test_real_slicing_cli.py",
    "test_real_video_quality_checks.py",
    "test_real_video_workflow.py",
    "test_script_highlight_alignment.py",
    "test_selection_diagnostics.py",
    "test_selection_quality_scoring.py",
    "test_slicing_cli.py",
    "test_tool_catalog.py",
}

CURRENT_GATE_TEST_FILES = {
    "test_api_runtime_prompt_memory_candidates.py",
    "test_api_runtime_service.py",
    "test_api_runtime_service_v02.py",
    "test_architecture_audit_gates.py",
    "test_ci_maintenance_workflow.py",
    "test_cli_command_registry_boundaries.py",
    "test_studio_mainline_cleanup.py",
}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    legacy_marker = pytest.mark.legacy
    for item in items:
        if is_legacy_test_path(Path(str(item.path))):
            item.add_marker(legacy_marker)


def is_legacy_test_path(path: Path) -> bool:
    name = path.name
    if name in CURRENT_GATE_TEST_FILES:
        return False
    if name in LEGACY_TEST_FILES:
        return True
    return any(name.startswith(prefix) for prefix in LEGACY_TEST_FILE_PREFIXES)
