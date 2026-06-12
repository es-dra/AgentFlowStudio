from __future__ import annotations

import hashlib
import json
from typing import Any

from apps.api.runtime_attribute_vocabulary import ATTRIBUTE_GROUPS
from apps.api.runtime_context_budget import apply_context_budget, context_warnings, duplicate_labels
from apps.api.runtime_director_compiler import compile_director_setup
from apps.api.runtime_models import ContextSubgraph, DirectorSetup2D, TemporaryLockOverride
from apps.api.runtime_store import RuntimeStore
from apps.api.runtime_visual_assets import fixed_visual_assets_by_id, public_visual_asset


MAX_SUBGRAPH_NODES = 24
MAX_SUBGRAPH_EDGES = 32
MAX_SUBGRAPH_HOPS = 3
MAX_REFERENCE_EDGE_DEPTH = 6
MAX_OPTIMIZE_SIGNATURES = 4
MAX_GENERATE_FULL_CHARACTER_ASSETS = 3
MAX_GENERATE_FULL_SCENE_ASSETS = 1
RESOLVER_VERSION = "context_resolver_v0.2"
RELATION_PRIORITY = {"reference": 0, "director": 1, "generation": 2}
FORBIDDEN_ASSET_TEXT_KEYS = {"signature", "feature_card", "negative_locks", "visual_asset", "visual_assets"}


def resolve_context_bundle(
    store: RuntimeStore,
    project_id: str,
    *,
    mode: str,
    visible_prompt: str,
    context_subgraph: ContextSubgraph,
    temporary_lock_overrides: list[TemporaryLockOverride] | None = None,
    include_fixed_assets: bool = True,
    style_preference: str | None = None,
    prompt_char_limit: int = 1500,
    reference_image_slots: int = 1,
    director_setup: DirectorSetup2D | None = None,
) -> dict[str, Any]:
    _validate_subgraph(context_subgraph)
    assets = fixed_visual_assets_by_id(store, project_id)
    connected, node_hops = _connected_asset_refs(context_subgraph)
    sorted_connected_ids = _sort_asset_ids(assets, connected)
    overrides = _override_pairs(temporary_lock_overrides or [])

    if mode == "optimize":
        candidate_ids = _optimize_asset_ids(assets, sorted_connected_ids, visible_prompt)
    elif mode == "generate":
        candidate_ids = sorted_connected_ids if include_fixed_assets else []
    else:
        raise ValueError("context resolver mode must be optimize or generate")

    included_ids, arbitration_exclusions = _apply_label_arbitration(assets, candidate_ids)
    detail_levels = _asset_detail_levels(assets, included_ids, mode)
    degraded_exclusions = _degraded_asset_exclusions(assets, included_ids, detail_levels) if mode == "generate" else []
    included = [
        _included_asset(assets[asset_id], connected.get(asset_id), mode, detail_levels.get(asset_id, "signature_only"))
        for asset_id in included_ids
        if asset_id in assets
    ]
    excluded = _excluded_assets(
        assets,
        included_ids,
        connected,
        mode,
        include_fixed_assets,
        extra_exclusions=[*arbitration_exclusions, *degraded_exclusions],
    )
    available = _available_assets(assets, included_ids, connected, visible_prompt)
    upstream_lines = _upstream_summary_lines(context_subgraph, node_hops)
    director_compile = _director_compile_result(director_setup, assets)
    text_channel = _text_channel(
        mode,
        visible_prompt,
        [(assets[item], detail_levels.get(item, "signature_only")) for item in included_ids if item in assets],
        overrides,
        upstream_lines=upstream_lines,
        style_preference=style_preference,
        director_compile=director_compile,
    )
    included_asset_records = [
        assets[item]
        for item in included_ids
        if item in assets and detail_levels.get(item) == "full_card"
    ]
    subject_asset = _subject_reference_asset(included_asset_records, connected)
    reference_channel = _reference_image_channel(included_asset_records, connected, reference_image_slots)
    text_channel, budget = apply_context_budget(mode, text_channel, total_prompt_budget=prompt_char_limit)
    warnings = context_warnings(assets, connected, visible_prompt, overrides)

    return {
        "schema_version": "0.1.0",
        "resolver_version": RESOLVER_VERSION,
        "vocabulary_hash": _hash_payload(ATTRIBUTE_GROUPS),
        "mode": mode,
        "included_assets": included,
        "excluded_assets": excluded,
        "available_project_assets": available,
        "text_channel": text_channel,
        "reference_image_channel": reference_channel,
        "subject_reference_asset_id": subject_asset.get("asset_id") if subject_asset else None,
        "warnings": warnings,
        "budget": budget,
        "temporary_lock_overrides": [
            {"asset_id": item.asset_id, "lock_text": item.lock_text, "reason": item.reason}
            for item in (temporary_lock_overrides or [])
        ],
        "director_compile_result": director_compile,
        "trace_summary": {
            "context_subgraph_assertion": "client_supplied_not_security_boundary",
            "asset_truth_source": "runtime_visual_asset_store_by_id",
            "duplicate_label_candidates": duplicate_labels([assets[item] for item in included_ids if item in assets]),
            "selection_rule": "label_version_terminal_then_hop_then_reference_director_generation_then_asset_id",
            "generate_full_card_limits": {
                "character": MAX_GENERATE_FULL_CHARACTER_ASSETS,
                "scene": MAX_GENERATE_FULL_SCENE_ASSETS,
            },
        },
    }


