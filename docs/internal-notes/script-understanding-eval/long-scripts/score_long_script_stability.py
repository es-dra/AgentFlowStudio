#!/usr/bin/env python3
"""Score long-script runtime stability observations (checklist protocol).

Not an accuracy scorer. Inputs are observations from run_stability_checks.py
or synthetic observation payloads built for protocol self-checks.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must be a JSON object")
    return data


def _probe(name: str, passed: bool, detail: Any = None) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _rate(values: list[bool] | None) -> float | None:
    if not values:
        return None
    return sum(1 for ok in values if ok) / len(values)


def score_observations(corpus: dict[str, Any], observations: dict[str, Any]) -> dict[str, Any]:
    thresholds = {
        **(corpus.get("thresholds") or {}),
        **(observations.get("thresholds") or {}),
    }
    soft = int(thresholds.get("discovery_soft_ceiling") or 40)
    hard = int(thresholds.get("discovery_hard_ceiling") or 80)
    scripts = list(observations.get("scripts") or [])

    script_results: list[dict[str, Any]] = []
    for item in scripts:
        probes = []
        crashed = bool(item.get("crashed"))
        probes.append(_probe("crash_free", not crashed, item.get("errors") or []))
        probes.append(
            _probe(
                "free_path_deterministic",
                (not crashed) and bool(item.get("free_path_deterministic")),
                {
                    "digests": item.get("free_path_digests"),
                    "discovery_counts_across_runs": item.get("discovery_counts_across_runs"),
                },
            )
        )
        discovery = item.get("discovery_count")
        if discovery is None:
            probes.append(_probe("discovery_soft_ceiling", False, "missing_discovery_count"))
            probes.append(_probe("discovery_hard_ceiling", False, "missing_discovery_count"))
        else:
            probes.append(
                _probe(
                    "discovery_soft_ceiling",
                    int(discovery) <= soft,
                    {"discovery_count": discovery, "soft_ceiling": soft},
                )
            )
            probes.append(
                _probe(
                    "discovery_hard_ceiling",
                    int(discovery) <= hard,
                    {"discovery_count": discovery, "hard_ceiling": hard},
                )
            )
        budget = item.get("budget_probe") or {}
        probes.append(
            _probe(
                "budget_enforced",
                (not crashed) and bool(budget.get("budget_enforced")),
                budget,
            )
        )
        script_results.append(
            {
                "id": item.get("id"),
                "label": item.get("label"),
                "kind": item.get("kind"),
                "char_count": item.get("char_count"),
                "discovery_count": discovery,
                "discovery_per_1k_chars": item.get("discovery_per_1k_chars"),
                "probes": probes,
                "all_passed": all(probe["passed"] for probe in probes),
            }
        )

    flat = [probe for script in script_results for probe in script["probes"]]
    failed = [probe for probe in flat if not probe["passed"]]
    by_name: dict[str, list[bool]] = {}
    for probe in flat:
        by_name.setdefault(str(probe["name"]), []).append(bool(probe["passed"]))

    summary = {
        "script_count": len(script_results),
        "probe_count": len(flat),
        "probes_passed": len(flat) - len(failed),
        "probes_failed": len(failed),
        "checklist_pass_rate": ((len(flat) - len(failed)) / len(flat)) if flat else None,
        "all_scripts_passed": all(item["all_passed"] for item in script_results) if script_results else False,
        "crash_free_rate": _rate(by_name.get("crash_free")),
        "free_path_deterministic_rate": _rate(by_name.get("free_path_deterministic")),
        "budget_enforced_rate": _rate(by_name.get("budget_enforced")),
        "soft_ceiling_pass_rate": _rate(by_name.get("discovery_soft_ceiling")),
        "hard_ceiling_pass_rate": _rate(by_name.get("discovery_hard_ceiling")),
        "failed_probe_names": sorted({str(probe["name"]) for probe in failed}),
        "remote_llm_calls_in_observations": observations.get("remote_llm_calls"),
    }

    return {
        "schema_version": "long_script_stability_score_v0.1",
        "summary": summary,
        "scripts": script_results,
    }


def build_synthetic_observations(corpus: dict[str, Any], mode: str) -> dict[str, Any]:
    """Hand-written observation payloads for scorer unit checks."""
    thresholds = dict(corpus.get("thresholds") or {})
    budget = int(thresholds.get("budget_max_calls_probe") or 3)
    scripts_out: list[dict[str, Any]] = []
    for index, script in enumerate(corpus.get("scripts") or []):
        discovered = 12 if script.get("kind") == "long" else 4
        suppressed = 1 if script.get("kind") == "long" else 0
        eligible = discovered - suppressed
        judged = min(eligible, budget)
        skipped = max(0, eligible - budget)
        digest_a = f"digest-{script['id']}-a"
        digest_b = digest_a
        budget_ok = True
        crashed = False
        if mode == "perfect":
            pass
        elif mode == "nondeterministic":
            digest_b = f"digest-{script['id']}-b"
        elif mode == "budget_bypass":
            judged = eligible  # pretend all eligible judged despite max_calls
            skipped = 0
            budget_ok = False
        else:
            raise ValueError(f"unknown synthetic mode: {mode}")
        scripts_out.append(
            {
                "id": script["id"],
                "label": script.get("label"),
                "kind": script.get("kind"),
                "path": script.get("path"),
                "char_count": 3000 if script.get("kind") == "long" else 500,
                "crashed": crashed,
                "errors": [],
                "free_path_digests": [digest_a, digest_b],
                "free_path_deterministic": digest_a == digest_b,
                "discovery_count": discovered,
                "discovery_counts_across_runs": [discovered, discovered],
                "discovery_per_1k_chars": discovered / 3.0,
                "budget_probe": {
                    "max_calls": budget,
                    "discovered_count": discovered,
                    "suppressed_known_identity_count": suppressed,
                    "eligible_count": eligible,
                    "judged_count": judged,
                    "budget_skipped_count": skipped,
                    "expected_judged": min(eligible, budget),
                    "expected_skipped": max(0, eligible - budget),
                    "budget_enforced": budget_ok
                    and judged == min(eligible, budget)
                    and skipped == max(0, eligible - budget),
                    "used_mock_judge": True,
                },
            }
        )
        if mode != "perfect" and index > 0:
            # restore perfect budget/det for remaining scripts so rates are not all 0
            scripts_out[-1]["free_path_digests"] = [digest_a, digest_a]
            scripts_out[-1]["free_path_deterministic"] = True
            if mode == "budget_bypass":
                scripts_out[-1]["budget_probe"] = {
                    "max_calls": budget,
                    "discovered_count": discovered,
                    "suppressed_known_identity_count": suppressed,
                    "eligible_count": eligible,
                    "judged_count": min(eligible, budget),
                    "budget_skipped_count": max(0, eligible - budget),
                    "expected_judged": min(eligible, budget),
                    "expected_skipped": max(0, eligible - budget),
                    "budget_enforced": True,
                    "used_mock_judge": True,
                }
    return {
        "schema_version": "long_script_stability_observations_v0.1",
        "mode": mode,
        "thresholds": thresholds,
        "remote_llm_calls": 0,
        "scripts": scripts_out,
    }


def _round_floats(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, list):
        return [_round_floats(item) for item in value]
    if isinstance(value, dict):
        return {key: _round_floats(item) for key, item in value.items()}
    return value


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus", type=Path, help="Path to corpus.json")
    parser.add_argument("observations", nargs="?", type=Path, help="Path to observations JSON")
    parser.add_argument(
        "--synthetic",
        choices=["perfect", "nondeterministic", "budget_bypass"],
        help="Built-in observation payloads for scorer checks",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    if bool(args.observations) == bool(args.synthetic):
        parser.error("provide exactly one of an observations JSON path or --synthetic")

    corpus = _load_json(args.corpus)
    observations = (
        build_synthetic_observations(corpus, args.synthetic)
        if args.synthetic
        else _load_json(args.observations)
    )
    result = score_observations(corpus, observations)
    print(json.dumps(_round_floats(result), ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
