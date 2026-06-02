from __future__ import annotations

import json

from agentflow_studio.model_gateway import MockLLMProvider
from agentflow_studio.schemas import Hook, ShortVideoScript


def test_mock_llm_provider_returns_valid_hook_json() -> None:
    provider = MockLLMProvider()

    payload = json.loads(provider.generate("prompt", task_type="hook_analysis"))
    hooks = [Hook.model_validate(item) for item in payload]

    assert hooks
    assert hooks[0].hook_id
    assert 0.0 <= hooks[0].score <= 1.0


def test_mock_llm_provider_returns_valid_script_json() -> None:
    provider = MockLLMProvider()

    payload = json.loads(provider.generate("prompt", task_type="short_video_script"))
    scripts = [ShortVideoScript.model_validate(item) for item in payload]

    assert scripts
    assert scripts[0].script_id
    assert scripts[0].segments
