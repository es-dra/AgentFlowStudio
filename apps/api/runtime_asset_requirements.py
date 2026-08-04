"""Derived Scene asset requirements (read-only projection).

Not a CandidateFact entity_kind. Rows are projected from already-confirmed
Scene→Character cast appearances / Scene→Prop ownership plus optional
entity↔Script Core bindings.

See docs/internal-notes/asset-requirement-derived-view-20260804.md.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from apps.api.runtime_candidate_fact_status import AuthoritativeScriptFact
from apps.api.runtime_entity_asset_bindings import lookup_asset_id_for_entity
from apps.api.runtime_store import RuntimeStore

CAST_APPEARANCE_PATH = re.compile(
    r"^scene\[(?P<scene_id>.+)\]\.cast\[(?P<order_index>\d+)\]\.appearance$"
)
PROP_FIELD_PATH = re.compile(
    r"^scene\[(?P<scene_id>.+)\]\.props\[(?P<order_index>\d+)\]\."
    r"(?P<slot>name|importance)$"
)

UNBOUND_NOTE = "暂无 Core asset 绑定"
AssetKind = Literal["character", "prop"]
ScopeKind = Literal["scene"]
BindingStatus = Literal["bound", "unbound"]


class SceneCharacterAssetRequirement(BaseModel):
    """One derived character-asset need for a confirmed Scene cast membership."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["asset_requirement"] = "asset_requirement"
    requirement_id: str = Field(min_length=1, max_length=120)
    scope_kind: ScopeKind = "scene"
    scope_entity_id: str = Field(min_length=1, max_length=120)
    scope_display_name: str | None = Field(default=None, max_length=200)
    asset_kind: AssetKind = "character"
    character_entity_id: str = Field(min_length=1, max_length=120)
    display_name: str = Field(min_length=1, max_length=200)
    order_index: int = Field(ge=0)
    source_cast_authoritative_fact_id: str = Field(min_length=1, max_length=120)
    source_cast_field_path: str = Field(min_length=1, max_length=160)
    source_revision_id: str = Field(min_length=1, max_length=120)
    core_asset_id: str | None = Field(default=None, max_length=120)
    core_asset_binding_status: BindingStatus
    core_asset_binding_note: str | None = Field(default=None, max_length=200)