def provider_prompt_from_bundle(bundle: dict[str, Any]) -> str:
    # Identity/locks lead the prompt: if the provider hard limit ever tail-cuts
    # the joined text, the loss order matches the priority order (preference
    # and summaries die first, locks never), consistent with lock > user text.
    text = bundle.get("text_channel") if isinstance(bundle.get("text_channel"), dict) else {}
    parts = [
        str(text.get("asset_identity_segment") or "").strip(),
        str(text.get("visible_prompt") or "").strip(),
        str(text.get("scene_director_segment") or "").strip(),
        str(text.get("upstream_summary_segment") or "").strip(),
        str(text.get("preference_segment") or "").strip(),
    ]
    return "\n".join(part for part in parts if part)


def _validate_subgraph(subgraph: ContextSubgraph) -> None:
    if len(subgraph.nodes) > MAX_SUBGRAPH_NODES:
        raise ValueError("context_subgraph exceeds the 24 node limit")
    if len(subgraph.edges) > MAX_SUBGRAPH_EDGES:
        raise ValueError("context_subgraph exceeds the 32 edge limit")
    for node in subgraph.nodes:
        extra = getattr(node, "model_extra", {}) or {}
        forbidden = FORBIDDEN_ASSET_TEXT_KEYS.intersection(extra)
        if forbidden:
            raise ValueError("context_subgraph must pass visual asset ids only, not asset text")
    for edge in subgraph.edges:
        extra = getattr(edge, "model_extra", {}) or {}
        forbidden = FORBIDDEN_ASSET_TEXT_KEYS.intersection(extra)
        if forbidden:
            raise ValueError("context_subgraph edge contains forbidden asset text")


def _connected_asset_refs(subgraph: ContextSubgraph) -> tuple[dict[str, dict[str, Any]], dict[str, int]]:
    nodes = {node.id: node for node in subgraph.nodes}
    upstream_by_to: dict[str, list[Any]] = {}
    for edge in subgraph.edges:
        upstream_by_to.setdefault(edge.to_node_id, []).append(edge)
    queue: list[tuple[str, int, int, str]] = [(subgraph.target_node_id, 0, 0, "generation")]
    visited: dict[str, int] = {}
    visited_costs: dict[str, tuple[int, int]] = {}
    refs: dict[str, dict[str, Any]] = {}
    while queue:
        node_id, hop, reference_depth, relation = queue.pop(0)
        if hop > MAX_SUBGRAPH_HOPS or reference_depth > MAX_REFERENCE_EDGE_DEPTH:
            continue
        previous = visited_costs.get(node_id)
        if previous and previous <= (hop, reference_depth):
            continue
        visited_costs[node_id] = (hop, reference_depth)
        visited[node_id] = hop
        node = nodes.get(node_id)
        if node:
            for asset_id in node.visual_asset_ids:
                _remember_ref(refs, str(asset_id), hop, relation, node_id)
        for edge in upstream_by_to.get(node_id, []):
            next_relation = str(edge.relation_type or "generation")
            next_hop = hop if next_relation == "reference" else hop + 1
            next_reference_depth = reference_depth + 1 if next_relation == "reference" else reference_depth
            queue.append((edge.from_node_id, next_hop, next_reference_depth, next_relation))
    return refs, visited


