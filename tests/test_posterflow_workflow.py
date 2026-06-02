from __future__ import annotations

import base64
import json
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from agentflow_studio.harness.inspection import inspect_run
from agentflow_studio.harness.reviewer import review_run
from agentflow_studio.production.posterflow import provider as poster_provider
from agentflow_studio.production.posterflow.schemas import (
    ContextAssemblyTrace,
    ContextBundle,
    NextRoundPrompt,
    PosterCandidatesManifest,
    PosterFeedbackSignalLog,
    PosterMemoryCandidates,
    PosterModelInvocations,
    PosterPreferenceProfile,
    PosterPromptPack,
)


PNG_B64 = base64.b64encode(
    base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    )
).decode("ascii")


class FakeResponse:
    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type, exc, traceback) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps({"data": [{"b64_json": PNG_B64}, {"b64_json": PNG_B64}, {"b64_json": PNG_B64}]}).encode(
            "utf-8"
        )


def test_posterflow_memory_demo_workflow_generates_visual_artifacts(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)

    expected = [
        "poster_brief.json",
        "poster_plan.json",
        "poster_prompt_pack.json",
        "poster_model_invocations.json",
        "poster_candidates_manifest.json",
        "poster_feedback.jsonl",
        "poster_feedback_signal_log.json",
        "poster_memory_candidates.json",
        "poster_memory_candidates.jsonl",
        "poster_memory_decisions.json",
        "poster_memory_review.jsonl",
        "poster_preference_profile.json",
        "project_prefix.md",
        "context_bundle.json",
        "context_assembly_trace.json",
        "next_round_prompt.json",
        "round_2/poster_prompt_pack.json",
        "round_2/poster_candidates_manifest.json",
        "round_2/poster_model_invocations.json",
        "round_2/image_candidates/candidate_001.png",
        "poster_round_comparison.json",
        "poster_two_round_report.md",
        "poster_report.md",
        "poster_preview.html",
        "manifest.json",
        "run_manifest.json",
        "trace.json",
    ]
    for filename in expected:
        assert (output_dir / filename).is_file(), filename

    manifest = PosterCandidatesManifest.model_validate(_json(output_dir / "poster_candidates_manifest.json"))
    assert len(manifest.candidates) == 3
    assert all((output_dir / candidate.image_path).is_file() for candidate in manifest.candidates)

    PosterPromptPack.model_validate(_json(output_dir / "poster_prompt_pack.json"))
    feedback = PosterFeedbackSignalLog.model_validate(_json(output_dir / "poster_feedback_signal_log.json"))
    memory = PosterMemoryCandidates.model_validate(_json(output_dir / "poster_memory_candidates.json"))
    profile = PosterPreferenceProfile.model_validate(_json(output_dir / "poster_preference_profile.json"))
    context_bundle = ContextBundle.model_validate(_json(output_dir / "context_bundle.json"))
    context_trace = ContextAssemblyTrace.model_validate(_json(output_dir / "context_assembly_trace.json"))
    next_prompt = NextRoundPrompt.model_validate(_json(output_dir / "next_round_prompt.json"))
    raw_feedback = _jsonl(output_dir / "poster_feedback.jsonl")
    memory_candidates = _jsonl(output_dir / "poster_memory_candidates.jsonl")
    memory_review = _jsonl(output_dir / "poster_memory_review.jsonl")

    assert feedback.source_of_truth == "poster_feedback.jsonl"
    assert feedback.is_primary_feedback_store is False
    assert {event["target_id"] for event in raw_feedback} == {"candidate_001", "candidate_002", "candidate_003"}
    assert {event["target_type"] for event in raw_feedback} == {"poster_candidate"}
    assert {candidate["promotion_status"] for candidate in memory_candidates} == {"candidate"}
    assert {candidate.promotion_status for candidate in memory.candidates} == {"candidate"}
    assert {decision["writes_long_term_memory"] for decision in memory_review} == {False}
    assert {decision["review_mode"] for decision in memory_review} == {"demo_human_review_gate"}
    review_decision_ids = {decision["review_id"] for decision in memory_review}
    assert profile.status == "demo_only"
    assert profile.writes_long_term_memory is False
    assert set(profile.source_promotion_decisions) == review_decision_ids
    assert context_bundle.project_prefix_path == "project_prefix.md"
    assert context_bundle.preference_profile_path == "poster_preference_profile.json"
    assert set(context_bundle.source_promotion_decisions) == review_decision_ids
    assert context_bundle.source_artifacts["memory_review"] == "poster_memory_review.jsonl"
    assert context_bundle.source_artifacts["memory_candidates"] == "poster_memory_candidates.jsonl"
    assert context_bundle.context_layers["hot"]["project_prefix"] == "project_prefix.md"
    assert set(context_bundle.context_layers["warm"]["memory_refs"]) == set(profile.source_memory_candidates)
    assert set(context_bundle.context_layers["warm"]["promotion_decision_refs"]) == review_decision_ids
    assert context_bundle.cache_plan["cache_key"].startswith(f"{profile.project_id}:1:")
    assert set(context_bundle.cache_plan["invalidation_refs"]) == set(
        profile.source_memory_candidates + profile.source_promotion_decisions
    )
    assert {decision["status"] for decision in context_trace.selection_decisions} == {"included", "excluded"}
    assert set(context_trace.promotion_decision_refs) == review_decision_ids
    assert "no_rag_configured" in {
        decision["reason"] for decision in context_trace.selection_decisions if decision["status"] == "excluded"
    }
    assert next_prompt.memory_context["preference_profile_path"] == "poster_preference_profile.json"
    assert next_prompt.memory_context["context_bundle_path"] == "context_bundle.json"
    assert set(next_prompt.memory_context["promotion_decision_refs"]) == review_decision_ids
    assert next_prompt.writes_long_term_memory is False
    assert "candidate_001.png" in (output_dir / "poster_preview.html").read_text(encoding="utf-8")

    round_2_prompt = PosterPromptPack.model_validate(_json(output_dir / "round_2/poster_prompt_pack.json"))
    round_2_manifest = PosterCandidatesManifest.model_validate(_json(output_dir / "round_2/poster_candidates_manifest.json"))
    PosterModelInvocations.model_validate(_json(output_dir / "round_2/poster_model_invocations.json"))
    comparison = _json(output_dir / "poster_round_comparison.json")

    assert round_2_prompt.run_id == next_prompt.new_run_id
    assert round_2_prompt.prompt_id == f"{next_prompt.new_run_id}_poster_prompt_001"
    assert round_2_prompt.positive_prompt == next_prompt.composed_positive_prompt
    assert round_2_prompt.context_usage["preference_profile_used"] is True
    assert round_2_prompt.context_usage["project_prefix_used"] is True
    assert set(round_2_prompt.context_usage["memory_refs"]) == set(profile.source_memory_candidates)
    assert round_2_manifest.run_id == next_prompt.new_run_id
    assert round_2_manifest.source_refs["poster_prompt_pack"] == "round_2/poster_prompt_pack.json"
    assert len(round_2_manifest.candidates) == 3
    assert all(candidate.image_path.startswith("round_2/image_candidates/") for candidate in round_2_manifest.candidates)
    assert all((output_dir / candidate.image_path).is_file() for candidate in round_2_manifest.candidates)
    assert comparison["artifact_type"] == "poster_round_comparison"
    assert comparison["round_1"]["run_id"] == manifest.run_id
    assert comparison["round_2"]["run_id"] == round_2_manifest.run_id
    assert comparison["memory_reuse"]["writes_long_term_memory"] is False
    assert set(comparison["memory_reuse"]["memory_refs"]) == set(profile.source_memory_candidates)
    assert set(comparison["memory_reuse"]["promotion_decision_refs"]) == review_decision_ids
    assert [step["stage"] for step in comparison["evidence_chain"]] == [
        "round_1_evidence",
        "candidate_memory",
        "review_decision",
        "context_bundle",
        "round_2_reuse",
        "comparison_output",
    ]
    assert comparison["evidence_chain"][0]["artifact_refs"] == [
        "poster_candidates_manifest.json",
        "poster_feedback.jsonl",
        "poster_feedback_signal_log.json",
    ]
    assert comparison["evidence_chain"][2]["source_refs"]["memory_candidates"] == "poster_memory_candidates.jsonl"
    assert comparison["evidence_chain"][3]["source_refs"]["memory_review"] == "poster_memory_review.jsonl"
    assert comparison["evidence_chain"][3]["source_refs"]["promotion_decision_refs"] == ", ".join(
        sorted(review_decision_ids)
    )
    assert comparison["evidence_chain"][4]["source_refs"]["context_bundle"] == "context_bundle.json"
    assert comparison["evidence_chain"][4]["source_refs"]["promotion_decision_refs"] == ", ".join(
        sorted(review_decision_ids)
    )
    assert {step["writes_long_term_memory"] for step in comparison["evidence_chain"]} == {False}
    assert "demo evidence only" in comparison["validation_boundary"]
    two_round_report = (output_dir / "poster_two_round_report.md").read_text(encoding="utf-8")
    assert "Round 2" in two_round_report
    assert "Evidence Chain" in two_round_report
    assert "candidate_memory" in two_round_report


