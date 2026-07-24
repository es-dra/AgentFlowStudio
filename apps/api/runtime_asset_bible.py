from __future__ import annotations

import re
from copy import deepcopy
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any, Mapping

from fastapi import FastAPI, HTTPException, Request

from apps.api.runtime_asset_extraction import normalize_asset_refs_with_diagnostics
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
COMMANDS = {"generate_candidates", "approve", "reject", "edit", "merge", "split", "lock"}
ASSET_TYPES = {"character", "scene", "prop"}


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
    source_node_id = _token(body.get("source_node_id"), "source_node_id")
    revision_id = _token(body.get("script_revision_id"), "script_revision_id")
    shot_plan = body.get("shot_plan") if isinstance(body.get("shot_plan"), Mapping) else {}
    scenes = [item for item in shot_plan.get("scenes", []) if isinstance(item, Mapping)][:80]
    if not source_text or not scenes:
        raise ValueError("asset candidates require an applied screenplay and shot plan")
    source_digest = sha256(source_text.encode("utf-8")).hexdigest()
    shot_candidate_id = _optional_token(shot_plan.get("candidate_id"))
    occurrence_index: dict[tuple[str, str], dict[str, Any]] = {}

    def collect(refs: list[dict[str, Any]], *, scene_id: str = "", shot_id: str = "", evidence: str = "") -> None:
        for ref in refs:
            asset_type = str(ref.get("asset_type") or "")
            label = str(ref.get("display_name") or ref.get("label") or "").strip()
            if asset_type not in ASSET_TYPES or not label:
                continue
            key = (asset_type, _normalized_name(label))
            item = occurrence_index.setdefault(
                key,
                {
                    "asset_type": asset_type,
                    "display_name": label[:120],
                    "aliases": set(),
                    "scene_ids": set(),
                    "shot_ids": set(),
                    "confidence": 0.0,
                    "evidence": [],
                },
            )
            item["aliases"].add(label[:120])
            if scene_id:
                item["scene_ids"].add(scene_id)
            if shot_id:
                item["shot_ids"].add(shot_id)
            item["confidence"] = max(item["confidence"], float(ref.get("confidence") or 0.55))
            excerpt = str(ref.get("evidence_text") or evidence or "").strip()[:240]
            if excerpt and excerpt not in item["evidence"]:
                item["evidence"].append(excerpt)

    source_refs, _ = normalize_asset_refs_with_diagnostics([], context=source_text, include_inferred=True)
    collect(source_refs, evidence=source_text)
    shot_count = 0
    for scene_index, scene in enumerate(scenes):
        scene_id = safe_id(str(scene.get("scene_id") or f"scene-{scene_index + 1}"))
        scene_name = str(scene.get("name") or scene.get("title") or f"场景 {scene_index + 1}").strip()[:120]
        collect(
            [
                {
                    "asset_type": "scene",
                    "display_name": scene_name,
                    "confidence": 1.0,
                    "evidence_text": scene_name,
                }
            ],
            scene_id=scene_id,
            evidence=scene_name,
        )
        for shot_index, shot in enumerate(item for item in scene.get("shots", []) if isinstance(item, Mapping)):
            shot_count += 1
            shot_id = safe_id(str(shot.get("shot_id") or f"{scene_id}-shot-{shot_index + 1}"))
            context = " ".join(
                str(shot.get(key) or "")
                for key in ("title", "description", "narrative_purpose", "blocking", "dialogue", "sound")
            ).strip()
            refs, _ = normalize_asset_refs_with_diagnostics(
                list(shot.get("asset_refs") or []),
                context=context,
                include_inferred=True,
            )
            collect(refs, scene_id=scene_id, shot_id=shot_id, evidence=context)

    assets = [
        _candidate_asset(project_id, item, source_node_id=source_node_id, revision_id=revision_id)
        for _, item in sorted(occurrence_index.items(), key=lambda pair: (pair[0][0], pair[0][1]))
    ]
    if not assets:
        raise ValueError("no reviewable character, scene, or prop candidates were recognized")
    candidate_set_id = f"asset-candidates-{canonical_digest({'project': project_id, 'source': source_digest, 'shot': shot_candidate_id})[:16]}"
    return {
        "candidate_set_id": candidate_set_id,
        "version": 1,
        "source_node_id": source_node_id,
        "script_revision_id": revision_id,
        "shot_candidate_id": shot_candidate_id,
        "scene_count": len(scenes),
        "shot_count": shot_count,
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
    if command_type == "generate_candidates":
        generated = build_asset_candidate_set(project_id, body)
        result = {
            "schema_version": SCHEMA_VERSION,
            "authority_mode": str(body.get("authority_mode") or "legacy_studio_adapter"),
            "status": "candidate_review",
            "version": 1,
            "candidate_set": {key: value for key, value in generated.items() if key != "assets"},
            "assets": generated["assets"],
            "revisions": [],
            "current_revision_id": "",
            "locked_revision_id": "",
            "locked_at": "",
            "last_receipt": {},
            "idempotency_keys": [],
            "provider_dispatch_count": 0,
            "external_cost_usd": 0,
        }
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
    if command_type == "approve":
        index[target_ids[0]]["review_state"] = "approved"
        index[target_ids[0]]["needs_confirmation"] = False
    elif command_type == "reject":
        index[target_ids[0]]["review_state"] = "rejected"
        index[target_ids[0]]["needs_confirmation"] = False
    elif command_type == "edit":
        _edit_asset(index[target_ids[0]], command.get("patch"))
    elif command_type == "merge":
        if len(target_ids) < 2 or any(item not in index for item in target_ids):
            raise ValueError("merge requires at least two current assets")
        assets = _merge_assets(project_id, assets, target_ids, command)
    elif command_type == "split":
        assets = _split_asset(project_id, assets, target_ids[0], command)
    elif command_type == "lock":
        unresolved = [item["stable_id"] for item in assets if item["review_state"] == "candidate"]
        if unresolved:
            raise ValueError("approve or reject every active candidate before locking")
        if not any(item["review_state"] == "approved" for item in assets):
            raise ValueError("Asset Bible requires at least one approved asset")
        current["status"] = "locked"
        current["locked_at"] = command_time
    result = {**current, "assets": assets, "version": int(current.get("version") or 0) + 1}
    result = _append_revision(result, command_type, created_at=command_time)
    if command_type == "lock":
        result["locked_revision_id"] = result["current_revision_id"]
    return result


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
        "positive_traits": [],
        "negative_locks": list(profile.get("negative_locks") or []),
        "pending_fields": ["positive_traits", "visual_identity"],
        "source_evidence": [
            {
                "source_type": "applied_shot_plan" if shot_ids else "script_revision",
                "source_id": shot_ids[0] if shot_ids else revision_id or source_node_id,
                "excerpt": excerpt,
            }
            for excerpt in item.get("evidence", [])[:4]
        ],
        "lineage": {"parent_ids": [], "merged_from_ids": []},
    }


