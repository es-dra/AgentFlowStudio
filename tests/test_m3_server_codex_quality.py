from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

from agentflow_studio.m3_server_codex_quality import (evaluate_artifact_root, evaluation_target_digest,
    materialize_evidence, staged_generation_contract)
from tools import m3_server_codex_film_domain_pack as film_pack
from tools.m3_server_codex_film_domain_pack import ROLES, controlled_attempt_ledger, load_external_corpus


def _corpus() -> dict:
    stage_metadata = {stage: {"generation_run_id": f"gen-{stage}", "output_digest": f"digest-{stage}"} for stage in
                      ("script", "understanding_assets", "story_plan", "deterministic_assembly_validation")}
    stage_metadata["deterministic_assembly_validation"]["assembly_validation"] = {
        "shots": [{"duration_seconds": 3}, {"duration_seconds": 4}, {"duration_seconds": 5}], "declared_total_duration_seconds": 12,
        "manifest_shot_ids": ["s1", "s2", "s3"], "covered_shot_ids": ["s1", "s2", "s3"], "referenced_asset_ids": ["a1"],
        "resolved_asset_ids": ["a1"], "referenced_ref_ids": ["r1"], "resolved_ref_ids": ["r1"],
        "chinese_professional_fields": ["镜头连续性"], "shot_count_range": [3, 3], "shot_count_range_source_constraint": "brief-constraint"}
    manifests = staged_generation_contract("synthetic", stage_metadata); target = evaluation_target_digest(manifests)
    reports = [{"role": role, "evaluator_run_id": f"eval-{role}", "target_digest": target, "evidence_refs": ["manifest:story_plan"],
                "criterion_findings": [f"finding-{index}"], "score": 70 + index, "score_rationale": f"rationale-{index}",
                "provider_dispatch_count": 0, "remote_dispatch_count": 0, "cost_usd": 0}
               for index, role in enumerate(sorted(ROLES))]
    return {"model_surface": "server_codex", "provider_dispatch_count": 0, "remote_dispatch_count": 0, "cost_usd": 0,
            "cases": [{"case_id": "synthetic", "context_provenance": {"knowledge_provenance_refs": ["k1"], "provider_dispatch_count": 0, "cost_usd": 0},
                       "issue_ledger": [{"status": "OPEN", "issue_id": "i1"}], "manifests": manifests, "evaluation_reports": reports}]}


def _root(tmp_path: Path, corpus: dict | None = None) -> Path:
    return Path(materialize_evidence(tmp_path, corpus or _corpus()))


def test_minimal_domain_neutral_evidence_passes(tmp_path):
    assert evaluate_artifact_root(_root(tmp_path), expected_case_count=1, expected_roles=ROLES)["verdict"] == "PASS"


@pytest.mark.parametrize("mutation", [
    lambda c: c.update(model_surface="wrong"), lambda c: c["cases"][0]["context_provenance"].update(provider_dispatch_count=1),
    lambda c: c.update(writes_memory=True), lambda c: c["cases"][0].update(issue_ledger=[]),
    lambda c: c["cases"][0]["evaluation_reports"][0].update(evaluator_run_id="gen-script"),
    lambda c: c["cases"][0]["evaluation_reports"][1].update(evaluator_run_id=c["cases"][0]["evaluation_reports"][0]["evaluator_run_id"]),
    lambda c: c["cases"][0]["evaluation_reports"][0].update(target_digest="bad"),
    lambda c: c["cases"][0]["evaluation_reports"][0].update(evidence_refs=[]),
    lambda c: c["cases"][0]["evaluation_reports"][1].update(score=c["cases"][0]["evaluation_reports"][0]["score"], criterion_findings=c["cases"][0]["evaluation_reports"][0]["criterion_findings"], score_rationale=c["cases"][0]["evaluation_reports"][0]["score_rationale"]),
    lambda c: c["cases"][0]["manifests"][3]["assembly_validation"].update(shots=[{"duration_seconds": 6}] * 4, declared_total_duration_seconds=24),
    lambda c: c["cases"][0]["manifests"][3]["assembly_validation"].update(shot_count_range_source_constraint=None),
    lambda c: c["cases"][0]["manifests"][3]["assembly_validation"].update(resolved_asset_ids=[]),
    lambda c: c["cases"][0]["manifests"][3]["assembly_validation"].update(covered_shot_ids=["s1"]),
    lambda c: c["cases"][0]["manifests"][3]["assembly_validation"].update(declared_total_duration_seconds=99),
    lambda c: c["cases"][0].update(replan={"scope": "affected_only"}),
    lambda c: c["cases"][0]["manifests"][3]["assembly_validation"].update(chinese_professional_fields=["English only"]),
    lambda c: c["cases"][0].update(issue_ledger=[{"status": "PASS"}]),
])
def test_each_strict_gate_mutation_fails(tmp_path, mutation):
    corpus = copy.deepcopy(_corpus()); mutation(corpus)
    assert evaluate_artifact_root(_root(tmp_path, corpus), expected_roles=ROLES)["verdict"] == "FAIL"


def test_old_82_identical_report_pattern_fails(tmp_path):
    corpus = _corpus()
    for report in corpus["cases"][0]["evaluation_reports"]:
        report.update(score=82, criterion_findings=["Controlled draft reviewed against film-domain rubric."], score_rationale="same")
    assert evaluate_artifact_root(_root(tmp_path, corpus), expected_roles=ROLES)["verdict"] == "FAIL"


def test_external_corpus_must_be_tmp_and_explicit(tmp_path):
    (tmp_path / "domain_pack.json").write_text(json.dumps(_corpus()), encoding="utf-8")
    assert load_external_corpus(corpus_root=tmp_path)["cases"]
    with pytest.raises(ValueError): load_external_corpus()


def test_current_controlled_ledger_is_fail_with_counts():
    from agentflow_studio.m3_server_codex_quality import evaluate_ledger
    result = evaluate_ledger(controlled_attempt_ledger(), expected_roles=ROLES)
    assert result["verdict"] == "FAIL"
    assert (result["P0"], result["P1"]) == (11, 7)


def test_controlled_ledger_requires_all_professional_roles():
    from agentflow_studio.m3_server_codex_quality import evaluate_ledger
    ledger = controlled_attempt_ledger()
    ledger["cases"][1]["professional_reviews"].pop()
    result = evaluate_ledger(ledger, expected_roles=ROLES)
    assert result["verdict"] == "FAIL"
    assert any(item["issue"] == "professional review role coverage missing or duplicated" for item in result["findings"])


def test_generate_cli_returns_success_without_verdict(tmp_path, monkeypatch, capsys):
    ledger_path = tmp_path / "ledger.json"
    ledger_path.write_text(json.dumps(_corpus()), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["film-pack", "generate", str(tmp_path), "--ledger", str(ledger_path)])
    assert film_pack.main() == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "generated"
    assert Path(output["artifact_root"]).resolve().is_relative_to(tmp_path.resolve())
