from __future__ import annotations

import json

from agentflow_studio.roi_sop import analyze_hooks_from_text, generate_scripts_from_hooks
from agentflow_studio.schemas import Hook, ShortVideoScript
from agentflow_studio.utils.json_io import write_json


def test_analyze_hooks_from_text_returns_hooks() -> None:
    hooks = analyze_hooks_from_text("女主被误会后当众反转，揭露真正身份。")

    assert hooks
    assert all(isinstance(hook, Hook) for hook in hooks)


def test_generate_scripts_from_hooks_returns_scripts() -> None:
    hooks = analyze_hooks_from_text("女主被误会后当众反转，揭露真正身份。")

    scripts = generate_scripts_from_hooks(hooks)

    assert scripts
    assert all(isinstance(script, ShortVideoScript) for script in scripts)
    assert {script.hook_id for script in scripts}.issubset({hook.hook_id for hook in hooks})


def test_write_json_writes_pydantic_models(tmp_path) -> None:
    hooks = analyze_hooks_from_text("女主被误会后当众反转，揭露真正身份。")
    scripts = generate_scripts_from_hooks(hooks)

    hooks_path = tmp_path / "hooks.json"
    scripts_path = tmp_path / "scripts.json"
    write_json(hooks_path, hooks)
    write_json(scripts_path, scripts)

    loaded_hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    loaded_scripts = json.loads(scripts_path.read_text(encoding="utf-8"))

    assert [Hook.model_validate(item) for item in loaded_hooks]
    assert [ShortVideoScript.model_validate(item) for item in loaded_scripts]
