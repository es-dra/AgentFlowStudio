from __future__ import annotations

from pathlib import Path

from agentflow.contracts.examples import (
    AGENTFLOW_CONTRACT_SCHEMA_VERSION,
    AGENTFLOW_EXAMPLE_PATHS,
    AGENTFLOW_EXAMPLE_TYPES,
    load_agentflow_example,
    load_agentflow_examples,
)


def test_agentflow_contract_helpers_list_committed_examples() -> None:
    assert AGENTFLOW_CONTRACT_SCHEMA_VERSION == "0.1.0"
    assert Path("examples/agentflow/project_manifest.example.json") in AGENTFLOW_EXAMPLE_PATHS
    assert Path("examples/agentflow/feedback_event.example.jsonl") in AGENTFLOW_EXAMPLE_PATHS

    expected_types = {
        "agentflow_project_manifest",
        "agentflow_artifact_map",
        "agentflow_feedback_event",
        "agentflow_memory_candidate",
        "agentflow_memory_promotion_decision",
        "agentflow_skill_invocation",
        "agentflow_skill_result",
        "agentflow_router_decision",
        "agentflow_intermediate_asset",
        "agentflow_reusable_asset_profile",
        "agentflow_asset_reuse_decision",
        "agentflow_narratostudio_asset_feedback_review",
    }
    assert expected_types <= AGENTFLOW_EXAMPLE_TYPES


def test_load_agentflow_example_reads_json_and_jsonl_examples() -> None:
    project_manifest = load_agentflow_example(Path("examples/agentflow/project_manifest.example.json"))
    feedback_events = load_agentflow_example(Path("examples/agentflow/feedback_event.example.jsonl"))

    assert isinstance(project_manifest, dict)
    assert project_manifest["schema_version"] == AGENTFLOW_CONTRACT_SCHEMA_VERSION
    assert project_manifest["artifact_type"] == "agentflow_project_manifest"
    assert isinstance(feedback_events, list)
    assert feedback_events
    assert {event["artifact_type"] for event in feedback_events} == {"agentflow_feedback_event"}


def test_load_agentflow_examples_preserves_path_and_payload_pairs() -> None:
    loaded_examples = load_agentflow_examples()
    loaded_paths = {path for path, _payload in loaded_examples}

    assert loaded_paths == set(AGENTFLOW_EXAMPLE_PATHS)
    assert all(path.exists() for path, _payload in loaded_examples)


def test_agentflow_contract_helpers_do_not_expose_runtime_execution() -> None:
    import agentflow.contracts.examples as examples

    forbidden_names = {
        "execute",
        "run_workflow",
        "invoke_skill",
        "select_skill",
        "write_memory",
    }
    assert not (forbidden_names & set(dir(examples)))


def test_agentflow_contract_helpers_are_recorded_in_phase15_roadmap() -> None:
    phase15 = Path("docs/agentflow_phase15_roadmap.md").read_text(encoding="utf-8")

    assert "Phase 15.16" in phase15
    assert "AgentFlow Contract Example Helpers" in phase15
    assert "does not move validators" in phase15