def _edit_asset(asset: dict[str, Any], patch: Any) -> None:
    data = patch if isinstance(patch, Mapping) else {}
    if "display_name" in data:
        name = str(data.get("display_name") or "").strip()[:120]
        if not name:
            raise ValueError("asset display name cannot be empty")
        if asset["display_name"] not in asset["aliases"]:
            asset["aliases"].append(asset["display_name"])
        asset["display_name"] = name
    for field in ("aliases", "positive_traits", "negative_locks"):
        if field in data:
            values = [str(item).strip()[:160] for item in data.get(field, []) if str(item).strip()]
            asset[field] = list(dict.fromkeys(values))[:24]
    asset["review_state"] = "candidate"
    asset["needs_confirmation"] = True
    asset["pending_fields"] = [
        field for field in asset.get("pending_fields", []) if field not in {"positive_traits", "visual_identity"}
    ]


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
    return [item for item in assets if item["stable_id"] not in target_ids] + [primary]


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
    assigned_ref_list = [
        ref
        for child in children
        for ref in [*child["occurrences"]["scene_ids"], *child["occurrences"]["shot_ids"]]
    ]
    assigned_refs = set(assigned_ref_list)
    source_refs = set([*source["occurrences"]["scene_ids"], *source["occurrences"]["shot_ids"]])
    if source_refs and (assigned_refs != source_refs or len(assigned_ref_list) != len(assigned_refs)):
        raise ValueError("split occurrence assignments must cover every source occurrence exactly once")
    return [item for item in assets if item["stable_id"] != target_id] + children


def _append_revision(state: dict[str, Any], command_type: str, *, created_at: str) -> dict[str, Any]:
    revision_id = f"asset-bible-r{int(state.get('version') or 0)}-{canonical_digest(state.get('assets', []))[:10]}"
    revision = {
        "revision_id": revision_id,
        "version": int(state.get("version") or 0),
        "status": state.get("status", "candidate_review"),
        "created_at": created_at,
        "command_type": command_type,
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
    if str(command.get("type")) == "generate_candidates":
        impacted = list(after.get("assets", []))
    scene_ids = sorted({ref for item in impacted for ref in item.get("occurrences", {}).get("scene_ids", [])})
    shot_ids = sorted({ref for item in impacted for ref in item.get("occurrences", {}).get("shot_ids", [])})
    return {
        "asset_ids": sorted({item["stable_id"] for item in impacted}),
        "scene_ids": scene_ids,
        "shot_ids": shot_ids,
        "scene_count": len(scene_ids),
        "shot_count": len(shot_ids),
        "prompt_candidate_count": len(shot_ids),
        "graph_mutation_before_confirm": 0,
        "preserved_on_cancel": True,
    }


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
    current_asset_ids = {str(item["stable_id"]) for item in state.get("assets", [])}
    previous_asset_ids = {str(item["stable_id"]) for item in previous_state.get("assets", [])}
    removed_asset_ids = sorted((previous_asset_ids - current_asset_ids) & graph_nodes)
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
                    "state": "active" if asset["review_state"] != "rejected" else "invalidated",
                    "metadata": {
                        "kind": asset["asset_type"],
                        "display_name": asset["display_name"],
                        "aliases": asset["aliases"],
                        "review_state": asset["review_state"],
                        "continuity_states": asset["continuity_states"],
                        "positive_traits": asset["positive_traits"],
                        "negative_locks": asset["negative_locks"],
                        "source_evidence": asset["source_evidence"],
                        "asset_bible_revision_id": state.get("current_revision_id", ""),
                    },
                },
            }
        )
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
        "generate_candidates": f"已建立 {len(state.get('assets', []))} 个零 Provider 资产候选，等待逐项审核。",
        "approve": "资产候选已批准，引用关系保持可追溯。",
        "reject": "资产候选已拒绝，未进入后续媒体准入。",
        "edit": "资产候选修订已保存为新版本。",
        "merge": "资产候选已合并，原稳定 ID 保留在线性记录中。",
        "split": "资产候选已拆分，出现范围已重新绑定。",
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
    allowed = {"type", "target_id", "target_ids", "patch", "display_name", "names", "occurrence_assignments"}
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
