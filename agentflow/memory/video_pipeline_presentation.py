from __future__ import annotations

from pathlib import Path
from typing import Any

from agentflow_studio.utils import write_json

from agentflow.memory.video_pipeline import PROTOCOL_TYPE, SCHEMA_VERSION
from agentflow.memory.video_pipeline_observation import OBSERVATION_TYPE
from agentflow.memory.video_pipeline_review import REVIEW_TYPE


PRESENTATION_TYPE = "agentflow_memory_video_pipeline_presentation_package"
UNSAFE_FRAGMENTS = (
    "D:\\",
    "C:\\",
    "file://",
    "data:image/",
    "Bearer ",
    "signed_url",
    "signature=",
    "token=",
    "api_key",
    "secret_key",
    "https://",
    "http://",
    ".mp4",
    ".mov",
)


def build_memory_video_pipeline_presentation(
    protocol: dict[str, Any],
    review: dict[str, Any],
    observation: dict[str, Any],
) -> dict[str, Any]:
    """Build a presentation-facing package from protocol, review, and observation."""
    _validate_inputs(protocol, review, observation)
    memory_lane = _lane(protocol, "memory_backed")
    baseline_lane = _lane(protocol, "baseline")
    observations = observation["observations"]
    package = {
        "schema_version": SCHEMA_VERSION,
        "artifact_type": PRESENTATION_TYPE,
        "protocol_id": protocol["protocol_id"],
        "demo_title": protocol["project_brief"]["title"],
        "provider_calls_started_by_package": False,
        "writes_long_term_memory": False,
        "one_sentence_takeaway": (
            "Under the same keyframe, task, model, duration, and storyboard, the memory-backed lane showed "
            "more stable repeat behavior while remaining a bounded visual signal."
        ),
        "experiment_setup": {
            "user_task": protocol["project_brief"]["user_task"],
            "target_format": protocol["project_brief"]["target_format"],
            "style": protocol["project_brief"]["style"],
            "same_for_both_lanes": [
                "user_task",
                "source_keyframe",
                "provider_route",
                "video_model",
                "duration_sec",
                "storyboard_checkpoints",
            ],
            "provider_route": {
                "video_service_id": protocol["provider_route"]["video_service_id"],
                "video_model": protocol["provider_route"]["video_model"],
                "duration_sec": protocol["provider_route"]["duration_sec"],
                "mode": protocol["provider_route"]["mode"],
                "aspect_ratio": protocol["provider_route"]["aspect_ratio"],
            },
            "storyboard_checkpoints": protocol["storyboard"]["shot_checkpoints"],
            "intended_difference": "memory_context_only",
        },
        "input_difference": {
            "baseline": _baseline_input_text(baseline_lane),
            "memory_backed": list(memory_lane.get("memory_refs") or []),
        },
        "result_summary": {
            **observation["observed_signal_summary"],
            "run_count": review["cross_run_stability"]["run_count"],
            "lane_repeat_counts": review["cross_run_stability"]["lane_repeat_counts"],
        },
        "observation_table": [
            {
                "criterion": item["criterion"],
                "verdict": item["verdict"],
                "note": item["note"],
            }
            for item in observations
        ],
        "slidev_outline": _slidev_outline(protocol, observation),
        "speaker_notes": _speaker_notes(),
        "claim_boundaries": {
            "runtime_verification": "manifest_status_only",
            **observation["claim_boundaries"],
        },
    }
    _reject_unsafe_refs(package)
    return package


def write_memory_video_pipeline_presentation(package: dict[str, Any], output_dir: str | Path) -> list[Path]:
    output_root = Path(output_dir)
    paths = [
        write_json(output_root / "memory_video_pipeline_presentation_package.json", package),
    ]
    brief_path = output_root / "memory_video_pipeline_presentation_brief.md"
    brief_path.parent.mkdir(parents=True, exist_ok=True)
    brief_path.write_text(render_presentation_brief(package), encoding="utf-8")
    paths.append(brief_path)
    slidev_path = output_root / "slidev_insert.md"
    slidev_path.write_text(render_slidev_insert(package), encoding="utf-8")
    paths.append(slidev_path)
    return paths


