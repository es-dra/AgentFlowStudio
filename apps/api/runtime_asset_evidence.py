from __future__ import annotations

from typing import Any, Iterable, Mapping

from apps.api.runtime_store import safe_id


SUPPORTED_SOURCE_TYPES = {
    "occurrence_ledger",
    "applied_shot_plan",
    "script_revision",
}


def canonicalize_source_evidence(
    values: Iterable[Any],
    *,
    asset_id: str = "",
    max_records: int = 12,
) -> list[dict[str, Any]]:
    canonical_asset_id = strict_stable_id(asset_id)
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for value in values:
        if not isinstance(value, Mapping):
            continue
        source_type = str(value.get("source_type") or "").strip()
        source_id = strict_stable_id(value.get("source_id"))
        if source_type not in SUPPORTED_SOURCE_TYPES or not source_id:
            continue
        if (
            source_type == "occurrence_ledger"
            and canonical_asset_id
            and source_id != canonical_asset_id
        ):
            continue
        excerpt = str(value.get("excerpt") or "").strip()[:240]
        key = (source_type, source_id, excerpt)
        evidence = grouped.setdefault(
            key,
            {
                "source_type": source_type,
                "source_id": source_id,
                "excerpt": excerpt,
                "scene_ids": set(),
                "shot_ids": set(),
            },
        )
        evidence["scene_ids"].update(strict_stable_ids(value.get("scene_ids"), limit=80))
        evidence["shot_ids"].update(strict_stable_ids(value.get("shot_ids"), limit=160))
    result = []
    for key in sorted(
        grouped,
        key=lambda item: (
            0 if item[0] == "occurrence_ledger" else 1,
            item,
        ),
    )[:max_records]:
        evidence = grouped[key]
        result.append(
            {
                "source_type": evidence["source_type"],
                "source_id": evidence["source_id"],
                "excerpt": evidence["excerpt"],
                "scene_ids": sorted(evidence["scene_ids"])[:80],
                "shot_ids": sorted(evidence["shot_ids"])[:160],
            }
        )
    return result


def authoritative_source_evidence(
    asset: Mapping[str, Any],
    known_shot_ids: set[str],
) -> tuple[set[str], list[dict[str, Any]]]:
    asset_id = strict_stable_id(asset.get("stable_id"))
    known = {token for item in known_shot_ids if (token := strict_stable_id(item))}
    occurrences = asset.get("occurrences") if isinstance(asset.get("occurrences"), Mapping) else {}
    occurrence_shot_ids = strict_stable_ids(
        occurrences.get("shot_ids"),
        limit=160,
    ) & known
    traceable_shot_ids: set[str] = set()
    records: list[dict[str, Any]] = []
    for evidence in canonicalize_source_evidence(
        asset.get("source_evidence", []),
        asset_id=asset_id,
    ):
        source_type = evidence["source_type"]
        source_id = evidence["source_id"]
        if source_type == "occurrence_ledger":
            if not asset_id or source_id != asset_id:
                continue
            evidence_shot_ids = set(evidence["shot_ids"]) & occurrence_shot_ids
        elif source_type == "applied_shot_plan":
            if source_id not in occurrence_shot_ids:
                continue
            evidence_shot_ids = set(evidence["shot_ids"]) & occurrence_shot_ids
            evidence_shot_ids.add(source_id)
        else:
            evidence_shot_ids = set()
        traceable_shot_ids.update(evidence_shot_ids)
        records.append(
            {
                "source_type": source_type,
                "source_id": source_id,
                "scene_ids": evidence["scene_ids"],
                "shot_ids": sorted(evidence_shot_ids),
            }
        )
    return traceable_shot_ids, records


def strict_stable_id(value: Any) -> str:
    raw = str(value or "").strip()
    return raw if raw and safe_id(raw) == raw else ""


def strict_stable_ids(value: Any, *, limit: int) -> set[str]:
    values = value if isinstance(value, list) else []
    return {
        token
        for item in values[:limit]
        if (token := strict_stable_id(item))
    }


__all__ = (
    "SUPPORTED_SOURCE_TYPES",
    "authoritative_source_evidence",
    "canonicalize_source_evidence",
    "strict_stable_id",
    "strict_stable_ids",
)