class ScenePropAssetRequirement(BaseModel):
    """One derived prop-asset need for a confirmed Scene prop name."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["asset_requirement"] = "asset_requirement"
    requirement_id: str = Field(min_length=1, max_length=120)
    scope_kind: ScopeKind = "scene"
    scope_entity_id: str = Field(min_length=1, max_length=120)
    scope_display_name: str | None = Field(default=None, max_length=200)
    asset_kind: Literal["prop"] = "prop"
    display_name: str = Field(min_length=1, max_length=200)
    importance: str | None = Field(default=None, max_length=2000)
    order_index: int = Field(ge=0)
    source_prop_authoritative_fact_id: str = Field(min_length=1, max_length=120)
    source_prop_field_path: str = Field(min_length=1, max_length=160)
    source_importance_authoritative_fact_id: str | None = Field(
        default=None,
        max_length=120,
    )
    source_revision_id: str = Field(min_length=1, max_length=120)
    core_asset_id: str | None = Field(default=None, max_length=120)
    core_asset_binding_status: BindingStatus
    core_asset_binding_note: str | None = Field(default=None, max_length=200)


SceneAssetRequirement = SceneCharacterAssetRequirement | ScenePropAssetRequirement


def _requirement_id(
    *,
    revision_id: str,
    scene_entity_id: str,
    character_entity_id: str,
) -> str:
    digest = hashlib.sha256(
        f"{revision_id}|{scene_entity_id}|{character_entity_id}|character".encode()
    ).hexdigest()[:20]
    return f"areq_{digest}"


def _parse_cast_appearance(field_path: str) -> tuple[str, int] | None:
    match = CAST_APPEARANCE_PATH.fullmatch(field_path)
    if not match:
        return None
    return match.group("scene_id"), int(match.group("order_index"))


def _parse_prop_field(field_path: str) -> tuple[str, int, str] | None:
    match = PROP_FIELD_PATH.fullmatch(field_path)
    if not match:
        return None
    return (
        match.group("scene_id"),
        int(match.group("order_index")),
        match.group("slot"),
    )


def _binding_state(
    store: RuntimeStore | None,
    *,
    project_id: str,
    entity_id: str,
    revision_id: str,
    field_path: str,
    authoritative_fact_id: str | None = None,
    display_name: str | None = None,
) -> tuple[str | None, BindingStatus, str | None]:
    if store is None:
        return None, "unbound", UNBOUND_NOTE
    bindings = lookup_asset_id_for_entity(
        store,
        project_id=project_id,
        entity_id=entity_id,
        revision_id=revision_id,
        field_path=field_path,
    )
    if authoritative_fact_id is not None:
        bindings = [
            row
            for row in bindings
            if row.authoritative_fact_id == authoritative_fact_id
        ]
    if display_name is not None:
        bindings = [row for row in bindings if row.display_name == display_name]
    if len(bindings) == 1:
        return bindings[0].core_asset_id, "bound", None
    if len(bindings) > 1:
        return (
            None,
            "unbound",
            "暂无 Core asset 绑定（同 revision 存在多条 field-path 绑定）",
        )
    return None, "unbound", UNBOUND_NOTE


def _prop_requirement_id(
    *,
    revision_id: str,
    scene_entity_id: str,
    prop_field_path: str,
) -> str:
    digest = hashlib.sha256(
        f"{revision_id}|{scene_entity_id}|{prop_field_path}|prop".encode()
    ).hexdigest()[:20]
    return f"areq_{digest}"


def project_scene_asset_requirements(
    store: RuntimeStore | None,
    *,
    project_id: str,
    authoritative_facts: list[AuthoritativeScriptFact],
    revision_id: str | None = None,
) -> list[SceneAssetRequirement]:
    """Project Scene asset needs only from active authoritative ownership facts."""

    if not authoritative_facts:
        return []

    scene_names = {
        fact.entity_id: fact.text
        for fact in authoritative_facts
        if fact.entity_kind == "scene" and fact.field_path == "scene.name"
        and (revision_id is None or fact.source_revision_id == revision_id)
    }
    prop_importance: dict[tuple[str, int, str], AuthoritativeScriptFact] = {}
    for fact in authoritative_facts:
        if fact.entity_kind != "scene":
            continue
        parsed = _parse_prop_field(fact.field_path)
        if parsed is None or parsed[2] != "importance":
            continue
        if fact.entity_id != parsed[0]:
            continue
        if revision_id and fact.source_revision_id != revision_id:
            continue
        prop_importance[(parsed[0], parsed[1], fact.source_revision_id)] = fact

    rows: list[SceneAssetRequirement] = []
    for fact in authoritative_facts:
        if revision_id and fact.source_revision_id != revision_id:
            continue
        if fact.entity_kind == "character":
            parsed_cast = _parse_cast_appearance(fact.field_path)
            if parsed_cast is None:
                continue
            scene_entity_id, order_index = parsed_cast
            core_asset_id, binding_status, binding_note = _binding_state(
                store,
                project_id=project_id,
                entity_id=fact.entity_id,
                revision_id=fact.source_revision_id,
                field_path="identity.display_name",
                display_name=fact.text,
            )
            rows.append(
                SceneCharacterAssetRequirement(
                    requirement_id=_requirement_id(
                        revision_id=fact.source_revision_id,
                        scene_entity_id=scene_entity_id,
                        character_entity_id=fact.entity_id,
                    ),
                    scope_entity_id=scene_entity_id,
                    scope_display_name=scene_names.get(scene_entity_id),
                    character_entity_id=fact.entity_id,
                    display_name=fact.text,
                    order_index=order_index,
                    source_cast_authoritative_fact_id=fact.authoritative_fact_id,
                    source_cast_field_path=fact.field_path,
                    source_revision_id=fact.source_revision_id,
                    core_asset_id=core_asset_id,
                    core_asset_binding_status=binding_status,
                    core_asset_binding_note=binding_note,
                )
            )
            continue

        if fact.entity_kind != "scene":
            continue
        parsed_prop = _parse_prop_field(fact.field_path)
        if parsed_prop is None or parsed_prop[2] != "name":
            continue
        scene_entity_id, order_index, _ = parsed_prop
        if fact.entity_id != scene_entity_id:
            continue
        importance_fact = prop_importance.get(
            (scene_entity_id, order_index, fact.source_revision_id)
        )
        core_asset_id, binding_status, binding_note = _binding_state(
            store,
            project_id=project_id,
            entity_id=fact.entity_id,
            revision_id=fact.source_revision_id,
            field_path=fact.field_path,
            authoritative_fact_id=fact.authoritative_fact_id,
            display_name=fact.text,
        )
        rows.append(
            ScenePropAssetRequirement(
                requirement_id=_prop_requirement_id(
                    revision_id=fact.source_revision_id,
                    scene_entity_id=scene_entity_id,
                    prop_field_path=fact.field_path,
                ),
                scope_entity_id=scene_entity_id,
                scope_display_name=scene_names.get(scene_entity_id),
                display_name=fact.text,
                importance=importance_fact.text if importance_fact else None,
                order_index=order_index,
                source_prop_authoritative_fact_id=fact.authoritative_fact_id,
                source_prop_field_path=fact.field_path,
                source_importance_authoritative_fact_id=(
                    importance_fact.authoritative_fact_id if importance_fact else None
                ),
                source_revision_id=fact.source_revision_id,
                core_asset_id=core_asset_id,
                core_asset_binding_status=binding_status,
                core_asset_binding_note=binding_note,
            )
        )

    rows.sort(
        key=lambda row: (
            row.scope_display_name or row.scope_entity_id,
            row.asset_kind,
            row.order_index,
            row.display_name,
        )
    )
    return rows


def project_scene_character_asset_requirements(
    store: RuntimeStore | None,
    *,
    project_id: str,
    authoritative_facts: list[AuthoritativeScriptFact],
    revision_id: str | None = None,
) -> list[SceneCharacterAssetRequirement]:
    """Backward-compatible character-only slice of the Scene projection."""

    return [
        row
        for row in project_scene_asset_requirements(
            store,
            project_id=project_id,
            authoritative_facts=authoritative_facts,
            revision_id=revision_id,
        )
        if isinstance(row, SceneCharacterAssetRequirement)
    ]


def asset_requirements_payload(
    rows: list[SceneAssetRequirement],
) -> list[dict[str, Any]]:
    return [row.model_dump(mode="json") for row in rows]


__all__ = (
    "UNBOUND_NOTE",
    "SceneAssetRequirement",
    "SceneCharacterAssetRequirement",
    "ScenePropAssetRequirement",
    "asset_requirements_payload",
    "project_scene_asset_requirements",
    "project_scene_character_asset_requirements",
)
