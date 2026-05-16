from __future__ import annotations

import re
from pathlib import Path
from typing import Any


VARIABLE_PATTERN = re.compile(r"{{\s*([A-Za-z_][A-Za-z0-9_]*)\s*}}")


class PromptManager:
    """Load markdown prompts and render simple {{ variable }} placeholders."""

    def __init__(self, prompts_dir: str | Path = "prompts") -> None:
        self.prompts_dir = Path(prompts_dir)

    def load(self, template_name: str) -> str:
        template_path = self.prompts_dir / template_name
        if not template_path.is_file():
            raise FileNotFoundError(f"Prompt template not found: {template_path}")
        return template_path.read_text(encoding="utf-8")

    def render(self, template_name: str, variables: dict[str, Any]) -> str:
        template = self.load(template_name)

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            if name not in variables:
                raise ValueError(f"Missing prompt variable: {name}")
            return str(variables[name])

        return VARIABLE_PATTERN.sub(replace, template)
