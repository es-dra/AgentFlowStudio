from __future__ import annotations

import copy
import json
from pathlib import Path

from agentflow.memory.assets import validate_asset_memory_contract_set


INTERMEDIATE_ASSET_EXAMPLE = Path("examples/agentflow/intermediate_asset.example.json")
REUSABLE_ASSET_PROFILE_EXAMPLE = Path("examples/agentflow/reusable_asset_profile.example.json")
ASSET_REUSE_DECISION_EXAMPLE = Path("examples/agentflow/asset_reuse_decision.example.json")
MEMORY_CANDIDATE_EXAMPLE = Path("examples/agentflow/memory_candidate.example.json")
MEMORY_PROMOTION_DECISION_EXAMPLE = Path("examples/agentflow/memory_promotion_decision.example.json")


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _contract_set() -> dict[str, dict]:
    return {
        "intermediate_asset": _json(INTERMEDIATE_ASSET_EXAMPLE),
        "reusable_asset_profile": _json(REUSABLE_ASSET_PROFILE_EXAMPLE),
        "asset_reuse_decision": _json(ASSET_REUSE_DECISION_EXAMPLE),
        "memory_candidate": _json(MEMORY_CANDIDATE_EXAMPLE),
        "memory_promotion_decision": _json(MEMORY_PROMOTION_DECISION_EXAMPLE),
    }


def test_asset_memory_validator_accepts_current_examples_without_runtime() -> None:
    contracts = _contract_set()

    validation = validate_asset_memory_contract_set(**contracts)

    assert validation["schema_version"] == "0.1.0"
    assert validation["artifact_type"] == "agentflow_asset_memory_validation"
    assert validation["validation_scope"] == "asset_memory_contract_set"
    assert validation["runtime_status"] == "not_implemented"
    assert validation["does_not_execute"] is True
    assert validation["writes_long_term_memory"] is False
    assert validation["overall_status"] == "passed"
    assert all(check["status"] == "passed" for check in validation["checks"])


def test_asset_memory_validator_rejects_candidate_memory_as_promoted() -> None:
    contracts = _contract_set()
    contracts["memory_candidate"]["promotion_status"] = "promoted"

    validation = validate_asset_memory_contract_set(**contracts)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"memory_candidate_candidate_only"}


def test_asset_memory_validator_requires_explicit_non_writing_promotion_decision() -> None:
    contracts = _contract_set()
    contracts["memory_promotion_decision"]["writes_long_term_memory"] = True

    validation = validate_asset_memory_contract_set(**contracts)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"promotion_decision_does_not_write_memory"}


def test_asset_memory_validator_requires_asset_promotion_chain() -> None:
    contracts = _contract_set()
    contracts["reusable_asset_profile"]["source_intermediate_asset_ids"] = ["missing_intermediate_asset"]

    validation = validate_asset_memory_contract_set(**contracts)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"reusable_profile_links_intermediate_asset"}


def test_asset_memory_validator_requires_profile_promotion_decision_ref() -> None:
    contracts = _contract_set()
    contracts["reusable_asset_profile"]["promotion_decision_ref"] = (
        "agentflow_memory_promotion_decision:missing_decision"
    )

    validation = validate_asset_memory_contract_set(**contracts)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"reusable_profile_links_promotion_decision"}


def test_asset_memory_validator_keeps_reuse_decision_decision_only() -> None:
    contracts = _contract_set()
    contracts["asset_reuse_decision"]["does_not_execute"] = False

    validation = validate_asset_memory_contract_set(**contracts)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"asset_reuse_decision_only"}


def test_asset_memory_validator_rejects_private_paths_and_generated_media() -> None:
    contracts = _contract_set()
    contracts["intermediate_asset"]["evidence_refs"].append("D:\\private\\clip.mp4?api_key=abc123")

    validation = validate_asset_memory_contract_set(**contracts)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"no_private_paths_or_secrets"}


def test_asset_memory_validator_does_not_mutate_inputs() -> None:
    contracts = _contract_set()
    original = copy.deepcopy(contracts)

    validate_asset_memory_contract_set(**contracts)

    assert contracts == original


def _failed_check_ids(validation: dict) -> set[str]:
    return {check["check_id"] for check in validation["checks"] if check["status"] == "failed"}
