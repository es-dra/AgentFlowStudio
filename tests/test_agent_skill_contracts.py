from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agentflow_studio.workflow_engine import load_workflow


SKILL_FILES = [
    Path("skills/agentflow_production_handoff.skill.yaml"),
    Path("skills/video_to_real_clips.skill.yaml"),
]


def test_agent_skill_contracts_reference_existing_workflows() -> None:
    for skill_path in SKILL_FILES:
        skill = _load_skill(skill_path)
        workflow_path = Path(skill["primary_workflow"])
        workflow = load_workflow(workflow_path)

        assert workflow_path.is_file()
        assert workflow.metadata["kind"] in {"production", "slicing"}
        assert "agent" in workflow.metadata["audience"]
        assert workflow.quality_profile in {"agentflow_production_handoff", "video_real_clips"}


def test_agent_skill_contracts_declare_current_outputs_and_quality_gates() -> None:
    production = _load_skill(Path("skills/agentflow_production_handoff.skill.yaml"))
    slicing = _load_skill(Path("skills/video_to_real_clips.skill.yaml"))

    assert "production_handoff.json" in production["output_artifacts"]
    assert "production_report.md" in production["output_artifacts"]
    assert "memory_candidates.json" in production["output_artifacts"]
    assert "real_slice_manifest.json" in slicing["output_artifacts"]
    assert "clips/" in slicing["output_artifacts"]
    for skill in [production, slicing]:
        assert set(skill["quality_gates"]) >= {"inspect-run", "review-run"}
        assert skill["dependencies"]["network"] is False


def _load_skill(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload
