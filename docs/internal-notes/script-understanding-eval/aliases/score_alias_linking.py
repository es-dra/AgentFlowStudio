#!/usr/bin/env python3
"""Offline scorer for alias / identity-linking proposal clusters.

Inputs:
  1. gold_cases.json from this directory.
  2. Candidate proposal JSON with this reusable shape:

     {
       "schema_version": "alias_identity_linking_candidates_v0.1",
       "cases": [
         {
           "id": "A1",
           "predicted_clusters": [
             {"id": "P1", "mentions": ["陈默", "陈师傅"]},
             {"id": "P2", "mentions": ["李薇"]}
           ]
         }
       ]
     }

The scorer implements the formulas in DESIGN.md:
  - mention universe M = M* ∩ Msys for BCubed and regular cross-gold false merges
  - extraction recall gap is reported separately
  - false split rate counts gold clusters with size >= 2 after intersection with M
  - false merge rate is over cross-gold-cluster forbidden pairs plus must_not_link
  - must_not_link pairs are HARD_FAIL when both surfaces are present in system output
    and placed in the same predicted cluster
  - coverage metrics sit in the same summary as macro F1/FSR/FMR: what share of
    gold multi-mention clusters (size >= 2) actually enter the FSR scoring universe
    (|C ∩ M| >= 2), and which cases have linkable gold but no FSR score

Small clarification from DESIGN.md:
  must_not_link pairs that include a gold-exempt or ambiguous surface, such as A6
  "陈师傅" or A8 "妈", are evaluated when both sides are present in Msys even if
  the extra surface is not in a gold cluster. This preserves the intended hard
  guardrail without forcing those surfaces into the BCubed denominator.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    gold_mentions: int
    system_mentions: int
    scoring_mentions: int
    extraction_recall_gap: list[str]
    linkable_gold_cluster_count: int
    linkable_gold_clusters_scored: int
    linkable_gold_clusters_unscored: list[str]
    fsr_scorable: bool
    bcubed_precision: float | None
    bcubed_recall: float | None
    bcubed_f1: float | None
    false_split_rate: float | None
    false_split_count: int
    false_split_denominator: int
    split_fragment_mean: float | None
    false_merge_rate: float | None
    false_merge_count: int
    false_merge_denominator: int
    hard_fail: bool
    hard_fail_pairs: list[tuple[str, str]]


def _cluster_mentions(cluster: dict[str, Any]) -> list[str]:
    mentions = cluster.get("mentions")
    if not isinstance(mentions, list) or not all(isinstance(m, str) for m in mentions):
        raise ValueError(f"cluster has invalid mentions: {cluster!r}")
    return mentions


def _canonical_pair(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def _index_clusters(clusters: Iterable[dict[str, Any]], *, label: str) -> tuple[dict[str, set[str]], dict[str, str]]:
    by_id: dict[str, set[str]] = {}
    mention_to_cluster: dict[str, str] = {}
    for index, cluster in enumerate(clusters, start=1):
        cluster_id = str(cluster.get("id") or f"{label}{index}")
        mentions = set(_cluster_mentions(cluster))
        if not mentions:
            continue
        duplicate_mentions = mentions.intersection(mention_to_cluster)
        if duplicate_mentions:
            duplicate_text = ", ".join(sorted(duplicate_mentions))
            raise ValueError(f"{label} clusters contain duplicate mention(s): {duplicate_text}")
        by_id[cluster_id] = mentions
        for mention in mentions:
            mention_to_cluster[mention] = cluster_id
    return by_id, mention_to_cluster


def _sys_cluster_for(mention: str, sys_index: dict[str, str]) -> str:
    return sys_index.get(mention, f"__singleton_missing_link__:{mention}")


def _same_sys_cluster(a: str, b: str, sys_index: dict[str, str]) -> bool:
    return a in sys_index and b in sys_index and sys_index[a] == sys_index[b]


def _bcubed(
    universe: set[str],
    gold_clusters: dict[str, set[str]],
    gold_index: dict[str, str],
    sys_clusters: dict[str, set[str]],
    sys_index: dict[str, str],
) -> tuple[float | None, float | None, float | None]:
    if not universe:
        return None, None, None

    precision_sum = 0.0
    recall_sum = 0.0
    for mention in universe:
        gold_set = gold_clusters[gold_index[mention]].intersection(universe)
        sys_set = sys_clusters[sys_index[mention]].intersection(universe)
        overlap = gold_set.intersection(sys_set)
        precision_sum += len(overlap) / len(sys_set)
        recall_sum += len(overlap) / len(gold_set)

    precision = precision_sum / len(universe)
    recall = recall_sum / len(universe)
    if precision == 0 and recall == 0:
        return precision, recall, 0.0
    return precision, recall, (2 * precision * recall) / (precision + recall)


def _false_split(
    universe: set[str],
    gold_clusters: dict[str, set[str]],
    sys_index: dict[str, str],
) -> tuple[float | None, int, int, float | None]:
    denominator = 0
    split_count = 0
    split_fragments: list[int] = []

    for gold_set in gold_clusters.values():
        scoped = gold_set.intersection(universe)
        if len(scoped) < 2:
            continue
        denominator += 1
        covering_sys_clusters = {_sys_cluster_for(mention, sys_index) for mention in scoped}
        fragment_count = len(covering_sys_clusters)
        if fragment_count > 1:
            split_count += 1
            split_fragments.append(fragment_count)

    if denominator == 0:
        return None, split_count, denominator, None
    fragment_mean = sum(split_fragments) / len(split_fragments) if split_fragments else 0.0
    return split_count / denominator, split_count, denominator, fragment_mean


def _false_merge(
    universe: set[str],
    system_mentions: set[str],
    gold_clusters: dict[str, set[str]],
    sys_index: dict[str, str],
    must_not_link: Iterable[Iterable[str]],
) -> tuple[float | None, int, int, bool, list[tuple[str, str]]]:
    forbidden_pairs: set[tuple[str, str]] = set()

    for left_id, right_id in combinations(gold_clusters, 2):
        for left in gold_clusters[left_id].intersection(universe):
            for right in gold_clusters[right_id].intersection(universe):
                forbidden_pairs.add(_canonical_pair(left, right))

    hard_fail_pairs: list[tuple[str, str]] = []
    for raw_pair in must_not_link:
        pair = list(raw_pair)
        if len(pair) != 2 or not all(isinstance(item, str) for item in pair):
            raise ValueError(f"invalid must_not_link pair: {raw_pair!r}")
        left, right = pair
        if left in system_mentions and right in system_mentions:
            canonical = _canonical_pair(left, right)
            forbidden_pairs.add(canonical)
            if _same_sys_cluster(left, right, sys_index):
                hard_fail_pairs.append(canonical)

    false_merge_count = 0
    for left, right in forbidden_pairs:
        if _same_sys_cluster(left, right, sys_index):
            false_merge_count += 1

    denominator = len(forbidden_pairs)
    if denominator == 0:
        return None, false_merge_count, denominator, bool(hard_fail_pairs), sorted(set(hard_fail_pairs))
    return false_merge_count / denominator, false_merge_count, denominator, bool(hard_fail_pairs), sorted(set(hard_fail_pairs))


def _linkable_coverage(
    gold_clusters: dict[str, set[str]],
    universe: set[str],
) -> tuple[int, int, list[str]]:
    """Gold clusters with size >= 2 need a linking judgment.

    A cluster is *scored* for FSR only when at least two of its surfaces are in M.
    Otherwise it is uncovered: missing aliases inflate macro F1/FSR by dropping out.
    """
    linkable = 0
    scored = 0
    unscored_ids: list[str] = []
    for cluster_id, gold_set in gold_clusters.items():
        if len(gold_set) < 2:
            continue
        linkable += 1
        if len(gold_set.intersection(universe)) >= 2:
            scored += 1
        else:
            unscored_ids.append(cluster_id)
    return linkable, scored, unscored_ids


def score_case(gold_case: dict[str, Any], candidate_case: dict[str, Any]) -> CaseScore:
    case_id = str(gold_case["id"])
    gold_clusters, gold_index = _index_clusters(gold_case.get("gold_clusters", []), label=f"{case_id}:gold")
    sys_clusters, sys_index = _index_clusters(candidate_case.get("predicted_clusters", []), label=f"{case_id}:sys")

    gold_mentions = set(gold_index)
    system_mentions = set(sys_index)
    universe = gold_mentions.intersection(system_mentions)
    extraction_recall_gap = sorted(gold_mentions.difference(system_mentions))
    linkable, linkable_scored, unscored_ids = _linkable_coverage(gold_clusters, universe)

    precision, recall, f1 = _bcubed(universe, gold_clusters, gold_index, sys_clusters, sys_index)
    fsr, split_count, split_denominator, fragment_mean = _false_split(universe, gold_clusters, sys_index)
    fmr, merge_count, merge_denominator, hard_fail, hard_fail_pairs = _false_merge(
        universe,
        system_mentions,
        gold_clusters,
        sys_index,
        gold_case.get("must_not_link", []),
    )

    return CaseScore(
        case_id=case_id,
        gold_mentions=len(gold_mentions),
        system_mentions=len(system_mentions),
        scoring_mentions=len(universe),
        extraction_recall_gap=extraction_recall_gap,
        linkable_gold_cluster_count=linkable,
        linkable_gold_clusters_scored=linkable_scored,
        linkable_gold_clusters_unscored=unscored_ids,
        fsr_scorable=fsr is not None,
        bcubed_precision=precision,
        bcubed_recall=recall,
        bcubed_f1=f1,
        false_split_rate=fsr,
        false_split_count=split_count,
        false_split_denominator=split_denominator,
        split_fragment_mean=fragment_mean,
        false_merge_rate=fmr,
        false_merge_count=merge_count,
        false_merge_denominator=merge_denominator,
        hard_fail=hard_fail,
        hard_fail_pairs=hard_fail_pairs,
    )


def score_dataset(gold_data: dict[str, Any], candidate_data: dict[str, Any]) -> dict[str, Any]:
    gold_by_id = {str(case["id"]): case for case in gold_data.get("cases", [])}
    candidates_by_id = {str(case["id"]): case for case in candidate_data.get("cases", [])}
    missing = sorted(set(gold_by_id).difference(candidates_by_id))
    if missing:
        raise ValueError(f"candidate data missing case(s): {', '.join(missing)}")

    case_scores = [score_case(gold_by_id[case_id], candidates_by_id[case_id]) for case_id in sorted(gold_by_id)]

    def macro(values: Iterable[float | None]) -> float | None:
        actual = [value for value in values if value is not None]
        if not actual:
            return None
        return sum(actual) / len(actual)

    linkable_total = sum(score.linkable_gold_cluster_count for score in case_scores)
    linkable_scored = sum(score.linkable_gold_clusters_scored for score in case_scores)
    cases_missing_fsr = [
        score.case_id
        for score in case_scores
        if score.linkable_gold_cluster_count > 0 and not score.fsr_scorable
    ]
    coverage_rate = (linkable_scored / linkable_total) if linkable_total else None

    # Coverage fields sit beside quality macros on purpose: F1 without coverage
    # overstates how much of the alias problem was actually judged.
    summary = {
        "case_count": len(case_scores),
        "hard_fail_case_count": sum(1 for score in case_scores if score.hard_fail),
        "linkable_gold_cluster_count": linkable_total,
        "linkable_gold_clusters_scored": linkable_scored,
        "linkable_cluster_coverage_rate": coverage_rate,
        "cases_missing_fsr_score_count": len(cases_missing_fsr),
        "cases_missing_fsr_score": cases_missing_fsr,
        "macro_bcubed_precision": macro(score.bcubed_precision for score in case_scores),
        "macro_bcubed_recall": macro(score.bcubed_recall for score in case_scores),
        "macro_bcubed_f1": macro(score.bcubed_f1 for score in case_scores),
        "macro_false_split_rate": macro(score.false_split_rate for score in case_scores),
        "macro_false_merge_rate": macro(score.false_merge_rate for score in case_scores),
    }

    return {
        "schema_version": "alias_identity_linking_score_v0.1",
        "summary": summary,
        "cases": [
            {
                "id": score.case_id,
                "gold_mentions": score.gold_mentions,
                "system_mentions": score.system_mentions,
                "scoring_mentions": score.scoring_mentions,
                "extraction_recall_gap": score.extraction_recall_gap,
                "linkable_gold_cluster_count": score.linkable_gold_cluster_count,
                "linkable_gold_clusters_scored": score.linkable_gold_clusters_scored,
                "linkable_gold_clusters_unscored": score.linkable_gold_clusters_unscored,
                "fsr_scorable": score.fsr_scorable,
                "bcubed_precision": score.bcubed_precision,
                "bcubed_recall": score.bcubed_recall,
                "bcubed_f1": score.bcubed_f1,
                "false_split_rate": score.false_split_rate,
                "false_split_count": score.false_split_count,
                "false_split_denominator": score.false_split_denominator,
                "split_fragment_mean": score.split_fragment_mean,
                "false_merge_rate": score.false_merge_rate,
                "false_merge_count": score.false_merge_count,
                "false_merge_denominator": score.false_merge_denominator,
                "hard_fail": score.hard_fail,
                "hard_fail_pairs": [list(pair) for pair in score.hard_fail_pairs],
            }
            for score in case_scores
        ],
    }


def build_synthetic_candidates(gold_data: dict[str, Any], mode: str) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for gold_case in gold_data.get("cases", []):
        case_id = str(gold_case["id"])
        gold_clusters = gold_case.get("gold_clusters", [])

        if mode == "perfect":
            predicted = gold_clusters
        elif mode == "partial_miss":
            predicted = []
            for cluster in gold_clusters:
                mentions = _cluster_mentions(cluster)
                if case_id == "A1":
                    mentions = [mention for mention in mentions if mention != "陈师傅"]
                elif case_id == "A2" and "阿可" in mentions:
                    mentions = ["周可"]
                predicted.append({"id": cluster.get("id"), "mentions": mentions})
        elif mode == "split_aliases":
            predicted = []
            index = 1
            for cluster in gold_clusters:
                for mention in _cluster_mentions(cluster):
                    predicted.append({"id": f"S{index}", "mentions": [mention]})
                    index += 1
        elif mode == "must_not_violation":
            predicted = [dict(cluster) for cluster in gold_clusters]
            if case_id == "A5":
                predicted = [
                    {"id": "BAD1", "mentions": ["陈默", "陈明"]},
                    {"id": "P2", "mentions": ["民警"]},
                    {"id": "P3", "mentions": ["陈先生"]},
                ]
        else:
            raise ValueError(f"unknown synthetic mode: {mode}")

        cases.append({"id": case_id, "predicted_clusters": predicted})

    return {
        "schema_version": "alias_identity_linking_candidates_v0.1",
        "mode": mode,
        "cases": cases,
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
    parser.add_argument("gold", type=Path, help="Path to gold_cases.json")
    parser.add_argument("candidates", nargs="?", type=Path, help="Path to candidate proposal JSON")
    parser.add_argument(
        "--synthetic",
        choices=["perfect", "partial_miss", "split_aliases", "must_not_violation"],
        help="Use built-in hand-written candidate data instead of a candidate file.",
    )
    parser.add_argument("--case", dest="case_id", help="Print only one case score after scoring the full dataset")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args(argv)

    if bool(args.candidates) == bool(args.synthetic):
        parser.error("provide exactly one of a candidate JSON path or --synthetic")

    gold_data = _load_json(args.gold)
    candidate_data = build_synthetic_candidates(gold_data, args.synthetic) if args.synthetic else _load_json(args.candidates)
    result = score_dataset(gold_data, candidate_data)

    if args.case_id:
        matching = [case for case in result["cases"] if case["id"] == args.case_id]
        if not matching:
            raise ValueError(f"case not found in score output: {args.case_id}")
        result = {"schema_version": result["schema_version"], "case": matching[0]}

    indent = 2 if args.pretty else None
    print(json.dumps(_round_floats(result), ensure_ascii=False, indent=indent, sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
