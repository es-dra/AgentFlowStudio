from __future__ import annotations

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

from agentflow.memory.production_feedback import (
    FEEDBACK_CAPTURE_KIND,
    build_production_memory_feedback_capture,
)


EXAMPLE_PATH = Path("examples/agentflow/production_memory_loop.example.json")


def load_example() -> dict:
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def test_feedback_capture_drafts_candidate_and_pending_promotion_without_writes() -> None:
    payload = load_example()
    capture = build_production_memory_feedback_capture(
        payload,
        target_ref="artifact:approved_storyboard:v1",
        decision="accepted",
        summary="Carry the reviewed storyboard structure into the next pass.",
        reviewer_role="operator",
        created_at="2026-06-02T00:00:00+08:00",
    )

    assert capture["kind"] == FEEDBACK_CAPTURE_KIND
    assert capture["provider_calls_started"] is False
    assert capture["writes_long_term_memory"] is False
    assert capture["does_not_execute"] is True
    assert capture["feedback_event"]["target_ref"] == "artifact:approved_storyboard:v1"
    assert capture["feedback_event"]["decision"] == "accepted"
    assert capture["memory_candidate"]["status"] == "candidate"
    assert capture["memory_candidate"]["candidate_is_promoted_memory"] is False
    assert capture["promotion_decision_template"]["decision"] == "pending"
    assert capture["promotion_decision_template"]["template_only"] is True
    assert capture["promotion_decision_template"]["writes_long_term_memory"] is False


def test_feedback_capture_missing_target_ref_fails() -> None:
    with pytest.raises(ValueError, match="target_ref does not exist"):
        build_production_memory_feedback_capture(
            load_example(),
            target_ref="artifact:missing",
            decision="accepted",
            summary="Missing target should fail.",
            reviewer_role="operator",
            created_at="2026-06-02T00:00:00+08:00",
        )


def test_feedback_capture_rejects_private_paths_or_media_refs() -> None:
    with pytest.raises(ValueError, match="unsafe"):
        build_production_memory_feedback_capture(
            load_example(),
            target_ref="artifact:approved_storyboard:v1",
            decision="accepted",
            summary="Do not include D:\\Private\\source.mp4 in a memory candidate.",
            reviewer_role="operator",
            created_at="2026-06-02T00:00:00+08:00",
        )


def test_feedback_capture_does_not_mutate_source_loop() -> None:
    payload = load_example()
    before = deepcopy(payload)

    build_production_memory_feedback_capture(
        payload,
        target_ref="artifact:approved_storyboard:v1",
        decision="accepted",
        summary="Capture this as candidate evidence.",
        reviewer_role="operator",
        created_at="2026-06-02T00:00:00+08:00",
    )

    assert payload == before


def test_cli_draft_feedback_writes_draft_packet_without_promoting(tmp_path: Path) -> None:
    output_dir = tmp_path / "feedback_capture"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "apps.cli.main",
            "production-memory-loop-draft-feedback",
            str(EXAMPLE_PATH),
            "--target-ref",
            "artifact:approved_storyboard:v1",
            "--decision",
            "accepted",
            "--summary",
            "Carry the reviewed storyboard structure into the next pass.",
            "--created-at",
            "2026-06-02T00:00:00+08:00",
            "--output",
            str(output_dir),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "Production memory feedback capture: draft" in result.stdout
    packet = json.loads((output_dir / "production_memory_feedback_capture.json").read_text(encoding="utf-8"))
    candidate = json.loads((output_dir / "memory_candidate.json").read_text(encoding="utf-8"))
    decision = json.loads((output_dir / "promotion_decision_template.json").read_text(encoding="utf-8"))
    assert packet["writes_long_term_memory"] is False
    assert candidate["candidate_is_promoted_memory"] is False
    assert decision["decision"] == "pending"
