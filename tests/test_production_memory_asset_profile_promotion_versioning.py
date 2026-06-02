from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from agentflow.memory.production_asset_profile_promotion import (
    ASSET_PROFILE_PROMOTION_DECISION_KIND,
    ASSET_PROFILE_VERSION_KIND,
    build_asset_profile_promotion_review,
    write_asset_profile_promotion_review,
)
from narratocut.utils import write_json
from tests.production_memory_asset_profile_promotion_helpers import (
    GENERATED_AT,
    asset_profiles_and_candidate,
    profile_by_id,
)


def test_asset_profile_promotion_decision_applies_v2_profile_without_memory_write(tmp_path: Path) -> None:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)
    before_profiles = deepcopy(asset_profiles)
    before_candidate = deepcopy(candidate)

    decision, version = build_asset_profile_promotion_review(
        asset_profiles=asset_profiles,
        update_candidate=candidate,
        decision="promoted",
        rationale="Operator approved the structured profile patch for tester review continuity.",
        reviewer_role="operator",
        decided_at=GENERATED_AT,
    )

    assert asset_profiles == before_profiles
    assert candidate == before_candidate
    assert decision["kind"] == ASSET_PROFILE_PROMOTION_DECISION_KIND
    assert decision["decision"] == "promoted"
    assert decision["candidate_id"] == candidate["candidate_id"]
    assert decision["profile_version_allowed"] is True
    assert decision["creates_profile_version"] is True
    assert decision["writes_long_term_memory"] is False
    assert decision["writes_company_kb"] is False
    assert decision["decision_is_durable_memory_write"] is False
    assert version is not None
    assert version["kind"] == ASSET_PROFILE_VERSION_KIND
    assert version["source_profile_id"] == "asset-profile:character:lead:v1"
    assert version["profile_id"] == "asset-profile:character:lead:v2"
    assert version["profile_version"] == "v2"
    assert version["source_decision_id"] == decision["decision_id"]
    assert version["profile_version_applied"] is True
    assert version["writes_long_term_memory"] is False
    assert version["writes_company_kb"] is False
    profile = version["profile"]
    assert profile["kind"] == "agentflow_production_memory_asset_profile"
    assert profile["profile_id"] == "asset-profile:character:lead:v2"
    assert profile["profile_version"] == "v2"
    assert profile["supersedes_profile_id"] == "asset-profile:character:lead:v1"
    assert "do not change age impression" in profile["negative_constraints"]
    assert candidate["source_feedback_event_id"] in profile["evidence_refs"]
    assert decision["decision_id"] in profile["promotion_decision_refs"]
    assert profile["writes_long_term_memory"] is False
    assert profile["writes_company_kb"] is False


def test_rejected_asset_profile_update_candidate_records_decision_without_version(tmp_path: Path) -> None:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)

    decision, version = build_asset_profile_promotion_review(
        asset_profiles=asset_profiles,
        update_candidate=candidate,
        decision="rejected",
        rationale="Operator rejected this profile patch for the next review round.",
        reviewer_role="operator",
        decided_at=GENERATED_AT,
    )

    assert decision["decision"] == "rejected"
    assert decision["profile_version_allowed"] is False
    assert decision["creates_profile_version"] is False
    assert decision["next_context_eligibility"] == "blocked_by_explicit_operator_decision"
    assert decision["writes_long_term_memory"] is False
    assert version is None

def test_blocked_asset_profile_update_candidate_cannot_be_promoted(tmp_path: Path) -> None:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)
    candidate["candidate_generation_status"] = "blocked_missing_patch_ops"
    candidate["proposed_profile_patch"]["patch_ops"] = []

    with pytest.raises(ValueError, match="candidate_only"):
        build_asset_profile_promotion_review(
            asset_profiles=asset_profiles,
            update_candidate=candidate,
            decision="promoted",
            rationale="Should not promote a blocked candidate.",
            reviewer_role="operator",
            decided_at=GENERATED_AT,
        )

def test_unknown_asset_profile_ref_fails_promotion_review(tmp_path: Path) -> None:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)
    candidate["profile_id"] = "asset-profile:missing:v1"

    with pytest.raises(ValueError, match="profile_id does not exist"):
        build_asset_profile_promotion_review(
            asset_profiles=asset_profiles,
            update_candidate=candidate,
            decision="promoted",
            rationale="Missing profile must fail.",
            reviewer_role="operator",
            decided_at=GENERATED_AT,
        )

def test_polluted_source_profile_write_flags_fail_promotion_review(tmp_path: Path) -> None:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)
    profile = profile_by_id(asset_profiles, "asset-profile:character:lead:v1")
    profile["writes_long_term_memory"] = True

    with pytest.raises(ValueError, match="writes_long_term_memory false"):
        build_asset_profile_promotion_review(
            asset_profiles=asset_profiles,
            update_candidate=candidate,
            decision="promoted",
            rationale="Polluted source profile must fail before versioning.",
            reviewer_role="operator",
            decided_at=GENERATED_AT,
        )


