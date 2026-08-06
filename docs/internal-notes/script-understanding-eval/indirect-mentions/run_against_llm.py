#!/usr/bin/env python3
"""Run gold_cases.json through the production split-fields LLM judge.

COST WARNING
------------
This harness issues one paid remote LLM call per gold case (oracle path):
it judges the gold mention against the gold context_snippet using
apps.api.runtime_script_indirect_mention_proposals._default_remote_judge.

It does NOT run full-script discovery+extract (that would be dozens of calls
on long scripts). Discovery coverage is out of scope for this dimension's
primary score; judgment quality is.

Requires:
  AFS_ALLOW_REMOTE_LLM=true
  AFS_PROVIDER_CONFIG pointing at a live LLM service

Writes indirect_mention_candidates_v0.1 JSON for score_indirect_mentions.py.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from apps.api.runtime_script_indirect_mention_proposals import (  # noqa: E402
    _default_remote_judge,
)


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _run_case(gold_case: dict[str, Any], *, out_root: Path) -> dict[str, Any]:
    case_id = str(gold_case["id"])
    mention = str(gold_case["mention"])
    snippet = str(gold_case.get("context_snippet") or "")
    if not snippet.strip():
        return {
            "id": case_id,
            "mention": mention,
            "status": "unjudged",
            "error": "missing_context_snippet",
        }
    case_dir = out_root / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    try:
        judgment = _default_remote_judge(snippet, mention, case_dir)
    except Exception as exc:  # noqa: BLE001 - eval harness must record failures
        return {
            "id": case_id,
            "mention": mention,
            "status": "unjudged",
            "error": f"{type(exc).__name__}: {exc}",
            "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        }
    refers = bool(judgment.get("refers_to_real_character"))
    present = bool(judgment.get("is_present_in_scene"))
    return {
        "id": case_id,
        "mention": mention,
        "status": "judged",
        "refers_to_real_character": refers,
        "refers_to_real_character_confidence": judgment.get("refers_to_real_character_confidence"),
        "refers_to_real_character_reason": judgment.get("refers_to_real_character_reason"),
        "is_present_in_scene": present,
        "is_present_in_scene_confidence": judgment.get("is_present_in_scene_confidence"),
        "is_present_in_scene_reason": judgment.get("is_present_in_scene_reason"),
        "is_indirect_mention": bool(refers and not present),
        "latency_ms": round((time.perf_counter() - started) * 1000, 1),
        "scoring_policy": gold_case.get("scoring_policy"),
        "cost_class": "paid_remote_llm",
    }


def run_gold(
    gold_data: dict[str, Any],
    *,
    include_known_limitation: bool = True,
    max_calls: int | None = None,
) -> dict[str, Any]:
    cases_in = list(gold_data.get("cases") or [])
    if not include_known_limitation:
        cases_in = [case for case in cases_in if case.get("scoring_policy") == "required"]
    if max_calls is not None:
        cases_in = cases_in[: max(0, int(max_calls))]

    started = time.perf_counter()
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="afs-indirect-mention-eval-") as tmp:
        out_root = Path(tmp)
        for gold_case in cases_in:
            results.append(_run_case(gold_case, out_root=out_root))

    # Ensure every gold id is present for the scorer (unjudged stubs for skipped).
    ran_ids = {str(item["id"]) for item in results}
    for gold_case in gold_data.get("cases") or []:
        case_id = str(gold_case["id"])
        if case_id in ran_ids:
            continue
        results.append(
            {
                "id": case_id,
                "mention": gold_case.get("mention"),
                "status": "unjudged",
                "error": "skipped_by_runner_filter",
                "scoring_policy": gold_case.get("scoring_policy"),
            }
        )

    ok = sum(1 for item in results if item.get("status") == "judged")
    return {
        "schema_version": "indirect_mention_candidates_v0.1",
        "candidate_path": "oracle_llm_on_gold_snippet",
        "cost_class": "paid_remote_llm",
        "llm_call_count": ok,
        "wall_time_sec": round(time.perf_counter() - started, 2),
        "cases": results,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--skip-known-limitation",
        action="store_true",
        help="Do not spend LLM calls on known_limitation_excluded cases.",
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=None,
        help="Optional hard cap on LLM calls (first N gold cases after filters).",
    )
    args = parser.parse_args(argv)

    if os.environ.get("AFS_ALLOW_REMOTE_LLM", "").strip().lower() not in {"1", "true", "yes", "on"}:
        print("AFS_ALLOW_REMOTE_LLM must be true", file=sys.stderr)
        return 2
    if not os.environ.get("AFS_PROVIDER_CONFIG"):
        print("AFS_PROVIDER_CONFIG required", file=sys.stderr)
        return 2

    gold_data = _load_json(args.gold)
    payload = run_gold(
        gold_data,
        include_known_limitation=not args.skip_known_limitation,
        max_calls=args.max_calls,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(args.out), "llm_call_count": payload["llm_call_count"], "wall_time_sec": payload["wall_time_sec"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
