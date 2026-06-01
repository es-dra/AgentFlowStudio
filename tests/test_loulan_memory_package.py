from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from agentflow.memory.loulan_package import build_loulan_memory_package
from tests.loulan_memory_package_fixtures import _loulan_fixture, _write_json


def test_loulan_memory_package_blocks_candidates_and_builtin_image_route(tmp_path: Path) -> None:
    root = _loulan_fixture(tmp_path)

    package = build_loulan_memory_package(root, created_at="2026-06-01T09:00:00+08:00")

    assert package["artifact_type"] == "agentflow_loulan_memory_package"
    assert package["project"]["project_id"] == "loulan_scene_assets"
    assert package["provider_calls_started"] is False
    assert package["writes_long_term_memory"] is False
    assert package["project"]["source_root_label"] == root.name
    assert package["shot_summary"]["total_shots"] == 2
    assert package["shot_summary"]["status_counts"]["keyframe_candidate_pending_review"] == 1
    assert package["asset_summary"]["status_counts"]["approved"] == 1
    assert package["asset_summary"]["status_counts"]["candidate_pending_human_review"] == 1
    assert package["asset_summary"]["missing_sha256_count"] == 1
    assert package["asset_summary"]["rejected_asset_count"] == 1
    assert package["provider_route_safety"]["image_generation"] == "blocked_until_api_workbench"
    assert package["provider_route_safety"]["unsafe_builtin_image_route_detected"] is True
    assert package["project_audits"] == {
        "manifest_reference": {
            "status": "pass",
            "artifact_ref": "reviews/manifest_reference_audit.json",
            "report_ref": "reviews/manifest_reference_audit.md",
            "summary": {
                "json_files_checked": 14,
                "registry_assets": 87,
                "errors": 0,
                "missing_sha256": 0,
                "missing_files": 0,
                "absolute_refs": 0,
                "secret_like_refs": 0,
                "manifest_string_issues": 0,
                "invalid_asset_types": 0,
                "invalid_statuses": 0,
            },
        },
        "text_encoding": {
            "status": "pass",
            "artifact_ref": "reviews/text_encoding_audit.json",
            "report_ref": "reviews/text_encoding_audit.md",
            "summary": {
                "text_files_checked": 268,
                "decode_errors": 0,
                "marker_hits": 0,
                "errors": 0,
            },
        },
        "phase_gate": {
            "status": "blocked_until_b01_human_review",
            "artifact_ref": "reviews/asset_governance_phase_audit.json",
            "report_ref": "reviews/asset_governance_phase_audit.md",
            "summary": {
                "phases": 5,
                "passed": 4,
                "blocked_expected": 1,
                "failures": 0,
                "registry_assets": 87,
                "eligible_context_refs": 3,
                "blocked_context_refs": 84,
                "pending_b01_decisions": 5,
            },
        },
    }
    assert package["feedback_loop_gates"]["b01"]["status"] == "blocked_pending_human_review"
    assert package["feedback_loop_gates"]["b01"]["pending_decisions"] == 5
    assert package["feedback_loop_gates"]["b01"]["context_projection_ready"] is False
    assert package["feedback_loop_gates"]["b01"]["source_ref"] == "manifests/afs_b01_feedback_loop_gate.json"
    crosswalk = package["feedback_loop_gates"]["b01_decision_crosswalk"]
    assert crosswalk["status"] == "blocked_pending_human_review"
    assert crosswalk["local_shot_gate"]["decision_count"] == 5
    assert crosswalk["afs_b01_import_gate"]["decision_count"] == 7
    assert crosswalk["afs_broader_decision_review_gate"]["decision_count"] == 47
    assert crosswalk["afs_broader_decision_review_gate"]["target_ref_count"] == 47
    assert crosswalk["source_ref"] == "manifests/afs_b01_decision_crosswalk.json"
    entrypoint = package["feedback_loop_gates"]["b01_operator_entrypoint"]
    assert entrypoint["status"] == "blocked_pending_human_review"
    assert entrypoint["source_ref"] == "manifests/b01_operator_entrypoint.json"
    assert (entrypoint["pending_decisions"], entrypoint["operator_steps"], entrypoint["blocked_until_count"]) == (5, 6, 4)
    assert (entrypoint["recommendations"], entrypoint["pending_operator_decisions"]) == (5, 5)
    assert package["promotion_gates"]["overall_status"] == "blocked"
    assert package["next_context_bundle_draft"]["eligible_memory_refs"] == ["character:zhou_tong_school_v1"]
    assert {
        "character:guan_pingping_v2",
        "human/rejected/guan_pingping_v1.png",
    } <= set(package["next_context_bundle_draft"]["blocked_memory_refs"])
    assert [node["label"] for node in package["canvas_nodes"]] == [
        "Project",
        "Shots",
        "Assets",
        "Memory Loaded",
        "Baseline Plan",
        "Memory-backed Plan",
        "Review",
        "Feedback",
        "Next Pass",
    ]

    serialized = json.dumps(package, ensure_ascii=False)
    assert str(root) not in serialized
    assert "D:\\" not in serialized
    assert "api_key" not in serialized
    assert ".mp4" not in serialized


