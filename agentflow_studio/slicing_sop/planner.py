from __future__ import annotations

from agentflow_studio.schemas import ClipPlan, ClipSegment, ScriptSegment, ShortVideoScript


def generate_clip_plans_from_scripts(scripts: list[ShortVideoScript]) -> list[ClipPlan]:
    """Create deterministic mock clip plans from short-video scripts."""
    return [_clip_plan_from_script(script) for script in scripts]


def _clip_plan_from_script(script: ShortVideoScript) -> ClipPlan:
    segments: list[ClipSegment] = []
    cursor = 0.0
    plan_id = f"clip_plan_{script.script_id}"
    script_segments = script.segments or []

    if not script_segments:
        script_segments = [
            ScriptSegment(
                segment_type="opening",
                text=script.opening_3s,
                duration_sec=float(script.target_duration_sec),
            )
        ]

    voiceover_lines: list[str] = []
    for index, segment in enumerate(script_segments, start=1):
        duration = float(segment.duration_sec or _fallback_duration(script, len(script_segments)))
        end_sec = cursor + duration
        text = segment.text
        voiceover_lines.append(text)
        segments.append(
            ClipSegment(
                segment_id=f"{plan_id}_seg_{index:03d}",
                source_video=f"mock://{script.script_id}",
                start_sec=cursor,
                end_sec=end_sec,
                text=text,
                metadata={"script_segment_type": segment.segment_type},
            )
        )
        cursor = end_sec

    return ClipPlan(
        clip_plan_id=plan_id,
        project_id=script.project_id,
        hook_id=script.hook_id,
        script_id=script.script_id,
        duration_sec=cursor,
        title=script.title,
        cover_text=script.cover_text,
        segments=segments,
        voiceover_text="\n".join(voiceover_lines),
        cta_text=script.cta,
        output_name=f"{plan_id}.txt",
        metadata={
            "platform": script.platform,
            "style": script.style,
            "source": "mock_phase5_planner",
        },
    )


def _fallback_duration(script: ShortVideoScript, segment_count: int) -> float:
    return max(float(script.target_duration_sec) / max(segment_count, 1), 1.0)
