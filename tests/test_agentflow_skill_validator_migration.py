from __future__ import annotations

import json
from pathlib import Path

from agentflow.harness.agentflow_skill import validate_skill_invocation_result_replay
from narratocut.harness.agentflow_skill import (
    validate_skill_invocation_result_replay as compatibility_validate_skill_invocation_result_replay,
)


SKILL_INVOCATION_EXAMPLE = Path("examples/agentflow/skill_invocation.example.json")
SKILL_RESULT_EXAMPLE = Path("examples/agentflow/skill_result.example.json")


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_skill_replay_validator_imports_from_agentflow_harness() -> None:
    validation = validate_skill_invocation_result_replay(
        _json(SKILL_INVOCATION_EXAMPLE),
        _json(SKILL_RESULT_EXAMPLE),
    )

    assert validation["artifact_type"] == "agentflow_skill_replay_validation"
    assert validation["overall_status"] == "passed"
    assert validation["does_not_execute"] is True


def test_narratocut_skill_replay_validator_import_path_is_compatibility_wrapper() -> None:
    assert compatibility_validate_skill_invocation_result_replay is validate_skill_invocation_result_replay
