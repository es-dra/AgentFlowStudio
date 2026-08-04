"""Narrow revision-scoped bindings between candidate-fact IDs and Script Core assets.

DRAFT OF PRODUCTION BRIDGE (2026-08-04)
---------------------------------------
This is intentionally NOT a full lifecycle sync between Script Core Truth and
the candidate confirmation ledger. Those systems differ in minting, confirmation,
and supersede semantics (see docs/internal-notes/scene-cast-and-id-bridge-20260804.md).

Rules
-----
1. Bind only after human confirmation of Character ``identity.display_name``,
   Scene ``scene.name``, or Scene-owned ``scene[...].props[N].name``.
2. Match Script Core assets on the same revision by exact display_name + type;
   if none, leave unbound (never invent an asset).
3. Bidirectional lookup over *active* bindings only.
4. Supersede updates authoritative_fact_id on the same entity_id/field_path/revision.
5. Revision change marks prior-revision bindings stale.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from agentflow.harness.json_io import write_json
from apps.api.runtime_candidate_fact_status import AuthoritativeScriptFact
from apps.api.runtime_store import RuntimeStore, read_json, reject_unsafe_payload, safe_id


BINDINGS_SCHEMA_VERSION = "afs.entity_asset_bindings.v0.1"
ARTIFACT_TYPE = "afs_entity_asset_bindings"
BindKind = Literal["human_confirmation"]
BindingStatus = Literal["active", "stale"]


class EntityAssetBinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    binding_id: str = Field(min_length=1, max_length=120)
    project_id: str = Field(min_length=1, max_length=128)
    revision_id: str = Field(min_length=1, max_length=120)
    entity_kind: Literal["character", "scene"]
    entity_id: str = Field(min_length=1, max_length=120)
    field_path: str = Field(min_length=1, max_length=160)
    authoritative_fact_id: str = Field(min_length=1, max_length=120)
    core_asset_id: str = Field(min_length=1, max_length=120)
    bind_kind: BindKind = "human_confirmation"
    status: BindingStatus = "active"
    bound_at: datetime
    display_name: str = Field(min_length=1, max_length=200)


class EntityAssetBindingStore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(default=BINDINGS_SCHEMA_VERSION)
    artifact_type: str = Field(default=ARTIFACT_TYPE)
    project_id: str
    bindings: list[EntityAssetBinding] = Field(default_factory=list)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def _bindings_dir(store: RuntimeStore, project_id: str) -> Path:
    return store.projects_dir / safe_id(project_id) / "entity_asset_bindings"


def _bindings_path(store: RuntimeStore, project_id: str) -> Path:
    return _bindings_dir(store, project_id) / "bindings.json"


def load_bindings(store: RuntimeStore, project_id: str) -> EntityAssetBindingStore:
    path = _bindings_path(store, project_id)
    if not path.exists():
        return EntityAssetBindingStore(project_id=project_id)
    payload = read_json(path)
    return EntityAssetBindingStore.model_validate(payload)


def save_bindings(store: RuntimeStore, bindings: EntityAssetBindingStore) -> None:
    path = _bindings_path(store, bindings.project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = bindings.model_dump(mode="json")
    reject_unsafe_payload(payload)
    write_json(path, payload)


def _truth_assets(store: RuntimeStore, project_id: str) -> dict[str, Any]:
    path = store.projects_dir / safe_id(project_id) / "script_core_truth" / "truth_state.json"
    if not path.exists():
        return {}
    payload = read_json(path)
    assets = payload.get("assets")
    return assets if isinstance(assets, dict) else {}


def _bindable_asset_type(fact: AuthoritativeScriptFact) -> str | None:
    if fact.entity_kind == "character" and fact.field_path == "identity.display_name":
        return "character"
    if fact.entity_kind == "scene" and fact.field_path == "scene.name":
        return "main_scene"
    if fact.entity_kind == "scene" and re.fullmatch(
        r"scene\[.+\]\.props\[\d+\]\.name",
        fact.field_path,
    ):
        return "prop"
    return None


def find_matching_core_asset(
    store: RuntimeStore,
    *,
    project_id: str,
    revision_id: str,
    asset_type: str,
    display_name: str,
) -> dict[str, Any] | None:
    label = display_name.strip()
    if not label:
        return None
    matches: list[dict[str, Any]] = []
    for asset in _truth_assets(store, project_id).values():
        if not isinstance(asset, dict):
            continue
        if str(asset.get("revision_id") or "") != revision_id:
            continue
        if str(asset.get("asset_type") or "") != asset_type:
            continue
        if str(asset.get("status") or "") in {"retired", "undone"}:
            continue
        asset_label = str(asset.get("display_name") or asset.get("name") or "").strip()
        if asset_label != label:
            continue
        matches.append(asset)
    if len(matches) != 1:
        # Zero or ambiguous — fail closed, do not guess.
        return None
    return matches[0]


def bind_authoritative_fact_to_core_asset(
    store: RuntimeStore,
    fact: AuthoritativeScriptFact,
) -> EntityAssetBinding | None:
    """Create/update an active binding when a unique Core asset match exists."""

    asset_type = _bindable_asset_type(fact)
    if asset_type is None:
        return None
    bindings = load_bindings(store, fact.project_id)
    active_slot_bindings = [
        row
        for row in bindings.bindings
        if row.status == "active"
        and row.revision_id == fact.source_revision_id
        and row.entity_id == fact.entity_id
        and row.field_path == fact.field_path
    ]
    asset = find_matching_core_asset(
        store,
        project_id=fact.project_id,
        revision_id=fact.source_revision_id,
        asset_type=asset_type,
        display_name=fact.text,
    )
    if asset is None:
        if active_slot_bindings:
            for row in active_slot_bindings:
                row.status = "stale"
            save_bindings(store, bindings)
        return None

    when = _now()
    existing = active_slot_bindings[-1] if active_slot_bindings else None
    if existing is not None:
        for duplicate in active_slot_bindings[:-1]:
            duplicate.status = "stale"
        existing.authoritative_fact_id = fact.authoritative_fact_id
        existing.core_asset_id = str(asset["asset_id"])
        existing.display_name = fact.text
        existing.bound_at = when
        save_bindings(store, bindings)
        return existing

    row = EntityAssetBinding(
        binding_id=_id("bind"),
        project_id=fact.project_id,
        revision_id=fact.source_revision_id,
        entity_kind=fact.entity_kind,  # type: ignore[arg-type]
        entity_id=fact.entity_id,
        field_path=fact.field_path,
        authoritative_fact_id=fact.authoritative_fact_id,
        core_asset_id=str(asset["asset_id"]),
        bound_at=when,
        display_name=fact.text,
    )
    bindings.bindings.append(row)
    save_bindings(store, bindings)
    return row


def lookup_asset_id_for_entity(
    store: RuntimeStore,
    *,
    project_id: str,
    entity_id: str,
    revision_id: str | None = None,
    field_path: str | None = None,
) -> list[EntityAssetBinding]:
    bindings = load_bindings(store, project_id)
    rows = [
        row
        for row in bindings.bindings
        if row.status == "active" and row.entity_id == entity_id
    ]
    if revision_id:
        rows = [row for row in rows if row.revision_id == revision_id]
    if field_path:
        rows = [row for row in rows if row.field_path == field_path]
    return rows


def lookup_entity_for_asset_id(
    store: RuntimeStore,
    *,
    project_id: str,
    core_asset_id: str,
    revision_id: str | None = None,
) -> list[EntityAssetBinding]:
    bindings = load_bindings(store, project_id)
    rows = [
        row
        for row in bindings.bindings
        if row.status == "active" and row.core_asset_id == core_asset_id
    ]
    if revision_id:
        rows = [row for row in rows if row.revision_id == revision_id]
    return rows


def mark_bindings_stale_for_revision_change(
    store: RuntimeStore,
    *,
    project_id: str,
    new_revision_id: str,
) -> int:
    bindings = load_bindings(store, project_id)
    changed = 0
    for row in bindings.bindings:
        if row.status != "active":
            continue
        if row.revision_id == new_revision_id:
            continue
        row.status = "stale"
        changed += 1
    if changed:
        save_bindings(store, bindings)
    return changed


__all__ = (
    "BINDINGS_SCHEMA_VERSION",
    "EntityAssetBinding",
    "EntityAssetBindingStore",
    "bind_authoritative_fact_to_core_asset",
    "find_matching_core_asset",
    "load_bindings",
    "lookup_asset_id_for_entity",
    "lookup_entity_for_asset_id",
    "mark_bindings_stale_for_revision_change",
    "save_bindings",
)
