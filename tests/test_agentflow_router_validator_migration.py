from __future__ import annotations

import json
from pathlib import Path

from agentflow.harness.agentflow_router import validate_router_decision_dry_run
from agentflow_studio.harness.agentflow_router import (
    validate_router_decision_dry_run as compatibility_validate_router_decision_dry_run,
)


ROUTER_DECISION_EXAMPLE = Path("examples/agentflow/router_decision.example.json")
KNOWN_SKILL_IDS = {
    "agentflow_studio.production.production_handoff",
    "agentflow_studio.slicing.video_to_real_clips",
}


def _router_decision() -> dict:
    return json.loads(ROUTER_DECISION_EXAMPLE.read_text(encoding="utf-8"))


def test_router_validator_imports_from_agentflow_harness() -> None:
    validation = validate_router_decision_dry_run(_router_decision(), known_skill_ids=KNOWN_SKILL_IDS)

    assert validation["artifact_type"] == "agentflow_router_dry_run_validation"
    assert validation["overall_status"] == "passed"
    assert validation["does_not_execute"] is True


def test_agentflow_studio_router_validator_import_path_is_compatibility_wrapper() -> None:
    assert compatibility_validate_router_decision_dry_run is validate_router_decision_dry_run
