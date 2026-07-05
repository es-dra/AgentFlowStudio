from __future__ import annotations

import hashlib
import re
from typing import Any

from agentflow.algorithms.structured_source_output_qa_checklist._safety import (
    dicts as _dicts,
    has_unsafe_payload as _has_unsafe_payload,
    safe_list as _list,
    safe_note as _safe_note,
    safe_token as _safe_token,
)


ALGORITHM_ID = "afs.asset_identity_reuse_graph.v0.1"
ARTIFACT_TYPE = "agentflow_asset_identity_reuse_graph"
SCHEMA_VERSION = "0.1.0"
INPUT_CONTRACT = "safe observed asset refs with descriptive signatures and reviewed asset-id evidence"
OUTPUT_CONTRACT = "fail-closed canonical asset identity graph with review-only alias suggestions"
EVIDENCE_BOUNDARY = "deterministic graph contract only; no provider call, runtime action, media QA, memory write, or human acceptance"
FAILURE_MODES = (
    "display_name_only_not_identity_key",
    "missing_descriptive_signature",
    "missing_safe_asset_id_evidence",
    "generic_or_provisional_name_not_identity_key",
    "proper_name_only_not_identity_key",
    "identity_group_contains_conflict_or_reversal",
    "unsafe_input_payload",
)
MIN_AUTOLINK_CONFIDENCE = 0.86
ALIAS_SUGGESTION_MIN_CONFIDENCE = 0.55
ALIAS_SUGGESTION_MAX_CONFIDENCE = 0.81
NON_CLAIMS = [
    "no provider call or provider smoke",
    "no generated media claim",
    "no runtime verification",
    "no human acceptance",
    "no business validation",
    "no durable memory promotion",
    "no Company OS or company KB write",
    "alias suggestions require review",
]

_GENERIC_NAME_RE = re.compile(
    r"(?i)\b(unknown|unnamed|generic|placeholder|provisional|temp|draft|subject|object|asset|"
    r"character\s*[a-z0-9]*|hero|person|figure)\b"
)
_CONFLICT_STATES = {"conflict", "conflicted", "blocked_conflict", "contradicted"}
_REVERSAL_STATES = {"reversal", "reversed", "reversal_requested", "undo", "unlink_requested"}
_UNSAFE_BOOL_KEYS = {"provider_calls_started", "generated_media_claimed", "writes_long_term_memory", "writes_company_kb"}
_KEY_FIELDS = ["asset_type", "descriptive_signature", "safe_asset_id_evidence"]


