"""Derived Scene character asset requirements (read-only projection).

Not a CandidateFact entity_kind. Rows are projected from already-confirmed
Scene→Character cast appearances plus optional entity↔Script Core bindings.

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

UNBOUND_NOTE = "暂无 Core asset 绑定"
AssetKind = Literal["character"]
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


def project_scene_character_asset_requirements(
    store: RuntimeStore | None,
    *,
    project_id: str,
    authoritative_facts: list[AuthoritativeScriptFact],
    revision_id: str | None = None,
) -> list[SceneCharacterAssetRequirement]:
    """Project character asset needs from confirmed Scene cast appearances.

    Props / Beat scopes are intentionally omitted until those foundations exist.
    """

    if not authoritative_facts:
        return []

    scene_names = {
        fact.entity_id: fact.text
        for fact in authoritative_facts
        if fact.entity_kind == "scene" and fact.field_path == "scene.name"
    }

    rows: list[SceneCharacterAssetRequirement] = []
    for fact in authoritative_facts:
        if fact.entity_kind != "character":
            continue
        parsed = _parse_cast_appearance(fact.field_path)
        if parsed is None:
            continue
        scene_entity_id, order_index = parsed
        if revision_id and fact.source_revision_id != revision_id:
            continue

        core_asset_id: str | None = None
        binding_status: BindingStatus = "unbound"
        binding_note: str | None = UNBOUND_NOTE
        if store is not None:
            bindings = lookup_asset_id_for_entity(
                store,
                project_id=project_id,
                entity_id=fact.entity_id,
                revision_id=fact.source_revision_id,
                field_path="identity.display_name",
            )
            if len(bindings) == 1:
                core_asset_id = bindings[0].core_asset_id
                binding_status = "bound"
                binding_note = None
            elif len(bindings) > 1:
                # Ambiguous active bindings — fail closed, do not pick one.
                binding_note = "暂无 Core asset 绑定（同 revision 存在多条 identity 绑定）"

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

    rows.sort(
        key=lambda row: (
            row.scope_display_name or row.scope_entity_id,
            row.order_index,
            row.display_name,
        )
    )
    return rows


def asset_requirements_payload(
    rows: list[SceneCharacterAssetRequirement],
) -> list[dict[str, Any]]:
    return [row.model_dump(mode="json") for row in rows]


__all__ = (
    "UNBOUND_NOTE",
    "SceneCharacterAssetRequirement",
    "asset_requirements_payload",
    "project_scene_character_asset_requirements",
)
