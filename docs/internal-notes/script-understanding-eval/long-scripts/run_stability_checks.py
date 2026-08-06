#!/usr/bin/env python3
"""Collect long-script runtime stability observations (free / mock-LLM).

COST: default path uses a mock judge — zero remote LLM calls.
Optional --live-smoke issues one budget-capped paid call on a single script.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import traceback
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.api.runtime_script_alias_proposals import build_alias_link_proposals  # noqa: E402
from apps.api.runtime_script_candidate_extraction import (  # noqa: E402
    extract_characters,
    extract_scenes,
)
from apps.api.runtime_script_indirect_mention_discovery import (  # noqa: E402
    discover_indirect_mention_candidates,
)
from apps.api.runtime_script_indirect_mention_proposals import (  # noqa: E402
    build_indirect_mention_proposals,
)
from apps.api.runtime_script_scene_name_normalization import (  # noqa: E402
    build_scene_name_normalization_proposals,
)


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a JSON object")
    return data


def _sha(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_discovery(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "mention": item.get("mention"),
            "start": item.get("start"),
            "end": item.get("end"),
            "discovery_method": item.get("discovery_method"),
            "discovery_methods": list(item.get("discovery_methods") or []),
            "occurrence_count": item.get("occurrence_count"),
            "already_extracted_as_character": bool(item.get("already_extracted_as_character")),
        }
        for item in items
    ]


def _canonical_proposals(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "proposal_id": item.get("proposal_id"),
            "relation_type": item.get("relation_type"),
            "target_display_name": item.get("target_display_name"),
            "alias": item.get("alias"),
            "canonical_scene_name": item.get("canonical_scene_name"),
            "variant_scene_name": item.get("variant_scene_name"),
            "method": item.get("method") or item.get("extraction_method"),
            "confidence": item.get("confidence"),
        }
        for item in items
    ]


def _facts(items: list[Any]) -> list[dict[str, Any]]:
    return [{"value": item.value, "start": item.start, "end": item.end, "method": item.method} for item in items]


def _mock_judge(text: str, mention: str, output_dir: Path) -> dict[str, Any]:
    # Deterministic mock: person-shaped short CJK → refers=true, present=false.
    # Not an accuracy oracle — only exercises budget/dispatch plumbing.
    looks_person = 2 <= len(mention) <= 4 and all("\u4e00" <= ch <= "\u9fff" for ch in mention)
    return {
        "refers_to_real_character": looks_person,
        "refers_to_real_character_confidence": 0.5,
        "refers_to_real_character_reason": "mock",
        "is_present_in_scene": False,
        "is_present_in_scene_confidence": 1.0,
        "is_present_in_scene_reason": "mock",
        "is_indirect_mention": bool(looks_person),
    }


def _observe_script(script: dict[str, Any], *, repo: Path, budget_max_calls: int, determinism_runs: int) -> dict[str, Any]:
    script_id = str(script["id"])
    path = repo / str(script["path"])
    record: dict[str, Any] = {
        "id": script_id,
        "label": script.get("label"),
        "kind": script.get("kind"),
        "path": str(script["path"]),
        "errors": [],
        "crashed": False,
    }
    try:
        source = path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        record["crashed"] = True
        record["errors"].append(f"read_failed: {type(exc).__name__}: {exc}")
        return record

    record["char_count"] = len(source)
    digests_free: list[str] = []
    discovery_counts: list[int] = []
    try:
        for _ in range(max(2, int(determinism_runs))):
            discoveries = discover_indirect_mention_candidates(source)
            characters = extract_characters(source)
            scenes = extract_scenes(source)
            aliases = build_alias_link_proposals(source, characters)
            scene_norms = build_scene_name_normalization_proposals(source, scenes)
            bundle = {
                "discovery": _canonical_discovery(discoveries),
                "characters": _facts(characters),
                "scenes": _facts(scenes),
                "alias_proposals": _canonical_proposals(aliases),
                "scene_name_normalization_proposals": _canonical_proposals(scene_norms),
            }
            digests_free.append(_sha(bundle))
            discovery_counts.append(len(discoveries))
        record["free_path_digests"] = digests_free
        record["free_path_deterministic"] = len(set(digests_free)) == 1
        record["discovery_count"] = discovery_counts[0]
        record["discovery_counts_across_runs"] = discovery_counts
        record["discovery_per_1k_chars"] = round(
            (discovery_counts[0] / max(len(source), 1)) * 1000.0, 6
        )
        record["character_count"] = len(extract_characters(source))
        record["scene_count"] = len(extract_scenes(source))
        record["alias_proposal_count"] = len(
            build_alias_link_proposals(source, extract_characters(source))
        )
        record["scene_normalization_proposal_count"] = len(
            build_scene_name_normalization_proposals(source, extract_scenes(source))
        )
        record["discovery_mentions"] = [
            item["mention"] for item in _canonical_discovery(discover_indirect_mention_candidates(source))
        ]
    except Exception as exc:  # noqa: BLE001
        record["crashed"] = True
        record["errors"].append(f"free_path: {type(exc).__name__}: {exc}")
        record["traceback"] = traceback.format_exc(limit=8)
        return record

    try:
        built = build_indirect_mention_proposals(
            source,
            judge=_mock_judge,
            max_calls=budget_max_calls,
        )
        discovered = int(built.get("discovered_count") or 0)
        judged = int(built.get("judged_count") or 0)
        skipped = list(built.get("budget_skipped") or [])
        suppressed = list(built.get("suppressed_known_identity") or [])
        # Budget applies to eligible mentions after known-identity suppression,
        # not to raw discovery count (see build_indirect_mention_proposals).
        eligible = max(0, discovered - len(suppressed))
        expected_judged = min(eligible, budget_max_calls)
        expected_skipped = max(0, eligible - budget_max_calls)
        record["budget_probe"] = {
            "max_calls": budget_max_calls,
            "discovered_count": discovered,
            "suppressed_known_identity_count": len(suppressed),
            "eligible_count": eligible,
            "judged_count": judged,
            "budget_skipped_count": len(skipped),
            "proposal_count": len(built.get("proposals") or []),
            "expected_judged": expected_judged,
            "expected_skipped": expected_skipped,
            "budget_enforced": judged == expected_judged and len(skipped) == expected_skipped,
            "cost_class": built.get("cost_class"),
            "used_mock_judge": True,
        }
    except Exception as exc:  # noqa: BLE001
        record["crashed"] = True
        record["errors"].append(f"budget_probe: {type(exc).__name__}: {exc}")
        record["traceback"] = traceback.format_exc(limit=8)
    return record


def run_corpus(corpus: dict[str, Any], *, repo: Path, live_smoke: bool = False) -> dict[str, Any]:
    thresholds = corpus.get("thresholds") or {}
    budget = int(thresholds.get("budget_max_calls_probe") or 3)
    runs = int(thresholds.get("determinism_runs") or 2)
    started = time.perf_counter()
    scripts = [_observe_script(item, repo=repo, budget_max_calls=budget, determinism_runs=runs) for item in corpus.get("scripts") or []]
    payload: dict[str, Any] = {
        "schema_version": "long_script_stability_observations_v0.1",
        "thresholds": thresholds,
        "remote_llm_calls": 0,
        "wall_time_sec": round(time.perf_counter() - started, 3),
        "scripts": scripts,
    }
    if live_smoke:
        # Optional single paid call — not used by run_all.py.
        target = next((item for item in scripts if item.get("kind") == "generalization_short"), scripts[0] if scripts else None)
        if target and not target.get("crashed"):
            from apps.api.runtime_script_indirect_mention_proposals import _default_remote_judge

            source = (repo / str(target["path"])).read_text(encoding="utf-8")
            try:
                built = build_indirect_mention_proposals(source, judge=_default_remote_judge, max_calls=1)
                payload["live_smoke"] = {
                    "script_id": target["id"],
                    "max_calls": 1,
                    "discovered_count": built.get("discovered_count"),
                    "judged_count": built.get("judged_count"),
                    "budget_skipped_count": len(built.get("budget_skipped") or []),
                    "ok": True,
                }
                payload["remote_llm_calls"] = int(built.get("remote_dispatch_count") or 0)
            except Exception as exc:  # noqa: BLE001
                payload["live_smoke"] = {
                    "script_id": target["id"],
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
    return payload


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--live-smoke",
        action="store_true",
        help="Optional: one budget-capped paid LLM call on one short script (not for run_all).",
    )
    args = parser.parse_args(argv)

    corpus = _load_json(args.corpus)
    payload = run_corpus(corpus, repo=REPO_ROOT, live_smoke=args.live_smoke)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(args.out),
                "script_count": len(payload.get("scripts") or []),
                "remote_llm_calls": payload.get("remote_llm_calls"),
                "wall_time_sec": payload.get("wall_time_sec"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
