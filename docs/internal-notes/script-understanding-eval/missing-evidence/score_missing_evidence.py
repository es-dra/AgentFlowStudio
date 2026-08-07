#!/usr/bin/env python3
"""Offline scorer for missing-evidence judgments (slots + scene_cast).

Inputs:
  1. gold_cases.json from this directory.
  2. System prediction JSON:

     {
       "schema_version": "missing_evidence_candidates_v0.1",
       "cases": [
         {
           "id": "M1",
           "missing_slots": [],
           "characters": ["陈默", "李薇"],
           "scenes": ["会议室", "地下车库"],
           "relations": [
             {
               "relation_type": "scene_cast",
               "scene": "地下车库",
               "member": "陈默",
               "status": "missing",
               "evidence_status": "missing"
             }
           ]
         }
       ]
     }

Coverage (same lesson as alias eval):
  - Slot judgments always score when gold declares expected/forbidden slots.
  - Relation judgments score only when both scene and member appear in the
    system character/scene lists (prerequisites met). Otherwise they are
    uncovered and excluded from FP/FN denominators — reported in summary.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SLOT_NAMES = ("named_characters", "main_scenes")


@dataclass
class Judgment:
    kind: str  # slot | relation
    key: str
    expected_missing: bool
    predicted_missing: bool | None  # None = uncovered
    detail: str = ""


@dataclass
class CaseScore:
    case_id: str
    judgments: list[Judgment] = field(default_factory=list)
    prerequisite_gaps: list[str] = field(default_factory=list)
    uncovered_relation_keys: list[str] = field(default_factory=list)

    @property
    def scored(self) -> list[Judgment]:
        return [item for item in self.judgments if item.predicted_missing is not None]

    @property
    def true_positive(self) -> int:
        return sum(1 for item in self.scored if item.expected_missing and item.predicted_missing)

    @property
    def true_negative(self) -> int:
        return sum(1 for item in self.scored if (not item.expected_missing) and (not item.predicted_missing))

    @property
    def false_positive(self) -> int:
        return sum(1 for item in self.scored if (not item.expected_missing) and item.predicted_missing)

    @property
    def false_negative(self) -> int:
        return sum(1 for item in self.scored if item.expected_missing and (not item.predicted_missing))


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _relation_key(item: dict[str, Any]) -> str:
    return f"{item.get('relation_type', 'scene_cast')}|{item.get('scene')}|{item.get('member')}"


def _is_relation_missing(row: dict[str, Any]) -> bool:
    status = str(row.get("status") or "")
    evidence_status = str(row.get("evidence_status") or "")
    return status == "missing" or evidence_status == "missing"


def score_case(gold_case: dict[str, Any], system_case: dict[str, Any]) -> CaseScore:
    case_id = str(gold_case["id"])
    score = CaseScore(case_id=case_id)

    system_slots = set(system_case.get("missing_slots") or [])
    system_characters = set(system_case.get("characters") or [])
    system_scenes = set(system_case.get("scenes") or [])
    relations = {
        _relation_key(item): item
        for item in (system_case.get("relations") or [])
        if str(item.get("relation_type") or "scene_cast") == "scene_cast"
    }

    for name in gold_case.get("require_characters") or []:
        if name not in system_characters:
            score.prerequisite_gaps.append(f"character:{name}")
    for name in gold_case.get("require_scenes") or []:
        if name not in system_scenes:
            score.prerequisite_gaps.append(f"scene:{name}")

    expected_missing_slots = set(gold_case.get("expected_missing_slots") or [])
    forbidden_missing_slots = set(gold_case.get("forbidden_missing_slots") or [])
    for slot in SLOT_NAMES:
        if slot in expected_missing_slots:
            score.judgments.append(
                Judgment(
                    kind="slot",
                    key=slot,
                    expected_missing=True,
                    predicted_missing=slot in system_slots,
                    detail="expected_missing_slots",
                )
            )
        elif slot in forbidden_missing_slots:
            score.judgments.append(
                Judgment(
                    kind="slot",
                    key=slot,
                    expected_missing=False,
                    predicted_missing=slot in system_slots,
                    detail="forbidden_missing_slots",
                )
            )

    def score_relation(spec: dict[str, Any], *, expect_missing: bool) -> None:
        key = _relation_key(spec)
        scene = str(spec.get("scene") or "")
        member = str(spec.get("member") or "")
        if scene not in system_scenes or member not in system_characters:
            score.uncovered_relation_keys.append(key)
            score.judgments.append(
                Judgment(
                    kind="relation",
                    key=key,
                    expected_missing=expect_missing,
                    predicted_missing=None,
                    detail="uncovered_missing_endpoint",
                )
            )
            return
        row = relations.get(key)
        if row is None:
            # Endpoints exist but no relationship row:
            # - if gold expects missing → FN risk if we treat as "not missing" (predicted_missing=False)
            # - if gold expects present → count as missing/absent evidence (predicted_missing=True → FP)
            predicted_missing = False if expect_missing else True
            score.judgments.append(
                Judgment(
                    kind="relation",
                    key=key,
                    expected_missing=expect_missing,
                    predicted_missing=predicted_missing,
                    detail="relation_row_absent",
                )
            )
            return
        score.judgments.append(
            Judgment(
                kind="relation",
                key=key,
                expected_missing=expect_missing,
                predicted_missing=_is_relation_missing(row),
                detail=str(row.get("status") or ""),
            )
        )

    for spec in gold_case.get("expected_relation_missing") or []:
        score_relation(spec, expect_missing=True)
    for spec in gold_case.get("expected_relation_present") or []:
        score_relation(spec, expect_missing=False)

    return score


def _rates(scores: list[CaseScore]) -> dict[str, Any]:
    tp = sum(score.true_positive for score in scores)
    tn = sum(score.true_negative for score in scores)
    fp = sum(score.false_positive for score in scores)
    fn = sum(score.false_negative for score in scores)
    scored = tp + tn + fp + fn
    present_denom = fp + tn  # gold said should NOT be missing
    missing_denom = fn + tp  # gold said SHOULD be missing
    return {
        "judgment_count_scored": scored,
        "true_positive_missing": tp,
        "true_negative_present": tn,
        "false_positive_missing": fp,
        "false_negative_missing": fn,
        "missing_judgment_accuracy": ((tp + tn) / scored) if scored else None,
        "false_positive_missing_rate": (fp / present_denom) if present_denom else None,
        "false_negative_missing_rate": (fn / missing_denom) if missing_denom else None,
    }


def score_dataset(gold_data: dict[str, Any], system_data: dict[str, Any]) -> dict[str, Any]:
    gold_by_id = {str(case["id"]): case for case in gold_data.get("cases", [])}
    system_by_id = {str(case["id"]): case for case in system_data.get("cases", [])}
    missing = sorted(set(gold_by_id).difference(system_by_id))
    if missing:
        raise ValueError(f"system data missing case(s): {', '.join(missing)}")

    case_scores = [score_case(gold_by_id[case_id], system_by_id[case_id]) for case_id in sorted(gold_by_id)]
    rates = _rates(case_scores)

    relation_judgments = [item for score in case_scores for item in score.judgments if item.kind == "relation"]
    relation_scored = [item for item in relation_judgments if item.predicted_missing is not None]
    relation_total = len(relation_judgments)
    relation_covered = len(relation_scored)

    cases_with_prereq_gaps = [score.case_id for score in case_scores if score.prerequisite_gaps]
    cases_with_uncovered_relations = [score.case_id for score in case_scores if score.uncovered_relation_keys]

    summary = {
        "case_count": len(case_scores),
        "relation_judgment_count": relation_total,
        "relation_judgments_scored": relation_covered,
        "relation_judgment_coverage_rate": (relation_covered / relation_total) if relation_total else None,
        "cases_with_prerequisite_gaps_count": len(cases_with_prereq_gaps),
        "cases_with_prerequisite_gaps": cases_with_prereq_gaps,
        "cases_with_uncovered_relations_count": len(cases_with_uncovered_relations),
        "cases_with_uncovered_relations": cases_with_uncovered_relations,
        **rates,
    }

    return {
        "schema_version": "missing_evidence_score_v0.1",
        "summary": summary,
        "cases": [
            {
                "id": score.case_id,
                "prerequisite_gaps": score.prerequisite_gaps,
                "uncovered_relation_keys": score.uncovered_relation_keys,
                "true_positive_missing": score.true_positive,
                "true_negative_present": score.true_negative,
                "false_positive_missing": score.false_positive,
                "false_negative_missing": score.false_negative,
                "judgments": [
                    {
                        "kind": item.kind,
                        "key": item.key,
                        "expected_missing": item.expected_missing,
                        "predicted_missing": item.predicted_missing,
                        "detail": item.detail,
                        "outcome": (
                            None
                            if item.predicted_missing is None
                            else (
                                "TP"
                                if item.expected_missing and item.predicted_missing
                                else "TN"
                                if (not item.expected_missing) and (not item.predicted_missing)
                                else "FP"
                                if (not item.expected_missing) and item.predicted_missing
                                else "FN"
                            )
                        ),
                    }
                    for item in score.judgments
                ],
            }
            for score in case_scores
        ],
    }


def build_synthetic_system(gold_data: dict[str, Any], mode: str) -> dict[str, Any]:
    """Hand-written system outputs for scorer unit checks (not production extract)."""
    cases: list[dict[str, Any]] = []
    for gold in gold_data.get("cases", []):
        case_id = str(gold["id"])
        if mode == "perfect":
            missing_slots = list(gold.get("expected_missing_slots") or [])
            characters = list(gold.get("require_characters") or [])
            scenes = list(gold.get("require_scenes") or [])
            relations = []
            for spec in gold.get("expected_relation_missing") or []:
                relations.append({**spec, "status": "missing", "evidence_status": "missing"})
            for spec in gold.get("expected_relation_present") or []:
                relations.append({**spec, "status": "candidate", "evidence_status": "extracted_from_text"})
            # M2 has empty requires but still needs empty lists
            if case_id == "M2":
                characters, scenes = [], []
        elif mode == "over_missing":
            # Mark everything missing → high FP on present guards
            missing_slots = ["named_characters", "main_scenes"]
            characters = list(gold.get("require_characters") or [])
            scenes = list(gold.get("require_scenes") or [])
            relations = []
            for spec in list(gold.get("expected_relation_missing") or []) + list(
                gold.get("expected_relation_present") or []
            ):
                relations.append({**spec, "status": "missing", "evidence_status": "missing"})
        elif mode == "under_missing":
            # Never mark missing → high FN
            missing_slots = []
            characters = list(gold.get("require_characters") or []) or ["幽灵"]
            scenes = list(gold.get("require_scenes") or []) or ["幽灵场景"]
            if case_id == "M2":
                characters, scenes = ["女人"], ["房间"]
            relations = []
            for spec in list(gold.get("expected_relation_missing") or []) + list(
                gold.get("expected_relation_present") or []
            ):
                relations.append({**spec, "status": "candidate", "evidence_status": "extracted_from_text"})
        else:
            raise ValueError(f"unknown synthetic mode: {mode}")

        cases.append(
            {
                "id": case_id,
                "missing_slots": missing_slots,
                "characters": characters,
                "scenes": scenes,
                "relations": relations,
            }
        )
    return {"schema_version": "missing_evidence_candidates_v0.1", "mode": mode, "cases": cases}


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
        choices=["perfect", "over_missing", "under_missing"],
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
