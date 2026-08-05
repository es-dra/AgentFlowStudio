#!/usr/bin/env python3
"""Run the script-understanding eval framework across all current dimensions.

This is an orchestration layer only. Dimension scorers keep owning their
protocols and metrics.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
ALIASES = ROOT / "aliases"
MISSING_EVIDENCE = ROOT / "missing-evidence"
SUMMARY_PATH = ROOT / "script_understanding_eval_summary.json"


def _run_json(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    stdout = completed.stdout.strip()
    if not stdout:
        return {}
    return json.loads(stdout)


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True, text=True, capture_output=True)


def _round(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 6)
    if isinstance(value, list):
        return [_round(item) for item in value]
    if isinstance(value, dict):
        return {key: _round(item) for key, item in value.items()}
    return value


def _protocol_status(checks: dict[str, dict[str, Any]]) -> dict[str, Any]:
    failed = [name for name, check in checks.items() if not check.get("passed")]
    return {
        "verified_with_synthetic_data": not failed,
        "synthetic_checks": checks,
        "failed_checks": failed,
    }


def _run_aliases(python: str) -> dict[str, Any]:
    gold = ALIASES / "gold_cases.json"
    candidates = ALIASES / "deterministic_candidates.json"
    report = ALIASES / "deterministic_score_report.json"

    synthetic_perfect = _run_json(
        [python, str(ALIASES / "score_alias_linking.py"), str(gold), "--synthetic", "perfect"]
    )
    synthetic_split = _run_json(
        [python, str(ALIASES / "score_alias_linking.py"), str(gold), "--synthetic", "split_aliases"]
    )
    synthetic_must_not = _run_json(
        [python, str(ALIASES / "score_alias_linking.py"), str(gold), "--synthetic", "must_not_violation"]
    )

    _run([python, str(ALIASES / "deterministic_alias_proposer.py"), "--gold", str(gold), "--out", str(candidates)])
    real = _run_json([python, str(ALIASES / "score_alias_linking.py"), str(gold), str(candidates)])
    report.write_text(json.dumps(_round(real), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checks = {
        "perfect_macro_f1_is_1": {
            "passed": synthetic_perfect["summary"].get("macro_bcubed_f1") == 1.0,
            "observed": synthetic_perfect["summary"].get("macro_bcubed_f1"),
        },
        "split_aliases_has_false_splits": {
            "passed": (synthetic_split["summary"].get("macro_false_split_rate") or 0) > 0,
            "observed": synthetic_split["summary"].get("macro_false_split_rate"),
        },
        "must_not_violation_triggers_hard_fail": {
            "passed": synthetic_must_not["summary"].get("hard_fail_case_count") == 1,
            "observed": synthetic_must_not["summary"].get("hard_fail_case_count"),
        },
    }
    summary = real["summary"]
    return {
        "dimension": "aliases",
        "description": "alias and identity-linking proposal clusters",
        "protocol": _protocol_status(checks),
        "real_run": {
            "candidate_path": str(candidates.relative_to(ROOT)),
            "report_path": str(report.relative_to(ROOT)),
            "case_count": summary.get("case_count"),
            "macro_bcubed_f1": summary.get("macro_bcubed_f1"),
            "linkable_cluster_coverage_rate": summary.get("linkable_cluster_coverage_rate"),
            "macro_false_split_rate": summary.get("macro_false_split_rate"),
            "macro_false_merge_rate": summary.get("macro_false_merge_rate"),
            "hard_fail_case_count": summary.get("hard_fail_case_count"),
            "cases_missing_fsr_score": summary.get("cases_missing_fsr_score"),
        },
    }


def _run_missing_evidence(python: str) -> dict[str, Any]:
    gold = MISSING_EVIDENCE / "gold_cases.json"
    candidates = MISSING_EVIDENCE / "runtime_candidates.json"
    report = MISSING_EVIDENCE / "runtime_score_report.json"

    synthetic_perfect = _run_json(
        [python, str(MISSING_EVIDENCE / "score_missing_evidence.py"), str(gold), "--synthetic", "perfect"]
    )
    synthetic_over = _run_json(
        [python, str(MISSING_EVIDENCE / "score_missing_evidence.py"), str(gold), "--synthetic", "over_missing"]
    )
    synthetic_under = _run_json(
        [python, str(MISSING_EVIDENCE / "score_missing_evidence.py"), str(gold), "--synthetic", "under_missing"]
    )

    _run([python, str(MISSING_EVIDENCE / "run_against_runtime.py"), "--gold", str(gold), "--out", str(candidates)])
    real = _run_json([python, str(MISSING_EVIDENCE / "score_missing_evidence.py"), str(gold), str(candidates)])
    report.write_text(json.dumps(_round(real), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checks = {
        "perfect_accuracy_is_1": {
            "passed": synthetic_perfect["summary"].get("missing_judgment_accuracy") == 1.0,
            "observed": synthetic_perfect["summary"].get("missing_judgment_accuracy"),
        },
        "over_missing_has_fp_rate_1": {
            "passed": synthetic_over["summary"].get("false_positive_missing_rate") == 1.0,
            "observed": synthetic_over["summary"].get("false_positive_missing_rate"),
        },
        "under_missing_has_fn_rate_1": {
            "passed": synthetic_under["summary"].get("false_negative_missing_rate") == 1.0,
            "observed": synthetic_under["summary"].get("false_negative_missing_rate"),
        },
    }
    summary = real["summary"]
    return {
        "dimension": "missing-evidence",
        "description": "missing slot and scene_cast evidence judgments",
        "protocol": _protocol_status(checks),
        "real_run": {
            "candidate_path": str(candidates.relative_to(ROOT)),
            "report_path": str(report.relative_to(ROOT)),
            "case_count": summary.get("case_count"),
            "judgment_count_scored": summary.get("judgment_count_scored"),
            "missing_judgment_accuracy": summary.get("missing_judgment_accuracy"),
            "false_positive_missing_rate": summary.get("false_positive_missing_rate"),
            "false_negative_missing_rate": summary.get("false_negative_missing_rate"),
            "relation_judgment_coverage_rate": summary.get("relation_judgment_coverage_rate"),
            "cases_with_prerequisite_gaps_count": summary.get("cases_with_prerequisite_gaps_count"),
            "cases_with_uncovered_relations_count": summary.get("cases_with_uncovered_relations_count"),
        },
    }


def run_all(python: str) -> dict[str, Any]:
    dimensions = [_run_aliases(python), _run_missing_evidence(python)]
    verified = [item["dimension"] for item in dimensions if item["protocol"]["verified_with_synthetic_data"]]
    unverified = [item["dimension"] for item in dimensions if not item["protocol"]["verified_with_synthetic_data"]]
    payload = {
        "schema_version": "script_understanding_eval_framework_v0.1",
        "framework_health": {
            "covered_dimensions": [item["dimension"] for item in dimensions],
            "protocol_verified_dimensions": verified,
            "protocol_unverified_dimensions": unverified,
            "health_note": (
                "Framework reports dimension-level metrics only; it does not combine aliases and "
                "missing-evidence into a single score."
            ),
        },
        "dimensions": dimensions,
    }
    SUMMARY_PATH.write_text(json.dumps(_round(payload), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", default=sys.executable, help="Python executable used for dimension scripts.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the framework summary.")
    args = parser.parse_args(argv)

    payload = run_all(args.python)
    print(json.dumps(_round(payload), ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
