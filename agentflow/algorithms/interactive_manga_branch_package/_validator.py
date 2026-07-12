from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from . import (
    BRANCH_ASSET_SCOPES,
    PROTECTED_NON_CLAIMS,
    REFERENCE_POLICY,
    REQUIRED_EVIDENCE_MAPPING_FIELDS,
    SHARED_ASSET_SCOPES,
    UNSAFE_MARKERS,
)
from ._helpers import (
    dict_items,
    reject_unsafe_markers,
    require_resolved_ref,
    require_resolved_refs,
    required_dict,
    required_list,
    required_text,
    validate_non_claims,
)


def load_json_fixture(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("branch package fixture must be a JSON object")
    return payload


def load_branch_package_fixture(path: str | Path) -> dict[str, Any]:
    return validate_branch_package_fixture(load_json_fixture(path))


def validate_branch_package_fixture(payload: dict[str, Any]) -> dict[str, Any]:
    reject_unsafe_markers(payload, UNSAFE_MARKERS)
    validate_non_claims(payload.get("non_claims"), owner="fixture", require_all=True, protected_non_claims=PROTECTED_NON_CLAIMS)
    package = required_dict(payload, "branch_package")
    refs = _known_refs(payload, package)
    graph_artifacts = _validate_graph_references(package, refs)
    choice_points = required_list(package, "choice_points")
    branch_paths = required_list(package, "branch_paths")
    branch_shots = required_list(package, "branch_shots")
    asset_needs = required_list(package, "asset_needs")
    constraints = required_list(package, "continuity_constraints")
    requirements = required_list(package, "evidence_requirements")

    if len(choice_points) != 1:
        raise ValueError("branch package fixture must contain one choice point")
    if len(branch_paths) != 2:
        raise ValueError("branch package fixture must contain two branch paths")

    _validate_package_refs(package, refs)
    asset_by_ref = _validate_asset_needs(asset_needs, refs)
    constraint_by_ref = _validate_continuity_constraints(constraints, refs)
    paths_by_ref = _validate_choice_and_paths(choice_points[0], branch_paths, refs, asset_by_ref, constraint_by_ref)
    shot_mappings = _validate_branch_shots(branch_shots, refs, paths_by_ref)
    _validate_evidence_requirements(requirements, refs, graph_artifacts)
    _validate_handoff(required_dict(package, "handoff"), refs)
    return _report(payload, package, branch_paths, branch_shots, asset_needs, constraints, requirements, shot_mappings, graph_artifacts)


def _known_refs(payload: dict[str, Any], package: dict[str, Any]) -> set[str]:
    refs = {str(ref) for ref in payload.get("external_refs") or []}
    refs.add(required_text(package, "package_ref"))
    for field, ref_field in (
        ("choice_points", "choice_point_ref"),
        ("branch_paths", "branch_path_ref"),
        ("asset_needs", "asset_need_ref"),
        ("continuity_constraints", "constraint_ref"),
        ("evidence_requirements", "evidence_requirement_ref"),
        ("production_graph_references", "production_graph_ref"),
    ):
        for item in package.get(field) or []:
            refs.add(required_text(item, ref_field))
    for item in package.get("branch_shots") or []:
        refs.add(required_text(item, "branch_shot_ref"))
        refs.add(required_text(item, "branch_specific_shot_ref"))
    refs.add(required_text(required_dict(package, "handoff"), "handoff_ref"))
    return refs


def _validate_package_refs(package: dict[str, Any], refs: set[str]) -> None:
    for field in ("project_ref", "source_script_ref", "source_storyboard_ref", "production_graph_ref"):
        require_resolved_ref(required_text(package, field), refs, owner=package["package_ref"], field=field)
    require_resolved_refs(package.get("source_refs") or [], refs, owner=package["package_ref"], field="source_refs")


def _validate_graph_references(package: dict[str, Any], refs: set[str]) -> set[str]:
    artifacts: set[str] = set()
    for item in required_list(package, "production_graph_references"):
        graph_ref = required_text(item, "production_graph_ref")
        if item.get("extension_policy") != REFERENCE_POLICY:
            raise ValueError(f"production graph reference must be reference-only: {graph_ref}")
        if item.get("graph_node_writes_required") is not False:
            raise ValueError(f"graph node write claim is not allowed: {graph_ref}")
        if item.get("branch_graph_node_refs"):
            raise ValueError(f"branch graph node refs require a future evaluator gate: {graph_ref}")
        require_resolved_refs(item.get("node_refs") or [], refs, owner=graph_ref, field="node_refs")
        artifacts.add(required_text(item, "artifact_id"))
    return artifacts


def _validate_asset_needs(items: list[Any], refs: set[str]) -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    for item in dict_items(items, "asset need"):
        ref = required_text(item, "asset_need_ref")
        scope = required_text(item, "scope")
        if ref in assets:
            raise ValueError(f"duplicate asset need: {ref}")
        if scope not in SHARED_ASSET_SCOPES | BRANCH_ASSET_SCOPES:
            raise ValueError(f"unknown asset need scope: {ref}")
        if item.get("provider_enrichment_gate") != "closed_future_gate_required":
            raise ValueError(f"asset provider enrichment gate must stay closed: {ref}")
        if item.get("provider_prompt_inclusion_allowed") is not False:
            raise ValueError(f"asset provider prompt inclusion must stay closed: {ref}")
        require_resolved_refs(item.get("applies_to_branch_path_refs") or [], refs, owner=ref, field="applies_to_branch_path_refs")
        require_resolved_refs(item.get("evidence_refs") or [], refs, owner=ref, field="evidence_refs")
        if item.get("source_asset_ref"):
            require_resolved_ref(str(item["source_asset_ref"]), refs, owner=ref, field="source_asset_ref")
        assets[ref] = item
    if not any(asset["scope"] in SHARED_ASSET_SCOPES for asset in assets.values()):
        raise ValueError("branch package must declare shared asset needs")
    if not any(asset["scope"] in BRANCH_ASSET_SCOPES for asset in assets.values()):
        raise ValueError("branch package must declare branch-specific asset needs")
    return assets


def _validate_continuity_constraints(items: list[Any], refs: set[str]) -> dict[str, dict[str, Any]]:
    constraints: dict[str, dict[str, Any]] = {}
    for item in dict_items(items, "continuity constraint"):
        ref = required_text(item, "constraint_ref")
        scope = required_text(item, "scope")
        if scope not in {"shared_across_paths", "branch_specific"}:
            raise ValueError(f"unknown continuity scope: {ref}")
        if not item.get("must_remain_stable") or "allowed_divergence" not in item:
            raise ValueError(f"continuity constraint missing stability or divergence rule: {ref}")
        require_resolved_refs(item.get("applies_to_refs") or [], refs, owner=ref, field="applies_to_refs")
        require_resolved_refs(item.get("evidence_refs") or [], refs, owner=ref, field="evidence_refs")
        constraints[ref] = item
    if not any(item["scope"] == "shared_across_paths" for item in constraints.values()):
        raise ValueError("branch package must declare shared continuity constraints")
    if not any(item["scope"] == "branch_specific" for item in constraints.values()):
        raise ValueError("branch package must declare branch-specific continuity constraints")
    return constraints


def _validate_choice_and_paths(
    choice: dict[str, Any],
    paths: list[Any],
    refs: set[str],
    asset_by_ref: dict[str, dict[str, Any]],
    constraint_by_ref: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    choice_ref = required_text(choice, "choice_point_ref")
    branch_path_refs = choice.get("branch_path_refs") or []
    if int(choice.get("required_branch_count") or 0) != 2 or len(branch_path_refs) != 2:
        raise ValueError(f"choice point must require exactly two branch paths: {choice_ref}")
    require_resolved_refs(choice.get("source_refs") or [], refs, owner=choice_ref, field="source_refs")
    require_resolved_refs(choice.get("shared_setup_shot_refs") or [], refs, owner=choice_ref, field="shared_setup_shot_refs")
    paths_by_ref = {required_text(path, "branch_path_ref"): path for path in dict_items(paths, "branch path")}
    if set(branch_path_refs) != set(paths_by_ref):
        raise ValueError(f"choice point branch refs must match package paths: {choice_ref}")
    for path_ref, path in paths_by_ref.items():
        require_resolved_ref(required_text(path, "choice_point_ref"), {choice_ref}, owner=path_ref, field="choice_point_ref")
        for field in ("branch_shot_refs", "asset_need_refs", "continuity_constraint_refs"):
            require_resolved_refs(path.get(field) or [], refs, owner=path_ref, field=field)
        require_resolved_ref(required_text(path, "converges_to_ref"), refs, owner=path_ref, field="converges_to_ref")
        if not _path_has_asset_scope(path, asset_by_ref, SHARED_ASSET_SCOPES):
            raise ValueError(f"branch path missing shared asset need: {path_ref}")
        if not _path_has_asset_scope(path, asset_by_ref, BRANCH_ASSET_SCOPES):
            raise ValueError(f"branch path missing branch-specific asset need: {path_ref}")
        for constraint_ref in path.get("continuity_constraint_refs") or []:
            if str(constraint_ref) not in constraint_by_ref:
                raise ValueError(f"branch path continuity ref must resolve: {path_ref}")
    return paths_by_ref


def _validate_branch_shots(items: list[Any], refs: set[str], paths_by_ref: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    mappings: list[dict[str, str]] = []
    for item in dict_items(items, "branch shot"):
        shot_ref = required_text(item, "branch_shot_ref")
        path_ref = required_text(item, "branch_path_ref")
        if path_ref not in paths_by_ref or shot_ref not in paths_by_ref[path_ref].get("branch_shot_refs", []):
            raise ValueError(f"branch shot missing from parent path order: {shot_ref}")
        base_storyboard_ref = required_text(item, "base_storyboard_ref")
        base_shot_ref = required_text(item, "base_shot_ref")
        branch_specific_shot_ref = required_text(item, "branch_specific_shot_ref")
        require_resolved_ref(base_storyboard_ref, refs, owner=shot_ref, field="base_storyboard_ref")
        require_resolved_ref(base_shot_ref, refs, owner=shot_ref, field="base_shot_ref")
        if branch_specific_shot_ref == base_shot_ref:
            raise ValueError(f"branch shot must carry a branch-specific shot ref: {shot_ref}")
        for field in ("required_asset_refs", "continuity_constraint_refs", "evidence_refs"):
            require_resolved_refs(item.get(field) or [], refs, owner=shot_ref, field=field)
        mappings.append(
            {
                "branch_shot_ref": shot_ref,
                "base_storyboard_ref": base_storyboard_ref,
                "base_shot_ref": base_shot_ref,
                "branch_specific_shot_ref": branch_specific_shot_ref,
            }
        )
    return mappings


def _validate_evidence_requirements(items: list[Any], refs: set[str], graph_artifacts: set[str]) -> None:
    for item in dict_items(items, "evidence requirement"):
        ref = required_text(item, "evidence_requirement_ref")
        mapped_refs = required_dict(item, "mapped_refs")
        for field in REQUIRED_EVIDENCE_MAPPING_FIELDS:
            values = mapped_refs.get(field)
            if not isinstance(values, list) or not values:
                raise ValueError(f"evidence requirement missing mapped {field}: {ref}")
            if field == "production_graph_artifact_refs":
                for artifact_ref in values:
                    if str(artifact_ref) not in graph_artifacts:
                        raise ValueError(f"unresolved graph artifact ref in evidence requirement: {ref}")
            else:
                require_resolved_refs(values, refs, owner=ref, field=field)
        require_resolved_refs(item.get("source_refs") or [], refs, owner=ref, field="source_refs")


def _validate_handoff(item: dict[str, Any], refs: set[str]) -> None:
    handoff_ref = required_text(item, "handoff_ref")
    for field in ("handoff_target", "next_owner", "next_action", "close_condition"):
        required_text(item, field)
    require_resolved_refs(item.get("target_refs") or [], refs, owner=handoff_ref, field="target_refs")
    require_resolved_refs(item.get("evidence_refs") or [], refs, owner=handoff_ref, field="evidence_refs")
    validate_non_claims(item.get("non_claims"), owner=handoff_ref, require_all=False, protected_non_claims=PROTECTED_NON_CLAIMS)


def _report(
    payload: dict[str, Any],
    package: dict[str, Any],
    branch_paths: list[dict[str, Any]],
    branch_shots: list[dict[str, Any]],
    asset_needs: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    shot_mappings: list[dict[str, str]],
    graph_artifacts: set[str],
) -> dict[str, Any]:
    asset_scope_counts = Counter(str(item["scope"]) for item in asset_needs)
    continuity_scope_counts = Counter(str(item["scope"]) for item in constraints)
    asset_by_ref = {item["asset_need_ref"]: item for item in asset_needs}
    return {
        "fixture_id": required_text(payload, "fixture_id"),
        "fixture_claim_level": required_text(payload, "fixture_claim_level"),
        "package_ref": required_text(package, "package_ref"),
        "summary": {
            "choice_point_count": 1,
            "branch_path_count": len(branch_paths),
            "branch_shot_count": len(branch_shots),
            "asset_need_count": len(asset_needs),
            "shared_asset_need_count": sum(asset_scope_counts[scope] for scope in SHARED_ASSET_SCOPES),
            "branch_specific_asset_need_count": sum(asset_scope_counts[scope] for scope in BRANCH_ASSET_SCOPES),
            "continuity_constraint_count": len(constraints),
            "evidence_requirement_count": len(requirements),
        },
        "branch_paths": {path["branch_path_ref"]: list(path["branch_shot_refs"]) for path in branch_paths},
        "branch_shot_mappings": shot_mappings,
        "asset_need_scopes": dict(sorted(asset_scope_counts.items())),
        "continuity_scopes": dict(sorted(continuity_scope_counts.items())),
        "all_paths_have_shared_and_branch_specific_assets": all(
            _path_has_asset_scope(path, asset_by_ref, SHARED_ASSET_SCOPES)
            and _path_has_asset_scope(path, asset_by_ref, BRANCH_ASSET_SCOPES)
            for path in branch_paths
        ),
        "all_paths_have_continuity_constraints": all(bool(path.get("continuity_constraint_refs")) for path in branch_paths),
        "evidence_mapping_fields": sorted(REQUIRED_EVIDENCE_MAPPING_FIELDS),
        "production_graph_boundary": {
            "reference_policy": REFERENCE_POLICY,
            "graph_node_writes_required": False,
            "graph_artifact_refs": sorted(graph_artifacts),
        },
        "source_boundary_refs": list(payload.get("source_boundary_refs") or []),
        "stage1_residuals": list(payload.get("stage1_residuals") or []),
        "non_claims": dict(payload["non_claims"]),
    }


def _path_has_asset_scope(path: dict[str, Any], asset_by_ref: dict[str, dict[str, Any]], scopes: set[str]) -> bool:
    return any(asset_by_ref.get(str(ref), {}).get("scope") in scopes for ref in path.get("asset_need_refs") or [])