def _upstream_summary_lines(subgraph: ContextSubgraph, node_hops: dict[str, int], limit: int = 3) -> list[str]:
    nodes = {node.id: node for node in subgraph.nodes}
    candidates = sorted(
        (
            (hop, node_id)
            for node_id, hop in node_hops.items()
            if node_id != subgraph.target_node_id and node_id in nodes and str(nodes[node_id].prompt or "").strip()
        ),
    )
    lines: list[str] = []
    for hop, node_id in candidates[:limit]:
        node = nodes[node_id]
        title = str(node.title or node_id).strip()
        prompt = str(node.prompt or "").strip()[:120]
        lines.append(f"{title}: {prompt}")
    return lines


def _remember_ref(refs: dict[str, dict[str, Any]], asset_id: str, hop: int, relation: str, node_id: str) -> None:
    if not asset_id:
        return
    current = refs.get(asset_id)
    priority = RELATION_PRIORITY.get(relation, 9)
    if current and (current["hop"], RELATION_PRIORITY.get(current["relation_type"], 9)) <= (hop, priority):
        return
    refs[asset_id] = {"hop": hop, "relation_type": relation, "source_node_id": node_id}


def _sort_asset_ids(assets: dict[str, dict[str, Any]], refs: dict[str, dict[str, Any]]) -> list[str]:
    return sorted(
        [asset_id for asset_id in refs if asset_id in assets],
        key=lambda asset_id: (
            refs[asset_id]["hop"],
            RELATION_PRIORITY.get(refs[asset_id]["relation_type"], 9),
            asset_id,
        ),
    )


def _optimize_asset_ids(assets: dict[str, dict[str, Any]], connected_ids: list[str], prompt: str) -> list[str]:
    selected: list[str] = []
    for asset_id in connected_ids:
        if asset_id not in selected:
            selected.append(asset_id)
    prompt_fold = prompt.casefold()
    for asset_id, asset in sorted(assets.items()):
        label = str(asset.get("label") or "").casefold()
        if label and label in prompt_fold and asset_id not in selected:
            selected.append(asset_id)
    return selected[:MAX_OPTIMIZE_SIGNATURES]


def _apply_label_arbitration(
    assets: dict[str, dict[str, Any]],
    candidate_ids: list[str],
) -> tuple[list[str], list[dict[str, Any]]]:
    groups: dict[tuple[str, str], list[str]] = {}
    for asset_id in candidate_ids:
        asset = assets.get(asset_id)
        if not asset:
            continue
        key = (str(asset.get("asset_type") or ""), str(asset.get("label") or "").casefold())
        groups.setdefault(key, []).append(asset_id)

    selected_by_group: dict[tuple[str, str], str] = {}
    exclusions: list[dict[str, Any]] = []
    for key, ids in groups.items():
        unique_ids = [item for index, item in enumerate(ids) if item and item not in ids[:index]]
        if len(unique_ids) == 1:
            selected_by_group[key] = unique_ids[0]
            continue
        selected = _terminal_asset_id(assets, unique_ids)
        selected_by_group[key] = selected
        for asset_id in unique_ids:
            if asset_id == selected:
                continue
            asset = assets[asset_id]
            exclusions.append(
                {
                    "asset_id": asset_id,
                    "label": asset.get("label"),
                    "asset_type": asset.get("asset_type"),
                    "reason": "superseded_by_newer_label_version",
                    "selected_asset_id": selected,
                }
            )

    selected_ids: list[str] = []
    for asset_id in candidate_ids:
        asset = assets.get(asset_id)
        if not asset:
            continue
        key = (str(asset.get("asset_type") or ""), str(asset.get("label") or "").casefold())
        selected = selected_by_group.get(key, asset_id)
        if selected == asset_id and selected not in selected_ids:
            selected_ids.append(selected)
    return selected_ids, exclusions


def _terminal_asset_id(assets: dict[str, dict[str, Any]], ids: list[str]) -> str:
    superseded = {
        str(assets[asset_id].get("supersedes_asset_id") or "")
        for asset_id in ids
        if str(assets[asset_id].get("supersedes_asset_id") or "") in ids
    }
    terminals = [asset_id for asset_id in ids if asset_id not in superseded] or ids
    return sorted(terminals, key=lambda asset_id: (_asset_recorded_at(assets[asset_id]), asset_id))[-1]


def _asset_recorded_at(asset: dict[str, Any]) -> str:
    review = asset.get("promotion_review") if isinstance(asset.get("promotion_review"), dict) else {}
    return str(review.get("server_recorded_at") or asset.get("created_at") or "")


