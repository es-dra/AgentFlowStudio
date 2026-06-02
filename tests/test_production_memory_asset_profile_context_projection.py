from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

from agentflow.memory.production_asset_profile_context_projection import (
    ASSET_PROFILE_CONTEXT_PROJECTION_KIND,
    build_asset_profile_context_projection,
    write_asset_profile_context_projection,
)
from agentflow.memory.production_asset_profile_promotion import (
    build_asset_profile_promotion_review,
)
from agentflow_studio.utils import write_json
from tests.production_memory_asset_profile_promotion_helpers import (
    GENERATED_AT,
    asset_profiles_and_candidate,
)


def test_asset_profile_context_projection_includes_promoted_profile_version(tmp_path: Path) -> None:
    version = _promoted_version(tmp_path)

    projection = build_asset_profile_context_projection(
        asset_profile_versions=[version],
        generated_at="2026-06-03T00:30:00+08:00",
    )

    assert projection["kind"] == ASSET_PROFILE_CONTEXT_PROJECTION_KIND
    assert projection["projection_status"] == "ready"
    assert projection["included_refs"][0]["ref_id"] == "asset-profile:character:lead:v2"
    assert projection["included_refs"][0]["source_version_id"] == version["version_id"]
    assert projection["included_refs"][0]["version_change_summary"] == version["version_change_summary"]
    assert projection["blocked_refs"] == [
        {
            "ref_id": "asset-profile:character:lead:v1",
            "reason": "superseded_by_profile_version",
            "superseded_by": "asset-profile:character:lead:v2",
        }
    ]
    assert projection["context_payload"]["asset_profile_refs"] == projection["included_refs"]
    assert projection["provider_calls_started"] is False
    assert projection["writes_long_term_memory"] is False
    assert projection["writes_company_kb"] is False


def test_asset_profile_context_projection_blocks_unusable_profile_version(tmp_path: Path) -> None:
    version = _promoted_version(tmp_path)
    version["usable_for_next_context"] = False

    projection = build_asset_profile_context_projection(
        asset_profile_versions=[version],
        generated_at="2026-06-03T00:30:00+08:00",
    )

    assert projection["projection_status"] == "blocked"
    assert projection["included_refs"] == []
    assert _blocked_reasons(projection)["asset-profile:character:lead:v2"] == "profile_version_not_usable_for_next_context"


def test_asset_profile_context_projection_blocks_decision_only_artifact(tmp_path: Path) -> None:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)
    decision, version = build_asset_profile_promotion_review(
        asset_profiles=asset_profiles,
        update_candidate=candidate,
        decision="rejected",
        rationale="Operator rejected this profile patch for the next review round.",
        reviewer_role="operator",
        decided_at=GENERATED_AT,
    )

    assert version is None
    projection = build_asset_profile_context_projection(
        asset_profile_versions=[decision],
        generated_at="2026-06-03T00:30:00+08:00",
    )

    assert projection["included_refs"] == []
    assert _blocked_reasons(projection)[decision["decision_id"]] == "invalid_profile_version_kind"


def test_asset_profile_context_projection_blocks_stale_superseded_versions(tmp_path: Path) -> None:
    v2 = _promoted_version(tmp_path)
    v3 = deepcopy(v2)
    v3["version_id"] = "asset-profile-version:lead:v3"
    v3["source_profile_id"] = "asset-profile:character:lead:v2"
    v3["profile_id"] = "asset-profile:character:lead:v3"
    v3["profile_version"] = "v3"
    v3["profile"]["profile_id"] = "asset-profile:character:lead:v3"
    v3["profile"]["profile_version"] = "v3"
    v3["profile"]["supersedes_profile_id"] = "asset-profile:character:lead:v2"
    v3["version_change_summary"]["target_profile_id"] = "asset-profile:character:lead:v3"

    projection = build_asset_profile_context_projection(
        asset_profile_versions=[v2, v3],
        generated_at="2026-06-03T00:30:00+08:00",
    )

    included = {ref["ref_id"] for ref in projection["included_refs"]}
    blocked = _blocked_reasons(projection)
    assert included == {"asset-profile:character:lead:v3"}
    assert blocked["asset-profile:character:lead:v2"] == "superseded_by_newer_profile_version"
    assert blocked["asset-profile:character:lead:v1"] == "superseded_by_profile_version"


def test_asset_profile_context_projection_blocks_missing_decision_ref(tmp_path: Path) -> None:
    version = _promoted_version(tmp_path)
    version["profile"]["promotion_decision_refs"] = []
    version["profile"]["profile_version_decision_refs"] = []

    projection = build_asset_profile_context_projection(
        asset_profile_versions=[version],
        generated_at="2026-06-03T00:30:00+08:00",
    )

    assert projection["included_refs"] == []
    assert _blocked_reasons(projection)[version["source_decision_id"]] == "missing_profile_version_decision_ref"


def test_asset_profile_context_projection_cli_smoke(tmp_path: Path) -> None:
    version = _promoted_version(tmp_path)
    version_path = write_json(tmp_path / "asset_profile_version.json", version)
    output_dir = tmp_path / "projection"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-asset-profile-context-projection",
            "--asset-profile-version",
            str(version_path),
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Asset profile context projection: ready" in result.stdout
    assert (output_dir / "asset_profile_context_projection.json").exists()
    assert (output_dir / "asset_profile_context_projection.md").exists()
    payload = json.loads((output_dir / "asset_profile_context_projection.json").read_text(encoding="utf-8"))
    assert payload["kind"] == ASSET_PROFILE_CONTEXT_PROJECTION_KIND


def _promoted_version(tmp_path: Path) -> dict:
    asset_profiles, candidate = asset_profiles_and_candidate(tmp_path)
    _decision, version = build_asset_profile_promotion_review(
        asset_profiles=asset_profiles,
        update_candidate=candidate,
        decision="promoted",
        rationale="Operator approved the structured profile patch for tester review continuity.",
        reviewer_role="operator",
        decided_at=GENERATED_AT,
    )
    assert version is not None
    return version


def _blocked_reasons(projection: dict) -> dict[str, str]:
    return {str(item["ref_id"]): str(item["reason"]) for item in projection["blocked_refs"]}
