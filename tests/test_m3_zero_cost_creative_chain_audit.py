from __future__ import annotations

import json
from pathlib import Path

from apps.api.runtime_m3_zero_cost_kernel import evaluate_zero_cost_creative_chain_corpus
from tools.evaluate_m3_zero_cost_creative_chain import evaluate


ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "tests/fixtures/m3_zero_cost_creative_chain_cases.json"


def _corpus() -> dict:
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def test_m3_original_corpus_covers_required_cases_and_adversarial_variants() -> None:
    corpus = _corpus()
    assert corpus["provenance"]["authoring_mode"] == "server_codex_original"
    assert corpus["provenance"]["copyright_source_text_copied"] is False
    assert corpus["provenance"]["provider_dispatch_count"] == 0
    assert len(corpus["cases"]) >= 5
    assert len(corpus["adversarial_variants"]) >= 10
    categories = " ".join(case["category"] for case in corpus["cases"])
    for marker in ("60-90", "45-75", "2-3", "30-60", "90-180"):
        assert marker in categories


def test_m3_creative_chain_case_contracts_pass_without_provider_or_template_pollution() -> None:
    corpus = _corpus()
    report = evaluate_zero_cost_creative_chain_corpus(corpus)
    assert report["verdict"] == "PASS", report["findings"]
    assert report["P0"] == 0
    assert report["P1"] == 0
    assert report["provider_dispatch_count"] == 0
    shot_counts = [len(case["story_plan_candidate"]["shots"]) for case in corpus["cases"]]
    assert len(set(shot_counts)) > 1
    for case in corpus["cases"]:
        durations = [float(shot["duration_seconds"]) for shot in case["story_plan_candidate"]["shots"]]
        assert not (len(durations) == 4 and all(duration == 15 for duration in durations))
        assert len(set(durations)) > 1
        assert case["agent_chat_lifecycle"]["states"] == ["preview", "confirmed", "receipt", "undo"]
        assert case["agent_chat_lifecycle"]["provider_dispatch_count"] == 0
        assert case["agent_chat_lifecycle"]["storyboard_write"] is False
        assert case["agent_chat_lifecycle"]["raw_command_visible_default"] is False
        affected = set(case["affected_only_replan"]["affected_ids"])
        preserved = set(case["affected_only_replan"]["preserved_ids"])
        assert affected
        assert preserved
        assert not affected & preserved


def test_m3_independent_evaluator_passes_exact_contract(tmp_path) -> None:
    report = evaluate(ROOT, CORPUS_PATH)
    assert report["verdict"] == "PASS", report["findings"]
    assert report["P0"] == 0
    assert report["P1"] == 0
    assert report["case_count"] >= 5
    assert report["adversarial_variant_count"] >= 10
    assert report["provider_dispatch_count"] == 0
    assert report["remote_dispatch_count"] == 0
