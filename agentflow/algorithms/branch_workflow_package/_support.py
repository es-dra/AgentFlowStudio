from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from agentflow.algorithms.interactive_manga_branch_package._helpers import required_dict, required_text

from . import REFERENCE_POLICY


def repo_root_for_fixture(path: str | Path) -> Path:
    fixture_path = Path(path)
    if not fixture_path.is_absolute():
        return Path.cwd()
    parents = list(fixture_path.parents)
    if len(parents) >= 4 and parents[2].name == "tests":
        return parents[3]
    return Path.cwd()


def known_refs(source_payload: dict[str, Any], package: dict[str, Any]) -> set[str]:
    refs = {str(ref) for ref in source_payload.get("external_refs") or []}
    source_package = required_dict(source_payload, "branch_package")
    refs.add(required_text(source_package, "package_ref"))
    refs.add(required_text(package, "package_ref"))
    for field in ("project_id", "source_script_ref", "source_storyboard_ref"):
        refs.add(required_text(package, field))
    for field, ref_field in (
        ("choice_points", "choice_point_ref"),
        ("branch_paths", "branch_path_ref"),
        ("branch_shots", "branch_shot_ref"),
        ("asset_needs", "asset_need_ref"),
        ("continuity_constraints", "constraint_ref"),
        ("evidence_requirements", "evidence_requirement_ref"),
        ("production_graph_references", "production_graph_ref"),
    ):
        for item in package.get(field) or []:
            refs.add(required_text(item, ref_field))
    for item in package.get("branch_shots") or []:
        refs.add(required_text(item, "branch_specific_shot_ref"))
    for item in package.get("asset_needs") or []:
        if item.get("source_asset_ref"):
            refs.add(str(item["source_asset_ref"]))
    refs.add(required_text(required_dict(package, "handoff"), "handoff_ref"))
    confirmation = package.get("fixed_asset_confirmation_evidence")
    if isinstance(confirmation, dict):
        refs.update(str(ref) for ref in confirmation.get("local_confirmation_evidence_refs") or [])
        for item in confirmation.get("asset_confirmation_records") or []:
            if not isinstance(item, dict):
                continue
            for field in ("confirmation_ref", "source_asset_ref", "owner_decision_ref", "reviewer_decision_ref", "close_condition_ref"):
                if item.get(field):
                    refs.add(str(item[field]))
        for item in confirmation.get("residual_question_closures") or []:
            if not isinstance(item, dict):
                continue
            for field in ("closure_ref", "owner_decision_ref", "reviewer_decision_ref", "close_condition_ref"):
                if item.get(field):
                    refs.add(str(item[field]))
    return refs


def validation_report(
    payload: dict[str, Any],
    package: dict[str, Any],
    source_report: dict[str, Any],
    choices: dict[str, dict[str, Any]],
    paths: dict[str, dict[str, Any]],
    shots: dict[str, dict[str, Any]],
    assets: dict[str, dict[str, Any]],
    constraints: dict[str, dict[str, Any]],
    graph_artifacts: set[str],
    readiness: dict[str, Any],
    review_status: dict[str, Any],
    fixed_asset_confirmation_evidence: dict[str, Any],
    generation_planning_candidate: dict[str, Any],
    accepted_generation_plan_packet: dict[str, Any],
) -> dict[str, Any]:
    asset_scope_counts = Counter(str(item["scope"]) for item in assets.values())
    confirmation_counts = Counter(str(item["confirmation_state"]) for item in assets.values())
    return {
        "fixture_id": required_text(payload, "fixture_id"),
        "fixture_claim_level": required_text(payload, "fixture_claim_level"),
        "package_id": required_text(package, "package_id"),
        "package_stage": required_text(package, "package_stage"),
        "source_fixture": {
            "fixture_id": source_report["fixture_id"],
            "package_ref": source_report["package_ref"],
        },
        "summary": {
            "choice_point_count": len(choices),
            "branch_path_count": len(paths),
            "branch_shot_count": len(shots),
            "asset_need_count": len(assets),
            "continuity_constraint_count": len(constraints),
            "evidence_requirement_count": len(package["evidence_requirements"]),
            "handoff_count": 1,
        },
        "asset_need_scopes": dict(sorted(asset_scope_counts.items())),
        "confirmation_state_counts": dict(sorted(confirmation_counts.items())),
        "production_graph_boundary": {
            "reference_policy": REFERENCE_POLICY,
            "graph_node_writes_required": False,
            "graph_artifact_refs": sorted(graph_artifacts),
        },
        "review_status": {
            "review_state": review_status["review_state"],
            "blockers": review_status["blockers"],
            "open_question_count": len(review_status["open_questions"]),
            "open_question_refs": review_status["open_question_refs"],
            "unresolved_open_question_refs": review_status["unresolved_open_question_refs"],
        },
        "residual_boundary": review_status["residual_boundary"],
        "readiness": readiness,
        "fixed_asset_confirmation_evidence": fixed_asset_confirmation_evidence,
        "generation_planning_candidate": generation_planning_candidate,
        "accepted_generation_plan_packet": accepted_generation_plan_packet,
        "source_boundary_refs": list(payload.get("source_boundary_refs") or []),
        "residual_boundaries": list(payload.get("residual_boundaries") or []),
        "non_claims": dict(payload["non_claims"]),
    }
