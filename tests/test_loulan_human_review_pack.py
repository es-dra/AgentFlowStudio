from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from agentflow.memory.loulan_api_workbench import build_loulan_api_workbench_plan
from agentflow.memory.loulan_human_review_pack import (
    build_loulan_human_review_pack,
    write_loulan_human_review_pack,
)
from agentflow.memory.loulan_package import build_loulan_memory_package
from tests.test_loulan_memory_package import _loulan_fixture


def test_loulan_human_review_pack_prepares_pending_b01_decisions(tmp_path: Path) -> None:
    root = _loulan_review_fixture(tmp_path)
    package = build_loulan_memory_package(root, created_at="2026-06-01T09:00:00+08:00")
    api_plan = build_loulan_api_workbench_plan(package, created_at="2026-06-01T10:00:00+08:00")

    pack = build_loulan_human_review_pack(
        package,
        api_plan,
        project_root=root,
        block_id="B01",
        created_at="2026-06-01T11:00:00+08:00",
    )

    assert pack["artifact_type"] == "agentflow_loulan_human_review_pack"
    assert pack["provider_calls_started"] is False
    assert pack["writes_long_term_memory"] is False
    assert pack["human_acceptance_recorded"] is False
    assert pack["review_scope"]["block_id"] == "B01"
    assert pack["review_scope"]["status"] == "pending_human_review"
    assert [card["candidate_id"] for card in pack["shot_review_cards"]] == ["B01-S01-h1", "B01-S02-h1"]
    assert pack["shot_review_cards"][0]["image_sha256"] == "sha-b01-s01-h1"
    assert pack["shot_review_cards"][1]["evidence_status"] == "blocked"
    assert pack["shot_review_cards"][1]["rejected_evidence_refs"] == [
        "assets/images/B01-S02-h1-rejected-character-turnaround.png"
    ]
    assert pack["asset_review"]["candidate_memory_refs"] == ["character:guan_pingping_v2"]
    assert pack["asset_review"]["approved_or_promoted_memory_refs"] == ["character:zhou_tong_school_v1"]
    assert pack["promotion_decision_drafts"][0]["draft_status"] == "pending_human_review"
    assert pack["promotion_decision_drafts"][0]["writes_long_term_memory"] is False
    assert pack["feedback_event_draft"]["decision"] == "note"
    assert pack["next_pass_readiness"]["status"] == "blocked_until_human_review"

    serialized = json.dumps(pack, ensure_ascii=False)
    for forbidden in ["D:\\", "C:\\", "file://", ".mp4", ".mov", "api_key", "secret_key", "Bearer ", "signed_url"]:
        assert forbidden not in serialized


def test_loulan_human_review_pack_blocks_missing_image_hash(tmp_path: Path) -> None:
    root = _loulan_review_fixture(tmp_path)
    image_qa = json.loads((root / "reviews" / "B01-horizontal-pack" / "image_qa.json").read_text(encoding="utf-8"))
    image_qa["shots"][0].pop("sha256")
    _write_json(root / "reviews" / "B01-horizontal-pack" / "image_qa.json", image_qa)
    package = build_loulan_memory_package(root, created_at="2026-06-01T09:00:00+08:00")
    api_plan = build_loulan_api_workbench_plan(package, created_at="2026-06-01T10:00:00+08:00")

    pack = build_loulan_human_review_pack(
        package,
        api_plan,
        project_root=root,
        block_id="B01",
        created_at="2026-06-01T11:00:00+08:00",
    )

    assert pack["shot_review_cards"][0]["evidence_status"] == "blocked"
    assert "missing_image_sha256" in pack["shot_review_cards"][0]["blocking_reasons"]
    assert "shot:B01-S01" in pack["next_pass_readiness"]["blocked_refs"]


