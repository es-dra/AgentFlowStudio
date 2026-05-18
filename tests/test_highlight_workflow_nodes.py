from __future__ import annotations

import json

import pytest

from narratocut.schemas import ClipPlan, HighlightPlan
from narratocut.workflow_engine import WorkflowContext
from narratocut.workflow_engine.definitions import WorkflowStepDefinition
from narratocut.workflow_engine.highlight_nodes import (
    detect_highlights_node,
    generate_highlight_clip_plan_node,
    load_script_node,
    load_transcript_node,
    rank_highlights_by_roi_node,
    write_clip_plan_node,
    write_highlight_plan_node,
)


def test_script_highlight_nodes_write_ranked_highlight_plan_without_clip_plan(tmp_path) -> None:
    context = _context(tmp_path, inputs={"script_path": "examples/demo_highlight/script.txt"})

    load_script_node(_step("load_script", inputs={"script": "script_path"}), context)
    detect_highlights_node(
        _step(
            "detect_highlights",
            inputs={"input_mode": "script_only", "script_text": "script_text", "max_highlights": 3},
        ),
        context,
    )
    rank_highlights_by_roi_node(_step("rank_highlights", inputs={"highlight_plan": "highlight_plan"}), context)
    artifacts = write_highlight_plan_node(
        _step(
            "write_highlight_plan",
            inputs={"highlight_plan": "highlight_plan"},
            outputs={"highlight_plan": "highlight_plan.json"},
        ),
        context,
    )

    assert artifacts == ["highlight_plan.json"]
    assert "clip_plan" not in context.artifacts
    highlight_plan = HighlightPlan.model_validate(
        json.loads((context.output_dir / "highlight_plan.json").read_text(encoding="utf-8"))
    )
    assert highlight_plan.input_mode == "script_only"
    assert all(highlight.start_time is None for highlight in highlight_plan.highlights)
    assert all("ranking_factors" in highlight.metadata for highlight in highlight_plan.highlights)


def test_transcript_highlight_nodes_write_highlight_plan_and_clip_plan(tmp_path) -> None:
    context = _context(
        tmp_path,
        inputs={
            "transcript_path": "examples/demo_highlight/transcript.json",
            "source_video": "input.mp4",
        },
    )

    load_transcript_node(_step("load_transcript", inputs={"transcript": "transcript_path"}), context)
    detect_highlights_node(
        _step(
            "detect_highlights",
            inputs={"input_mode": "timestamped_transcript", "transcript": "transcript", "max_highlights": 3},
        ),
        context,
    )
    rank_highlights_by_roi_node(_step("rank_highlights", inputs={"highlight_plan": "highlight_plan"}), context)
    generate_highlight_clip_plan_node(
        _step(
            "generate_clip_plan",
            inputs={"highlight_plan": "highlight_plan", "source_video": "source_video"},
        ),
        context,
    )
    write_highlight_plan_node(
        _step(
            "write_highlight_plan",
            inputs={"highlight_plan": "highlight_plan"},
            outputs={"highlight_plan": "highlight_plan.json"},
        ),
        context,
    )
    write_clip_plan_node(
        _step("write_clip_plan", inputs={"clip_plan": "clip_plan"}, outputs={"clip_plan": "clip_plan.json"}),
        context,
    )

    highlight_plan = HighlightPlan.model_validate(
        json.loads((context.output_dir / "highlight_plan.json").read_text(encoding="utf-8"))
    )
    clip_plan = ClipPlan.model_validate(json.loads((context.output_dir / "clip_plan.json").read_text(encoding="utf-8")))

    assert highlight_plan.input_mode == "timestamped_transcript"
    assert all(highlight.start_time is not None for highlight in highlight_plan.highlights)
    assert len(clip_plan.segments) == len(highlight_plan.highlights)
    assert clip_plan.segments[0].metadata["highlight_id"] == highlight_plan.highlights[0].highlight_id
    assert clip_plan.segments[0].metadata["ranking_factors"]["final_score"] >= 0


def test_generate_highlight_clip_plan_node_rejects_script_only_plan(tmp_path) -> None:
    context = _context(
        tmp_path,
        inputs={"script_path": "examples/demo_highlight/script.txt", "source_video": "input.mp4"},
    )
    load_script_node(_step("load_script", inputs={"script": "script_path"}), context)
    detect_highlights_node(
        _step("detect_highlights", inputs={"input_mode": "script_only", "script_text": "script_text"}),
        context,
    )

    with pytest.raises(ValueError, match="script_only"):
        generate_highlight_clip_plan_node(
            _step("generate_clip_plan", inputs={"highlight_plan": "highlight_plan", "source_video": "source_video"}),
            context,
        )


def test_load_transcript_node_validates_transcript_schema(tmp_path) -> None:
    transcript_path = tmp_path / "bad_transcript.json"
    transcript_path.write_text('{"transcript_id": "bad", "segments": []}', encoding="utf-8")
    context = _context(tmp_path, inputs={"transcript_path": str(transcript_path)})

    with pytest.raises(ValueError, match="Transcript schema"):
        load_transcript_node(_step("load_transcript", inputs={"transcript": "transcript_path"}), context)


def _context(tmp_path, *, inputs: dict[str, object]) -> WorkflowContext:
    return WorkflowContext(
        run_id="run_highlight_nodes",
        workflow_name="highlight_nodes",
        output_dir=tmp_path / "run",
        inputs=inputs,
    )


def _step(
    step_id: str,
    *,
    inputs: dict[str, object] | None = None,
    outputs: dict[str, str] | None = None,
) -> WorkflowStepDefinition:
    return WorkflowStepDefinition(
        id=step_id,
        type=step_id,
        inputs=inputs or {},
        outputs=outputs or {},
    )
