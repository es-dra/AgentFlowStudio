from __future__ import annotations

import base64
import json
from pathlib import Path

from apps.cli.workflow_commands import run_workflow_from_cli
from narratocut.harness.inspection import inspect_run
from narratocut.harness.reviewer import review_run
from narratostudio.posterflow import provider as poster_provider


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


def test_posterflow_review_fails_when_candidate_image_is_missing(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    (output_dir / "image_candidates" / "candidate_001.png").unlink()

    inspection = inspect_run(output_dir)
    review = review_run(output_dir)
    signals = inspection["quality_report"]["feedback_signals"]

    assert inspection["status"] == "fail"
    assert review["status"] == "failed"
    assert "posterflow_candidate_images_exist" in _failed_ids(review)
    assert inspection["quality_report"]["summary"]["quality_feedback_signal_count"] >= 1
    assert {
        signal["source_check_id"]
        for signal in signals
    } >= {"posterflow_candidate_images_exist"}
    candidate_signal = next(
        signal for signal in signals if signal["source_check_id"] == "posterflow_candidate_images_exist"
    )
    assert candidate_signal["failure_category"] == "generated_artifact_failure"
    assert candidate_signal["status"] == "candidate"
    assert candidate_signal["writes_long_term_memory"] is False
    assert candidate_signal["evidence_refs"] == ["quality_report.json"]


def test_posterflow_review_fails_when_feedback_references_unknown_candidate(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    feedback = _json(output_dir / "poster_feedback_signal_log.json")
    feedback["signals"][0]["candidate_id"] = "missing_candidate"
    (output_dir / "poster_feedback_signal_log.json").write_text(
        json.dumps(feedback, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_feedback_candidate_refs_known" in _failed_ids(review)


def test_posterflow_review_fails_when_profile_uses_unapproved_memory(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    profile = _json(output_dir / "poster_preference_profile.json")
    profile["source_memory_candidates"].append("missing_memory_candidate")
    (output_dir / "poster_preference_profile.json").write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_profile_uses_accepted_memory" in _failed_ids(review)


def test_posterflow_review_fails_when_memory_review_links_unknown_candidate(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    review_events = _jsonl(output_dir / "poster_memory_review.jsonl")
    review_events[0]["memory_candidate_id"] = "missing_memory_candidate"
    (output_dir / "poster_memory_review.jsonl").write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in review_events) + "\n",
        encoding="utf-8",
    )

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_memory_review_refs_candidates" in _failed_ids(review)
    assert "posterflow_memory_review_matches_decisions" in _failed_ids(review)


def test_posterflow_review_fails_when_context_bundle_loses_promotion_decision_refs(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    bundle = _json(output_dir / "context_bundle.json")
    bundle["source_promotion_decisions"] = []
    bundle["context_layers"]["warm"]["promotion_decision_refs"] = []
    (output_dir / "context_bundle.json").write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_context_bundle_refs_promotion_decisions" in _failed_ids(review)


def test_posterflow_review_fails_when_next_prompt_loses_promotion_decision_refs(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    next_prompt = _json(output_dir / "next_round_prompt.json")
    next_prompt["memory_context"]["promotion_decision_refs"] = []
    (output_dir / "next_round_prompt.json").write_text(
        json.dumps(next_prompt, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_next_prompt_refs_promotion_decisions" in _failed_ids(review)


def test_posterflow_review_fails_when_feedback_signal_replaces_raw_feedback(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    (output_dir / "poster_feedback.jsonl").unlink()

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_poster_feedback_exists" in _failed_ids(review)
    assert "posterflow_feedback_source_of_truth_is_raw_jsonl" in _failed_ids(review)


def test_posterflow_review_fails_when_memory_review_claims_durable_write(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    review_events = _jsonl(output_dir / "poster_memory_review.jsonl")
    review_events[0]["writes_long_term_memory"] = True
    (output_dir / "poster_memory_review.jsonl").write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in review_events) + "\n",
        encoding="utf-8",
    )

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_memory_review_no_long_term_write" in _failed_ids(review)


def test_posterflow_review_fails_when_context_trace_points_to_wrong_bundle(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    trace = _json(output_dir / "context_assembly_trace.json")
    trace["bundle_id"] = "wrong_bundle"
    (output_dir / "context_assembly_trace.json").write_text(
        json.dumps(trace, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_context_trace_refs_bundle" in _failed_ids(review)


def test_posterflow_review_fails_when_round_2_manifest_breaks_memory_reuse(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    comparison = _json(output_dir / "poster_round_comparison.json")
    comparison["round_2"]["candidate_images"] = []
    (output_dir / "poster_round_comparison.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_round_2_comparison_candidate_images_match" in _failed_ids(review)


def test_posterflow_review_fails_when_evidence_chain_loses_review_decision(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    comparison = _json(output_dir / "poster_round_comparison.json")
    review_step = next(step for step in comparison["evidence_chain"] if step["stage"] == "review_decision")
    review_step["artifact_refs"] = ["poster_memory_candidates.jsonl"]
    (output_dir / "poster_round_comparison.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_evidence_chain_review_decision_refs_review" in _failed_ids(review)


def test_posterflow_review_fails_when_evidence_chain_loses_promotion_decision_refs(monkeypatch, tmp_path) -> None:
    output_dir = _run_posterflow_workflow(monkeypatch, tmp_path)
    comparison = _json(output_dir / "poster_round_comparison.json")
    reuse_step = next(step for step in comparison["evidence_chain"] if step["stage"] == "round_2_reuse")
    reuse_step["source_refs"].pop("promotion_decision_refs", None)
    (output_dir / "poster_round_comparison.json").write_text(
        json.dumps(comparison, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    inspect_run(output_dir)
    review = review_run(output_dir)

    assert review["status"] == "failed"
    assert "posterflow_evidence_chain_reuse_refs_promotion_decisions" in _failed_ids(review)


def _run_posterflow_workflow(monkeypatch, tmp_path) -> Path:
    def fake_urlopen(request, timeout):
        return FakeResponse()

    monkeypatch.setattr(poster_provider.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setenv("NARRATOCUT_ALLOW_REMOTE_IMAGE", "true")
    monkeypatch.setenv("NARRATOCUT_IMAGE_BASE_URL", "https://example.test/v1")
    monkeypatch.setenv("NARRATOCUT_IMAGE_API_KEY", "secret-key")
    monkeypatch.setenv("NARRATOCUT_IMAGE_MODEL", "fake-image-model")

    output_dir = tmp_path / "poster_run"
    status, _manifest_path = run_workflow_from_cli(
        Path("workflows/posterflow_memory_demo.yaml"),
        Path("examples/posterflow/poster_brief.example.json"),
        output_dir,
    )
    assert status == "success"
    return output_dir


def _failed_ids(review: dict) -> set[str]:
    return {
        check["id"]
        for section in review["sections"]
        for check in section["checks"]
        if check["status"] == "failed"
    }


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