def test_loulan_human_review_pack_cli_writes_review_artifacts(tmp_path: Path) -> None:
    root = _loulan_review_fixture(tmp_path)
    package = build_loulan_memory_package(root, created_at="2026-06-01T09:00:00+08:00")
    api_plan = build_loulan_api_workbench_plan(package, created_at="2026-06-01T10:00:00+08:00")
    package_path = tmp_path / "loulan_memory_package.json"
    api_plan_path = tmp_path / "loulan_api_workbench_plan.json"
    package_path.write_text(json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8")
    api_plan_path.write_text(json.dumps(api_plan, ensure_ascii=False, indent=2), encoding="utf-8")
    output = tmp_path / "human_review"

    result = CliRunner().invoke(
        app,
        [
            "loulan-human-review-pack",
            "--package",
            str(package_path),
            "--api-plan",
            str(api_plan_path),
            "--project-root",
            str(root),
            "--block-id",
            "B01",
            "--created-at",
            "2026-06-01T11:00:00+08:00",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Loulan human review pack" in result.output
    assert "Human acceptance: not recorded" in result.output
    for name in [
        "loulan_human_review_pack.json",
        "shot_review_cards.json",
        "promotion_decision_drafts.json",
        "feedback_event_draft.json",
        "loulan_human_review_pack.md",
    ]:
        assert (output / name).is_file()


def test_loulan_human_review_pack_contract_example_is_registered() -> None:
    payload = json.loads(Path("examples/agentflow/loulan_human_review_pack.example.json").read_text(encoding="utf-8"))
    registry = json.loads(Path("examples/agentflow/contract_registry.example.json").read_text(encoding="utf-8"))

    assert payload["artifact_type"] == "agentflow_loulan_human_review_pack"
    assert payload["human_acceptance_recorded"] is False
    assert payload["writes_long_term_memory"] is False
    assert payload["next_pass_readiness"]["status"] == "blocked_until_human_review"
    assert "agentflow_loulan_human_review_pack" in {contract["artifact_type"] for contract in registry["contracts"]}
    assert "loulan_human_review_pack_no_acceptance" in {rule["rule_id"] for rule in registry["validation_rules"]}


def _loulan_review_fixture(tmp_path: Path) -> Path:
    root = _loulan_fixture(tmp_path)
    _write_json(
        root / "manifests" / "shot_list.json",
        {
            "shots": [
                {
                    "shot_id": "B01-S01",
                    "generation_block": 1,
                    "scene": "Loulan ruins",
                    "quality_status": "horizontal_keyframe_candidate_pending_review",
                    "versioned_image_path": "assets/images/B01-S01-h1.png",
                    "feedback_asset": "asset_library/director_notes/B01-S01_h1_feedback.md",
                    "motion_intent": "asset_library/motion_intent/B01-S01_h1_motion_intent.md",
                },
                {
                    "shot_id": "B01-S02",
                    "generation_block": 1,
                    "scene": "Loulan ruins",
                    "quality_status": "horizontal_keyframe_candidate_pending_review",
                    "versioned_image_path": "assets/images/B01-S02-h1.png",
                    "director_art_card": "reviews/B01-S02-h1/director_art_card.md",
                    "feedback_asset": "asset_library/director_notes/B01-S02_h1_feedback.md",
                    "motion_intent": "asset_library/motion_intent/B01-S02_h1_motion_intent.md",
                    "rejected_previous_asset": "assets/images/B01-S02-h1-rejected-character-turnaround.png",
                },
                {"shot_id": "B02-S01", "generation_block": 2, "quality_status": "planned"},
            ]
        },
    )
    (root / "reviews" / "B01-horizontal-pack").mkdir(parents=True, exist_ok=True)
    (root / "reviews" / "B01-horizontal-pack" / "director_summary.md").write_text(
        "Status: B01 has horizontal keyframe candidates pending human review.", encoding="utf-8"
    )
    _write_json(
        root / "reviews" / "B01-horizontal-pack" / "image_qa.json",
        {
            "shots": [
                {
                    "shot": "B01-S01-h1",
                    "path": str(root / "assets" / "images" / "B01-S01-h1.png"),
                    "size": "1920x1080",
                    "sha256": "sha-b01-s01-h1",
                },
                {
                    "shot": "B01-S02-h1",
                    "path": str(root / "assets" / "images" / "B01-S02-h1.png"),
                    "size": "1920x1080",
                    "sha256": "sha-b01-s02-h1",
                },
            ]
        },
    )
    (root / "asset_library" / "motion_intent").mkdir(parents=True, exist_ok=True)
    (root / "reviews" / "B01-S02-h1").mkdir(parents=True, exist_ok=True)
    (root / "reviews" / "B01-S02-h1" / "director_art_card.md").write_text("review", encoding="utf-8")
    (root / "asset_library" / "director_notes" / "B01-S01_h1_feedback.md").write_text("feedback", encoding="utf-8")
    (root / "asset_library" / "director_notes" / "B01-S02_h1_feedback.md").write_text("feedback", encoding="utf-8")
    return root


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
