from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from narratocut.schemas import StepResult


@dataclass
class WorkflowContext:
    run_id: str
    workflow_name: str
    output_dir: Path
    workflow_path: str | None = None
    mode: str = "mock"
    ffmpeg_required: bool = False
    network_required: bool = False
    inputs: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    step_results: list[StepResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.output_dir = Path(self.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def resolve_input(self, name: str) -> Any:
        if name in self.inputs:
            return self.inputs[name]
        if name in self.artifacts:
            return str(self.output_dir / self.artifacts[name])
        return name

    def output_path(self, relative_path: str) -> Path:
        return self.output_dir / relative_path