def build_asset_identity_reuse_graph(
    *,
    project_id: str,
    observed_assets: list[dict[str, Any]] | None,
    existing_asset_nodes: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    project = _safe_token(project_id)
    payload = {"observed_assets": observed_assets or [], "existing_asset_nodes": existing_asset_nodes or []}
    if _has_unsafe_payload(payload) or _has_unsafe_bool_claim(payload):
        return _packet(project, "blocked_unsafe", unsafe=True)

    observations = [_observation(item) for item in _dicts(observed_assets)]
    blocked: list[dict[str, Any]] = []
    groups: dict[tuple[str, str, tuple[str, ...]], list[dict[str, Any]]] = {}
    for observation in observations:
        reasons = _block_reasons(observation)
        key = _identity_key(observation)
        if key is None:
            blocked.append(_blocked(observation, reasons))
        else:
            groups.setdefault(key, []).append({**observation, "block_reasons": reasons})

    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    aliases: list[dict[str, Any]] = []
    for group in groups.values():
        if any(item["has_conflict_or_reversal"] for item in group):
            blocked.extend(
                _blocked(item, [*item["block_reasons"], "identity_group_contains_conflict_or_reversal"])
                for item in group
            )
            continue
        node = _node(project, group)
        nodes.append(node)
        if len(group) > 1:
            edges.append(_edge(node, group))
        alias = _alias(node, group)
        if alias:
            aliases.append(alias)

    generic_count = sum(1 for item in blocked if "generic_or_provisional_name_not_identity_key" in item["block_reasons"])
    return _packet(project, _state(blocked, nodes, edges), len(observations), nodes, edges, aliases, blocked, generic_count)


def _packet(
    project_id: str,
    graph_state: str,
    observed_count: int = 0,
    nodes: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
    aliases: list[dict[str, Any]] | None = None,
    blocked: list[dict[str, Any]] | None = None,
    generic_count: int = 0,
    unsafe: bool = False,
) -> dict[str, Any]:
    nodes, edges, aliases, blocked = nodes or [], edges or [], aliases or [], blocked or []
    audit = _audit()
    return {
        "artifact_type": ARTIFACT_TYPE,
        "schema_version": SCHEMA_VERSION,
        "algorithm_id": ALGORITHM_ID,
        "project_id": project_id,
        "graph_state": graph_state,
        "identity_policy": {
            "display_name_is_label_only": True,
            "display_name_used_as_identity_key": False,
            "canonical_key_fields": _KEY_FIELDS,
            "alias_suggestions_are_review_only": True,
            "conflict_or_reversal_blocks_auto_link": True,
            "fail_closed": True,
        },
        "summary": {
            "observed_asset_count": observed_count,
            "canonical_asset_node_count": len(nodes),
            "auto_link_edge_count": len(edges),
            "alias_suggestion_count": len(aliases),
            "blocked_observation_count": len(blocked),
            "generic_or_provisional_name_rejected_count": generic_count,
            "unsafe_input_rejected": unsafe,
            **audit,
        },
        "canonical_asset_nodes": nodes,
        "auto_link_edges": edges,
        "alias_suggestions": aliases,
        "blocked_observations": blocked,
        "audit_metadata": {**audit, "display_name_used_as_identity_key": False, "graph_output_suppressed_for_unsafe_input": unsafe},
        "provider_calls_started": False,
        "generated_media_claimed": False,
        "writes_long_term_memory": False,
        "writes_company_kb": False,
        "non_claims": NON_CLAIMS,
    }


def _observation(item: dict[str, Any]) -> dict[str, Any]:
    display_name = _safe_label(item.get("display_name") or item.get("label") or item.get("name"))
    signature = _safe_note(item.get("descriptive_signature") or item.get("signature"))
    evidence = _asset_id_evidence(item)
    return {
        "observation_id": _safe_token(item.get("observation_id") or item.get("node_id") or item.get("shot_id")) or "observation",
        "shot_id": _safe_token(item.get("shot_id")),
        "asset_type": _safe_token(item.get("asset_type") or item.get("type")),
        "display_name": display_name,
        "descriptive_signature": signature,
        "normalized_signature": _normalized_signature(signature),
        "safe_asset_id_evidence": evidence,
        "safe_asset_ids": [entry["asset_id"] for entry in evidence],
        "proper_name_evidence": _proper_names(item),
        "generic_or_provisional_display_name": _is_generic_name(display_name),
        "has_conflict_or_reversal": _has_conflict_or_reversal(item),
    }


def _block_reasons(observation: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    has_signature = bool(observation["normalized_signature"])
    has_asset_id = bool(observation["safe_asset_id_evidence"])
    if observation["has_conflict_or_reversal"]:
        reasons.append("conflict_or_reversal_present")
    if not has_signature:
        reasons.append("missing_descriptive_signature")
    if not has_asset_id:
        reasons.append("missing_safe_asset_id_evidence")
    if observation["display_name"] and not has_signature and not has_asset_id:
        reasons.append("display_name_only_not_identity_key")
    if observation["generic_or_provisional_display_name"] and not (has_signature and has_asset_id):
        reasons.append("generic_or_provisional_name_not_identity_key")
    if observation["proper_name_evidence"] and not (has_signature and has_asset_id):
        reasons.append("proper_name_only_not_identity_key")
    if not observation["asset_type"]:
        reasons.append("missing_asset_type")
    return _unique(reasons)


def _identity_key(observation: dict[str, Any]) -> tuple[str, str, tuple[str, ...]] | None:
    if not observation["asset_type"] or not observation["normalized_signature"] or not observation["safe_asset_ids"]:
        return None
    return (observation["asset_type"], observation["normalized_signature"], tuple(sorted(observation["safe_asset_ids"])))


def _node(project_id: str, group: list[dict[str, Any]]) -> dict[str, Any]:
    first = group[0]
    asset_ids = sorted({asset_id for item in group for asset_id in item["safe_asset_ids"]})
    display_names = sorted({item["display_name"] for item in group if item["display_name"]})
    node_id = _node_id(project_id, first["asset_type"], first["normalized_signature"], asset_ids)
    proper_name_strength = any(item["proper_name_evidence"] for item in group)
    return {
        "canonical_asset_node_id": node_id,
        "asset_type": first["asset_type"],
        "display_name": display_names[0] if display_names else "",
        "display_names": display_names,
        "descriptive_signature": first["descriptive_signature"],
        "safe_asset_id_evidence": _unique_evidence([entry for item in group for entry in item["safe_asset_id_evidence"]]),
        "source_observation_ids": [item["observation_id"] for item in group],
        "source_shot_ids": _unique([item["shot_id"] for item in group if item["shot_id"]]),
        "identity_key_fields": _KEY_FIELDS,
        "label_policy": {"display_name_is_label_only": True, "display_name_used_as_identity_key": False},
        "evidence_strength": {
            "descriptive_signature": True,
            "safe_asset_id_evidence": True,
            "proper_name_evidence": proper_name_strength,
            "multi_shot_observation": len(group) > 1,
        },
        "confidence": _confidence(group),
    }


def _edge(node: dict[str, Any], group: list[dict[str, Any]]) -> dict[str, Any]:
    observation_ids = [item["observation_id"] for item in group]
    matched = ["descriptive_signature", "safe_asset_id_evidence"]
    if node["evidence_strength"]["proper_name_evidence"]:
        matched.append("proper_name_evidence_strengthened_match")
    return {
        "edge_id": f"asset_identity_reuse:{node['canonical_asset_node_id']}:{_short_hash('|'.join(observation_ids))}",
        "relationship_type": "asset_identity_reuse_auto_link",
        "canonical_asset_node_id": node["canonical_asset_node_id"],
        "observation_ids": observation_ids,
        "source_shot_ids": node["source_shot_ids"],
        "matched_evidence": matched,
        "confidence": node["confidence"],
        "review_required": False,
        "reversible": True,
        "conflict_or_reversal_blocked": False,
    }


def _alias(node: dict[str, Any], group: list[dict[str, Any]]) -> dict[str, Any] | None:
    names = [name for name in node["display_names"] if not _is_generic_name(name)]
    if len({_normalized_label(name) for name in names}) < 2:
        return None
    confidence = round(min(ALIAS_SUGGESTION_MAX_CONFIDENCE, max(ALIAS_SUGGESTION_MIN_CONFIDENCE, 0.72)), 3)
    return {
        "suggestion_id": f"alias_suggestion:{node['canonical_asset_node_id']}:{_short_hash('|'.join(names))}",
        "canonical_asset_node_id": node["canonical_asset_node_id"],
        "canonical_display_name": names[0],
        "suggested_aliases": [
            {"display_name": name, "confidence": confidence, "reason": "same_signature_and_safe_asset_id_evidence_but_alias_review_required"}
            for name in names[1:]
        ],
        "suggestion_state": "review_required",
        "review_only": True,
        "auto_link_authorized": False,
        "source_observation_ids": [item["observation_id"] for item in group],
    }


def _blocked(observation: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    return {
        "observation_id": observation["observation_id"],
        "shot_id": observation["shot_id"],
        "asset_type": observation["asset_type"],
        "display_name": observation["display_name"],
        "block_state": "blocked",
        "block_reasons": _unique(reasons),
        "auto_link_allowed": False,
    }


def _asset_id_evidence(item: dict[str, Any]) -> list[dict[str, str]]:
    raw = item.get("asset_id_evidence") or item.get("asset_refs") or []
    raw = [raw] if isinstance(raw, (str, dict)) else raw
    evidence: list[dict[str, str]] = []
    for entry in _list(raw):
        if isinstance(entry, str):
            asset_id, evidence_type, source_ref_id = _safe_token(entry), "asset_id_ref", ""
        elif isinstance(entry, dict):
            asset_id = _safe_token(entry.get("asset_id") or entry.get("fixed_asset_id") or entry.get("artifact_id"))
            evidence_type = _safe_token(entry.get("evidence_type") or entry.get("source_type")) or "asset_id_ref"
            source_ref_id = _safe_token(entry.get("source_ref_id") or entry.get("artifact_id"))
        else:
            continue
        if asset_id:
            evidence.append({"asset_id": asset_id, "evidence_type": evidence_type, "source_ref_id": source_ref_id})
    return _unique_evidence(evidence)


def _proper_names(item: dict[str, Any]) -> list[dict[str, str]]:
    raw = item.get("proper_name_evidence") or item.get("name_evidence") or []
    raw = [raw] if isinstance(raw, (str, dict)) else raw
    records: list[dict[str, str]] = []
    for entry in _list(raw):
        name = _safe_label(entry.get("name")) if isinstance(entry, dict) else _safe_label(entry)
        source_ref_id = _safe_token(entry.get("source_ref_id")) if isinstance(entry, dict) else ""
        if name and not _is_generic_name(name):
            records.append({"name": name, "source_ref_id": source_ref_id})
    return records[:8]


def _has_conflict_or_reversal(item: dict[str, Any]) -> bool:
    conflict_state = _safe_token(item.get("conflict_state") or item.get("identity_conflict_state"))
    reversal_state = _safe_token(item.get("reversal_state") or item.get("reuse_reversal_state"))
    return bool(item.get("conflict") is True or item.get("reversal") is True or conflict_state in _CONFLICT_STATES or reversal_state in _REVERSAL_STATES)


def _state(blocked: list[dict[str, Any]], nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> str:
    reasons = {reason for item in blocked for reason in item["block_reasons"]}
    if "identity_group_contains_conflict_or_reversal" in reasons and not edges:
        return "blocked_conflict"
    if blocked and not nodes:
        return "blocked_missing_identity_evidence"
    return "ready_with_blocks" if blocked else "ready"


def _audit() -> dict[str, bool]:
    return {"provider_calls_started": False, "generated_media_claimed": False, "writes_long_term_memory": False, "writes_company_kb": False}


def _node_id(project_id: str, asset_type: str, signature: str, asset_ids: list[str]) -> str:
    primary_asset_id = asset_ids[0] if asset_ids else "asset"
    return f"asset_identity:{project_id}:{asset_type}:{primary_asset_id}:{_short_hash(signature + '|' + '|'.join(asset_ids))}"


def _confidence(group: list[dict[str, Any]]) -> float:
    return round(min(0.97, 0.88 + (0.03 if len(group) > 1 else 0) + (0.05 if any(item["proper_name_evidence"] for item in group) else 0)), 3)


def _has_unsafe_bool_claim(value: Any) -> bool:
    if isinstance(value, dict):
        return any((key in _UNSAFE_BOOL_KEYS and item is True) or _has_unsafe_bool_claim(item) for key, item in value.items())
    return any(_has_unsafe_bool_claim(item) for item in value) if isinstance(value, list) else False


def _safe_label(value: Any) -> str:
    return _safe_note(value)[:80]


def _normalized_signature(value: str) -> str:
    return " ".join(re.sub(r"[^0-9A-Za-z]+", " ", str(value or "").casefold()).split())[:240]


def _normalized_label(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "", str(value or "").casefold())


def _is_generic_name(value: str) -> bool:
    text = str(value or "").strip()
    return bool(text and _GENERIC_NAME_RE.search(text))


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


def _unique_evidence(values: list[dict[str, str]]) -> list[dict[str, str]]:
    unique: dict[tuple[str, str, str], dict[str, str]] = {}
    for item in values:
        key = (item.get("asset_id", ""), item.get("evidence_type", ""), item.get("source_ref_id", ""))
        if key[0]:
            unique[key] = item
    return list(unique.values())


__all__ = (
    "ALGORITHM_ID",
    "ALIAS_SUGGESTION_MAX_CONFIDENCE",
    "ALIAS_SUGGESTION_MIN_CONFIDENCE",
    "ARTIFACT_TYPE",
    "EVIDENCE_BOUNDARY",
    "FAILURE_MODES",
    "INPUT_CONTRACT",
    "MIN_AUTOLINK_CONFIDENCE",
    "NON_CLAIMS",
    "OUTPUT_CONTRACT",
    "SCHEMA_VERSION",
    "build_asset_identity_reuse_graph",
)
