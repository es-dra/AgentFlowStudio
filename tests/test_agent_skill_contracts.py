from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from narratocut.workflow_engine import load_workflow


SKILL_FILES = [
    Path("skills/short_highlight_package.skill.yaml"),
    Path("skills/video_script_highlight_package.skill.yaml"),
]


def test_agent_skill_contracts_reference_existing_workflows() -> None:
    for skill_path in SKILL_FILES:
        skill = _load_skill(skill_path)
        workflow_path = Path(skill["primary_workflow"])
        workflow = load_workflow(workflow_path)

        assert workflow_path.is_file()
        assert workflow.metadata["kind"] == "product"
        assert "agent" in workflow.metadata["audience"]
        assert workflow.quality_profile == "finished_package"


def test_agent_skill_contracts_declare_package_report_and_quality_gates() -> None:
    for skill_path in SKILL_FILES:
        skill = _load_skill(skill_path)

        assert "package_report.md" in skill["output_artifacts"]
        assert "finished_package_manifest.json" in skill["output_artifacts"]
        assert set(skill["quality_gates"]) >= {"inspect-run", "review-run"}
        assert skill["dependencies"]["network"] is False


def _load_skill(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload
