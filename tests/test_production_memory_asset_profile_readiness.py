from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)
from agentflow.memory.production_asset_profiles import (
    ASSET_PROFILE_KIND,
    ASSET_PROFILE_READINESS_KIND,
    ASSET_PROFILE_SEED_KIND,
    ASSET_TEST_PACKAGE_KIND,
    build_asset_profile_test_package,
    load_asset_profile_seed,
    write_asset_profile_test_package,
)


EXAMPLE_LOOP = Path("examples/agentflow/production_memory_loop.example.json")
EXAMPLE_SEED = Path("examples/agentflow/production_memory_asset_profile_seed.example.json")
GENERATED_AT = "2026-06-02T00:00:00+08:00"


def test_asset_profile_package_builds_character_and_scene_readiness(tmp_path: Path) -> None:
    manifest_path = _write_operator_loop(tmp_path)
    seed = _seed()

    bundle = build_asset_profile_test_package(
        operator_artifact_path=manifest_path,
        asset_profile_seed=seed,
        generated_at=GENERATED_AT,
    )

    readiness = bundle["readiness"]
    package = bundle["test_package"]
    profiles = bundle["asset_profiles"]
    controls = {item["control_id"]: item["status"] for item in readiness["controls"]}

    assert readiness["kind"] == ASSET_PROFILE_READINESS_KIND
    assert readiness["readiness_status"] == "ready_for_tester_review"
    assert package["kind"] == ASSET_TEST_PACKAGE_KIND
    assert package["package_status"] == "ready_for_tester_review"
    assert {profile["profile_kind"] for profile in profiles} == {"character", "scene"}
    assert all(profile["kind"] == ASSET_PROFILE_KIND for profile in profiles)
    assert all(profile["writes_long_term_memory"] is False for profile in profiles)
    assert all(profile["writes_company_kb"] is False for profile in profiles)
    assert controls["feedback_is_not_memory"] == "passed"
    assert controls["candidate_is_not_promoted_memory"] == "passed"
    assert controls["profile_writes_no_durable_memory"] == "passed"
    assert profiles[0]["allowed_variations"] == ["pose", "expression", "camera angle"]
    assert profiles[0]["negative_constraints"] == ["do not add headwear", "do not change age impression"]
    assert bundle["provider_validation_plan"]["run_provider_validation"] is False
    assert bundle["provider_validation_blockers"][0]["blocker_id"] == "provider_validation_not_requested"


def test_asset_profile_readiness_blocks_missing_seed_refs(tmp_path: Path) -> None:
    manifest_path = _write_operator_loop(tmp_path)
    seed = _seed()
    seed["profiles"][0]["evidence_refs"] = ["artifact:does-not-exist"]

    bundle = build_asset_profile_test_package(
        operator_artifact_path=manifest_path,
        asset_profile_seed=seed,
        generated_at=GENERATED_AT,
    )

    assert bundle["readiness"]["readiness_status"] == "blocked_invalid_refs"
    assert bundle["test_package"]["package_status"] == "blocked"
    assert {
        (item["ref_id"], item["reason"]) for item in bundle["readiness"]["blocked_refs"]
    } == {("artifact:does-not-exist", "missing_reference")}


def test_asset_profile_readiness_blocks_rejected_and_pending_context_refs(tmp_path: Path) -> None:
    manifest_path = _write_operator_loop(tmp_path)
    seed = _seed()
    seed["profiles"][0]["evidence_refs"] = [
        "artifact:draft_storyboard:v1",
        "memory:candidate:pending-tone:v1",
    ]

    bundle = build_asset_profile_test_package(
        operator_artifact_path=manifest_path,
        asset_profile_seed=seed,
        generated_at=GENERATED_AT,
    )

    blocked = {item["ref_id"]: item["reason"] for item in bundle["readiness"]["blocked_refs"]}
    assert bundle["readiness"]["readiness_status"] == "blocked_invalid_refs"
    assert blocked["artifact:draft_storyboard:v1"] == "artifact_status_rejected"
    assert blocked["memory:candidate:pending-tone:v1"] == "memory_candidate_pending"


def test_asset_profile_seed_loader_rejects_private_material_paths(tmp_path: Path) -> None:
    path = tmp_path / "seed.json"
    seed = _seed()
    seed["project_material_refs"][0]["local_path"] = r"D:\Learning materials\Learning_notes\Company\secret.md"
    path.write_text(json.dumps(seed), encoding="utf-8")

    with pytest.raises(ValueError, match="private paths or secrets"):
        load_asset_profile_seed(path)