def test_loulan_memory_package_cli_writes_safe_dry_run_artifacts(tmp_path: Path) -> None:
    root = _loulan_fixture(tmp_path)
    output = tmp_path / "out"

    result = CliRunner().invoke(
        app,
        [
            "loulan-memory-package",
            "--project-root",
            str(root),
            "--created-at",
            "2026-06-01T09:00:00+08:00",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Loulan memory package" in result.output
    assert "Provider calls: not started" in result.output
    assert "Overall gate: blocked" in result.output
    assert "Manifest audit: pass; errors 0; invalid asset types 0; invalid statuses 0" in result.output
    assert "Text encoding audit: pass; errors 0" in result.output
    assert "Phase gate audit: blocked_until_b01_human_review; failures 0; pending B01 5" in result.output
    assert str(root) not in result.output

    package_path = output / "loulan_memory_package.json"
    report_path = output / "loulan_memory_package.md"
    assert package_path.exists()
    assert report_path.exists()
    package = json.loads(package_path.read_text(encoding="utf-8"))
    assert package["artifact_type"] == "agentflow_loulan_memory_package"
    assert package["provider_route_safety"]["request_preview_only"] is True
    assert package["feedback_loop_gates"]["b01"]["status"] == "blocked_pending_human_review"
    report = report_path.read_text(encoding="utf-8")
    assert "durable Memory runtime: not implemented" in report
    assert "Invalid asset types: 0" in report
    assert "Invalid statuses: 0" in report
    assert "Phase gate failures: 0" in report


def test_loulan_memory_package_example_is_contract_safe() -> None:
    payload = json.loads(Path("examples/agentflow/loulan_memory_package.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_loulan_memory_package"
    assert payload["provider_calls_started"] is False
    assert payload["writes_long_term_memory"] is False
    assert payload["provider_route_safety"]["image_generation"] == "blocked_until_api_workbench"
    assert payload["promotion_gates"]["overall_status"] in {"ready", "blocked"}
    assert payload["api_workbench_skeleton"]["live_provider_calls"] == "blocked_by_default"
    assert payload["project_audits"]["manifest_reference"]["status"] == "pass"
    assert payload["project_audits"]["manifest_reference"]["summary"]["invalid_asset_types"] == 0
    assert payload["project_audits"]["manifest_reference"]["summary"]["invalid_statuses"] == 0
    assert payload["project_audits"]["text_encoding"]["status"] == "pass"
    assert payload["project_audits"]["text_encoding"]["summary"]["errors"] == 0
    assert payload["project_audits"]["phase_gate"]["status"] == "blocked_until_b01_human_review"
    assert payload["project_audits"]["phase_gate"]["summary"]["failures"] == 0
    assert payload["feedback_loop_gates"]["b01"]["provider_calls_started"] is False
    assert payload["feedback_loop_gates"]["b01_decision_crosswalk"]["afs_b01_import_gate"]["pending_count"] == 7
    assert payload["feedback_loop_gates"]["b01_operator_entrypoint"]["pending_operator_decisions"] == 5
    assert "asset:character_zhou_tong_school_v1" in payload["next_context_bundle_draft"]["eligible_memory_refs"]
    serialized = json.dumps(payload, ensure_ascii=False)
    assert "D:\\" not in serialized
    assert ".mp4" not in serialized
    assert "signed_url" not in serialized
