#!/usr/bin/env python3
"""Offline scorer for indirect-mention binary judgments.

Inputs:
  1. gold_cases.json from this directory.
  2. System prediction JSON:

     {
       "schema_version": "indirect_mention_candidates_v0.1",
       "cases": [
         {
           "id": "I1",
           "mention": "沈岚",
           "refers_to_real_character": true,
           "is_present_in_scene": false,
           "is_indirect_mention": true
         }
       ]
     }

Primary metrics score only gold cases with scoring_policy=required.
known_limitation_excluded cases are reported separately and do not enter
FP/FN denominators.

Metrics are binary classification rates per field (refers / present / derived
indirect). False positives and false negatives are reported separately; there
is no combined composite score.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


FIELDS = ("refers_to_real_character", "is_present_in_scene", "is_indirect_mention")
FIELD_SHORT = {
    "refers_to_real_character": "refers",
    "is_present_in_scene": "present",
    "is_indirect_mention": "indirect",
}


@dataclass
class FieldOutcome:
    field: str
    expected: bool
    predicted: bool | None
    outcome: str | None  # TP|TN|FP|FN|uncovered


@dataclass
class CaseScore:
    case_id: str
    mention: str
    scoring_policy: str
    outcomes: list[FieldOutcome]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _expected_fields(gold_case: dict[str, Any]) -> dict[str, bool]:
    refers = bool(gold_case["expected_refers_to_real_character"])
    present = bool(gold_case["expected_is_present_in_scene"])
    indirect = gold_case.get("expected_is_indirect_mention")
    if indirect is None:
        indirect = refers and not present
    else:
        indirect = bool(indirect)
    return {
        "refers_to_real_character": refers,
        "is_present_in_scene": present,
        "is_indirect_mention": indirect,
    }


def _predicted_fields(system_case: dict[str, Any]) -> dict[str, bool | None]:
    if system_case.get("status") == "unjudged" or system_case.get("error"):
        return {field: None for field in FIELDS}
    refers = system_case.get("refers_to_real_character")
    present = system_case.get("is_present_in_scene")
    if refers is None or present is None:
        return {field: None for field in FIELDS}
    refers_b = bool(refers)
    present_b = bool(present)
    indirect = system_case.get("is_indirect_mention")
    if indirect is None:
        indirect_b = refers_b and not present_b
    else:
        indirect_b = bool(indirect)
    return {
        "refers_to_real_character": refers_b,
        "is_present_in_scene": present_b,
        "is_indirect_mention": indirect_b,
    }


def _classify(expected: bool, predicted: bool | None) -> str | None:
    if predicted is None:
        return None
    if expected and predicted:
        return "TP"
    if (not expected) and (not predicted):
        return "TN"
    if (not expected) and predicted:
        return "FP"
    return "FN"


def score_case(gold_case: dict[str, Any], system_case: dict[str, Any]) -> CaseScore:
    expected = _expected_fields(gold_case)
    predicted = _predicted_fields(system_case)
    outcomes = [
        FieldOutcome(
            field=field,
            expected=expected[field],
            predicted=predicted[field],
            outcome=_classify(expected[field], predicted[field]),
        )
        for field in FIELDS
    ]
    return CaseScore(
        case_id=str(gold_case["id"]),
        mention=str(gold_case.get("mention") or system_case.get("mention") or ""),
        scoring_policy=str(gold_case.get("scoring_policy") or "required"),
        outcomes=outcomes,
    )


def _field_rates(scores: list[CaseScore], field: str) -> dict[str, Any]:
    outcomes = []
    for score in scores:
        for item in score.outcomes:
            if item.field == field and item.outcome is not None:
                outcomes.append(item.outcome)
    tp = outcomes.count("TP")
    tn = outcomes.count("TN")
    fp = outcomes.count("FP")
    fn = outcomes.count("FN")
    scored = tp + tn + fp + fn
    positive_denom = tp + fn  # gold true
    negative_denom = tn + fp  # gold false
    precision_denom = tp + fp
    recall_denom = tp + fn
    return {
        "judgment_count_scored": scored,
        "true_positive": tp,
        "true_negative": tn,
        "false_positive": fp,
        "false_negative": fn,
        "accuracy": ((tp + tn) / scored) if scored else None,
        "precision": (tp / precision_denom) if precision_denom else None,
        "recall": (tp / recall_denom) if recall_denom else None,
        "false_positive_rate": (fp / negative_denom) if negative_denom else None,
        "false_negative_rate": (fn / positive_denom) if positive_denom else None,
    }


def score_dataset(gold_data: dict[str, Any], system_data: dict[str, Any]) -> dict[str, Any]:
    gold_by_id = {str(case["id"]): case for case in gold_data.get("cases", [])}
    system_by_id = {str(case["id"]): case for case in system_data.get("cases", [])}
    missing = sorted(set(gold_by_id).difference(system_by_id))
    if missing:
        raise ValueError(f"system data missing case(s): {', '.join(missing)}")

    case_scores = [score_case(gold_by_id[case_id], system_by_id[case_id]) for case_id in sorted(gold_by_id)]
    primary = [score for score in case_scores if score.scoring_policy == "required"]
    boundary = [score for score in case_scores if score.scoring_policy != "required"]

    field_metrics = {FIELD_SHORT[field]: _field_rates(primary, field) for field in FIELDS}
    uncovered_primary = [
        score.case_id
        for score in primary
        if any(item.outcome is None for item in score.outcomes)
    ]

    summary = {
        "case_count": len(case_scores),
        "required_case_count": len(primary),
        "known_limitation_case_count": len(boundary),
        "uncovered_required_case_count": len(uncovered_primary),
        "uncovered_required_cases": uncovered_primary,
        "refers": field_metrics["refers"],
        "present": field_metrics["present"],
        "indirect": field_metrics["indirect"],
        # Convenience aliases matching framework reporting language
        "indirect_mention_accuracy": field_metrics["indirect"]["accuracy"],
        "false_positive_indirect_rate": field_metrics["indirect"]["false_positive_rate"],
        "false_negative_indirect_rate": field_metrics["indirect"]["false_negative_rate"],
        "false_positive_refers_rate": field_metrics["refers"]["false_positive_rate"],
        "false_negative_refers_rate": field_metrics["refers"]["false_negative_rate"],
    }

    def serialize(score: CaseScore) -> dict[str, Any]:
        return {
            "id": score.case_id,
            "mention": score.mention,
            "scoring_policy": score.scoring_policy,
            "fields": [
                {
                    "field": item.field,
                    "expected": item.expected,
                    "predicted": item.predicted,
                    "outcome": item.outcome,
                }
                for item in score.outcomes
            ],
        }

    return {
        "schema_version": "indirect_mention_score_v0.1",
        "summary": summary,
        "cases": [serialize(score) for score in case_scores if score.scoring_policy == "required"],
        "boundary_cases": [serialize(score) for score in boundary],
    }


def build_synthetic_system(gold_data: dict[str, Any], mode: str) -> dict[str, Any]:
    """Hand-written system outputs for scorer unit checks (not live LLM)."""
    cases: list[dict[str, Any]] = []
    for gold in gold_data.get("cases", []):
        expected = _expected_fields(gold)
        refers = expected["refers_to_real_character"]
        present = expected["is_present_in_scene"]
        if mode == "perfect":
            pass
        elif mode == "false_positive_refers":
            # Force noise / non-person spans to refers=true & present=false → FP on refers/indirect
            if not expected["refers_to_real_character"]:
                refers = True
                present = False
        elif mode == "false_negative_indirect":
            # Miss all true indirect mentions by denying refers
            if expected["is_indirect_mention"]:
                refers = False
                present = False
        else:
            raise ValueError(f"unknown synthetic mode: {mode}")
        cases.append(
            {
                "id": str(gold["id"]),
                "mention": gold.get("mention"),
                "refers_to_real_character": refers,
                "is_present_in_scene": present,
                "is_indirect_mention": bool(refers and not present),
            }
        )
    return {"schema_version": "indirect_mention_candidates_v0.1", "mode": mode, "cases": cases}


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
    parser.add_argument("gold", type=Path, help="Path to gold_cases.json")
    parser.add_argument("candidates", nargs="?", type=Path, help="Path to system prediction JSON")
    parser.add_argument(
        "--synthetic",
        choices=["perfect", "false_positive_refers", "false_negative_indirect"],
        help="Built-in hand-written system outputs for scorer checks",
    )
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args(argv)

    if bool(args.candidates) == bool(args.synthetic):
        parser.error("provide exactly one of a candidate JSON path or --synthetic")

    gold_data = _load_json(args.gold)
    system_data = build_synthetic_system(gold_data, args.synthetic) if args.synthetic else _load_json(args.candidates)
    result = score_dataset(gold_data, system_data)
    print(json.dumps(_round_floats(result), ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
