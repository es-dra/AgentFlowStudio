"""Non-authoritative scene-name normalization proposals.

Mirrors character alias-link proposals:
  - feature-flagged
  - status=candidate, authority=non_authoritative_proposal
  - never merges main_scene names or writes Production Graph

Safe rules (conservative):
  - both names must already be extracted main_scene candidates
  - shorter name is a contiguous prefix or suffix of the longer name
  - shorter name does not prefix/suffix-match any other extracted scene
  - shorter name length >= 2

Cases that are continuous mid-substrings only (e.g. 合租屋客厅 vs
顾晚合租屋的客厅 with an intervening 的) are intentionally not proposed.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


SCENE_NAME_NORMALIZATION_PROPOSAL_SCHEMA_VERSION = "afs.scene_name_normalization_proposal.v0.1"
_MIN_SHORT_LEN = 2


def build_scene_name_normalization_proposals(source_text: str, scenes: list[Any]) -> list[dict[str, Any]]:
    """Build non-authoritative scene full-name/short-name link proposals.

    These proposals never mutate scene assets and never collapse identities.
    Human review must call the explicit core asset merge_scene_name command.
    """
    facts = _scene_facts(scenes)
    if len(facts) < 2:
        return []

    names = [item["name"] for item in facts]
    proposals: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for short in names:
        if len(short) < _MIN_SHORT_LEN:
            continue
        longs = [
            long
            for long in names
            if long != short and len(long) > len(short) and _is_prefix_or_suffix(short, long)
        ]
        if len(longs) != 1:
            # Ambiguous (matches multiple longs) or no match → no proposal.
            continue
        long = longs[0]
        key = (long, short)
        if key in seen:
            continue
        seen.add(key)

        short_fact = next(item for item in facts if item["name"] == short)
        long_fact = next(item for item in facts if item["name"] == long)
        evidence_spans = [
            _span(source_text, long_fact["start"], long_fact["end"]),
            _span(source_text, short_fact["start"], short_fact["end"]),
        ]
        proposal_identity = {
            "schema_version": SCENE_NAME_NORMALIZATION_PROPOSAL_SCHEMA_VERSION,
            "canonical_scene_name": long,
            "variant_scene_name": short,
            "method": "scene_name_prefix_or_suffix_unique",
        }
        proposals.append(
            {
                "proposal_id": f"scenenorm_{_sha256_json(proposal_identity)[:20]}",
                "schema_version": SCENE_NAME_NORMALIZATION_PROPOSAL_SCHEMA_VERSION,
                "relation_type": "scene_name_normalization",
                "status": "candidate",
                "authority": "non_authoritative_proposal",
                "canonical_scene_name": long,
                "variant_scene_name": short,
                "confidence": 0.82,
                "evidence_spans": evidence_spans[:12],
                "extraction_method": "scene_name_prefix_or_suffix_unique",
                "review_action": "use_core_asset_command_merge_scene_name",
                "provider_dispatch_count": 0,
                "remote_dispatch_count": 0,
            }
        )

    return sorted(
        proposals,
        key=lambda item: (item["canonical_scene_name"], item["variant_scene_name"], item["extraction_method"]),
    )


def _is_prefix_or_suffix(short: str, long: str) -> bool:
    return long.startswith(short) or long.endswith(short)


def _scene_facts(scenes: list[Any]) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in scenes:
        name = str(getattr(item, "value", "") or "").strip()
        if not name or name in seen:
            continue
        seen.add(name)
        facts.append(
            {
                "name": name,
                "start": int(getattr(item, "start", 0) or 0),
                "end": int(getattr(item, "end", 0) or 0),
            }
        )
    return facts


def _span(source_text: str, start: int, end: int) -> dict[str, Any]:
    start = max(0, min(start, len(source_text)))
    end = max(start, min(end, len(source_text)))
    return {"start": start, "end": end, "quote": source_text[start:end]}


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


__all__ = (
    "SCENE_NAME_NORMALIZATION_PROPOSAL_SCHEMA_VERSION",
    "build_scene_name_normalization_proposals",
)
