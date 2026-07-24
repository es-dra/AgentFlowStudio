from __future__ import annotations

import re
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Mapping

from fastapi import FastAPI, HTTPException, Request

from apps.api.runtime_asset_recognition import recognize_asset_occurrences
from apps.api.runtime_asset_profile_plan import build_asset_profile_plan
from apps.api.runtime_auth import RuntimeAuthStore
from apps.api.runtime_production_graph import (
    GraphIdempotencyConflict,
    GraphVersionConflict,
    ProductionGraphError,
    ProductionGraphStore,
    canonical_digest,
    graph_has_authority,
)
from apps.api.runtime_store import RuntimeStore, reject_unsafe_payload, safe_id
from apps.api.runtime_studio_state_asset_bible import sanitize_asset_bible


SCHEMA_VERSION = "afs.asset_bible.v0.1"
COMMANDS = {
    "generate_candidates",
    "regenerate_candidates",
    "create_asset",
    "set_art_direction",
    "approve",
    "reject",
    "edit",
    "merge",
    "split",
    "reassign_occurrences",
    "mark_not_needed",
    "lock",
}
ASSET_TYPES = {"character", "scene", "prop"}
ART_DIRECTION_FIELDS = ("visual_style", "medium", "palette", "lighting")


def register_runtime_asset_bible_routes(app: FastAPI, store: RuntimeStore, auth: RuntimeAuthStore) -> None:
    graph_store = ProductionGraphStore(store)

    def require_access(request: Request, project_id: str) -> None:
        store.ensure_project_manifest(project_id)
        if auth.enabled():
            user = auth.require_user(request)
            if not auth.user_can_access_project(str(user["user_id"]), project_id):
                raise HTTPException(status_code=403, detail="project access denied")

    @app.get("/projects/{project_id}/m6/asset-bible")
    def get_asset_bible(project_id: str, request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        if not graph_has_authority(store, project_id):
            return _public_result({}, authority_mode="legacy_studio_adapter")
        graph = graph_store.load(project_id)
        state = _asset_bible_from_graph(graph, project_id)
        return {
            **_public_result(state, authority_mode="canonical_production_graph"),
            "graph_version": graph["version"],
            "graph_digest": graph["graph_digest"],
        }

    @app.post("/projects/{project_id}/m6/asset-bible/commands/preview")
    def preview_asset_bible_command(project_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        try:
            preview = preview_asset_bible_command_result(project_id, body)
            reject_unsafe_payload(preview)
            return preview
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/projects/{project_id}/m6/asset-bible/commands/confirm")
    def confirm_asset_bible_command(project_id: str, body: dict[str, Any], request: Request) -> dict[str, Any]:
        require_access(request, project_id)
        try:
            supplied_idempotency_key = _optional_token(body.get("idempotency_key"))
            current = _clean_state(body.get("asset_bible"))
            authority_mode = "legacy_studio_adapter"
            graph: dict[str, Any] | None = None
            if graph_has_authority(store, project_id):
                graph = graph_store.load(project_id)
                current = _asset_bible_from_graph(graph, project_id)
                authority_mode = "canonical_production_graph"
            if (
                supplied_idempotency_key
                and supplied_idempotency_key in current.get("idempotency_keys", [])
            ):
                replay = {
                    **_public_result(current, authority_mode=authority_mode),
                    "status": "confirmed",
                    "idempotent_replay": True,
                    "receipt": deepcopy(current.get("last_receipt", {})),
                }
                if graph is not None:
                    replay.update(
                        {
                            "graph_version": graph["version"],
                            "graph_digest": graph["graph_digest"],
                        }
                    )
                reject_unsafe_payload(replay)
                return replay
            preview = preview_asset_bible_command_result(project_id, body)
            supplied_digest = str(body.get("preview_digest") or "")
            if not supplied_digest or supplied_digest != preview["preview_digest"]:
                raise ValueError("asset Bible preview is stale; review the impact again")
            idempotency_key = _optional_token(body.get("idempotency_key")) or f"asset-{preview['preview_digest'][:32]}"
            result = deepcopy(preview["result"])
            state = result["asset_bible"]
            if idempotency_key in state.get("idempotency_keys", []):
                return {**result, "status": "confirmed", "idempotent_replay": True}
            state["idempotency_keys"] = [*state.get("idempotency_keys", []), idempotency_key][-40:]
            receipt = _receipt(state, preview["command"], preview["impact"])
            state["last_receipt"] = receipt
            result["asset_bible"] = state
            if graph_has_authority(store, project_id):
                graph = graph_store.load(project_id)
                expected = int(body.get("expected_graph_version", graph["version"]))
                previous_state = _clean_state(body.get("asset_bible"))
                events = _graph_events(project_id, state, graph, previous_state=previous_state)
                updated = graph_store.append(
                    project_id,
                    expected_version=expected,
                    idempotency_key=idempotency_key,
                    semantic_digest=canonical_digest({"asset_bible": state, "command": preview["command"]}),
                    events=events,
                )
                result.update(
                    {
                        "authority_mode": "canonical_production_graph",
                        "graph_version": updated["version"],
                        "graph_digest": updated["graph_digest"],
                        "idempotent_replay": bool(updated.get("idempotent_replay")),
                    }
                )
            else:
                result.update({"authority_mode": "legacy_studio_adapter", "idempotent_replay": False})
            reject_unsafe_payload(result)
            return {**result, "status": "confirmed", "receipt": receipt}
        except (GraphVersionConflict, GraphIdempotencyConflict) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except (ProductionGraphError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc


def preview_asset_bible_command_result(project_id: str, body: Mapping[str, Any]) -> dict[str, Any]:
    command = body.get("command") if isinstance(body.get("command"), Mapping) else {}
    command_type = str(command.get("type") or "")
    if command_type not in COMMANDS:
        raise ValueError("unsupported asset Bible command")
    current = _clean_state(body.get("asset_bible"))
    result = _apply_command(project_id, current, command, body)
    impact = _impact(current, result, command)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "status": "preview",
        "context_fingerprint": _optional_token(body.get("context_fingerprint")),
        "command": _safe_command(command),
        "impact": impact,
        "result": {
            "asset_bible": result,
            "provider_dispatch_count": 0,
            "external_cost_usd": 0,
            "graph_mutation": 0,
        },
        "provider_dispatch_count": 0,
        "external_cost_usd": 0,
        "requires_confirmation": True,
    }
    payload["preview_digest"] = canonical_digest(payload)
    return payload


def build_asset_candidate_set(project_id: str, body: Mapping[str, Any]) -> dict[str, Any]:
    source_text = str(body.get("source_text") or "").strip()[:12000]
    context_values = (
        body.get("source_context_texts")
        if isinstance(body.get("source_context_texts"), list)
        else []
    )
    source_context_texts = [
        str(item).strip()[:12000]
        for item in context_values
        if str(item).strip()
    ][:8]
    source_node_id = _token(body.get("source_node_id"), "source_node_id")
    revision_id = _token(body.get("script_revision_id"), "script_revision_id")
    shot_plan = body.get("shot_plan") if isinstance(body.get("shot_plan"), Mapping) else {}
    scenes = [item for item in shot_plan.get("scenes", []) if isinstance(item, Mapping)][:80]
    if not source_text or not scenes:
        raise ValueError("asset candidates require an applied screenplay and shot plan")
    source_digest = canonical_digest(
        {"source_text": source_text, "source_context_texts": source_context_texts}
    )
    shot_candidate_id = _optional_token(shot_plan.get("candidate_id"))
    recognition = recognize_asset_occurrences(source_text, source_context_texts, scenes)

    assets = [
        _candidate_asset(project_id, item, source_node_id=source_node_id, revision_id=revision_id)
        for item in recognition["assets"]
    ]
    if not assets:
        raise ValueError("no reviewable character, scene, or prop candidates were recognized")
    candidate_set_id = f"asset-candidates-{canonical_digest({'project': project_id, 'source': source_digest, 'shot': shot_candidate_id})[:16]}"
    anchors = []
    for anchor in recognition["required_asset_anchors"]:
        source_asset = next(
            (
                asset
                for asset in assets
                if asset["asset_type"] == anchor["asset_type"]
                and _asset_identity_overlap(asset, anchor)
            ),
            None,
        )
        anchors.append(
            {
                **anchor,
                "source_asset_id": source_asset["stable_id"] if source_asset else "",
            }
        )
    return {
        "candidate_set_id": candidate_set_id,
        "version": 1,
        "source_node_id": source_node_id,
        "script_revision_id": revision_id,
        "shot_candidate_id": shot_candidate_id,
        "scene_count": len(recognition["scene_catalog"]),
        "shot_count": len(recognition["shot_catalog"]),
        "scene_index": recognition["scene_catalog"],
        "shot_index": recognition["shot_catalog"],
        "required_asset_anchors": anchors,
        "recognition_ambiguities": recognition["recognition_ambiguities"],
        "source_digest": source_digest,
        "created_at": _requested_at(body),
        "assets": assets,
    }


def _apply_command(
    project_id: str,
    current: dict[str, Any],
    command: Mapping[str, Any],
    body: Mapping[str, Any],
) -> dict[str, Any]:
    command_type = str(command.get("type") or "")
    command_time = _requested_at(body)
    if command_type in {"generate_candidates", "regenerate_candidates"}:
        generated = build_asset_candidate_set(project_id, body)
        if command_type == "regenerate_candidates":
            if not current:
                raise ValueError("asset Bible candidates must be generated before re-recognition")
            if current.get("status") == "locked":
                raise ValueError("locked Asset Bible requires a new revision before re-recognition")
            assets, recognition_delta = _reconcile_recognition_assets(
                current.get("assets", []),
                generated["assets"],
            )
            result = {
                **current,
                "status": "candidate_review",
                "version": int(current.get("version") or 0) + 1,
                "candidate_set": {
                    key: value for key, value in generated.items() if key != "assets"
                },
                "assets": assets,
                "required_occurrences": _required_occurrences(
                    [
                        item
                        for item in assets
                        if item.get("review_state") not in {"rejected", "superseded"}
                    ]
                ),
                "occurrence_resolutions": [],
                "recognition_delta": recognition_delta,
                "locked_revision_id": "",
                "locked_at": "",
                "provider_dispatch_count": 0,
                "external_cost_usd": 0,
            }
            result = _refresh_coverage(result)
            return _append_revision(result, command_type, created_at=command_time)
        result = {
            "schema_version": SCHEMA_VERSION,
            "authority_mode": str(body.get("authority_mode") or "legacy_studio_adapter"),
            "status": "candidate_review",
            "version": 1,
            "candidate_set": {key: value for key, value in generated.items() if key != "assets"},
            "assets": generated["assets"],
            "required_occurrences": _required_occurrences(generated["assets"]),
            "occurrence_resolutions": [],
            "art_direction": {},
            "revisions": [],
            "current_revision_id": "",
            "locked_revision_id": "",
            "locked_at": "",
            "last_receipt": {},
            "idempotency_keys": [],
            "provider_dispatch_count": 0,
            "external_cost_usd": 0,
            "recognition_delta": {
                "added_asset_ids": [item["stable_id"] for item in generated["assets"]],
                "merged_asset_ids": [],
                "retained_asset_ids": [],
                "history_asset_ids": [],
            },
        }
        result = _refresh_coverage(result)
        return _append_revision(result, command_type, created_at=command_time)
    if not current:
        raise ValueError("asset Bible candidates must be generated first")
    expected_revision_id = _optional_token(body.get("expected_asset_bible_revision_id"))
    if expected_revision_id and expected_revision_id != current.get("current_revision_id"):
        raise ValueError("asset Bible revision changed; review the impact again")
    if current.get("status") == "locked":
        raise ValueError("locked Asset Bible requires a new revision before editing")
    assets = deepcopy(current["assets"])
    target_ids = [token for item in command.get("target_ids", []) if (token := _optional_token(item))]
    target_id = _optional_token(command.get("target_id"))
    if target_id and target_id not in target_ids:
        target_ids.append(target_id)
    index = {item["stable_id"]: item for item in assets}
    if command_type in {"approve", "reject", "edit", "split"} and (len(target_ids) != 1 or target_ids[0] not in index):
        raise ValueError("asset Bible command requires one current asset")
    if command_type == "set_art_direction":
        current["art_direction"] = _art_direction(
            command.get("art_direction"),
            confirmed_at=command_time,
            require_complete=True,
        )
    elif command_type == "approve":
        _assert_asset_visual_ready(index[target_ids[0]])
        index[target_ids[0]]["review_state"] = "approved"
        index[target_ids[0]]["needs_confirmation"] = False
    elif command_type == "reject":
        index[target_ids[0]]["review_state"] = "rejected"
        index[target_ids[0]]["needs_confirmation"] = False
    elif command_type == "edit":
        _edit_asset(index[target_ids[0]], command.get("patch"))
    elif command_type == "create_asset":
        asset = _create_asset(project_id, command)
        if asset["stable_id"] in index:
            raise ValueError("an asset with the same stable identity already exists")
        assets.append(asset)
        current["required_occurrences"] = [
            *current.get("required_occurrences", []),
            *_required_occurrences([asset]),
        ]
    elif command_type == "merge":
        if (
            len(target_ids) < 2
            or any(item not in index for item in target_ids)
            or any(index[item]["review_state"] in {"rejected", "superseded"} for item in target_ids)
        ):
            raise ValueError("merge requires at least two current assets")
        assets = _merge_assets(project_id, assets, target_ids, command)
        merged_id = next(
            item["stable_id"]
            for item in assets
            if set(item.get("lineage", {}).get("merged_from_ids", [])) == set(target_ids)
        )
        current["occurrence_resolutions"] = _reassign_resolution_targets(
            current.get("occurrence_resolutions", []),
            current.get("required_occurrences", []),
            source_asset_ids=set(target_ids),
            target_for_requirement=lambda _: merged_id,
        )
    elif command_type == "split":
        assets = _split_asset(project_id, assets, target_ids[0], command)
        children = [
            item for item in assets if target_ids[0] in item.get("lineage", {}).get("parent_ids", [])
        ]
        current["occurrence_resolutions"] = _reassign_resolution_targets(
            current.get("occurrence_resolutions", []),
            current.get("required_occurrences", []),
            source_asset_ids={target_ids[0]},
            target_for_requirement=lambda requirement: _split_target(children, requirement),
        )
    elif command_type == "reassign_occurrences":
        requirement_ids = _command_requirement_ids(command)
        destination = index.get(target_id)
        if not destination or destination["review_state"] in {"rejected", "superseded"}:
            raise ValueError("occurrences must be reassigned to a current asset")
        requirements_by_id = {
            item["requirement_id"]: item for item in current.get("required_occurrences", [])
        }
        if any(
            requirements_by_id.get(item, {}).get("asset_type") != destination["asset_type"]
            for item in requirement_ids
        ):
            raise ValueError("occurrences can only be reassigned to an asset of the same type")
        current["occurrence_resolutions"] = _set_occurrence_resolutions(
            current.get("occurrence_resolutions", []),
            current.get("required_occurrences", []),
            requirement_ids,
            resolution="assigned",
            assigned_asset_id=target_id,
            reason=str(command.get("reason") or "").strip()[:240],
        )
    elif command_type == "mark_not_needed":
        requirement_ids = _command_requirement_ids(command)
        reason = str(command.get("reason") or "").strip()[:240]
        if len(reason) < 4:
            raise ValueError("explicit not-needed resolution requires a reviewable reason")
        current["occurrence_resolutions"] = _set_occurrence_resolutions(
            current.get("occurrence_resolutions", []),
            current.get("required_occurrences", []),
            requirement_ids,
            resolution="not_needed",
            assigned_asset_id="",
            reason=reason,
        )
    elif command_type == "lock":
        unresolved = [item["stable_id"] for item in assets if item["review_state"] == "candidate"]
        if unresolved:
            raise ValueError("approve or reject every active candidate before locking")
        if not any(item["review_state"] == "approved" for item in assets):
            raise ValueError("Asset Bible requires at least one approved asset")
        checked = _refresh_coverage({**current, "assets": assets})
        coverage = checked["coverage"]
        if coverage["unresolved_required"]:
            raise ValueError(
                "Asset Bible lock blocked: "
                f"{coverage['unresolved_required']} required occurrences unresolved; "
                f"{coverage['shot_covered']}/{coverage['shot_total']} shots covered"
            )
        if not coverage.get("quality_pass", False):
            raise ValueError(
                "Asset Bible lock blocked: 识别质量门未通过："
                f"{coverage.get('missing_anchor_count', 0)} 个具名资产遗漏，"
                f"{coverage.get('alias_collision_count', 0)} 组别名冲突，"
                f"{coverage.get('orphan_scene_coverage_count', 0)} 个场景覆盖断裂，"
                f"{coverage.get('missing_source_evidence_shot_count', 0)} 个镜头缺少来源证据"
            )
        if not coverage["coverage_pass"]:
            raise ValueError(
                "Asset Bible lock blocked: "
                f"{coverage['unresolved_required']} required occurrences unresolved; "
                f"{coverage['shot_covered']}/{coverage['shot_total']} shots covered"
            )
        visual_blockers = [
            f"{item['display_name']}：{'、'.join(_asset_visual_blockers(item))}"
            for item in assets
            if item.get("review_state") == "approved" and _asset_visual_blockers(item)
        ]
        if visual_blockers:
            raise ValueError(
                "Asset Bible lock blocked: 视觉身份资料未完成："
                + "；".join(visual_blockers[:8])
            )
        _art_direction(current.get("art_direction"), require_complete=True)
        current["status"] = "locked"
        current["locked_at"] = command_time
    result = {**current, "assets": assets, "version": int(current.get("version") or 0) + 1}
    result = _refresh_coverage(result)
    result = _append_revision(result, command_type, created_at=command_time)
    if command_type == "lock":
        result["locked_revision_id"] = result["current_revision_id"]
    return result


def _create_asset(project_id: str, command: Mapping[str, Any]) -> dict[str, Any]:
    asset_type = str(command.get("asset_type") or "")
    display_name = str(command.get("display_name") or "").strip()[:120]
    if asset_type not in ASSET_TYPES or not display_name:
        raise ValueError("new asset requires a supported type and display name")
    item = {
        "asset_type": asset_type,
        "display_name": display_name,
        "aliases": {display_name, *[str(item).strip()[:120] for item in command.get("aliases", []) if str(item).strip()]},
        "scene_ids": {_token(item, "scene_id") for item in command.get("scene_ids", [])},
        "shot_ids": {_token(item, "shot_id") for item in command.get("shot_ids", [])},
        "confidence": 1.0,
        "evidence": [str(command.get("evidence") or "人工审核补充").strip()[:240]],
    }
    return _candidate_asset(project_id, item, source_node_id="human-review", revision_id="human-review")


def _candidate_asset(
    project_id: str,
    item: Mapping[str, Any],
    *,
    source_node_id: str,
    revision_id: str,
) -> dict[str, Any]:
    asset_type = str(item["asset_type"])
    label = str(item["display_name"])
    stable_id = (
        f"asset-{asset_type}-{_ascii_slug(label)}-"
        f"{sha256(f'{project_id}:{asset_type}:{_normalized_name(label)}'.encode()).hexdigest()[:8]}"
    )
    profile = build_asset_profile_plan(
        [
            {
                "asset_id": stable_id,
                "asset_type": asset_type,
                "label": label,
                "evidence_text": " ".join(item.get("evidence", [])[:2]),
            }
        ],
        " ".join(item.get("evidence", [])[:2]),
    )[0]
    scene_ids = sorted(item.get("scene_ids", set()))
    shot_ids = sorted(item.get("shot_ids", set()))
    continuity_id = f"continuity-{stable_id}"
    return {
        "stable_id": stable_id,
        "asset_type": asset_type,
        "display_name": label,
        "aliases": sorted(item.get("aliases", set())),
        "review_state": "candidate",
        "confidence": round(float(item.get("confidence") or 0.55), 3),
        "needs_confirmation": True,
        "occurrences": {"scene_ids": scene_ids, "shot_ids": shot_ids},
        "continuity_states": [
            {
                "state_id": continuity_id,
                "label": "默认连续性（待确认）",
                "status": "pending_confirmation",
                "scene_ids": scene_ids,
                "shot_ids": shot_ids,
            }
        ],
        "visual_identity": "",
        "positive_traits": [],
        "negative_locks": list(profile.get("negative_locks") or []),
        "pending_fields": ["positive_traits", "visual_identity", "continuity_state"],
        "source_evidence": [
            {
                "source_type": "occurrence_ledger",
                "source_id": stable_id,
                "scene_ids": scene_ids,
                "shot_ids": shot_ids,
                "excerpt": "已应用分镜中的场景与镜头出现范围",
            },
            *[
                {
                    "source_type": "applied_shot_plan" if shot_ids else "script_revision",
                    "source_id": shot_ids[0] if shot_ids else revision_id or source_node_id,
                    "excerpt": excerpt,
                }
                for excerpt in item.get("evidence", [])[:4]
            ],
        ],
        "lineage": {"parent_ids": [], "merged_from_ids": []},
    }


def _reconcile_recognition_assets(
    previous_assets: list[dict[str, Any]],
    generated_assets: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    previous = [deepcopy(item) for item in previous_assets]
    active = [
        item for item in previous if item.get("review_state") not in {"rejected", "superseded"}
    ]
    history = [
        item for item in previous if item.get("review_state") in {"rejected", "superseded"}
    ]
    matched_previous: set[str] = set()
    reconciled: list[dict[str, Any]] = []
    delta = {
        "added_asset_ids": [],
        "merged_asset_ids": [],
        "retained_asset_ids": [],
        "history_asset_ids": [],
    }
    new_history: list[dict[str, Any]] = []
    for generated in generated_assets:
        matches = [
            item
            for item in active
            if item.get("asset_type") == generated.get("asset_type")
            and _asset_identity_overlap(item, generated)
        ]
        approved = next(
            (item for item in matches if item.get("review_state") == "approved"),
            None,
        )
        if approved:
            retained = deepcopy(approved)
            retained["aliases"] = sorted(
                {
                    retained["display_name"],
                    generated["display_name"],
                    *retained.get("aliases", []),
                    *generated.get("aliases", []),
                }
            )
            retained["occurrences"] = deepcopy(generated["occurrences"])
            retained["source_evidence"] = _dedupe_evidence(
                [*retained.get("source_evidence", []), *generated.get("source_evidence", [])]
            )
            retained["confidence"] = max(
                float(retained.get("confidence") or 0),
                float(generated.get("confidence") or 0),
            )
            retained["continuity_states"] = deepcopy(generated.get("continuity_states", []))
            reconciled.append(retained)
            matched_previous.update(item["stable_id"] for item in matches)
            delta["retained_asset_ids"].append(retained["stable_id"])
            target_id = retained["stable_id"]
        else:
            candidate = deepcopy(generated)
            matched_previous.update(item["stable_id"] for item in matches)
            if matches:
                candidate["lineage"]["merged_from_ids"] = sorted(
                    {
                        *candidate.get("lineage", {}).get("merged_from_ids", []),
                        *(item["stable_id"] for item in matches),
                    }
                )
                delta["merged_asset_ids"].extend(item["stable_id"] for item in matches)
            else:
                delta["added_asset_ids"].append(candidate["stable_id"])
            reconciled.append(candidate)
            target_id = candidate["stable_id"]
        for item in matches:
            if item["stable_id"] == target_id:
                continue
            historical = deepcopy(item)
            historical["review_state"] = "superseded"
            historical["needs_confirmation"] = False
            historical["superseded_by_ids"] = [target_id]
            new_history.append(historical)
            delta["history_asset_ids"].append(historical["stable_id"])
    for item in active:
        if item["stable_id"] in matched_previous:
            continue
        if item.get("review_state") == "approved":
            reconciled.append(item)
            delta["retained_asset_ids"].append(item["stable_id"])
            continue
        historical = deepcopy(item)
        historical["review_state"] = "superseded"
        historical["needs_confirmation"] = False
        historical["superseded_by_ids"] = []
        new_history.append(historical)
        delta["history_asset_ids"].append(historical["stable_id"])
    history_by_id = {
        item["stable_id"]: item
        for item in [*history, *new_history]
        if item["stable_id"] not in {current["stable_id"] for current in reconciled}
    }
    return [*reconciled, *history_by_id.values()], {
        key: list(dict.fromkeys(values)) for key, values in delta.items()
    }


def _asset_identity_overlap(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_names = {
        _normalized_name(str(value))
        for value in [left.get("display_name"), *left.get("aliases", [])]
        if str(value or "").strip()
    }
    right_names = {
        _normalized_name(str(value))
        for value in [right.get("display_name"), *right.get("aliases", [])]
        if str(value or "").strip()
    }
    if left_names & right_names:
        return True
    return any(
        len(name) >= 2 and len(other) >= 2 and (name in other or other in name)
        for name in left_names
        for other in right_names
    )


def _dedupe_evidence(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen = set()
    for value in values:
        key = (
            str(value.get("source_type") or ""),
            str(value.get("source_id") or ""),
            str(value.get("excerpt") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        result.append(deepcopy(value))
    return result[:12]


def _edit_asset(asset: dict[str, Any], patch: Any) -> None:
    data = patch if isinstance(patch, Mapping) else {}
    if "display_name" in data:
        name = str(data.get("display_name") or "").strip()[:120]
        if not name:
            raise ValueError("asset display name cannot be empty")
        if asset["display_name"] not in asset["aliases"]:
            asset["aliases"].append(asset["display_name"])
        asset["display_name"] = name
    for field in ("aliases", "negative_locks"):
        if field in data:
            values = [str(item).strip()[:160] for item in data.get(field, []) if str(item).strip()]
            asset[field] = list(dict.fromkeys(values))[:24]
    if "visual_identity" in data:
        asset["visual_identity"] = str(data.get("visual_identity") or "").strip()[:600]
    if "positive_traits" in data:
        values = [str(item).strip()[:160] for item in data.get("positive_traits", []) if str(item).strip()]
        asset["positive_traits"] = list(dict.fromkeys(values))[:24]
    if "continuity_states" in data:
        labels = [
            str(item.get("label") if isinstance(item, Mapping) else item).strip()[:160]
            for item in data.get("continuity_states", [])
            if str(item.get("label") if isinstance(item, Mapping) else item).strip()
        ]
        asset["continuity_states"] = [
            {
                "state_id": f"continuity-{asset['stable_id']}-{index + 1}",
                "label": label,
                "status": "confirmed",
                "scene_ids": list(asset.get("occurrences", {}).get("scene_ids", [])),
                "shot_ids": list(asset.get("occurrences", {}).get("shot_ids", [])),
            }
            for index, label in enumerate(dict.fromkeys(labels))
        ][:16]
    asset["review_state"] = "candidate"
    asset["needs_confirmation"] = True
    pending = set(asset.get("pending_fields", []))
    for field, ready in (
        ("positive_traits", bool(asset.get("positive_traits"))),
        ("visual_identity", bool(str(asset.get("visual_identity") or "").strip())),
        (
            "continuity_state",
            any(
                item.get("status") == "confirmed" and str(item.get("label") or "").strip()
                for item in asset.get("continuity_states", [])
            ),
        ),
    ):
        if ready:
            pending.discard(field)
        else:
            pending.add(field)
    asset["pending_fields"] = sorted(pending)


def _asset_visual_blockers(asset: Mapping[str, Any]) -> list[str]:
    blockers = []
    pending = {
        str(item)
        for item in asset.get("pending_fields", [])
        if str(item) in {"positive_traits", "visual_identity", "continuity_state"}
    }
    if "visual_identity" in pending or not str(asset.get("visual_identity") or "").strip():
        blockers.append("视觉身份")
    if "positive_traits" in pending or not asset.get("positive_traits"):
        blockers.append("正向视觉特征")
    continuity_ready = any(
        isinstance(item, Mapping)
        and item.get("status") == "confirmed"
        and str(item.get("label") or "").strip()
        for item in asset.get("continuity_states", [])
    )
    if "continuity_state" in pending or not continuity_ready:
        blockers.append("连续性状态")
    return blockers


def _assert_asset_visual_ready(asset: Mapping[str, Any]) -> None:
    blockers = _asset_visual_blockers(asset)
    if blockers:
        raise ValueError(
            f"资产“{asset.get('display_name') or '待确认资产'}”仍缺少"
            f"{'、'.join(blockers)}；请先编辑并预览影响"
        )


def _art_direction(
    value: Any,
    *,
    confirmed_at: str = "",
    require_complete: bool = False,
) -> dict[str, Any]:
    data = value if isinstance(value, Mapping) else {}
    result = {
        field: str(data.get(field) or "").strip()[:240]
        for field in ART_DIRECTION_FIELDS
    }
    result.update(
        {
            "status": "confirmed" if all(result.values()) else "pending",
            "source": "human_review",
            "confirmed_at": str(data.get("confirmed_at") or confirmed_at or "")[:80],
        }
    )
    if require_complete and (
        result["status"] != "confirmed"
        or not result["confirmed_at"]
    ):
        missing = [
            {
                "visual_style": "视觉风格",
                "medium": "媒介与质感",
                "palette": "色彩方案",
                "lighting": "光线规则",
            }[field]
            for field in ART_DIRECTION_FIELDS
            if not result[field]
        ]
        raise ValueError(
            "统一美术方向尚未确认"
            + (f"：缺少{'、'.join(missing)}" if missing else "")
        )
    return result


def _required_occurrences(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    requirements = []
    for asset in assets:
        for occurrence_kind, field in (("scene", "scene_ids"), ("shot", "shot_ids")):
            for occurrence_id in asset.get("occurrences", {}).get(field, []):
                requirement_id = (
                    f"asset-requirement-"
                    f"{canonical_digest({'asset': asset['stable_id'], 'kind': occurrence_kind, 'id': occurrence_id})[:20]}"
                )
                requirements.append(
                    {
                        "requirement_id": requirement_id,
                        "source_asset_id": asset["stable_id"],
                        "asset_type": asset["asset_type"],
                        "occurrence_kind": occurrence_kind,
                        "occurrence_id": occurrence_id,
                    }
                )
    return sorted(requirements, key=lambda item: item["requirement_id"])


def _resolution_map(
    resolutions: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    requirement_ids = {item["requirement_id"] for item in requirements}
    result = {
        str(item.get("requirement_id")): deepcopy(item)
        for item in resolutions
        if str(item.get("requirement_id")) in requirement_ids
    }
    for requirement in requirements:
        result.setdefault(
            requirement["requirement_id"],
            {
                "requirement_id": requirement["requirement_id"],
                "resolution": "assigned",
                "assigned_asset_id": requirement["source_asset_id"],
                "reason": "",
            },
        )
    return result


def _source_evidence_shot_ids(
    asset: Mapping[str, Any],
    known_shot_ids: set[str],
) -> set[str]:
    result: set[str] = set()
    occurrence_shot_ids = {
        str(shot_id)
        for shot_id in asset.get("occurrences", {}).get("shot_ids", [])
        if str(shot_id) in known_shot_ids
    }
    for evidence in asset.get("source_evidence", []):
        if not isinstance(evidence, Mapping):
            continue
        result.update(
            str(shot_id)
            for shot_id in evidence.get("shot_ids", [])
            if str(shot_id) in occurrence_shot_ids
        )
        source_id = str(evidence.get("source_id") or "")
        if evidence.get("source_type") == "applied_shot_plan" and source_id in occurrence_shot_ids:
            result.add(source_id)
    return result


def _refresh_coverage(state: dict[str, Any]) -> dict[str, Any]:
    requirements = list(state.get("required_occurrences", []))
    resolutions = _resolution_map(list(state.get("occurrence_resolutions", [])), requirements)
    assets = {item["stable_id"]: item for item in state.get("assets", [])}
    ledger = []
    for requirement in requirements:
        resolution = resolutions[requirement["requirement_id"]]
        assigned_id = str(resolution.get("assigned_asset_id") or "")
        assigned = assets.get(assigned_id)
        resolution_type = str(resolution.get("resolution") or "assigned")
        reason = str(resolution.get("reason") or "").strip()
        if resolution_type == "not_needed" and reason:
            status = "not_needed"
            resolved = True
        elif assigned and assigned.get("review_state") == "approved":
            status = "approved"
            resolved = True
        elif assigned and assigned.get("review_state") == "candidate":
            status = "pending"
            resolved = False
        elif assigned and assigned.get("review_state") == "rejected":
            status = "rejected"
            resolved = False
        elif assigned and assigned.get("review_state") == "superseded":
            status = "superseded"
            resolved = False
        else:
            status = "orphaned"
            resolved = False
        ledger.append(
            {
                **requirement,
                "resolution": resolution_type,
                "assigned_asset_id": assigned_id,
                "reason": reason,
                "status": status,
                "resolved": resolved,
            }
        )
    candidate_set = state.get("candidate_set", {})
    scene_catalog = list(candidate_set.get("scene_index", []))
    shot_catalog = list(candidate_set.get("shot_index", []))
    scene_ids = {str(item.get("scene_id") or "") for item in scene_catalog if item.get("scene_id")}
    covered_shots = {
        str(item.get("shot_id") or "")
        for item in shot_catalog
        if item.get("shot_id") and str(item.get("scene_id") or "") in scene_ids
    }
    unresolved = [item for item in ledger if not item["resolved"]]
    unresolved_asset_ids = sorted(
        {
            str(item.get("assigned_asset_id") or item.get("source_asset_id") or "")
            for item in unresolved
            if item.get("assigned_asset_id") or item.get("source_asset_id")
        }
    )
    active_assets = [
        item for item in assets.values() if item.get("review_state") not in {"rejected", "superseded"}
    ]
    alias_owner: dict[tuple[str, str], str] = {}
    collisions = set()
    for asset in active_assets:
        for alias in {asset.get("display_name", ""), *asset.get("aliases", [])}:
            key = (str(asset.get("asset_type") or ""), _normalized_name(str(alias)))
            if not key[1]:
                continue
            if key in alias_owner and alias_owner[key] != asset["stable_id"]:
                collisions.add(key)
            alias_owner[key] = asset["stable_id"]
    known_shot_ids = {
        str(item.get("shot_id") or "")
        for item in shot_catalog
        if item.get("shot_id")
    }
    traceable_shot_ids = {
        shot_id
        for asset in active_assets
        for shot_id in _source_evidence_shot_ids(asset, known_shot_ids)
    }
    untraceable_shot_ids = sorted(known_shot_ids - traceable_shot_ids)
    anchors = [
        item
        for item in candidate_set.get("required_asset_anchors", [])
        if isinstance(item, Mapping)
    ]
    recognition_evidence_missing = bool(scene_catalog or shot_catalog) and not anchors
    missing_anchors = []
    for anchor in anchors:
        matched = next(
            (
                asset
                for asset in active_assets
                if asset.get("asset_type") == anchor.get("asset_type")
                and _asset_identity_overlap(asset, anchor)
            ),
            None,
        )
        if matched:
            continue
        source_asset_id = str(anchor.get("source_asset_id") or "")
        anchor_requirements = [
            item for item in ledger if item.get("source_asset_id") == source_asset_id
        ]
        if anchor_requirements and all(item.get("resolved") for item in anchor_requirements):
            continue
        missing_anchors.append(anchor)
    scene_descendant_missing = []
    shots_by_scene: dict[str, set[str]] = {}
    for shot in shot_catalog:
        shots_by_scene.setdefault(str(shot.get("scene_id") or ""), set()).add(
            str(shot.get("shot_id") or "")
        )
    for asset in active_assets:
        if asset.get("asset_type") != "scene":
            continue
        for scene_id in asset.get("occurrences", {}).get("scene_ids", []):
            expected_shots = shots_by_scene.get(str(scene_id), set())
            missing = sorted(expected_shots - set(asset.get("occurrences", {}).get("shot_ids", [])))
            if missing:
                scene_descendant_missing.append(
                    {
                        "asset_id": asset["stable_id"],
                        "display_name": asset["display_name"],
                        "scene_id": scene_id,
                        "missing_shot_ids": missing,
                    }
                )
    ambiguities = [
        item
        for item in candidate_set.get("recognition_ambiguities", [])
        if isinstance(item, Mapping)
    ]
    quality_issues = [
        *(
            [
                {
                    "code": "recognition_evidence_missing",
                    "asset_type": "",
                    "display_name": "当前识别版本",
                    "scene_count": len(scene_catalog),
                    "shot_count": len(shot_catalog),
                    "message": "当前版本缺少具名资产与出现范围的质量证据。",
                    "action": "预览重新识别并确认替换",
                }
            ]
            if recognition_evidence_missing
            else []
        ),
        *[
            {
                "code": "missing_script_anchor",
                "asset_type": str(item.get("asset_type") or ""),
                "display_name": str(item.get("display_name") or "具名资产"),
                "scene_count": len(item.get("scene_ids", [])),
                "shot_count": len(item.get("shot_ids", [])),
                "message": f"剧本中的具名资产“{item.get('display_name') or '待确认资产'}”尚未由当前资产承接。",
                "action": "重新识别或人工补充并确认出现范围",
            }
            for item in missing_anchors
        ],
        *[
            {
                "code": "orphan_scene_coverage",
                "asset_type": "scene",
                "display_name": item["display_name"],
                "scene_count": 1,
                "shot_count": len(item["missing_shot_ids"]),
                "message": f"场景“{item['display_name']}”未覆盖其全部下属镜头。",
                "action": "重新识别场景与镜头范围",
            }
            for item in scene_descendant_missing
        ],
        *(
            [
                {
                    "code": "missing_source_evidence",
                    "asset_type": "",
                    "display_name": "当前识别版本",
                    "scene_count": 0,
                    "shot_count": len(untraceable_shot_ids),
                    "message": f"{len(untraceable_shot_ids)} 个已应用镜头缺少可审核的资产来源证据。",
                    "action": "重新识别或补全资产出现范围证据后再锁定",
                }
            ]
            if untraceable_shot_ids
            else []
        ),
        *[
            {
                "code": str(item.get("code") or "recognition_ambiguity"),
                "asset_type": str(item.get("asset_type") or ""),
                "display_name": " / ".join(str(label) for label in item.get("labels", [])[:3]),
                "scene_count": 0,
                "shot_count": 0,
                "message": str(item.get("message") or "资产别名关系需要人工确认。"),
                "action": "检查别名并通过合并或拆分确认实例边界",
            }
            for item in ambiguities
        ],
        *[
            {
                "code": "alias_collision",
                "asset_type": asset_type,
                "display_name": alias,
                "scene_count": 0,
                "shot_count": 0,
                "message": f"别名“{alias}”同时属于多个当前资产。",
                "action": "编辑别名或合并重复资产",
            }
            for asset_type, alias in sorted(collisions)
        ],
    ]
    quality_pass = not quality_issues
    coverage = {
        "scene_total": len(scene_catalog),
        "scene_covered": len(scene_ids),
        "shot_total": len(shot_catalog),
        "shot_covered": len(covered_shots),
        "asset_shot_covered": len(traceable_shot_ids & known_shot_ids),
        "missing_source_evidence_shot_count": len(untraceable_shot_ids),
        "required_occurrence_total": len(ledger),
        "resolved_required": len(ledger) - len(unresolved),
        "unresolved_required": len(unresolved),
        "unresolved_asset_ids": unresolved_asset_ids,
        "unresolved_scene_count": len(
            {item["occurrence_id"] for item in unresolved if item["occurrence_kind"] == "scene"}
        ),
        "unresolved_shot_count": len(
            {item["occurrence_id"] for item in unresolved if item["occurrence_kind"] == "shot"}
        ),
        "alias_collision_count": len(collisions),
        "missing_anchor_count": len(missing_anchors),
        "orphan_scene_coverage_count": len(scene_descendant_missing),
        "recognition_ambiguity_count": len(ambiguities),
        "quality_issue_count": len(quality_issues),
        "quality_pass": quality_pass,
        "coverage_pass": (
            len(scene_catalog) > 0
            and len(shot_catalog) > 0
            and len(scene_ids) == len(scene_catalog)
            and len(covered_shots) == len(shot_catalog)
            and not untraceable_shot_ids
            and not unresolved
            and not collisions
            and quality_pass
        ),
    }
    return {
        **state,
        "occurrence_resolutions": list(resolutions.values()),
        "resolution_ledger": ledger,
        "recognition_quality": {
            "status": "pass" if quality_pass else "blocked",
            "issues": quality_issues,
            "missing_anchor_count": len(missing_anchors),
            "orphan_scene_coverage_count": len(scene_descendant_missing),
            "alias_collision_count": len(collisions),
            "recognition_ambiguity_count": len(ambiguities),
            "missing_source_evidence_shot_count": len(untraceable_shot_ids),
        },
        "coverage": coverage,
    }


def _command_requirement_ids(command: Mapping[str, Any]) -> list[str]:
    requirement_ids = [
        token for item in command.get("requirement_ids", []) if (token := _optional_token(item))
    ]
    if not requirement_ids:
        raise ValueError("occurrence resolution requires at least one requirement")
    return list(dict.fromkeys(requirement_ids))


def _set_occurrence_resolutions(
    resolutions: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    requirement_ids: list[str],
    *,
    resolution: str,
    assigned_asset_id: str,
    reason: str,
) -> list[dict[str, Any]]:
    known = {item["requirement_id"] for item in requirements}
    if any(item not in known for item in requirement_ids):
        raise ValueError("occurrence resolution references an unknown requirement")
    current = _resolution_map(resolutions, requirements)
    for requirement_id in requirement_ids:
        current[requirement_id] = {
            "requirement_id": requirement_id,
            "resolution": resolution,
            "assigned_asset_id": assigned_asset_id,
            "reason": reason,
        }
    return list(current.values())


def _reassign_resolution_targets(
    resolutions: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    *,
    source_asset_ids: set[str],
    target_for_requirement: Any,
) -> list[dict[str, Any]]:
    current = _resolution_map(resolutions, requirements)
    requirement_index = {item["requirement_id"]: item for item in requirements}
    for requirement_id, resolution in current.items():
        if resolution.get("resolution") != "assigned":
            continue
        if str(resolution.get("assigned_asset_id") or "") not in source_asset_ids:
            continue
        resolution["assigned_asset_id"] = target_for_requirement(requirement_index[requirement_id])
        resolution["reason"] = "由资产合并/拆分确认重绑定"
    return list(current.values())


def _split_target(children: list[dict[str, Any]], requirement: Mapping[str, Any]) -> str:
    field = "scene_ids" if requirement["occurrence_kind"] == "scene" else "shot_ids"
    matches = [
        item["stable_id"]
        for item in children
        if requirement["occurrence_id"] in item.get("occurrences", {}).get(field, [])
    ]
    if len(matches) != 1:
        raise ValueError("split must reassign every required occurrence exactly once")
    return matches[0]


def _merge_assets(
    project_id: str,
    assets: list[dict[str, Any]],
    target_ids: list[str],
    command: Mapping[str, Any],
) -> list[dict[str, Any]]:
    selected = [item for item in assets if item["stable_id"] in target_ids]
    if len({item["asset_type"] for item in selected}) != 1:
        raise ValueError("only assets of the same type can be merged")
    primary = deepcopy(selected[0])
    name = str(command.get("display_name") or primary["display_name"]).strip()[:120]
    primary["display_name"] = name or primary["display_name"]
    primary["aliases"] = sorted(
        set(primary.get("aliases", []))
        | {item["display_name"] for item in selected}
        | {alias for item in selected for alias in item.get("aliases", [])}
    )
    primary["occurrences"] = {
        "scene_ids": sorted({ref for item in selected for ref in item["occurrences"]["scene_ids"]}),
        "shot_ids": sorted({ref for item in selected for ref in item["occurrences"]["shot_ids"]}),
    }
    primary["lineage"]["merged_from_ids"] = target_ids
    primary["review_state"] = "candidate"
    primary["needs_confirmation"] = True
    primary["stable_id"] = (
        f"asset-{primary['asset_type']}-{_ascii_slug(primary['display_name'])}-"
        f"{sha256(f'{project_id}:merge:{':'.join(sorted(target_ids))}'.encode()).hexdigest()[:8]}"
    )
    superseded = []
    for item in selected:
        historical = deepcopy(item)
        historical["review_state"] = "superseded"
        historical["needs_confirmation"] = False
        historical["superseded_by_ids"] = [primary["stable_id"]]
        superseded.append(historical)
    return [item for item in assets if item["stable_id"] not in target_ids] + superseded + [primary]


def _split_asset(
    project_id: str,
    assets: list[dict[str, Any]],
    target_id: str,
    command: Mapping[str, Any],
) -> list[dict[str, Any]]:
    source = next(item for item in assets if item["stable_id"] == target_id)
    names = [str(item).strip()[:120] for item in command.get("names", []) if str(item).strip()]
    if len(names) != 2 or names[0] == names[1]:
        raise ValueError("split requires two distinct asset names")
    assignments = command.get("occurrence_assignments") if isinstance(command.get("occurrence_assignments"), Mapping) else {}
    children = []
    for index, name in enumerate(names):
        child = deepcopy(source)
        child["stable_id"] = (
            f"asset-{source['asset_type']}-{_ascii_slug(name)}-"
            f"{sha256(f'{project_id}:{target_id}:{index}:{name}'.encode()).hexdigest()[:8]}"
        )
        child["display_name"] = name
        child["aliases"] = [name]
        child["review_state"] = "candidate"
        child["needs_confirmation"] = True
        child["lineage"] = {"parent_ids": [target_id], "merged_from_ids": []}
        assigned = assignments.get(str(index)) if isinstance(assignments.get(str(index)), Mapping) else {}
        child["occurrences"] = {
            "scene_ids": [token for item in assigned.get("scene_ids", []) if (token := _optional_token(item))],
            "shot_ids": [token for item in assigned.get("shot_ids", []) if (token := _optional_token(item))],
        }
        children.append(child)
    for field in ("scene_ids", "shot_ids"):
        assigned_ref_list = [ref for child in children for ref in child["occurrences"][field]]
        assigned_refs = set(assigned_ref_list)
        source_refs = set(source["occurrences"][field])
        if source_refs and (assigned_refs != source_refs or len(assigned_ref_list) != len(assigned_refs)):
            raise ValueError("split occurrence assignments must cover every source occurrence exactly once")
    historical = deepcopy(source)
    historical["review_state"] = "superseded"
    historical["needs_confirmation"] = False
    historical["superseded_by_ids"] = [item["stable_id"] for item in children]
    return [item for item in assets if item["stable_id"] != target_id] + [historical, *children]


def _append_revision(state: dict[str, Any], command_type: str, *, created_at: str) -> dict[str, Any]:
    revision_id = f"asset-bible-r{int(state.get('version') or 0)}-{canonical_digest(state.get('assets', []))[:10]}"
    revision = {
        "revision_id": revision_id,
        "version": int(state.get("version") or 0),
        "status": state.get("status", "candidate_review"),
        "created_at": created_at,
        "command_type": command_type,
        "art_direction": deepcopy(state.get("art_direction", {})),
        "asset_snapshot": [
            {
                "stable_id": item["stable_id"],
                "display_name": item["display_name"],
                "asset_type": item["asset_type"],
                "review_state": item["review_state"],
            }
            for item in state.get("assets", [])
        ],
    }
    return {**state, "current_revision_id": revision_id, "revisions": [*state.get("revisions", []), revision][-24:]}


def _impact(before: Mapping[str, Any], after: Mapping[str, Any], command: Mapping[str, Any]) -> dict[str, Any]:
    target_ids = [token for item in command.get("target_ids", []) if (token := _optional_token(item))]
    target_id = _optional_token(command.get("target_id"))
    if target_id:
        target_ids.append(target_id)
    before_assets = {item["stable_id"]: item for item in before.get("assets", [])}
    impacted = [before_assets[item] for item in dict.fromkeys(target_ids) if item in before_assets]
    if str(command.get("type")) in {"generate_candidates", "regenerate_candidates"}:
        impacted = list(after.get("assets", []))
    requirement_ids = {
        token for item in command.get("requirement_ids", []) if (token := _optional_token(item))
    }
    if requirement_ids:
        impacted_requirements = [
            item
            for item in after.get("resolution_ledger", [])
            if item.get("requirement_id") in requirement_ids
        ]
    else:
        impacted_requirements = [
            item
            for item in after.get("resolution_ledger", [])
            if item.get("source_asset_id") in target_ids
            or item.get("assigned_asset_id") in target_ids
        ]
    scene_ids = (
        []
        if requirement_ids
        else sorted({ref for item in impacted for ref in item.get("occurrences", {}).get("scene_ids", [])})
    )
    shot_ids = (
        []
        if requirement_ids
        else sorted({ref for item in impacted for ref in item.get("occurrences", {}).get("shot_ids", [])})
    )
    scene_ids = sorted(
        set(scene_ids)
        | {
            item["occurrence_id"]
            for item in impacted_requirements
            if item.get("occurrence_kind") == "scene"
        }
    )
    shot_ids = sorted(
        set(shot_ids)
        | {
            item["occurrence_id"]
            for item in impacted_requirements
            if item.get("occurrence_kind") == "shot"
        }
    )
    payload = {
        "asset_ids": sorted(
            {item["stable_id"] for item in impacted}
            | {
                str(item.get("source_asset_id") or "")
                for item in impacted_requirements
                if item.get("source_asset_id")
            }
            | {
                str(item.get("assigned_asset_id") or "")
                for item in impacted_requirements
                if item.get("assigned_asset_id")
            }
        ),
        "scene_ids": scene_ids,
        "shot_ids": shot_ids,
        "scene_count": len(scene_ids),
        "shot_count": len(shot_ids),
        "prompt_candidate_count": len(shot_ids),
        "requirement_ids": sorted(requirement_ids),
        "occurrence_resolution_changes": [
            {
                "requirement_id": item["requirement_id"],
                "occurrence_kind": item["occurrence_kind"],
                "occurrence_id": item["occurrence_id"],
                "assigned_asset_id": item.get("assigned_asset_id", ""),
                "status": item.get("status", ""),
                "reason": item.get("reason", ""),
            }
            for item in impacted_requirements
        ],
        "unresolved_required_before": int(before.get("coverage", {}).get("unresolved_required") or 0),
        "unresolved_required_after": int(after.get("coverage", {}).get("unresolved_required") or 0),
        "graph_mutation_before_confirm": 0,
        "preserved_on_cancel": True,
    }
    if str(command.get("type")) in {"generate_candidates", "regenerate_candidates"}:
        delta = after.get("recognition_delta", {})
        payload["recognition_delta"] = {
            key: list(delta.get(key, []))
            for key in (
                "added_asset_ids",
                "merged_asset_ids",
                "retained_asset_ids",
                "history_asset_ids",
            )
        }
        payload["quality_issue_count_before"] = _quality_issue_count(before)
        payload["quality_issue_count_after"] = _quality_issue_count(after)
    return payload


def _quality_issue_count(state: Mapping[str, Any]) -> int:
    count = int(state.get("coverage", {}).get("quality_issue_count") or 0)
    if count:
        return count
    quality = state.get("recognition_quality")
    has_assets = bool(state.get("assets"))
    return 1 if has_assets and (not isinstance(quality, Mapping) or quality.get("status") != "pass") else 0


def _graph_events(
    project_id: str,
    state: Mapping[str, Any],
    graph: Mapping[str, Any],
    *,
    previous_state: Mapping[str, Any],
) -> list[dict[str, Any]]:
    bible_id = f"asset-bible-{safe_id(project_id)}"
    events: list[dict[str, Any]] = [
        {
            "type": "node_upserted",
            "node": {
                "node_id": bible_id,
                "category": "collection",
                "metadata": {
                    "kind": "asset_bible",
                    "asset_bible": dict(state),
                    "authority_mode": "canonical_production_graph",
                },
            },
        }
    ]
    graph_nodes = set(graph.get("nodes", {}))
    current_asset_ids = {
        str(item["stable_id"])
        for item in state.get("assets", [])
        if item.get("review_state") not in {"rejected", "superseded"}
    }
    previous_asset_ids = {str(item["stable_id"]) for item in previous_state.get("assets", [])}
    removed_asset_ids = sorted((previous_asset_ids - current_asset_ids) & graph_nodes)
    inactive_asset_ids = {
        str(item["stable_id"])
        for item in state.get("assets", [])
        if item.get("review_state") in {"rejected", "superseded"}
    }
    removed_asset_ids = sorted(set(removed_asset_ids) | (inactive_asset_ids & graph_nodes))
    for removed_id in removed_asset_ids:
        for relation in graph.get("relations", []):
            if removed_id not in {relation.get("from_id"), relation.get("to_id")}:
                continue
            events.append({"type": "relation_removed", **dict(relation)})
        events.append(
            {
                "type": "node_state_updated",
                "node_id": removed_id,
                "state": "invalidated",
                "metadata_patch": {
                    "superseded_by_asset_ids": sorted(current_asset_ids - previous_asset_ids),
                    "asset_bible_revision_id": state.get("current_revision_id", ""),
                },
            }
        )
    for asset in state.get("assets", []):
        asset_id = str(asset["stable_id"])
        events.append(
            {
                "type": "node_upserted",
                "node": {
                    "node_id": asset_id,
                    "category": "resource" if asset["asset_type"] != "character" else "entity",
                    "state": "active" if asset["review_state"] not in {"rejected", "superseded"} else "invalidated",
                    "metadata": {
                        "kind": asset["asset_type"],
                        "display_name": asset["display_name"],
                        "aliases": asset["aliases"],
                        "review_state": asset["review_state"],
                        "visual_identity": asset.get("visual_identity", ""),
                        "continuity_states": asset["continuity_states"],
                        "positive_traits": asset["positive_traits"],
                        "negative_locks": asset["negative_locks"],
                        "source_evidence": asset["source_evidence"],
                        "asset_bible_revision_id": state.get("current_revision_id", ""),
                    },
                },
            }
        )
        if asset["review_state"] in {"rejected", "superseded"}:
            continue
        events.append({"type": "relation_upserted", "from_id": bible_id, "to_id": asset_id, "relation_type": "contains"})
        for occurrence_id in [
            *asset.get("occurrences", {}).get("scene_ids", []),
            *asset.get("occurrences", {}).get("shot_ids", []),
        ]:
            if occurrence_id in graph_nodes:
                events.append(
                    {
                        "type": "relation_upserted",
                        "from_id": asset_id,
                        "to_id": occurrence_id,
                        "relation_type": "required_by",
                    }
                )
    return events


def _asset_bible_from_graph(graph: Mapping[str, Any], project_id: str) -> dict[str, Any]:
    node = graph.get("nodes", {}).get(f"asset-bible-{safe_id(project_id)}", {})
    metadata = node.get("metadata") if isinstance(node.get("metadata"), Mapping) else {}
    state = metadata.get("asset_bible") if isinstance(metadata.get("asset_bible"), Mapping) else {}
    return _clean_state(state)


def _clean_state(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping) or not value:
        return {}
    return sanitize_asset_bible(
        dict(value),
        text=lambda raw, fallback, length: str(raw if raw is not None else fallback)[:length],
        number=lambda raw, fallback: _number(raw, fallback),
        reject_forbidden=reject_unsafe_payload,
    )


def _receipt(state: Mapping[str, Any], command: Mapping[str, Any], impact: Mapping[str, Any]) -> dict[str, Any]:
    command_type = str(command.get("type") or "")
    summaries = {
        "generate_candidates": f"已建立 {len(state.get('assets', []))} 个本地确定性资产候选，未调用外部能力。",
        "regenerate_candidates": (
            f"已重新识别 {len([item for item in state.get('assets', []) if item.get('review_state') not in {'rejected', 'superseded'}])} "
            "个当前资产；已批准事实保留，旧候选进入历史，未调用外部能力。"
        ),
        "create_asset": "人工补充资产已进入候选审核，出现范围等待确认。",
        "set_art_direction": "统一美术方向已确认并写入 Asset Bible 当前版本。",
        "approve": "资产候选已批准，引用关系保持可追溯。",
        "reject": "资产候选已拒绝；仍被引用的出现范围会阻止锁定，直到完成重分配或明确无需。",
        "edit": "资产候选修订已保存为新版本。",
        "merge": "资产候选已合并，原稳定 ID 保留在线性记录中。",
        "split": "资产候选已拆分，出现范围已重新绑定。",
        "reassign_occurrences": "资产出现范围已重分配，并保留原始来源追溯。",
        "mark_not_needed": "所选出现范围已明确标记为无需，并记录审核理由。",
        "lock": "Asset Bible 已锁定；媒体结构准入已就绪。",
    }
    return {
        "receipt_id": f"asset-receipt-{canonical_digest({'revision': state.get('current_revision_id'), 'command': command})[:16]}",
        "command_type": command_type,
        "status": "confirmed",
        "summary": summaries.get(command_type, "Asset Bible 已更新。"),
        "confirmed_at": _now(),
        "version": int(state.get("version") or 0),
        "impact_scene_count": int(impact.get("scene_count") or 0),
        "impact_shot_count": int(impact.get("shot_count") or 0),
        "provider_dispatch_count": 0,
        "external_cost_usd": 0,
    }


def _public_result(state: Mapping[str, Any], *, authority_mode: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "ready" if state else "empty",
        "authority_mode": authority_mode,
        "asset_bible": dict(state),
        "provider_dispatch_count": 0,
        "external_cost_usd": 0,
    }


def _safe_command(command: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "type",
        "target_id",
        "target_ids",
        "patch",
        "asset_type",
        "display_name",
        "aliases",
        "scene_ids",
        "shot_ids",
        "evidence",
        "art_direction",
        "names",
        "occurrence_assignments",
        "requirement_ids",
        "reason",
    }
    return {key: deepcopy(value) for key, value in command.items() if key in allowed}


def _token(value: Any, field: str) -> str:
    raw = str(value or "").strip()
    token = safe_id(raw)
    if not raw or token != raw:
        raise ValueError(f"{field} is required and must be a stable id")
    return token


def _optional_token(value: Any) -> str:
    raw = str(value or "").strip()
    return safe_id(raw) if raw else ""


def _normalized_name(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).casefold()


def _ascii_slug(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "-", str(value or "")).strip("-").lower()[:32] or "item"


def _number(value: Any, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _requested_at(body: Mapping[str, Any]) -> str:
    raw = str(body.get("requested_at") or "").strip()
    if raw:
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC).isoformat()
        except ValueError as exc:
            raise ValueError("requested_at must be an ISO-8601 timestamp") from exc
    return "1970-01-01T00:00:00+00:00"


__all__ = (
    "SCHEMA_VERSION",
    "build_asset_candidate_set",
    "preview_asset_bible_command_result",
    "register_runtime_asset_bible_routes",
)
