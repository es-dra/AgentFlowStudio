#!/usr/bin/env python3
"""Run research-only script-understanding eval dimensions (offline).

This orchestration layer stays stdlib-only. It does not import apps.api and
does not call production runners.

Dimensions in this slice:
  - aliases (stdlib proposer + scorer)
  - missing-evidence (score checked-in historical candidates)
  - long-scripts (score checked-in historical observations)

Indirect-mentions shipped separately in PR #235 and are not re-run here.
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
LONG_SCRIPTS = ROOT / "long-scripts"
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

    # Stdlib-only deterministic proposer (no apps.api).
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
            "candidate_source": "deterministic_alias_proposer (stdlib)",
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

    # Historical structured candidates only — live runtime harness depends on apps.api
    # and is intentionally out of this research slice.
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
            "candidate_source": "checked-in historical runtime_candidates.json",
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


def _run_long_scripts(python: str) -> dict[str, Any]:
    corpus = LONG_SCRIPTS / "corpus.json"
    observations = LONG_SCRIPTS / "stability_observations.json"
    report = LONG_SCRIPTS / "stability_score_report.json"

    synthetic_perfect = _run_json(
        [python, str(LONG_SCRIPTS / "score_long_script_stability.py"), str(corpus), "--synthetic", "perfect"]
    )
    synthetic_nondet = _run_json(
        [
            python,
            str(LONG_SCRIPTS / "score_long_script_stability.py"),
            str(corpus),
            "--synthetic",
            "nondeterministic",
        ]
    )
    synthetic_budget = _run_json(
        [
            python,
            str(LONG_SCRIPTS / "score_long_script_stability.py"),
            str(corpus),
            "--synthetic",
            "budget_bypass",
        ]
    )

    # Historical structured observations only — live stability runner depends on apps.api.
    real = _run_json(
        [python, str(LONG_SCRIPTS / "score_long_script_stability.py"), str(corpus), str(observations)]
    )
    report.write_text(json.dumps(_round(real), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checks = {
        "perfect_checklist_pass_rate_is_1": {
            "passed": synthetic_perfect["summary"].get("checklist_pass_rate") == 1.0,
            "observed": synthetic_perfect["summary"].get("checklist_pass_rate"),
        },
        "nondeterministic_lowers_free_path_rate": {
            "passed": (synthetic_nondet["summary"].get("free_path_deterministic_rate") or 1.0) < 1.0,
            "observed": synthetic_nondet["summary"].get("free_path_deterministic_rate"),
        },
        "budget_bypass_lowers_budget_rate": {
            "passed": (synthetic_budget["summary"].get("budget_enforced_rate") or 1.0) < 1.0,
            "observed": synthetic_budget["summary"].get("budget_enforced_rate"),
        },
    }
    summary = real["summary"]
    return {
        "dimension": "long-scripts",
        "description": "long-text runtime stability / operability (not understanding accuracy)",
        "protocol": _protocol_status(checks),
        "real_run": {
            "observation_path": str(observations.relative_to(ROOT)),
            "report_path": str(report.relative_to(ROOT)),
            "observation_source": "checked-in historical stability_observations.json",
            "script_count": summary.get("script_count"),
            "checklist_pass_rate": summary.get("checklist_pass_rate"),
            "all_scripts_passed": summary.get("all_scripts_passed"),
            "crash_free_rate": summary.get("crash_free_rate"),
            "free_path_deterministic_rate": summary.get("free_path_deterministic_rate"),
            "budget_enforced_rate": summary.get("budget_enforced_rate"),
            "soft_ceiling_pass_rate": summary.get("soft_ceiling_pass_rate"),
            "hard_ceiling_pass_rate": summary.get("hard_ceiling_pass_rate"),
            "remote_llm_calls": summary.get("remote_llm_calls_in_observations"),
            "failed_probe_names": summary.get("failed_probe_names"),
        },
    }


def run_all(python: str) -> dict[str, Any]:
    dimensions = [
        _run_aliases(python),
        _run_missing_evidence(python),
        _run_long_scripts(python),
    ]
    verified = [item["dimension"] for item in dimensions if item["protocol"]["verified_with_synthetic_data"]]
    unverified = [item["dimension"] for item in dimensions if not item["protocol"]["verified_with_synthetic_data"]]
    payload = {
        "schema_version": "script_understanding_eval_framework_v0.1",
        "research_slice": {
            "dimensions_in_this_pr": ["aliases", "missing-evidence", "long-scripts"],
            "indirect_mentions": "shipped separately in PR #235; not re-copied here",
            "excludes_production_runners": True,
        },
        "framework_health": {
            "covered_dimensions": [item["dimension"] for item in dimensions],
            "protocol_verified_dimensions": verified,
            "protocol_unverified_dimensions": unverified,
            "health_note": (
                "This research slice covers 3/4 framework dimensions offline. "
                "Indirect-mentions is PR #235. Framework reports dimension-level "
                "metrics only; it does not combine scores. Long-scripts is stability, "
                "not a fourth accuracy metric."
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
