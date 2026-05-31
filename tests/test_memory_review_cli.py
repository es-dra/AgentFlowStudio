from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app


REVIEW_EXAMPLE = Path("examples/agentflow/memory_evidence_reuse_review.example.json")
CANDIDATE_EXAMPLE = Path("examples/agentflow/memory_candidate.example.json")
DECISION_EXAMPLE = Path("examples/agentflow/memory_promotion_decision.example.json")


def test_memory_review_cli_validates_evidence_reuse_without_writing_by_default(tmp_path) -> None:
    review_path = tmp_path / "review.json"
    candidate_path = tmp_path / "candidate.json"
    decision_path = tmp_path / "decision.json"
    review_path.write_text(REVIEW_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    candidate_path.write_text(CANDIDATE_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    decision_path.write_text(DECISION_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "memory-evidence-reuse-review",
            "--review",
            str(review_path),
            "--candidate",
            str(candidate_path),
            "--decision",
            str(decision_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Memory evidence reuse review: passed" in result.output
    assert "Review-only: true" in result.output
    assert "Writes long-term memory: false" in result.output
    assert "Provider calls: not started" in result.output
    assert "Output file: not written" in result.output
    assert str(review_path) not in result.output
    assert str(candidate_path) not in result.output
    assert str(decision_path) not in result.output
    assert {path.name for path in tmp_path.iterdir()} == {"review.json", "candidate.json", "decision.json"}


def test_memory_review_cli_writes_validation_only_when_output_is_explicit(tmp_path) -> None:
    output_path = tmp_path / "validation" / "memory_evidence_reuse_review_validation.json"

    result = CliRunner().invoke(
        app,
        [
            "memory-evidence-reuse-review",
            "--review",
            str(REVIEW_EXAMPLE),
            "--candidate",
            str(CANDIDATE_EXAMPLE),
            "--decision",
            str(DECISION_EXAMPLE),
            "--output",
            str(output_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Output file: written" in result.output
    assert output_path.is_file()
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["artifact_type"] == "agentflow_memory_evidence_reuse_review_validation"
    assert payload["overall_status"] == "passed"
    assert payload["does_not_execute"] is True
    assert payload["writes_long_term_memory"] is False


def test_memory_review_cli_fails_broken_second_pass_chain_without_writing(tmp_path) -> None:
    review = json.loads(REVIEW_EXAMPLE.read_text(encoding="utf-8"))
    review["second_pass_prompt"]["promotion_decision_refs"] = []
    review_path = tmp_path / "broken_review.json"
    review_path.write_text(json.dumps(review, ensure_ascii=False), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "memory-evidence-reuse-review",
            "--review",
            str(review_path),
            "--candidate",
            str(CANDIDATE_EXAMPLE),
            "--decision",
            str(DECISION_EXAMPLE),
        ],
    )

    assert result.exit_code == 1
    assert "Memory evidence reuse review: failed" in result.output
    assert "second_pass_prompt_refs_promotion_decision" in result.output
    assert "Output file: not written" in result.output
    assert list(tmp_path.iterdir()) == [review_path]


def test_memory_review_cli_fails_rejected_decision_reuse(tmp_path) -> None:
    decision = json.loads(DECISION_EXAMPLE.read_text(encoding="utf-8"))
    decision["decision"] = "rejected"
    decision_path = tmp_path / "rejected_decision.json"
    decision_path.write_text(json.dumps(decision, ensure_ascii=False), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "memory-evidence-reuse-review",
            "--review",
            str(REVIEW_EXAMPLE),
            "--candidate",
            str(CANDIDATE_EXAMPLE),
            "--decision",
            str(decision_path),
        ],
    )

    assert result.exit_code == 1
    assert "Memory evidence reuse review: failed" in result.output
    assert "promotion_decision_allows_context_reuse" in result.output
    assert "Provider calls: not started" in result.output


def test_memory_review_cli_accepts_powershell_utf8_bom_json(tmp_path) -> None:
    review_path = tmp_path / "review.json"
    candidate_path = tmp_path / "candidate.json"
    decision_path = tmp_path / "decision.json"
    review_path.write_text("\ufeff" + REVIEW_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    candidate_path.write_text("\ufeff" + CANDIDATE_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    decision_path.write_text("\ufeff" + DECISION_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "memory-evidence-reuse-review",
            "--review",
            str(review_path),
            "--candidate",
            str(candidate_path),
            "--decision",
            str(decision_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Memory evidence reuse review: passed" in result.output
