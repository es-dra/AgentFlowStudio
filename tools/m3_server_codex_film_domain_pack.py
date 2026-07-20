"""Controlled film evaluator/domain pack; never a product fixture or runtime input."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentflow_studio.m3_server_codex_quality import evaluate_artifact_root, evaluate_ledger, materialize_evidence

ROLES = {"story_editor", "director_cinematographer_editor", "asset_production_continuity", "agent_context_safety_product"}


def load_external_corpus(*, corpus_root: Path | str | None = None, ledger: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
    """Accept an explicit ledger or a domain pack JSON below /tmp; do not author cases."""
    if (corpus_root is None) == (ledger is None): raise ValueError("supply exactly one of corpus_root or ledger")
    if ledger is not None: return ledger
    root = Path(corpus_root).resolve()
    if root != Path("/tmp") and not str(root).startswith("/tmp/"): raise ValueError("external corpus root must be under /tmp")
    value = json.loads((root / "domain_pack.json").read_text(encoding="utf-8"))
    if not isinstance(value, dict): raise ValueError("domain_pack.json must contain an object")
    return value


def _professional_reviews(case_id: str, *, status: str, assessment: str) -> list[dict[str, Any]]:
    """Metadata-only review coverage for a failed controlled attempt."""
    return [{"role": role, "review_run_id": f"strict-ledger-{case_id.lower()}-{role}", "status": status,
             "evidence_refs": [f"controlled-ledger:{case_id}"], "assessment": assessment}
            for role in sorted(ROLES)]


def controlled_attempt_ledger() -> dict[str, Any]:
    """Known current-attempt defects, recorded as evidence without altering attempts."""
    return {"provider_dispatch_count": 0, "remote_dispatch_count": 0, "cost_usd": 0, "cases": [
        {"case_id": "A", "recorded_defects": [
            {"severity": "P0", "issue": "wrong model label"}, {"severity": "P0", "issue": "false timestamp"},
            {"severity": "P0", "issue": "digest mismatch"}, {"severity": "P0", "issue": "rollback refs lack artifact hashes"},
            {"severity": "P0", "issue": "unauditable knowledge provenance"}, {"severity": "P1", "issue": "dialogue weakness"},
            {"severity": "P1", "issue": "relationship weakness"}, {"severity": "P1", "issue": "no artifact-level fallback"},
            {"severity": "P0", "issue": "rights TBD"}],
         "professional_reviews": _professional_reviews("A", status="not_assessable_strict_fail",
                                                          assessment="Artifact is structurally unreliable; creative scoring is withheld.")},
        {"case_id": "B", "recorded_defects": [{"severity": "P0", "issue": "single oversized call timed out"}, {"severity": "P0", "issue": "no artifact"}],
         "professional_reviews": _professional_reviews("B", status="not_assessable_generation_failure",
                                                          assessment="Generation produced no artifact; this role cannot assess creative quality.")},
        {"case_id": "C", "issue_ledger": [{"status": "PASS"}], "replan": {"scope": "affected_only"}, "recorded_defects": [
            {"severity": "P1", "issue": "all ten shots 6 seconds"}, {"severity": "P1", "issue": "English-heavy"},
            {"severity": "P0", "issue": "injected 4-15 range"}, {"severity": "P1", "issue": "broad replan"},
            {"severity": "P1", "issue": "trope-heavy story"}],
         "professional_reviews": _professional_reviews("C", status="not_assessable_strict_fail",
                                                          assessment="Detected plan defects prevent calibrated creative scoring.")}
    ]}


def main() -> int:
    parser = argparse.ArgumentParser(description="Controlled, provider-free film-domain evaluator.")
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate"); generate.add_argument("artifact_root")
    source = generate.add_mutually_exclusive_group(required=True)
    source.add_argument("--corpus-root"); source.add_argument("--ledger")
    evaluate = sub.add_parser("evaluate"); evaluate.add_argument("artifact_root")
    ledger_command = sub.add_parser("evaluate-current-ledger"); ledger_command.add_argument("--output-root")
    args = parser.parse_args()
    if args.command == "generate":
        supplied = load_external_corpus(corpus_root=args.corpus_root) if args.corpus_root else load_external_corpus(ledger=json.loads(Path(args.ledger).read_text(encoding="utf-8")))
        result = {"artifact_root": materialize_evidence(args.artifact_root, supplied), "status": "generated"}
    elif args.command == "evaluate": result = evaluate_artifact_root(args.artifact_root, expected_roles=ROLES)
    else:
        result = evaluate_ledger(controlled_attempt_ledger(), expected_roles=ROLES)
        if args.output_root:
            output = Path(args.output_root).resolve()
            if output != Path("/tmp") and not str(output).startswith("/tmp/"):
                raise ValueError("ledger output root must be under /tmp")
            output.mkdir(parents=True, exist_ok=True)
            (output / "controlled_attempt_issue_ledger.json").write_text(
                json.dumps(controlled_attempt_ledger(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            (output / "controlled_attempt_evaluation_report.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            result["ledger_output_root"] = str(output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    if args.command == "generate":
        return 0
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__": raise SystemExit(main())
