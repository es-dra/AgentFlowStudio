from __future__ import annotations

import copy
import json
from pathlib import Path

from agentflow.memory.assets import validate_asset_memory_contract_set
from agentflow.memory.promotion import (
    PROMOTION_DECISION_STATUSES,
    validate_evidence_reuse_review,
    validate_memory_promotion_review,
)


INTERMEDIATE_ASSET_EXAMPLE = Path("examples/agentflow/intermediate_asset.example.json")
REUSABLE_ASSET_PROFILE_EXAMPLE = Path("examples/agentflow/reusable_asset_profile.example.json")
ASSET_REUSE_DECISION_EXAMPLE = Path("examples/agentflow/asset_reuse_decision.example.json")
MEMORY_CANDIDATE_EXAMPLE = Path("examples/agentflow/memory_candidate.example.json")
MEMORY_PROMOTION_DECISION_EXAMPLE = Path("examples/agentflow/memory_promotion_decision.example.json")
EVIDENCE_REUSE_REVIEW_EXAMPLE = Path("examples/agentflow/memory_evidence_reuse_review.example.json")


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


def test_asset_memory_validator_requires_supported_promotion_decision_status() -> None:
    contracts = _contract_set()
    contracts["memory_promotion_decision"]["decision"] = "accepted"

    validation = validate_asset_memory_contract_set(**contracts)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"promotion_decision_status_supported"}


def test_asset_memory_validator_requires_promotion_decision_evidence_refs() -> None:
    contracts = _contract_set()
    contracts["memory_promotion_decision"]["evidence_refs"] = []

    validation = validate_asset_memory_contract_set(**contracts)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"promotion_decision_has_evidence_refs"}


def test_asset_memory_validator_requires_promotion_decision_to_preserve_candidate_evidence() -> None:
    contracts = _contract_set()
    contracts["memory_promotion_decision"]["evidence_refs"] = ["unrelated_review_note"]

    validation = validate_asset_memory_contract_set(**contracts)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"promotion_decision_preserves_candidate_evidence"}


def test_memory_promotion_review_helper_accepts_all_supported_statuses() -> None:
    contracts = _contract_set()

    for decision_status in PROMOTION_DECISION_STATUSES:
        contracts["memory_promotion_decision"]["decision"] = decision_status
        review = validate_memory_promotion_review(
            memory_candidate=contracts["memory_candidate"],
            memory_promotion_decision=contracts["memory_promotion_decision"],
        )

        assert review["overall_status"] == "passed"
        assert review["decision"] == decision_status
        assert all(check["status"] == "passed" for check in review["checks"])


def test_memory_promotion_review_helper_rejects_durable_memory_claims() -> None:
    contracts = _contract_set()
    contracts["memory_promotion_decision"]["durable_memory_ref"] = "agentflow_memory:durable_001"

    review = validate_memory_promotion_review(
        memory_candidate=contracts["memory_candidate"],
        memory_promotion_decision=contracts["memory_promotion_decision"],
    )

    assert review["overall_status"] == "failed"
    assert _failed_check_ids(review) >= {"promotion_decision_no_durable_memory_claims"}


def test_asset_memory_validator_rejects_durable_memory_claim_refs() -> None:
    contracts = _contract_set()
    contracts["memory_promotion_decision"]["persisted_memory_id"] = "project_memory_001"

    validation = validate_asset_memory_contract_set(**contracts)

    assert validation["overall_status"] == "failed"
    assert _failed_check_ids(validation) >= {"promotion_decision_no_durable_memory_claims"}


def test_evidence_reuse_review_accepts_local_alpha_0_4_chain_example() -> None:
    review = validate_evidence_reuse_review(
        evidence_reuse_review=_json(EVIDENCE_REUSE_REVIEW_EXAMPLE),
        memory_candidate=_json(MEMORY_CANDIDATE_EXAMPLE),
        memory_promotion_decision=_json(MEMORY_PROMOTION_DECISION_EXAMPLE),
    )

    assert review["artifact_type"] == "agentflow_memory_evidence_reuse_review_validation"
    assert review["review_scope"] == "local_alpha_0_4_evidence_reuse"
    assert review["runtime_status"] == "not_implemented"
    assert review["does_not_execute"] is True
    assert review["writes_long_term_memory"] is False
    assert review["overall_status"] == "passed"
    assert all(check["status"] == "passed" for check in review["checks"])


def test_evidence_reuse_review_fails_when_second_pass_loses_promotion_decision_refs() -> None:
    payload = _json(EVIDENCE_REUSE_REVIEW_EXAMPLE)
    payload["second_pass_prompt"]["promotion_decision_refs"] = []

    review = validate_evidence_reuse_review(
        evidence_reuse_review=payload,
        memory_candidate=_json(MEMORY_CANDIDATE_EXAMPLE),
        memory_promotion_decision=_json(MEMORY_PROMOTION_DECISION_EXAMPLE),
    )

    assert review["overall_status"] == "failed"
    assert _failed_check_ids(review) >= {"second_pass_prompt_refs_promotion_decision"}


def test_evidence_reuse_review_fails_when_promotion_decision_rejects_reuse() -> None:
    decision = _json(MEMORY_PROMOTION_DECISION_EXAMPLE)
    decision["decision"] = "rejected"

    review = validate_evidence_reuse_review(
        evidence_reuse_review=_json(EVIDENCE_REUSE_REVIEW_EXAMPLE),
        memory_candidate=_json(MEMORY_CANDIDATE_EXAMPLE),
        memory_promotion_decision=decision,
    )

    assert review["overall_status"] == "failed"
    assert _failed_check_ids(review) >= {"promotion_decision_allows_context_reuse"}


def test_evidence_reuse_review_fails_when_context_writes_long_term_memory() -> None:
    payload = _json(EVIDENCE_REUSE_REVIEW_EXAMPLE)
    payload["context_bundle"]["writes_long_term_memory"] = True

    review = validate_evidence_reuse_review(
        evidence_reuse_review=payload,
        memory_candidate=_json(MEMORY_CANDIDATE_EXAMPLE),
        memory_promotion_decision=_json(MEMORY_PROMOTION_DECISION_EXAMPLE),
    )

    assert review["overall_status"] == "failed"
    assert _failed_check_ids(review) >= {"context_reuse_no_long_term_write"}


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