def _asset_detail_levels(assets: dict[str, dict[str, Any]], included_ids: list[str], mode: str) -> dict[str, str]:
    if mode != "generate":
        return {asset_id: "signature_only" for asset_id in included_ids}
    counts = {"character": 0, "scene": 0}
    limits = {"character": MAX_GENERATE_FULL_CHARACTER_ASSETS, "scene": MAX_GENERATE_FULL_SCENE_ASSETS}
    detail: dict[str, str] = {}
    for asset_id in included_ids:
        asset_type = str(assets.get(asset_id, {}).get("asset_type") or "character")
        if counts.get(asset_type, 0) < limits.get(asset_type, 0):
            detail[asset_id] = "full_card"
            counts[asset_type] = counts.get(asset_type, 0) + 1
        else:
            detail[asset_id] = "signature_only"
    return detail


def _degraded_asset_exclusions(
    assets: dict[str, dict[str, Any]],
    included_ids: list[str],
    detail_levels: dict[str, str],
) -> list[dict[str, Any]]:
    degraded: list[dict[str, Any]] = []
    for asset_id in included_ids:
        if detail_levels.get(asset_id) != "signature_only":
            continue
        asset = assets.get(asset_id)
        if not asset:
            continue
        degraded.append(
            {
                "asset_id": asset_id,
                "label": asset.get("label"),
                "asset_type": asset.get("asset_type"),
                "reason": "degraded_to_signature_over_limit",
                "degraded_channel": "signature_text",
            }
        )
    return degraded


def _included_asset(asset: dict[str, Any], ref: dict[str, Any] | None, mode: str, detail_level: str) -> dict[str, Any]:
    public = public_visual_asset(asset)
    public.update(
        {
            "channel": "signature_text" if mode == "optimize" else "companion_text",
            "detail_level": detail_level,
            "feature_card_hash": _hash_payload(asset.get("feature_card") if isinstance(asset.get("feature_card"), dict) else {}),
            "hop": (ref or {}).get("hop"),
            "relation_type": (ref or {}).get("relation_type"),
            "connected": ref is not None,
        }
    )
    return public


