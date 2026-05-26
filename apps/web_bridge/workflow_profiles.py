from __future__ import annotations

from pathlib import Path
from typing import Any


def workflow_web_profile(definition: Any, path: Path) -> dict[str, Any]:
    metadata = definition.metadata if isinstance(definition.metadata, dict) else {}
    explicit = metadata.get("web_profile") if isinstance(metadata.get("web_profile"), dict) else {}
    profile = _default_web_profile(definition.name, path)
    profile["kind"] = str(explicit.get("kind") or metadata.get("kind") or profile["kind"])
    profile["status"] = str(explicit.get("status") or metadata.get("status") or profile["status"])
    profile["summary"] = str(explicit.get("summary") or profile["summary"] or metadata.get("description") or "")
    profile["display_name"] = str(explicit.get("display_name") or profile["display_name"])
    profile["recommended_input"] = str(explicit.get("recommended_input") or profile["recommended_input"])
    profile["next_step_hint"] = str(explicit.get("next_step_hint") or profile["next_step_hint"])
    profile["quick_start"] = bool(explicit.get("quick_start", profile["quick_start"]))
    profile["requirements"] = _string_list(explicit.get("requirements", profile["requirements"]))
    profile["review_focus"] = _string_list(explicit.get("review_focus", profile["review_focus"]))
    return profile


def _default_web_profile(name: str, path: Path) -> dict[str, Any]:
    profiles: dict[str, dict[str, Any]] = {
        "mock_text_to_slices": {
            "kind": "demo",
            "status": "quick_start",
            "quick_start": True,
            "display_name": "本机演示：文本到切片",
            "summary": "本机演示 workflow：无需媒体、FFmpeg 或 ASR，可立即跑通文本到 mock clips 的监督闭环。",
            "recommended_input": "examples/demo_text/story.txt",
            "next_step_hint": "可直接生成计划并运行本机演示。",
            "requirements": [],
            "review_focus": ["mock_clips", "package_report"],
        },
        "mock_roi_to_script": {
            "kind": "demo",
            "status": "quick_start",
            "quick_start": True,
            "display_name": "本机演示：文本到脚本",
            "summary": "本机演示 workflow：无需媒体、FFmpeg 或 ASR，可立即跑通文本到脚本的最小链路。",
            "recommended_input": "examples/demo_text/story.txt",
            "next_step_hint": "可直接生成计划并运行本机演示。",
            "requirements": [],
            "review_focus": ["scripts", "package_report"],
        },
        "video_to_finished_package_local_asr": {
            "kind": "product",
            "status": "recommended",
            "quick_start": False,
            "display_name": "完整成品包：本地 ASR",
            "summary": "完整成品 workflow：需要本地视频、BGM、FFmpeg、ffprobe 和 faster-whisper/ctranslate2。",
            "recommended_input": "examples/demo_asr/video_to_finished_package_local_asr_input.example.json",
            "next_step_hint": "先补齐本地视频、BGM、FFmpeg/FFprobe 和 local ASR 依赖。",
            "requirements": ["local_media", "bgm", "ffmpeg", "ffprobe", "local_asr"],
            "review_focus": ["final_video", "subtitles", "cover", "bgm", "delivery_package"],
        },
        "video_script_to_finished_package_local_asr": {
            "kind": "product",
            "status": "recommended",
            "quick_start": False,
            "display_name": "完整成品包：视频脚本",
            "summary": "完整成品 workflow：用视频和脚本生成交付包，需要本地媒体、BGM、FFmpeg 和 local ASR。",
            "recommended_input": "examples/demo_asr/video_script_to_finished_package_local_asr_input.example.json",
            "next_step_hint": "先补齐本地视频、脚本、BGM、FFmpeg/FFprobe 和 local ASR 依赖。",
            "requirements": ["local_media", "script", "bgm", "ffmpeg", "ffprobe", "local_asr"],
            "review_focus": ["final_video", "script_alignment", "subtitles", "cover", "delivery_package"],
        },
    }
    return dict(
        profiles.get(
            name,
            {
                "kind": "workflow",
                "status": "available",
                "quick_start": False,
                "display_name": path.stem.replace("_", " "),
                "summary": f"{path.name} workflow.",
                "recommended_input": "examples/demo_text/story.txt",
                "next_step_hint": "检查输入后再生成计划。",
                "requirements": [],
                "review_focus": [],
            },
        )
    )


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []
