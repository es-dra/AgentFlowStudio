from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

from agentflow_studio.slicing_sop import check_media_tools
from agentflow_studio.workflow_engine.input_bundle import load_workflow_inputs

from apps.web_bridge.utils import display_ref


FILE_INPUT_KEYS = {
    "asr_download_root",
    "audio_extraction_mode",
    "asr_model",
    "asr_device",
    "asr_compute_type",
    "asr_beam_size",
    "asr_vad_filter",
    "language",
    "max_highlights",
    "max_clips",
    "output_clips_dir",
    "output_dir",
    "project_id",
    "project_name",
}


def bridge_health() -> dict[str, Any]:
    media_tools = check_media_tools()
    asr = _local_asr_payload()
    status = "ready" if media_tools.status == "ready" and asr["status"] == "ready" else "degraded"
    return {
        "service": "agentflow_studio_web_bridge",
        "status": status,
        "python": {
            "executable": display_ref(sys.executable),
            "version": sys.version.split()[0],
        },
        "workspace": display_ref(Path.cwd()),
        "media": {
            "status": media_tools.status,
            "ffmpeg": _media_tool_payload(media_tools.ffmpeg),
            "ffprobe": _media_tool_payload(media_tools.ffprobe),
            "warnings": media_tools.warnings,
        },
        "local_asr": asr,
    }


def inspect_workflow_input(input_path: Path) -> dict[str, Any]:
    path = Path(input_path)
    try:
        inputs = load_workflow_inputs(path)
    except Exception as exc:  # noqa: BLE001 - bridge returns input diagnostics instead of hiding them.
        return {
            "status": "fail",
            "input_path": display_ref(path),
            "inputs": [],
            "missing": [display_ref(path)],
            "categories": {},
            "summary": "输入文件不可读取",
            "next_action": "修正 input bundle 路径或 JSON 内容。",
            "warnings": [str(exc)],
        }
    missing: list[str] = []
    references: list[dict[str, Any]] = []
    categories: dict[str, list[str]] = {}
    for key, value in inputs.items():
        if key in FILE_INPUT_KEYS or not isinstance(value, str):
            continue
        if not _looks_like_file_ref(value):
            continue
        ref_path = Path(value)
        exists = ref_path.exists()
        if not exists:
            missing_ref = display_ref(value)
            missing.append(missing_ref)
            categories.setdefault(_input_category(key, value), []).append(missing_ref)
        references.append({"key": key, "path": display_ref(value), "exists": exists, "category": _input_category(key, value)})
    status = "fail" if not path.exists() or missing else "pass"
    warnings = []
    if not path.exists():
        warnings.append(f"input file missing: {display_ref(path)}")
    if missing:
        warnings.append(f"{len(missing)} referenced file(s) missing")
    return {
        "status": status,
        "input_path": display_ref(path),
        "inputs": references,
        "missing": missing,
        "categories": categories,
        "summary": "输入引用可用" if status == "pass" else f"存在 {len(missing)} 个缺失引用",
        "next_action": "可生成计划并运行。" if status == "pass" else "修正 input bundle 中的本地文件路径。",
        "warnings": warnings,
    }


def _local_asr_payload() -> dict[str, Any]:
    missing = [name for name in ["faster_whisper", "ctranslate2"] if importlib.util.find_spec(name) is None]
    return {
        "status": "ready" if not missing else "missing_optional_dependency",
        "provider": "faster_whisper",
        "available": not missing,
        "missing": missing,
        "warning": "Install local ASR dependencies with `python -m pip install faster-whisper`." if missing else "",
    }


def _media_tool_payload(info: Any) -> dict[str, Any]:
    return {
        "available": info.available,
        "executable": info.executable,
        "version": info.version,
        "error": info.error,
    }


def _looks_like_file_ref(value: str) -> bool:
    text = value.strip()
    if not text or "\n" in text:
        return False
    path = Path(text)
    if path.suffix:
        return True
    return "/" in text or "\\" in text


def _input_category(key: str, value: str) -> str:
    text = f"{key} {value}".lower()
    if any(token in text for token in ["video", ".mp4", ".webm", ".mov"]):
        return "local_media"
    if any(token in text for token in ["bgm", ".mp3", ".wav", "audio"]):
        return "bgm"
    if any(token in text for token in ["script", ".txt", ".md"]):
        return "script"
    if any(token in text for token in ["config", ".json", ".yaml", ".yml"]):
        return "config"
    return "file"
