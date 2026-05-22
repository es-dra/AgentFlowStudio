from __future__ import annotations

from agentflow.harness.constants import (
    AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS,
    AGENTFLOW_VALIDATION_SCHEMA_VERSION,
    FAILED,
    PASSED,
    WARNING,
)
from narratocut.harness import agentflow_router, agentflow_skill


def test_agentflow_harness_constants_define_shared_validation_contract() -> None:
    assert AGENTFLOW_VALIDATION_SCHEMA_VERSION == "0.1.0"
    assert PASSED == "passed"
    assert WARNING == "warning"
    assert FAILED == "failed"

    expected_forbidden_fragments = {
        "D:\\",
        "C:\\",
        "data/processed/runs",
        "data/raw/",
        ".mp4",
        ".mov",
        "api_key",
        "access_token",
        "refresh_token",
        "secret_key",
        "client_secret",
        "authorization:",
        "bearer ",
        "cookie=",
        "signed_url",
    }
    assert expected_forbidden_fragments <= set(AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS)


def test_existing_agentflow_validators_reuse_platform_constants() -> None:
    assert agentflow_router.SCHEMA_VERSION == AGENTFLOW_VALIDATION_SCHEMA_VERSION
    assert agentflow_skill.SCHEMA_VERSION == AGENTFLOW_VALIDATION_SCHEMA_VERSION
    assert agentflow_router.PASSED == PASSED
    assert agentflow_skill.PASSED == PASSED
    assert agentflow_router.FAILED == FAILED
    assert agentflow_skill.FAILED == FAILED
    assert agentflow_router.FORBIDDEN_DECISION_FRAGMENTS is AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
    assert agentflow_skill.FORBIDDEN_REPLAY_FRAGMENTS is AGENTFLOW_FORBIDDEN_PRIVATE_FRAGMENTS