def test_posterflow_examples_keep_readable_chinese_copy() -> None:
    brief = _json(Path("examples/posterflow/poster_brief.example.json"))
    feedback = _json(Path("examples/posterflow/poster_feedback.example.json"))

    assert "醒来" in brief["text_requirements"]["title"]
    assert "第一集" == brief["text_requirements"]["subtitle"]
    assert "高级" in brief["raw_user_request"]
    assert "电影感" in feedback["signals"][0]["user_note"]


def test_posterflow_inspect_and_review_pass_for_valid_run(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)

    assert inspection["status"] == "pass"
    assert inspection["quality_report"]["summary"]["quality_profile"] == "posterflow_memory_demo"
    assert inspection["quality_report"]["summary"]["quality_feedback_signal_count"] == 0
    assert inspection["quality_report"]["feedback_signals"] == []
    assert review["status"] == "passed"
    assert "posterflow_artifacts" in [section["name"] for section in review["sections"]]
    artifact_statuses = {item["path"]: item["status"] for item in inspection["artifacts"]}
    assert artifact_statuses["round_2/image_candidates/"] == "found"


def _run_posterflow_workflow(monkeypatch, tmp_path) -> Path:
    def fake_urlopen(request, timeout):
        return FakeResponse()

    monkeypatch.setattr(poster_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("AFS_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("AFS_IMAGE_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("AFS_IMAGE_API_KEY", "secret-key")
    monkeypatch.setenv("AFS_IMAGE_MODEL", "fake-image-model")

    output_dir = tmp_path / "poster_run"
    status, manifest_path = run_workflow_from_cli(
        Path("workflows/posterflow_memory_demo.yaml"),
        Path("examples/posterflow/poster_brief.example.json"),
        output_dir,
    )
    assert status == "success"
    assert manifest_path == output_dir / "manifest.json"
    return output_dir


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
