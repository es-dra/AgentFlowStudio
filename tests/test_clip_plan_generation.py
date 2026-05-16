from __future__ import annotations

from narratocut.schemas import ClipPlan, ScriptSegment, ShortVideoScript
from narratocut.slicing_sop import generate_clip_plans_from_scripts


def make_scripts(count: int = 3) -> list[ShortVideoScript]:
    scripts: list[ShortVideoScript] = []
    for index in range(1, count + 1):
        scripts.append(
            ShortVideoScript(
                script_id=f"script_{index:03d}",
                project_id="proj_mock",
                hook_id=f"hook_{index:03d}",
                title=f"第{index}条宣发脚本",
                cover_text="身份反转",
                opening_3s="所有人都以为她输了。",
                segments=[
                    ScriptSegment(segment_type="opening", text="开场反转", duration_sec=3),
                    ScriptSegment(segment_type="body", text="剧情推进", duration_sec=42),
                    ScriptSegment(segment_type="climax", text="悬念收束", duration_sec=10),
                ],
                cta="继续看完整剧情。",
            )
        )
    return scripts


def test_generate_clip_plans_from_scripts_creates_one_plan_per_script() -> None:
    plans = generate_clip_plans_from_scripts(make_scripts())

    assert len(plans) == 3
    assert all(isinstance(plan, ClipPlan) for plan in plans)
    assert [plan.script_id for plan in plans] == ["script_001", "script_002", "script_003"]
    assert all(plan.duration_sec == 55 for plan in plans)
    assert all(plan.render_spec.aspect_ratio == "9:16" for plan in plans)


def test_generate_clip_plans_preserves_script_content_in_segments() -> None:
    [plan] = generate_clip_plans_from_scripts(make_scripts(count=1))

    assert plan.clip_plan_id == "clip_plan_script_001"
    assert plan.project_id == "proj_mock"
    assert plan.hook_id == "hook_001"
    assert plan.title == "第1条宣发脚本"
    assert plan.cover_text == "身份反转"
    assert len(plan.segments) == 3
    assert plan.segments[0].segment_id == "clip_plan_script_001_seg_001"
    assert plan.segments[0].text == "开场反转"
    assert plan.segments[0].start_sec == 0
    assert plan.segments[0].end_sec == 3
    assert plan.voiceover_text == "开场反转\n剧情推进\n悬念收束"
    assert plan.cta_text == "继续看完整剧情。"
