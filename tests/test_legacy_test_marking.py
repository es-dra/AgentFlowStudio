from __future__ import annotations

from pathlib import Path

from conftest import is_legacy_test_path


def test_legacy_marker_includes_frozen_production_memory_and_distribution_tests() -> None:
    for name in (
        "test_production_memory_loop.py",
        "test_agentflow_production_workflow.py",
        "test_highlight_detector.py",
        "test_video_to_transcript_workflow.py",
        "test_tool_catalog.py",
    ):
        assert is_legacy_test_path(Path("tests") / name)


def test_legacy_marker_keeps_current_runtime_and_maintenance_gates_active() -> None:
    for name in (
        "test_api_runtime_service.py",
        "test_api_runtime_prompt_memory_candidates.py",
        "test_architecture_audit_gates.py",
        "test_ci_maintenance_workflow.py",
        "test_cli_command_registry_boundaries.py",
        "test_studio_mainline_cleanup.py",
    ):
        assert not is_legacy_test_path(Path("tests") / name)