def _excluded_assets(
    assets: dict[str, dict[str, Any]],
    included_ids: list[str],
    refs: dict[str, dict[str, Any]],
    mode: str,
    include_fixed_assets: bool,
    extra_exclusions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    excluded: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in extra_exclusions or []:
        asset_id = str(item.get("asset_id") or "")
        reason = str(item.get("reason") or "")
        if not asset_id or not reason:
            continue
        seen.add((asset_id, reason))
        excluded.append(item)
    for asset_id in sorted(refs):
        if asset_id in assets or asset_id in included_ids:
            continue
        reason = "retired_or_missing_visual_asset"
        if (asset_id, reason) in seen:
            continue
        seen.add((asset_id, reason))
        excluded.append({"asset_id": asset_id, "label": None, "asset_type": None, "reason": reason})
    for asset_id, asset in sorted(assets.items()):
        if asset_id in included_ids:
            continue
        reason = "not_selected_for_optimize" if mode == "optimize" else "not_connected_to_target"
        if mode == "generate" and not include_fixed_assets and asset_id in refs:
            reason = "fixed_assets_excluded_by_comparison_arm"
        if (asset_id, reason) in seen:
            continue
        excluded.append({"asset_id": asset_id, "label": asset.get("label"), "asset_type": asset.get("asset_type"), "reason": reason})
    return excluded


def _available_assets(
    assets: dict[str, dict[str, Any]],
    included_ids: list[str],
    refs: dict[str, dict[str, Any]],
    prompt: str,
) -> list[dict[str, Any]]:
    prompt_fold = prompt.casefold()
    items = []
    for asset_id, asset in sorted(assets.items()):
        label = str(asset.get("label") or "")
        public = public_visual_asset(asset)
        public["connected"] = asset_id in refs
        public["injected"] = asset_id in included_ids
        public["label_matched"] = bool(label and label.casefold() in prompt_fold)
        items.append(public)
    return items


def _text_channel(
    mode: str,
    visible_prompt: str,
    assets: list[tuple[dict[str, Any], str]],
    overrides: set[tuple[str, str]],
    *,
    upstream_lines: list[str] | None = None,
    style_preference: str | None = None,
    director_compile: dict[str, Any] | None = None,
) -> dict[str, str]:
    if mode == "optimize":
        signatures = [f"{asset['label']}: {asset.get('signature')}" for asset, _detail in assets]
        return {
            "visible_prompt": visible_prompt,
            "asset_signature_segment": "\n".join(signatures),
            "asset_identity_segment": "",
            "scene_director_segment": "",
            "upstream_summary_segment": "",
            "preference_segment": "",
        }
    identity_lines: list[str] = []
    scene_lines: list[str] = []
    for asset, detail_level in assets:
        if detail_level != "full_card":
            line = f"{asset.get('label')}: {asset.get('signature')}".strip()
            if asset.get("asset_type") == "scene":
                scene_lines.append(line)
            else:
                identity_lines.append(line)
            continue
        card = asset.get("feature_card") if isinstance(asset.get("feature_card"), dict) else {}
        card_text = "; ".join(f"{key}: {value}" for key, value in card.items())
        locks = [
            lock
            for lock in asset.get("negative_locks", [])
            if (str(asset.get("asset_id")), str(lock)) not in overrides
        ]
        line = f"{asset.get('label')}: {asset.get('signature')}. {card_text}. Locks: {'; '.join(locks)}".strip()
        if asset.get("asset_type") == "scene":
            scene_lines.append(line)
        else:
            identity_lines.append(line)
    preference = str(style_preference or "").strip()
    director_lines = _director_lines(director_compile)
    return {
        "visible_prompt": visible_prompt,
        "asset_signature_segment": "",
        "asset_identity_segment": "\n".join(identity_lines),
        "scene_director_segment": "\n".join([*director_lines, *scene_lines]),
        "upstream_summary_segment": "\n".join(upstream_lines or []),
        "preference_segment": f"style preference: {preference}" if preference else "",
    }


def _director_compile_result(director_setup: DirectorSetup2D | None, assets: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    if director_setup is None:
        return None
    signatures = {
        str(asset.get("asset_id")): str(asset.get("signature") or "")
        for asset in assets.values()
        if str(asset.get("signature") or "")
    }
    return compile_director_setup(director_setup, visual_asset_signatures=signatures)


def _director_lines(director_compile: dict[str, Any] | None) -> list[str]:
    if not director_compile:
        return []
    lines = []
    for section in director_compile.get("sections", []):
        if not isinstance(section, dict):
            continue
        title = str(section.get("title") or "").strip()
        text = str(section.get("text") or "").strip()
        if title and text:
            lines.append(f"{title}: {text}")
    return lines


def _subject_reference_asset(assets: list[dict[str, Any]], refs: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    characters = [asset for asset in assets if asset.get("asset_type") == "character" and asset.get("image_asset_refs")]
    if not characters:
        return None
    return sorted(
        characters,
        key=lambda asset: (
            refs.get(str(asset.get("asset_id")), {}).get("hop", 99),
            RELATION_PRIORITY.get(refs.get(str(asset.get("asset_id")), {}).get("relation_type", "generation"), 9),
            str(asset.get("asset_id")),
        ),
    )[0]


def _reference_image_channel(
    assets: list[dict[str, Any]],
    refs: dict[str, dict[str, Any]],
    reference_image_slots: int,
) -> list[dict[str, str]]:
    if reference_image_slots <= 0:
        return []
    characters = [asset for asset in assets if asset.get("asset_type") == "character" and asset.get("image_asset_refs")]
    sorted_characters = sorted(
        characters,
        key=lambda asset: (
            refs.get(str(asset.get("asset_id")), {}).get("hop", 99),
            RELATION_PRIORITY.get(refs.get(str(asset.get("asset_id")), {}).get("relation_type", "generation"), 9),
            str(asset.get("asset_id")),
        ),
    )
    channel: list[dict[str, str]] = []
    for asset in sorted_characters:
        image_refs = [str(item) for item in list(asset.get("image_asset_refs") or []) if str(item)]
        for image_ref in image_refs:
            channel.append({"asset_id": image_ref, "visual_asset_id": str(asset["asset_id"]), "role": "subject_reference"})
            if len(channel) >= reference_image_slots:
                return channel
    return channel


def _override_pairs(overrides: list[TemporaryLockOverride]) -> set[tuple[str, str]]:
    return {(item.asset_id, item.lock_text) for item in overrides}


def _hash_payload(value: Any) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:16]


__all__ = ("provider_prompt_from_bundle", "resolve_context_bundle")
