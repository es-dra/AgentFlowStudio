from __future__ import annotations

import json
from typing import Any


def reject_unsafe_markers(payload: dict[str, Any], unsafe_markers: tuple[str, ...]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False).lower()
    for marker in unsafe_markers:
        if marker and marker in serialized:
            raise ValueError("unsafe marker found in branch package fixture")


def validate_non_claims(
    non_claims: Any,
    *,
    owner: str,
    require_all: bool,
    protected_non_claims: set[str],
) -> None:
    if not isinstance(non_claims, dict):
        raise ValueError(f"{owner} non_claims must be present")
    if require_all:
        missing = sorted(protected_non_claims.difference(non_claims))
        if missing:
            raise ValueError(f"{owner} missing protected non-claims: {', '.join(missing)}")
    for claim in protected_non_claims:
        if claim in non_claims and non_claims[claim] is not False:
            raise ValueError(f"protected non-claim collapsed: {owner} {claim}")


def require_resolved_refs(values: list[Any], refs: set[str], *, owner: str, field: str) -> None:
    for value in values:
        require_resolved_ref(str(value), refs, owner=owner, field=field)


def require_resolved_ref(ref: str, refs: set[str], *, owner: str, field: str) -> None:
    if ref not in refs:
        raise ValueError(f"unresolved reference in {owner}.{field}: {ref}")


def required_list(payload: dict[str, Any], field: str) -> list[Any]:
    value = payload.get(field)
    if not isinstance(value, list) or not value:
        raise ValueError(f"missing required list: {field}")
    return value


def required_dict(payload: dict[str, Any], field: str) -> dict[str, Any]:
    value = payload.get(field)
    if not isinstance(value, dict):
        raise ValueError(f"missing required object: {field}")
    return value


def required_text(payload: dict[str, Any], field: str) -> str:
    value = str(payload.get(field) or "").strip()
    if not value:
        raise ValueError(f"missing required field: {field}")
    return value


def dict_items(items: list[Any], label: str) -> list[dict[str, Any]]:
    if not all(isinstance(item, dict) for item in items):
        raise ValueError(f"{label} entries must be JSON objects")
    return items
