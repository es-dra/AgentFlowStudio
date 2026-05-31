from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app
from agentflow.memory.loulan_b01_decision_import import (
    build_loulan_b01_decision_import,
    write_loulan_b01_decision_import,
)
from agentflow.memory.loulan_decision_intake import build_loulan_decision_intake_report
from agentflow.memory.loulan_decision_review_pack import build_loulan_decision_review_pack
from agentflow.memory.loulan_decision_worksheet import build_loulan_decision_worksheet
from tests.test_loulan_decision_template import _review_pack


def test_loulan_b01_decision_import_overlays_local_shot_decisions(tmp_path: Path) -> None:
    review_pack = _review_pack(tmp_path)
    local_decisions = _local_b01_decisions()

    imported = build_loulan_b01_decision_import(
        review_pack,
        local_decisions,
        created_at="2026-06-01T20:00:00+08:00",
    )

    assert imported["artifact_type"] == "agentflow_loulan_promotion_decisions"
    assert imported["template_status"] == "partially_imported_pending_human_input"
    assert imported["provider_calls_started"] is False
    assert imported["writes_long_term_memory"] is False
    assert imported["human_acceptance_recorded"] is False
    assert imported["source_decision_artifact_type"] == "loulan_b01_human_review_decision_template"
    assert imported["source_block_id"] == "B01"
    assert imported["import_summary"] == {
        "required_decisions": 3,
        "imported_ready_decisions": 2,
        "pending_decisions": 1,
        "skipped_local_items": 0,
    }
    by_ref = {item["target_ref"]: item for item in imported["decisions"]}
    assert by_ref["shot:B01-S01"]["decision"] == "approve_anchor"
    assert by_ref["shot:B01-S01"]["decided_by"] == "human"
    assert by_ref["shot:B01-S01"]["evidence_refs"] == [
        "assets/images/B01-S01-h1.png",
        "asset:keyframe_b01_s01_h1",
    ]
    assert by_ref["shot:B01-S02"]["decision"] == "request_repair"
    assert by_ref["shot:B01-S02"]["review_note"] == "Move Yiqi closer to the blue time ripple."
    assert by_ref["character:guan_pingping_v2"]["decision"] == "pending_human_review"


def test_loulan_b01_decision_import_keeps_pending_local_items_pending(tmp_path: Path) -> None:
    local_decisions = _local_b01_decisions()
    local_decisions["decision_items"][0]["decision"] = "pending_human_review"
    local_decisions["decision_items"][1]["decision"] = ""
    local_decisions["decision_items"][1]["repair_note"] = ""

    imported = build_loulan_b01_decision_import(
        _review_pack(tmp_path),
        local_decisions,
        created_at="2026-06-01T20:00:00+08:00",
    )

    by_ref = {item["target_ref"]: item for item in imported["decisions"]}
    assert imported["template_status"] == "partially_imported_pending_human_input"
    assert imported["import_summary"] == {
        "required_decisions": 3,
        "imported_ready_decisions": 0,
        "pending_decisions": 3,
        "skipped_local_items": 0,
    }
    assert by_ref["shot:B01-S01"]["decision"] == "pending_human_review"
    assert by_ref["shot:B01-S02"]["decision"] == "pending_human_review"


def test_loulan_b01_decision_import_flows_into_decision_intake(tmp_path: Path) -> None:
    review_pack = _review_pack(tmp_path)
    imported = build_loulan_b01_decision_import(
        review_pack,
        _local_b01_decisions(),
        created_at="2026-06-01T20:00:00+08:00",
    )
    decision_review = build_loulan_decision_review_pack(
        review_pack,
        imported,
        created_at="2026-06-01T20:10:00+08:00",
    )
    worksheet = build_loulan_decision_worksheet(
        decision_review,
        created_at="2026-06-01T20:20:00+08:00",
    )

    report = build_loulan_decision_intake_report(
        worksheet,
        imported,
        created_at="2026-06-01T20:30:00+08:00",
    )

    assert report["intake_status"] == "blocked_pending_manual_decisions"
    assert report["intake_summary"]["ready_count"] == 2
    assert report["intake_summary"]["pending_count"] == 1
    assert report["intake_summary"]["missing_count"] == 0


def test_loulan_b01_decision_import_cli_writes_artifacts(tmp_path: Path) -> None:
    review_pack = _review_pack(tmp_path)
    review_path = tmp_path / "review_pack.json"
    local_path = tmp_path / "b01_decisions.json"
    review_path.write_text(json.dumps(review_pack, ensure_ascii=False, indent=2), encoding="utf-8")
    local_path.write_text(json.dumps(_local_b01_decisions(), ensure_ascii=False, indent=2), encoding="utf-8")
    output = tmp_path / "b01_import"

    result = CliRunner().invoke(
        app,
        [
            "loulan-b01-decision-import",
            "--review-pack",
            str(review_path),
            "--b01-decisions",
            str(local_path),
            "--created-at",
            "2026-06-01T20:00:00+08:00",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Loulan B01 decision import" in result.output
    assert "Imported ready decisions: 2" in result.output
    assert "Human acceptance: not recorded" in result.output
    assert (output / "loulan_b01_decisions.imported.json").is_file()
    assert (output / "loulan_b01_decisions.imported.md").is_file()


def test_loulan_b01_decision_import_write_returns_artifacts(tmp_path: Path) -> None:
    imported = build_loulan_b01_decision_import(
        _review_pack(tmp_path),
        _local_b01_decisions(),
        created_at="2026-06-01T20:00:00+08:00",
    )

    paths = write_loulan_b01_decision_import(imported, tmp_path / "out")

    assert {path.name for path in paths} == {
        "loulan_b01_decisions.imported.json",
        "loulan_b01_decisions.imported.md",
    }


def _local_b01_decisions() -> dict:
    return {
        "schema_version": "0.1.0",
        "artifact_type": "loulan_b01_human_review_decision_template",
        "project_id": "loulan_scene_assets",
        "block_id": "B01",
        "status": "partially_filled_human_review",
        "provider_calls_started": False,
        "writes_long_term_memory": False,
        "human_acceptance_recorded": False,
        "decision_items": [
            {
                "decision_id": "decision_b01_s01",
                "target_shot_id": "B01-S01",
                "candidate_ref": "assets/images/B01-S01-h1.png",
                "registry_memory_ref": "asset:keyframe_b01_s01_h1",
                "decision": "approve_anchor",
                "repair_note": "",
            },
            {
                "decision_id": "decision_b01_s02",
                "target_shot_id": "B01-S02",
                "candidate_ref": "assets/images/B01-S02-h1.png",
                "registry_memory_ref": "asset:keyframe_b01_s02_h1",
                "decision": "request_repair",
                "repair_note": "Move Yiqi closer to the blue time ripple.",
            },
        ],
    }