def test_unsupported_patch_op_fails_before_versioning(tmp_path: Path) -> None:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)
    candidate["proposed_profile_patch"]["patch_ops"].append(
        {
            "op": "replace",
            "path": "/display_name",
            "value": "Unsafe replacement",
            "rationale": "Unsupported operation.",
            "evidence_refs": [candidate["source_feedback_event_id"]],
        }
    )

    with pytest.raises(ValueError, match="unsupported asset profile patch op"):
        build_asset_profile_promotion_review(
            asset_profiles=asset_profiles,
            update_candidate=candidate,
            decision="promoted",
            rationale="Unsupported patch operation must fail.",
            reviewer_role="operator",
            decided_at=GENERATED_AT,
        )


def test_add_unique_patch_does_not_duplicate_existing_profile_values(tmp_path: Path) -> None:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)
    profile = profile_by_id(asset_profiles, "asset-profile:character:lead:v1")
    profile["negative_constraints"].append("do not change age impression")

    _decision, version = build_asset_profile_promotion_review(
        asset_profiles=asset_profiles,
        update_candidate=candidate,
        decision="promoted",
        rationale="Approve without duplicating existing constraint values.",
        reviewer_role="operator",
        decided_at=GENERATED_AT,
    )

    assert version is not None
    assert version["profile"]["negative_constraints"].count("do not change age impression") == 1


def test_asset_profile_promotion_cli_writes_decision_and_version(tmp_path: Path) -> None:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)
    profiles_path = write_json(tmp_path / "asset_profiles.json", asset_profiles)
    candidate_path = write_json(tmp_path / "asset_profile_update_candidate.json", candidate)
    output_dir = tmp_path / "promotion"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-review-asset-profile-update-candidate",
            "--asset-profiles",
            str(profiles_path),
            "--asset-profile-update-candidate",
            str(candidate_path),
            "--decision",
            "promoted",
            "--rationale",
            "Operator approved the structured profile patch for tester review continuity.",
            "--decided-at",
            GENERATED_AT,
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Asset profile promotion decision: promoted" in result.stdout
    assert "Profile version: applied" in result.stdout
    assert (output_dir / "asset_profile_promotion_decision.json").exists()
    assert (output_dir / "asset_profile_version.json").exists()
    decision = json.loads((output_dir / "asset_profile_promotion_decision.json").read_text(encoding="utf-8"))
    version = json.loads((output_dir / "asset_profile_version.json").read_text(encoding="utf-8"))
    assert decision["kind"] == ASSET_PROFILE_PROMOTION_DECISION_KIND
    assert version["kind"] == ASSET_PROFILE_VERSION_KIND


def test_asset_profile_promotion_cli_requires_explicit_decision(tmp_path: Path) -> None:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)
    profiles_path = write_json(tmp_path / "asset_profiles.json", asset_profiles)
    candidate_path = write_json(tmp_path / "asset_profile_update_candidate.json", candidate)
    output_dir = tmp_path / "promotion"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-review-asset-profile-update-candidate",
            "--asset-profiles",
            str(profiles_path),
            "--asset-profile-update-candidate",
            str(candidate_path),
            "--rationale",
            "Decision flag omitted on purpose.",
            "--decided-at",
            GENERATED_AT,
            "--output",
            str(output_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert not (output_dir / "asset_profile_version.json").exists()


def test_asset_profile_promotion_writer_keeps_rejected_output_safe(tmp_path: Path) -> None:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)
    decision, version = build_asset_profile_promotion_review(
        asset_profiles=asset_profiles,
        update_candidate=candidate,
        decision="rejected",
        rationale="Operator rejected this profile patch for the next review round.",
        reviewer_role="operator",
        decided_at=GENERATED_AT,
    )

    written = write_asset_profile_promotion_review(decision, version, tmp_path / "promotion")
    serialized = "\n".join(path.read_text(encoding="utf-8") for path in written)

    assert "D:\\private" not in serialized
    assert "api_key" not in serialized.lower()
    assert "signed_url" not in serialized.lower()
    assert "Writes Company KB: false" in serialized


def test_rejected_review_removes_stale_profile_version_outputs(tmp_path: Path) -> None:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)
    output_dir = tmp_path / "promotion"
    promoted_decision, promoted_version = build_asset_profile_promotion_review(
        asset_profiles=asset_profiles,
        update_candidate=candidate,
        decision="promoted",
        rationale="Operator approved the structured profile patch.",
        reviewer_role="operator",
        decided_at=GENERATED_AT,
    )
    write_asset_profile_promotion_review(promoted_decision, promoted_version, output_dir)
    assert (output_dir / "asset_profile_version.json").exists()
    assert (output_dir / "asset_profile_version.md").exists()

    rejected_decision, rejected_version = build_asset_profile_promotion_review(
        asset_profiles=asset_profiles,
        update_candidate=candidate,
        decision="rejected",
        rationale="Operator rejected this profile patch on re-review.",
        reviewer_role="operator",
        decided_at="2026-06-02T00:30:00+08:00",
    )
    write_asset_profile_promotion_review(rejected_decision, rejected_version, output_dir)

    assert not (output_dir / "asset_profile_version.json").exists()
    assert not (output_dir / "asset_profile_version.md").exists()
