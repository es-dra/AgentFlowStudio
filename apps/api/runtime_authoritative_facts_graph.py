"""Optional Production Graph feed from AuthoritativeScriptFact (feature-flagged).

Gate: AFS_CANDIDATE_FACTS_FEED_PRODUCTION_GRAPH (default off).

When enabled, confirmed authoritative character/scene/script-profile/beat facts
can be appended as graph nodes via ProductionGraphStore.append. This does NOT
replace the M6 confirm → compile_film_candidate path; it is an independent side
channel.

Only AuthoritativeScriptFact values are accepted — never CandidateFact /
missing / conflicting rows.
"""

from __future__ import annotations

import os
import re
from typing import Any, Mapping

from apps.api.runtime_candidate_fact_status import AuthoritativeScriptFact
from apps.api.runtime_production_graph import (
    GraphVersionConflict,
    ProductionGraphError,
    ProductionGraphStore,
    canonical_digest,
)


FEED_PRODUCTION_GRAPH_ENV = "AFS_CANDIDATE_FACTS_FEED_PRODUCTION_GRAPH"
NAMESPACED_REVISION_NODES_ENV = "AFS_CANDIDATE_FACTS_USE_NAMESPACED_REVISION_NODES"
FEED_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def candidate_facts_feed_production_graph_enabled(env: Mapping[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return str(values.get(FEED_PRODUCTION_GRAPH_ENV, "")).strip().lower() in FEED_TRUE_VALUES


def namespaced_revision_nodes_enabled(env: Mapping[str, str] | None = None) -> bool:
    values = env if env is not None else os.environ
    return str(values.get(NAMESPACED_REVISION_NODES_ENV, "")).strip().lower() in FEED_TRUE_VALUES


def authoritative_fact_graph_node_id(fact: AuthoritativeScriptFact) -> str:
    """Stable graph node id derived from the authoritative fact identity."""

    if fact.entity_kind in {"script_profile", "beat"}:
        facet_key = canonical_digest(
            {
                "entity_kind": fact.entity_kind,
                "entity_id": fact.entity_id,
                "field_path": fact.field_path,
            }
        )[:24]
        return f"authfact-{fact.entity_kind}-{facet_key}"
    return f"authfact-{fact.entity_kind}-{fact.authoritative_fact_id}"


def authoritative_revision_graph_node_id(
    fact: AuthoritativeScriptFact,
    env: Mapping[str, str] | None = None,
) -> str:
    """Keep Script Truth source identity distinct from an expanded M6 revision."""

    if namespaced_revision_nodes_enabled(env):
        return (
            f"scripttruth-revision-{fact.source_revision_id}-"
            f"{fact.source_revision_digest[:16]}"
        )
    return fact.source_revision_id


def compile_authoritative_facts_to_graph_events(
    facts: list[AuthoritativeScriptFact],
) -> list[dict[str, Any]]:
    """Compile authoritative facts into node_upserted / relation_upserted events.

    Hard rule: callers must pass only AuthoritativeScriptFact instances
    (already past promote_candidate_fact). No candidate-status re-check here.
    """

    if not facts:
        return []

    events: list[dict[str, Any]] = []
    revision_ids: set[str] = set()
    namespaced_revisions = namespaced_revision_nodes_enabled()

    for fact in facts:
        if not isinstance(fact, AuthoritativeScriptFact):
            raise TypeError("only AuthoritativeScriptFact may feed Production Graph")
        revision_ids.add(fact.source_revision_id)

    for revision_id in sorted(revision_ids):
        matching = [f for f in facts if f.source_revision_id == revision_id]
        digest = matching[0].source_revision_digest if matching else ""
        revision_node_id = authoritative_revision_graph_node_id(matching[0])
        metadata = {
            "source": "authoritative_script_fact_feed",
            "source_revision_id": revision_id,
            "source_revision_digest": digest,
        }
        if namespaced_revisions:
            metadata["node_identity_kind"] = "script_truth_revision_for_authoritative_facts"
        events.append(
            {
                "type": "node_upserted",
                "node": {
                    "node_id": revision_node_id,
                    "category": "revision",
                    "metadata": metadata,
                },
            }
        )

    for fact in facts:
        node_id = authoritative_fact_graph_node_id(fact)
        category = {
            "character": "entity",
            "scene": "location",
            "script_profile": "profile",
            "beat": "beat",
        }[fact.entity_kind]
        metadata: dict[str, Any] = {
            "source": "authoritative_script_fact_feed",
            "authoritative_fact_id": fact.authoritative_fact_id,
            "source_candidate_fact_id": fact.source_candidate_fact_id,
            "source_revision_id": fact.source_revision_id,
            "source_revision_digest": fact.source_revision_digest,
            "field_path": fact.field_path,
            "entity_kind": fact.entity_kind,
            "entity_id": fact.entity_id,
            "promotion_kind": fact.promotion_kind,
            "source_confidence": fact.source_confidence,
            "text": fact.text,
        }
        if fact.entity_kind == "character":
            metadata["display_name"] = fact.text
        elif fact.entity_kind == "scene":
            metadata["name"] = fact.text
        elif fact.entity_kind == "script_profile":
            metadata["value"] = fact.text
        else:
            metadata["boundary_label"] = fact.text
            ownership = re.fullmatch(
                r"scene\[(?P<scene_id>.+)\]\.beats\[(?P<order_index>\d+)\]\.boundary",
                fact.field_path,
            )
            if ownership:
                metadata["parent_scene_id"] = ownership.group("scene_id")
                metadata["order_index"] = int(ownership.group("order_index"))
        if fact.human_confirmed_by:
            metadata["human_confirmed_by"] = fact.human_confirmed_by
        if fact.deterministic_check_id:
            metadata["deterministic_check_id"] = fact.deterministic_check_id

        events.append({"type": "node_upserted", "node": {"node_id": node_id, "category": category, "metadata": metadata}})
        events.append(
            {
                "type": "relation_upserted",
                "from_id": authoritative_revision_graph_node_id(fact),
                "to_id": node_id,
                "relation_type": "derived_from",
            }
        )
    return events


def feed_authoritative_facts_to_production_graph(
    graph_store: ProductionGraphStore,
    project_id: str,
    facts: list[AuthoritativeScriptFact],
) -> dict[str, Any]:
    """Append authoritative facts to Production Graph when the feed gate is on.

    Returns a small result dict. When the gate is off, returns skipped without
    touching the graph.
    """

    if not candidate_facts_feed_production_graph_enabled():
        return {
            "fed": False,
            "skipped": True,
            "reason": f"{FEED_PRODUCTION_GRAPH_ENV}_disabled",
            "node_ids": [],
            "graph_version": None,
        }
    if not facts:
        return {
            "fed": False,
            "skipped": True,
            "reason": "no_authoritative_facts",
            "node_ids": [],
            "graph_version": None,
        }

    events = compile_authoritative_facts_to_graph_events(facts)
    node_ids = [authoritative_fact_graph_node_id(f) for f in facts]
    namespaced_revisions = namespaced_revision_nodes_enabled()
    revision_node_ids = sorted({authoritative_revision_graph_node_id(f) for f in facts})
    semantic = canonical_digest(
        {
            "feed": "authoritative_script_facts",
            "fact_ids": sorted(f.authoritative_fact_id for f in facts),
            "texts": sorted(f.text for f in facts),
            "revision_node_ids": revision_node_ids,
        }
    )
    # One idempotency key per fact set write; single-fact writes use fact id.
    if len(facts) == 1:
        prefix = "authfact-feed-v2" if namespaced_revisions else "authfact-feed"
        idempotency_key = f"{prefix}-{facts[0].authoritative_fact_id}"
    else:
        prefix = "authfact-feed-v2" if namespaced_revisions else "authfact-feed"
        idempotency_key = f"{prefix}-{semantic[:24]}"

    graph = graph_store.ensure(project_id)
    try:
        updated = graph_store.append(
            project_id,
            expected_version=int(graph.get("version") or 0),
            idempotency_key=idempotency_key,
            semantic_digest=semantic,
            events=events,
        )
    except GraphVersionConflict:
        # One retry after reload — enough for local sequential confirm paths.
        graph = graph_store.load(project_id)
        updated = graph_store.append(
            project_id,
            expected_version=int(graph.get("version") or 0),
            idempotency_key=idempotency_key,
            semantic_digest=semantic,
            events=events,
        )
    except ProductionGraphError:
        raise

    return {
        "fed": True,
        "skipped": False,
        "reason": None,
        "node_ids": node_ids,
        "graph_version": updated.get("version"),
        "idempotent_replay": bool(updated.get("idempotent_replay")),
        "affects_production_graph": True,
    }


__all__ = (
    "FEED_PRODUCTION_GRAPH_ENV",
    "NAMESPACED_REVISION_NODES_ENV",
    "candidate_facts_feed_production_graph_enabled",
    "namespaced_revision_nodes_enabled",
    "authoritative_fact_graph_node_id",
    "authoritative_revision_graph_node_id",
    "compile_authoritative_facts_to_graph_events",
    "feed_authoritative_facts_to_production_graph",
)