def render_presentation_brief(package: dict[str, Any]) -> str:
    observations = "\n".join(
        f"- {item['criterion']}: {item['verdict']} - {item['note']}"
        for item in package["observation_table"]
    )
    return "\n".join(
        [
            "# Memory Advantage Demo Brief",
            "",
            f"Demo: {package['demo_title']}",
            "",
            "## One-Sentence Takeaway",
            "",
            package["one_sentence_takeaway"],
            "",
            "## Experiment Setup",
            "",
            "- Same keyframe, task, provider route, model, duration, and storyboard.",
            "- Baseline input: current task plus source keyframe only.",
            "- Memory-backed input: character, scene, and feedback memory cards.",
            "",
            "## Observed Signal",
            "",
            f"- Baseline more variable: {package['result_summary']['baseline_more_variable']}",
            f"- Memory-backed more stable: {package['result_summary']['memory_backed_more_stable']}",
            f"- Residual risk: {package['result_summary']['residual_risk']}",
            "",
            "## Observation Table",
            "",
            observations,
            "",
            "## Boundaries",
            "",
            "- Human acceptance: not acceptance.",
            "- Business validation: not validated.",
            "- Quality improvement claim: bounded visual signal only.",
            "- Durable Memory runtime: not implemented.",
            "",
        ]
    )


def render_slidev_insert(package: dict[str, Any]) -> str:
    slides = []
    for slide in package["slidev_outline"]:
        bullets = "\n".join(f"- {bullet}" for bullet in slide["bullets"])
        slides.append(f"---\n\n## {slide['title']}\n\n{bullets}\n")
    return "\n".join(slides)


def _validate_inputs(protocol: dict[str, Any], review: dict[str, Any], observation: dict[str, Any]) -> None:
    if protocol.get("schema_version") != SCHEMA_VERSION or protocol.get("artifact_type") != PROTOCOL_TYPE:
        raise ValueError(f"presentation package requires protocol artifact_type {PROTOCOL_TYPE}")
    if review.get("schema_version") != SCHEMA_VERSION or review.get("artifact_type") != REVIEW_TYPE:
        raise ValueError(f"presentation package requires review artifact_type {REVIEW_TYPE}")
    if observation.get("schema_version") != SCHEMA_VERSION or observation.get("artifact_type") != OBSERVATION_TYPE:
        raise ValueError(f"presentation package requires observation artifact_type {OBSERVATION_TYPE}")
    ids = {protocol.get("protocol_id"), review.get("protocol_id"), observation.get("protocol_id")}
    if len(ids) != 1:
        raise ValueError("presentation package inputs must share the same protocol_id")
    boundaries = observation.get("claim_boundaries") or {}
    if boundaries.get("human_acceptance") != "not_acceptance":
        raise ValueError("presentation package requires human_acceptance not_acceptance")
    if boundaries.get("quality_improvement_claim") != "bounded_visual_signal_only":
        raise ValueError("presentation package requires bounded visual signal claim")
    if boundaries.get("business_validation") != "not_validated":
        raise ValueError("presentation package requires business_validation not_validated")


def _lane(protocol: dict[str, Any], lane_id: str) -> dict[str, Any]:
    for lane in protocol["lanes"]:
        if lane["lane_id"] == lane_id:
            return lane
    raise ValueError(f"missing lane: {lane_id}")


def _baseline_input_text(lane: dict[str, Any]) -> str:
    if not lane.get("memory_refs"):
        return "current task plus source keyframe only"
    return str(lane.get("prompt_instructions") or "")


def _slidev_outline(protocol: dict[str, Any], observation: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "title": "实验问题",
            "bullets": [
                "同一关键帧、同一剧本、同一模型下，记忆上下文能否降低重复生成的发散？",
                f"任务：{protocol['project_brief']['user_task']}",
                "结论边界：这是 demo 观察信号，不是最终验收。",
            ],
        },
        {
            "title": "输入差异",
            "bullets": [
                "Baseline：当前任务 + 源关键帧。",
                "Memory-backed：额外使用角色记忆、场景记忆、反馈补丁。",
                "其余条件保持一致：模型、时长、分镜、源关键帧。",
            ],
        },
        {
            "title": "观察结果",
            "bullets": [
                f"Baseline 更发散：{observation['observed_signal_summary']['baseline_more_variable']}",
                f"Memory-backed 更稳定：{observation['observed_signal_summary']['memory_backed_more_stable']}",
                f"剩余风险：{observation['observed_signal_summary']['residual_risk']}",
            ],
        },
        {
            "title": "可讲清楚的边界",
            "bullets": [
                "不是商业验证。",
                "不是最终质量证明。",
                "不是 durable Memory runtime。",
                "是可复核的重复生成稳定性案例。",
            ],
        },
    ]


def _speaker_notes() -> list[str]:
    return [
        "这不是一次提示词炫技，而是把相同任务在重复生成下的稳定性差异记录下来。",
        "Baseline 每次都依赖当前输入自行发散；memory-backed 复用角色、场景和反馈记忆来收窄发散空间。",
        "当前证据适合比赛演示和架构说明，不适合说成最终产品质量证明。",
    ]


def _reject_unsafe_refs(value: Any) -> None:
    serialized = str(value)
    if any(fragment.lower() in serialized.lower() for fragment in UNSAFE_FRAGMENTS):
        raise ValueError("memory video presentation package contains unsafe path, provider URL, secret, or generated media reference")
