from __future__ import annotations

import json

from pydantic import ValidationError

from agentflow_studio.core.prompts import PromptManager
from agentflow_studio.model_gateway import LLMProvider, MockLLMProvider
from agentflow_studio.schemas import Hook, ShortVideoScript


def analyze_hooks_from_text(
    input_text: str,
    provider: LLMProvider | None = None,
) -> list[Hook]:
    prompt = PromptManager().render("hook_analysis.md", {"input_text": input_text})
    raw_output = (provider or MockLLMProvider()).generate(prompt, task_type="hook_analysis")
    payload = _load_json_list(raw_output, "hook_analysis")
    return _validate_hooks(payload)


def generate_scripts_from_hooks(
    hooks: list[Hook],
    provider: LLMProvider | None = None,
) -> list[ShortVideoScript]:
    hooks_json = json.dumps([hook.model_dump(mode="json") for hook in hooks], ensure_ascii=False, indent=2)
    prompt = PromptManager().render("short_video_script.md", {"hooks_json": hooks_json})
    raw_output = (provider or MockLLMProvider()).generate(prompt, task_type="short_video_script")
    payload = _load_json_list(raw_output, "short_video_script")
    return _validate_scripts(payload)


def _load_json_list(raw_output: str, task_type: str) -> list[object]:
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ValueError(f"LLM returned invalid JSON for {task_type}: {exc.msg}") from exc
    if not isinstance(payload, list):
        raise ValueError(f"LLM returned non-list JSON for {task_type}")
    return payload


def _validate_hooks(payload: list[object]) -> list[Hook]:
    try:
        return [Hook.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise ValueError(f"LLM hook_analysis JSON failed Hook validation: {exc}") from exc


def _validate_scripts(payload: list[object]) -> list[ShortVideoScript]:
    try:
        return [ShortVideoScript.model_validate(item) for item in payload]
    except ValidationError as exc:
        raise ValueError(f"LLM short_video_script JSON failed ShortVideoScript validation: {exc}") from exc
