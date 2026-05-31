from __future__ import annotations

import json
from pathlib import Path

from agentflow.memory.loulan_package import build_loulan_memory_package
from tests.test_loulan_memory_package import _loulan_fixture, _write_json


def test_loulan_memory_package_uses_unified_asset_registry_gates(tmp_path: Path) -> None:
    root = _loulan_registry_fixture(tmp_path)

    package = build_loulan_memory_package(root, created_at="2026-06-01T09:00:00+08:00")

    assert package["project_summary"]["project_id"] == "loulan_scene_assets"
    inventory = package["asset_inventory"]
    assert inventory["source_registry_ref"] == "manifests/asset_registry.json"
    assert inventory["total_assets"] == 7
    assert inventory["type_counts"] == {
        "character": 1,
        "feedback": 1,
        "keyframe": 1,
        "prop": 1,
        "run_evidence": 1,
        "scene": 1,
        "vfx": 1,
    }
    assert inventory["status_counts"]["approved_anchor"] == 1
    assert inventory["status_counts"]["candidate"] == 4
    assert inventory["status_counts"]["route_failed"] == 2
    assert package["next_context_bundle_draft"]["eligible_memory_refs"] == [
        "asset:character_zhou_tong_school_v1"
    ]
    assert {
        "asset:keyframe_b01_s01_h1",
        "asset:prop_chitu_bag_v1_failed",
        "asset:feedback_b01_director_summary",
        "asset:run_image2_route_failure",
    } <= set(package["next_context_bundle_draft"]["blocked_memory_refs"])
    assert package["promotion_gates"]["overall_status"] == "blocked"
    assert package["promotion_gates"]["eligible_statuses"] == ["approved_anchor", "promoted_reusable"]
    assert package["promotion_gates"]["blocked_statuses"] == [
        "candidate",
        "needs_repair",
        "rejected",
        "route_failed",
        "source_reference",
        "superseded",
    ]
    assert package["next_context_bundle_draft"]["blocked_refs_by_reason"]["route_failed"] == [
        "asset:prop_chitu_bag_v1_failed",
        "asset:run_image2_route_failure",
    ]

    serialized = json.dumps(package, ensure_ascii=False)
    assert str(root) not in serialized
    assert "D:\\" not in serialized
    assert "C:\\" not in serialized
    assert ".mp4" not in serialized
    assert "signed_url" not in serialized
    assert "api_key" not in serialized


def _loulan_registry_fixture(tmp_path: Path) -> Path:
    root = _loulan_fixture(tmp_path)
    media_refs = [
        "human/zhou_tong_school_v1.png",
        "assets/images/B01-S01-h1.png",
        "assets/props/chitu_horse_crossbody_bag_v1.png",
    ]
    for ref in media_refs:
        path = root / ref
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(ref, encoding="utf-8")
    _write_json(root / "manifests" / "asset_registry.json", _registry_payload())
    return root


def _registry_payload() -> dict:
    return {
        "schema_version": "0.1.0",
        "artifact_type": "loulan_unified_asset_registry",
        "project_id": "loulan_scene_assets",
        "updated_at": "2026-06-01T09:00:00+08:00",
        "assets": [
            _registry_asset("character_zhou_tong_school_v1", "character", "Zhou Tong approved school-phase anchor", "approved_anchor", "human/zhou_tong_school_v1.png", sha256="sha-approved"),
            _registry_asset("scene_loulan_ruins_sandstorm_v0", "scene", "Loulan ruins sandstorm card", "candidate", "asset_library/scenes/loulan_ruins_sandstorm_v0.md"),
            _registry_asset("vfx_blue_time_ripple_v0", "vfx", "Blue time ripple card", "candidate", "asset_library/vfx/blue_time_ripple_v0.md"),
            _registry_asset("keyframe_b01_s01_h1", "keyframe", "B01 horizontal keyframe pending human review", "candidate", "assets/images/B01-S01-h1.png", review_refs=["reviews/B01-horizontal-pack/director_summary.md"]),
            _registry_asset("prop_chitu_bag_v1_failed", "prop", "Chitu bag failed provider route", "route_failed", "assets/props/chitu_horse_crossbody_bag_v1.png", evidence_refs=["runs/image2/failed/chitu_bag/provider_failure_note.md"]),
            _registry_asset("feedback_b01_director_summary", "feedback", "B01 director summary", "candidate", "reviews/B01-horizontal-pack/director_summary.md"),
            _registry_asset("run_image2_route_failure", "run_evidence", "Built-in image route failure", "route_failed", "runs/image2/failed/chitu_bag/provider_failure_note.md"),
        ],
    }


def _registry_asset(
    asset_id: str,
    asset_type: str,
    role: str,
    status: str,
    current_ref: str,
    *,
    sha256: str = "",
    evidence_refs: list[str] | None = None,
    review_refs: list[str] | None = None,
) -> dict:
    return {
        "asset_id": asset_id,
        "asset_type": asset_type,
        "role": role,
        "status": status,
        "current_ref": current_ref,
        "source_refs": [current_ref],
        "evidence_refs": evidence_refs or [],
        "review_refs": review_refs or [],
        "sha256": sha256,
        "promotion_state": "eligible_for_context" if status == "approved_anchor" else "blocked",
        "reuse_policy": {"allowed_for_context": status == "approved_anchor", "requires_human_review": status != "approved_anchor"},
        "claim_boundary": {
            "human_acceptance": "human_reviewed_anchor" if status == "approved_anchor" else "not_acceptance",
            "business_validation": "not_validated",
            "durable_memory": "not_written",
        },
    }