def test_asset_profile_writer_keeps_runtime_package_safe(tmp_path: Path) -> None:
    manifest_path = _write_operator_loop(tmp_path)
    bundle = build_asset_profile_test_package(
        operator_artifact_path=manifest_path,
        asset_profile_seed=_seed(),
        generated_at=GENERATED_AT,
        project_materials_path=Path(r"D:\private\loulan-final-script.md"),
        character_reference_image_path=Path(r"D:\private\character.png"),
    )

    written = write_asset_profile_test_package(bundle, tmp_path / "asset_package")
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in written if path.suffix in {".json", ".md"})

    assert (tmp_path / "asset_package" / "asset_test_package.json").exists()
    assert (tmp_path / "asset_package" / "tester_feedback_template.md").exists()
    assert "D:\\private" not in serialized
    assert "character.png" not in serialized
    assert "provider secret" not in serialized.lower()


def test_asset_profile_cli_help_and_no_provider_smoke(tmp_path: Path) -> None:
    output_dir = tmp_path / "package"

    help_result = subprocess.run(
        [sys.executable, "-m", "apps.cli.main", "production-memory-loop-run-asset-test-package", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--asset-profile-seed" in help_result.stdout
    assert "--run-provider-validation" in help_result.stdout

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-asset-test-package",
            "--asset-profile-seed",
            str(EXAMPLE_SEED),
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Asset profile test package: ready_for_tester_review" in result.stdout
    assert "Provider validation: not requested" in result.stdout
    assert (output_dir / "operator_loop" / "production_memory_operator_loop_run.json").exists()
    assert (output_dir / "asset_test_package.json").exists()
    assert (output_dir / "asset_profile_readiness.json").exists()
    package = json.loads((output_dir / "asset_test_package.json").read_text(encoding="utf-8"))
    assert package["kind"] == ASSET_TEST_PACKAGE_KIND
    assert package["provider_calls_started"] is False
    assert package["writes_company_kb"] is False


def test_asset_profile_provider_validation_gate_writes_blockers_without_network(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("AFS_ALLOW_REMOTE_IMAGE", None)
    env.pop("AFS_ALLOW_REMOTE_VIDEO", None)
    output_dir = tmp_path / "package"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-run-asset-test-package",
            "--asset-profile-seed",
            str(EXAMPLE_SEED),
            "--run-provider-validation",
            "--image-service",
            "gpt_image2",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    blockers = json.loads((output_dir / "provider_validation_blockers.json").read_text(encoding="utf-8"))
    blocker_ids = {item["blocker_id"] for item in blockers["blockers"]}
    assert "Provider validation: blocked" in result.stdout
    assert "image_gate_unset" in blocker_ids
    assert "video_gate_unset" in blocker_ids
    assert "provider_config_missing" in blocker_ids
    assert "gpt_image2_adapter_unavailable" in blocker_ids
    assert not (output_dir / "provider_validation_result.json").exists()


def _write_operator_loop(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_LOOP)
    result = build_production_memory_operator_loop_run(
        loop,
        generated_at=GENERATED_AT,
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    write_production_memory_operator_loop_run(result, tmp_path, write_run_package=True, write_run_package_check=True)
    return tmp_path / "production_memory_operator_loop_run.json"


def _seed() -> dict:
    return {
        "kind": ASSET_PROFILE_SEED_KIND,
        "artifact_type": ASSET_PROFILE_SEED_KIND,
        "schema_version": "production-memory-loop/v1",
        "seed_id": "asset-profile-seed:generic-production-loop:v1",
        "project_id": "project:generic-content-loop",
        "project_material_refs": [
            {
                "ref_id": "local-material:script:v1",
                "material_kind": "script",
                "storage_policy": "local_ignored",
                "summary": "Sanitized final script placeholder for tester-supplied project materials.",
            }
        ],
        "profiles": [
            {
                "profile_id": "asset-profile:character:lead:v1",
                "profile_kind": "character",
                "display_name": "Sanitized lead character",
                "profile_scope": "project",
                "profile_version": "v1",
                "profile_status": "promoted",
                "context_eligibility": "included",
                "allowed_variations": ["pose", "expression", "camera angle"],
                "negative_constraints": ["do not add headwear", "do not change age impression"],
                "evidence_refs": ["artifact:approved_storyboard:v1", "memory:candidate:approved-style:v1"],
                "promotion_decision_refs": ["promotion:approved-style:v1"],
                "evidence_strength": "medium",
                "confidence": "tester_review_required",
            },
            {
                "profile_id": "asset-profile:scene:oasis:v1",
                "profile_kind": "scene",
                "display_name": "Sanitized oasis scene",
                "profile_scope": "project",
                "profile_version": "v1",
                "profile_status": "promoted",
                "context_eligibility": "included",
                "allowed_variations": ["lens", "foreground blocking"],
                "negative_constraints": ["do not remove the water landmark"],
                "evidence_refs": ["artifact:approved_storyboard:v1"],
                "promotion_decision_refs": ["promotion:approved-style:v1"],
                "evidence_strength": "medium",
                "confidence": "tester_review_required",
            },
        ],
        "provider_validation": {
            "image_prompt": "Sanitized character consistency keyframe prompt.",
            "video_prompt": "Sanitized scene continuity image-to-video prompt.",
        },
    }
