from __future__ import annotations

import base64
import json
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut.harness.inspection import inspect_run
from narratocut.harness.reviewer import review_run
from narratostudio.posterflow import provider as poster_provider
from narratostudio.posterflow.schemas import (
    ContextAssemblyTrace,
    ContextBundle,
    NextRoundPrompt,
    PosterCandidatesManifest,
    PosterFeedbackSignalLog,
    PosterMemoryCandidates,
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
    assert profile.status == "demo_only"
    assert profile.writes_long_term_memory is False
    assert context_bundle.project_prefix_path == "project_prefix.md"
    assert context_bundle.preference_profile_path == "poster_preference_profile.json"
    assert context_bundle.context_layers["hot"]["project_prefix"] == "project_prefix.md"
    assert set(context_bundle.context_layers["warm"]["memory_refs"]) == set(profile.source_memory_candidates)
    assert context_bundle.cache_plan["cache_key"].startswith(f"{profile.project_id}:1:")
    assert {decision["status"] for decision in context_trace.selection_decisions} == {"included", "excluded"}
    assert "no_rag_configured" in {
        decision["reason"] for decision in context_trace.selection_decisions if decision["status"] == "excluded"
    }
    assert next_prompt.memory_context["preference_profile_path"] == "poster_preference_profile.json"
    assert next_prompt.memory_context["context_bundle_path"] == "context_bundle.json"
    assert "candidate_001.png" in (output_dir / "poster_preview.html").read_text(encoding="utf-8")


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
    assert review["status"] == "passed"
    assert "posterflow_artifacts" in [section["name"] for section in review["sections"]]


def _run_posterflow_workflow(monkeypatch, tmp_path) -> Path:
    def fake_urlopen(request, timeout):
        return FakeResponse()

    monkeypatch.setattr(poster_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("NARRATOCUT_IMAGE_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("NARRATOCUT_IMAGE_API_KEY", "secret-key")
    monkeypatch.setenv("NARRATOCUT_IMAGE_MODEL", "fake-image-model")

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
