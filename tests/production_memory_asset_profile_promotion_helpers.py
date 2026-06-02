from __future__ import annotations

import json
from pathlib import Path

from agentflow.memory.production_asset_feedback import build_asset_feedback_event
from agentflow.memory.production_asset_profile_update_candidate import build_asset_profile_update_candidate
from agentflow.memory.production_asset_profiles import (
    build_asset_profile_test_package,
    load_asset_profile_seed,
    write_asset_profile_test_package,
)
from agentflow.memory.production_loop import load_production_memory_loop
from agentflow.memory.production_operator_loop import (
    build_production_memory_operator_loop_run,
    write_production_memory_operator_loop_run,
)

EXAMPLE_LOOP = Path("examples/agentflow/production_memory_loop.example.json")
EXAMPLE_SEED = Path("examples/agentflow/production_memory_asset_profile_seed.example.json")
EXAMPLE_FEEDBACK = Path("examples/agentflow/production_memory_asset_feedback.example.json")
GENERATED_AT = "2026-06-02T00:20:00+08:00"


def asset_profiles_and_candidate(tmp_path: Path) -> tuple[dict, dict]:
    package_dir = write_asset_package(tmp_path)
    asset_profiles = json.loads((package_dir / "asset_profiles.json").read_text(encoding="utf-8"))
    event = build_asset_feedback_event(
        asset_profiles=asset_profiles,
        asset_profile_readiness=json.loads((package_dir / "asset_profile_readiness.json").read_text(encoding="utf-8")),
        feedback_fixture=json.loads(EXAMPLE_FEEDBACK.read_text(encoding="utf-8")),
        generated_at="2026-06-02T00:00:00+08:00",
    )
    candidate = build_asset_profile_update_candidate(event, generated_at="2026-06-02T00:10:00+08:00")
    return asset_profiles, candidate


def write_asset_package(tmp_path: Path) -> Path:
    loop = load_production_memory_loop(EXAMPLE_LOOP)
    operator_result = build_production_memory_operator_loop_run(
        loop,
        generated_at="2026-06-02T00:00:00+08:00",
        source_kb_status="restructuring_or_unknown",
        draft_next_pass_result=True,
    )
    operator_dir = tmp_path / "operator_loop"
    write_production_memory_operator_loop_run(
        result=operator_result,
        output_dir=operator_dir,
        write_run_package=True,
        write_run_package_check=True,
    )
    bundle = build_asset_profile_test_package(
        operator_artifact_path=operator_dir / "production_memory_operator_loop_run.json",
        asset_profile_seed=load_asset_profile_seed(EXAMPLE_SEED),
        generated_at="2026-06-02T00:00:00+08:00",
    )
    package_dir = tmp_path / "asset_test_package"
    write_asset_profile_test_package(bundle, package_dir)
    return package_dir


def profile_by_id(asset_profiles: dict, profile_id: str) -> dict:
    for profile in asset_profiles["profiles"]:
        if profile["profile_id"] == profile_id:
            return profile
    raise AssertionError(f"profile missing: {profile_id}")


__all__ = (
    "GENERATED_AT",
    "asset_profiles_and_candidate",
    "profile_by_id",
)
