from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentflow.algorithms.interactive_manga_branch_package import (
    load_json_fixture as load_interactive_json_fixture,
    validate_branch_package_fixture,
)
from agentflow.algorithms.interactive_manga_branch_package._helpers import (
    dict_items,
    reject_unsafe_markers,
    require_resolved_ref,
    require_resolved_refs,
    required_dict,
    required_list,
    required_text,
    validate_non_claims,
)

from ._support import known_refs, repo_root_for_fixture, validation_report
from . import (
    BRANCH_ASSET_SCOPES,
    IMPLEMENTATION_READY_ASSET_STATES,
    PACKAGE_STAGES,
    PROTECTED_NON_CLAIMS,
    REFERENCE_POLICY,
    REQUIRED_MAPPED_REF_FIELDS,
    SHARED_ASSET_SCOPES,
    UNCONFIRMED_ASSET_STATES,
    UNSAFE_MARKERS,
)


def load_json_fixture(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("branch workflow package fixture must be a JSON object")
    return payload


def load_branch_workflow_package_fixture(path: str | Path) -> dict[str, Any]:
    payload = load_json_fixture(path)
    return validate_branch_workflow_package_fixture(payload, source_root=repo_root_for_fixture(path))


def validate_branch_workflow_package_fixture(
    payload: dict[str, Any],
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    reject_unsafe_markers(payload, UNSAFE_MARKERS)
    validate_non_claims(payload.get("non_claims"), owner="fixture", require_all=True, protected_non_claims=PROTECTED_NON_CLAIMS)
    package = required_dict(payload, "branch_workflow_package")
    source_payload, source_report = _validate_source_package(payload, package, source_root)
    refs = known_refs(source_payload, package)
    graph_artifacts = _validate_graph_references(package, refs, source_report)
    _validate_package_root(package, refs)
    choices = _validate_choice_points(required_list(package, "choice_points"), refs)
    paths = _validate_branch_paths(required_list(package, "branch_paths"), refs, choices)
    shots = _validate_branch_shots(required_list(package, "branch_shots"), refs, paths)
    assets = _validate_asset_needs(required_list(package, "asset_needs"), refs)
    constraints = _validate_continuity_constraints(required_list(package, "continuity_constraints"), refs)
    readiness = _validate_evidence_requirements(
        required_list(package, "evidence_requirements"),
        refs,
        graph_artifacts,
        assets,
    )
    handoff = _validate_handoff(required_dict(package, "handoff"), refs)
    readiness["blocked_reasons"] = list(handoff.get("blocked_reasons") or [])
    return validation_report(
        payload,
        package,
        source_report,
        choices,
        paths,
        shots,
        assets,
        constraints,
        graph_artifacts,
        readiness,
    )


def _validate_source_package(
    payload: dict[str, Any],
    package: dict[str, Any],
    source_root: str | Path | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    source_path = Path(required_text(payload, "source_branch_package_fixture_path"))
    if not source_path.is_absolute():
        source_path = Path(source_root or Path.cwd()) / source_path
    source_payload = load_interactive_json_fixture(source_path)
    source_report = validate_branch_package_fixture(source_payload)
    if required_text(package, "package_ref") != source_report["package_ref"]:
        raise ValueError("branch workflow package must reference the T53 source package")
    return source_payload, source_report


def _validate_package_root(package: dict[str, Any], refs: set[str]) -> None:
    if required_text(package, "package_stage") not in PACKAGE_STAGES:
        raise ValueError("unknown branch workflow package stage")
    for field in ("package_ref", "project_id", "source_script_ref", "source_storyboard_ref"):
        require_resolved_ref(required_text(package, field), refs, owner=package["package_id"], field=field)
    review_status = required_dict(package, "review_status")
    required_text(review_status, "review_state")
    if not isinstance(review_status.get("blockers"), list):
        raise ValueError("review_status.blockers must be a list")


def _validate_graph_references(package: dict[str, Any], refs: set[str], source_report: dict[str, Any]) -> set[str]:
    source_artifacts = set(source_report["production_graph_boundary"]["graph_artifact_refs"])
    artifacts: set[str] = set()
    for item in required_list(package, "production_graph_references"):
        graph_ref = required_text(item, "production_graph_ref")
        if item.get("extension_policy") != REFERENCE_POLICY or item.get("graph_node_writes_required") is not False:
            raise ValueError(f"production graph node write claim is not allowed: {graph_ref}")
        if item.get("branch_graph_node_refs"):
            raise ValueError(f"branch graph node writes require a future evaluator gate: {graph_ref}")
        require_resolved_refs(item.get("node_refs") or [], refs, owner=graph_ref, field="node_refs")
        artifact_id = required_text(item, "artifact_id")
        if artifact_id not in source_artifacts:
            raise ValueError(f"production graph artifact must come from T53 source report: {artifact_id}")
        artifacts.add(artifact_id)
    return artifacts


def _validate_choice_points(items: list[Any], refs: set[str]) -> dict[str, dict[str, Any]]:
    choices: dict[str, dict[str, Any]] = {}
    for item in dict_items(items, "choice point"):
        choice_ref = required_text(item, "choice_point_ref")
        choice_id = required_text(item, "choice_point_id")
        require_resolved_ref(required_text(item, "source_ref"), refs, owner=choice_ref, field="source_ref")
        require_resolved_refs(item.get("shared_setup_shot_refs") or [], refs, owner=choice_ref, field="shared_setup_shot_refs")
        branch_path_refs = item.get("branch_path_refs") or []
        if int(item.get("required_branch_count") or 0) != len(branch_path_refs):
            raise ValueError(f"choice point branch count mismatch: {choice_ref}")
        choices[choice_id] = item
    return choices


def _validate_branch_paths(items: list[Any], refs: set[str], choices: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    paths: dict[str, dict[str, Any]] = {}
    for item in dict_items(items, "branch path"):
        path_ref = required_text(item, "branch_path_ref")
        choice_id = required_text(item, "choice_point_id")
        choice = choices.get(choice_id)
        if not choice or path_ref not in choice.get("branch_path_refs", []):
            raise ValueError(f"branch path must belong to a choice point: {path_ref}")
        for field in ("converges_to", "choice_point_ref"):
            require_resolved_ref(required_text(item, field), refs, owner=path_ref, field=field)
        for field in ("branch_shot_refs", "asset_need_refs", "continuity_constraint_refs"):
            require_resolved_refs(item.get(field) or [], refs, owner=path_ref, field=field)
        for field in ("entry_state", "exit_state", "evidence_state"):
            required_text(item, field)
        paths[path_ref] = item
    return paths


def _validate_branch_shots(items: list[Any], refs: set[str], paths: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    shots: dict[str, dict[str, Any]] = {}
    for item in dict_items(items, "branch shot"):
        shot_ref = required_text(item, "branch_shot_ref")
        path_ref = required_text(item, "branch_path_ref")
        if path_ref not in paths or shot_ref not in paths[path_ref].get("branch_shot_refs", []):
            raise ValueError(f"branch shot must belong to its branch path: {shot_ref}")
        for field in ("storyboard_ref", "base_shot_ref", "branch_specific_shot_ref", "production_graph_ref"):
            require_resolved_ref(required_text(item, field), refs, owner=shot_ref, field=field)
        require_resolved_refs(item.get("required_assets") or [], refs, owner=shot_ref, field="required_assets")
        require_resolved_refs(item.get("evidence_refs") or [], refs, owner=shot_ref, field="evidence_refs")
        required_text(item, "handoff_state")
        shots[shot_ref] = item
    return shots


def _validate_asset_needs(items: list[Any], refs: set[str]) -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    for item in dict_items(items, "asset need"):
        ref = required_text(item, "asset_need_ref")
        scope = required_text(item, "scope")
        state = required_text(item, "confirmation_state")
        if scope not in SHARED_ASSET_SCOPES | BRANCH_ASSET_SCOPES:
            raise ValueError(f"unknown asset need scope: {ref}")
        if state in UNCONFIRMED_ASSET_STATES and item.get("implementation_ready_evidence_allowed") is not False:
            raise ValueError(f"unconfirmed candidate cannot be implementation-ready evidence: {ref}")
        if state in IMPLEMENTATION_READY_ASSET_STATES and item.get("implementation_ready_evidence_allowed") is not True:
            raise ValueError(f"confirmed asset must state implementation-ready evidence policy: {ref}")
        if item.get("provider_prompt_inclusion_allowed") is not False:
            raise ValueError(f"provider prompt inclusion must stay closed: {ref}")
        if item.get("source_asset_ref"):
            require_resolved_ref(str(item["source_asset_ref"]), refs, owner=ref, field="source_asset_ref")
        assets[ref] = item
    if not any(asset["scope"] in SHARED_ASSET_SCOPES for asset in assets.values()):
        raise ValueError("branch workflow package must declare shared asset needs")
    if not any(asset["scope"] in BRANCH_ASSET_SCOPES for asset in assets.values()):
        raise ValueError("branch workflow package must declare branch-specific asset needs")
    return assets


def _validate_continuity_constraints(items: list[Any], refs: set[str]) -> dict[str, dict[str, Any]]:
    constraints: dict[str, dict[str, Any]] = {}
    for item in dict_items(items, "continuity constraint"):
        ref = required_text(item, "constraint_ref")
        require_resolved_refs(item.get("applies_to") or [], refs, owner=ref, field="applies_to")
        if not item.get("must_remain_stable") or "allowed_divergence" not in item:
            raise ValueError(f"continuity constraint missing stability or divergence rule: {ref}")
        constraints[ref] = item
    return constraints


def _validate_evidence_requirements(
    items: list[Any],
    refs: set[str],
    graph_artifacts: set[str],
    assets: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    unconfirmed = sorted(ref for ref, item in assets.items() if item["confirmation_state"] in UNCONFIRMED_ASSET_STATES)
    implementation_ready_refs: list[str] = []
    excluded_candidates: list[str] = []
    review_complete = True
    generation_complete = True
    for item in dict_items(items, "evidence requirement"):
        ref = required_text(item, "evidence_requirement_ref")
        evidence_state = required_text(item, "evidence_state")
        accepted = set(item.get("accepted_evidence_states") or [])
        if evidence_state == "partial" and not str(item.get("evidence_gap_reason") or "").strip():
            raise ValueError(f"partial evidence requires evidence_gap_reason: {ref}")
        if item.get("required_for_stage") == "review_ready" and evidence_state not in accepted:
            review_complete = False
        if item.get("required_for_stage") == "accepted_for_generation_planning" and evidence_state not in accepted:
            generation_complete = False
        _validate_mapped_refs(required_dict(item, "mapped_refs"), refs, graph_artifacts, ref)
        for ready_ref in item.get("implementation_ready_evidence_refs") or []:
            ready_ref = str(ready_ref)
            require_resolved_ref(ready_ref, refs, owner=ref, field="implementation_ready_evidence_refs")
            if ready_ref in unconfirmed:
                raise ValueError(f"unconfirmed candidate cannot be implementation-ready evidence: {ready_ref}")
            implementation_ready_refs.append(ready_ref)
        excluded_candidates.extend(str(candidate) for candidate in item.get("excluded_unconfirmed_candidate_refs") or [])
    if sorted(set(excluded_candidates)) != unconfirmed:
        raise ValueError("unconfirmed candidates must be explicitly excluded from implementation-ready evidence")
    return {
        "review_ready_evidence_complete": review_complete,
        "implementation_ready_evidence_complete": generation_complete and not unconfirmed,
        "implementation_ready_asset_refs": sorted(set(implementation_ready_refs)),
        "excluded_unconfirmed_candidate_refs": unconfirmed,
    }


def _validate_mapped_refs(mapped: dict[str, Any], refs: set[str], graph_artifacts: set[str], owner: str) -> None:
    for field in REQUIRED_MAPPED_REF_FIELDS:
        values = mapped.get(field)
        if values is None:
            raise ValueError(f"evidence requirement missing mapped {field}: {owner}")
        if not isinstance(values, list):
            raise ValueError(f"mapped {field} must be a list: {owner}")
        if field == "production_graph_artifact_refs":
            for artifact_ref in values:
                if str(artifact_ref) not in graph_artifacts:
                    raise ValueError(f"unresolved graph artifact ref in evidence requirement: {owner}")
        else:
            require_resolved_refs(values, refs, owner=owner, field=field)


def _validate_handoff(item: dict[str, Any], refs: set[str]) -> dict[str, Any]:
    handoff_ref = required_text(item, "handoff_ref")
    for field in ("handoff_target", "next_owner", "next_action", "close_condition"):
        required_text(item, field)
    for field in ("write_scope_proposal", "verification_route", "blocked_reasons"):
        if not isinstance(item.get(field), list):
            raise ValueError(f"handoff {field} must be a list: {handoff_ref}")
    require_resolved_refs(item.get("target_refs") or [], refs, owner=handoff_ref, field="target_refs")
    require_resolved_refs(item.get("evidence_refs") or [], refs, owner=handoff_ref, field="evidence_refs")
    validate_non_claims(item.get("non_claims"), owner=handoff_ref, require_all=False, protected_non_claims=PROTECTED_NON_CLAIMS)
    return item
