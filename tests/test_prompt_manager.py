from __future__ import annotations

import pytest

from narratocut.core.prompts import PromptManager


def test_prompt_manager_loads_and_renders_template(tmp_path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "sample.md").write_text(
        "Analyze {{ input_text }} with {{hooks_json}}.",
        encoding="utf-8",
    )

    manager = PromptManager(prompts_dir=prompts_dir)

    rendered = manager.render(
        "sample.md",
        {"input_text": "测试剧情", "hooks_json": "[]"},
    )

    assert rendered == "Analyze 测试剧情 with []."


def test_prompt_manager_raises_for_missing_template(tmp_path) -> None:
    manager = PromptManager(prompts_dir=tmp_path)

    with pytest.raises(FileNotFoundError, match="Prompt template not found"):
        manager.render("missing.md", {})


def test_prompt_manager_raises_for_missing_variable(tmp_path) -> None:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "sample.md").write_text("Analyze {{ input_text }}.", encoding="utf-8")

    manager = PromptManager(prompts_dir=prompts_dir)

    with pytest.raises(ValueError, match="Missing prompt variable"):
        manager.render("sample.md", {})
