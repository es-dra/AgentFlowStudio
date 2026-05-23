from __future__ import annotations

import json
from pathlib import Path

import yaml

from agentflow.contracts.examples import (
    AGENTFLOW_ASSET_EXAMPLES,
    AGENTFLOW_EXAMPLE_PATHS,
    AGENTFLOW_SKILL_ROUTER_EXAMPLES,
)
from narratostudio import CreativeBrief


def test_project_manifest_example_has_schema_version() -> None:
    payload = json.loads(Path("examples/contracts/project_manifest.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1"
    assert payload["project_type"] == "short_video_distribution"
    assert isinstance(payload["runs"], list)
    assert isinstance(payload["packages"], list)


def test_feedback_example_jsonl_has_schema_version() -> None:
    lines = Path("examples/contracts/feedback.example.jsonl").read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines if line.strip()]

    assert events
    assert all(event["schema_version"] == "0.1" for event in events)
    assert {event["target_type"] for event in events} <= {"clip", "candidate", "package", "run"}


def test_platform_profile_examples_have_schema_version() -> None:
    profile_paths = sorted(Path("configs/platform_profiles").glob("*.yaml"))

    assert {path.name for path in profile_paths} >= {
        "douyin.yaml",
        "xiaohongshu.yaml",
        "youtube_shorts.yaml",
    }
    for path in profile_paths:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert payload["schema_version"] == "0.1"
        assert payload["platform_id"]
        assert payload["recommended_duration_sec"]["min"] > 0
        assert payload["aspect_ratio"]


def test_narratostudio_creative_brief_example_has_schema_version() -> None:
    payload = json.loads(Path("examples/narratostudio/creative_brief.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert CreativeBrief.model_validate(payload).artifact_type == "creative_brief"


def test_agentflow_project_manifest_example_has_schema_version() -> None:
    payload = json.loads(Path("examples/agentflow/project_manifest.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_project_manifest"
    assert {module["module_id"] for module in payload["modules"]} == {"narratostudio", "narratocut"}


def test_agentflow_artifact_map_example_has_schema_version() -> None:
    payload = json.loads(Path("examples/agentflow/artifact_map.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_artifact_map"
    assert {artifact["module_owner"] for artifact in payload["artifacts"]} == {"NarratoStudio", "NarratoCut"}


def test_agentflow_feedback_event_example_jsonl_has_schema_version() -> None:
    lines = Path("examples/agentflow/feedback_event.example.jsonl").read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines if line.strip()]

    assert events
    assert all(event["schema_version"] == "0.1.0" for event in events)
    assert {event["artifact_type"] for event in events} == {"agentflow_feedback_event"}
    assert {event["decision"] for event in events} <= {"accepted", "rejected", "needs_revision", "note", "published"}


def test_agentflow_memory_candidate_example_is_candidate_only() -> None:
    payload = json.loads(Path("examples/agentflow/memory_candidate.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_memory_candidate"
    assert payload["promotion_status"] == "candidate"
    assert payload["source_artifact"] == "memory_candidates.json"
    assert payload["source_of_truth"] == "feedback.jsonl"
    assert payload["evidence_refs"]


def test_agentflow_memory_promotion_decision_example_is_explicit_review() -> None:
    payload = json.loads(Path("examples/agentflow/memory_promotion_decision.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_memory_promotion_decision"
    assert payload["source_candidate_id"]
    assert payload["decision"] in {"promoted", "rejected", "merged", "expired"}
    assert payload["promotion_mode"] == "human_reviewed"
    assert payload["writes_long_term_memory"] is False


def test_agentflow_skill_invocation_example_declares_planned_call() -> None:
    payload = json.loads(Path("examples/agentflow/skill_invocation.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_skill_invocation"
    assert payload["skill_id"]
    assert payload["execution_status"] == "planned"
    assert payload["input_artifacts"]
    assert payload["forbidden_side_effects"]


def test_agentflow_skill_result_example_records_outputs_and_gates() -> None:
    payload = json.loads(Path("examples/agentflow/skill_result.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_skill_result"
    assert payload["skill_id"]
    assert payload["execution_status"] in {"succeeded", "failed", "blocked"}
    assert payload["output_artifacts"]
    assert payload["quality_gate_status"]["inspect_run"] in {"passed", "failed", "not_run"}
    assert payload["quality_gate_status"]["review_run"] in {"passed", "failed", "not_run"}


def test_agentflow_router_decision_example_selects_without_executing() -> None:
    payload = json.loads(Path("examples/agentflow/router_decision.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_router_decision"
    assert payload["selected_skill_id"]
    assert payload["selection_reason"]
    assert payload["rejected_candidate_skills"]
    assert all(candidate["skill_id"] and candidate["reason"] for candidate in payload["rejected_candidate_skills"])
    assert payload["execution_status"] == "decision_only"
    assert payload["executes_skill"] is False


def test_agentflow_intermediate_asset_example_is_candidate_with_evidence() -> None:
    payload = json.loads(Path("examples/agentflow/intermediate_asset.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_intermediate_asset"
    assert payload["asset_id"]
    assert payload["asset_kind"]
    assert payload["module_origin"] in {"NarratoStudio", "NarratoCut", "AgentFlow"}
    assert payload["source_artifact_refs"]
    assert payload["evidence_refs"]
    assert payload["reuse_status"] == "candidate"


def test_agentflow_reusable_asset_profile_requires_promotion_decision() -> None:
    payload = json.loads(Path("examples/agentflow/reusable_asset_profile.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_reusable_asset_profile"
    assert payload["asset_profile_id"]
    assert payload["source_intermediate_asset_ids"]
    assert payload["promotion_decision_ref"]
    assert payload["reuse_policy"]
    assert payload["active_status"] in {"active", "inactive", "superseded"}


def test_agentflow_asset_reuse_decision_is_decision_only() -> None:
    payload = json.loads(Path("examples/agentflow/asset_reuse_decision.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_asset_reuse_decision"
    assert payload["decision_id"]
    assert payload["target_task"]
    assert payload["selected_asset_profile_ids"]
    assert isinstance(payload["rejected_asset_profile_ids"], list)
    assert payload["reason"]
    assert payload["does_not_execute"] is True


def test_agentflow_narratostudio_asset_feedback_review_is_review_only() -> None:
    payload = json.loads(
        Path("examples/agentflow/narratostudio_asset_feedback_review.example.json").read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_narratostudio_asset_feedback_review"
    assert payload["validation_scope"] == "narratostudio_asset_feedback_loop"
    assert payload["runtime_status"] == "not_implemented"
    assert payload["does_not_execute"] is True
    assert payload["writes_long_term_memory"] is False
    assert payload["source_validation"]["overall_status"] == "passed"
    assert payload["asset_memory_step_status"] in {"passed", "failed", "not_run"}
    assert payload["asset_memory_validation"]["artifact_type"] == "agentflow_asset_memory_validation"


def test_agentflow_narratostudio_asset_feedback_review_validation_is_harness_only() -> None:
    payload = json.loads(
        Path("examples/agentflow/narratostudio_asset_feedback_review_validation.example.json").read_text(
            encoding="utf-8"
        )
    )

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_narratostudio_asset_feedback_review_validation"
    assert payload["validation_scope"] == "narratostudio_asset_feedback_review"
    assert payload["runtime_status"] == "not_implemented"
    assert payload["does_not_execute"] is True
    assert payload["writes_long_term_memory"] is False
    assert payload["overall_status"] in {"passed", "failed"}
    assert payload["checks"]


def test_agentflow_narratostudio_asset_feedback_review_gate_is_decision_only() -> None:
    payload = json.loads(
        Path("examples/agentflow/narratostudio_asset_feedback_review_gate.example.json").read_text(encoding="utf-8")
    )

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_narratostudio_asset_feedback_review_gate"
    assert payload["gate_scope"] == "narratostudio_asset_feedback_review"
    assert payload["runtime_status"] == "not_implemented"
    assert payload["does_not_execute"] is True
    assert payload["writes_long_term_memory"] is False
    assert payload["gate_status"] in {"passed", "blocked"}
    assert payload["source_validation_artifact_type"] == "agentflow_narratostudio_asset_feedback_review_validation"
    assert isinstance(payload["blocking_check_ids"], list)
    assert payload["next_allowed_actions"]
    check_ids = {check["check_id"] for check in payload["checks"]}
    assert {
        "validation_artifact_type",
        "validation_scope",
        "validation_passed",
        "validation_does_not_execute",
        "validation_does_not_write_memory",
    } <= check_ids


def test_agentflow_skill_router_examples_do_not_include_private_or_generated_paths() -> None:
    forbidden_fragments = [
        "D:\\",
        "C:\\",
        "data/processed/runs",
        "data/raw/",
        ".mp4",
        ".mov",
        "api_key",
        "token",
        "secret",
        "cookie",
        "signed_url",
    ]

    for path in AGENTFLOW_SKILL_ROUTER_EXAMPLES:
        raw_text = path.read_text(encoding="utf-8").lower()
        assert not any(fragment.lower() in raw_text for fragment in forbidden_fragments)


def test_agentflow_asset_examples_do_not_include_private_or_generated_paths() -> None:
    forbidden_fragments = [
        "D:\\",
        "C:\\",
        "data/processed/runs",
        "data/raw/",
        ".mp4",
        ".mov",
        "api_key",
        "token",
        "secret",
        "cookie",
        "signed_url",
    ]

    for path in AGENTFLOW_ASSET_EXAMPLES:
        raw_text = path.read_text(encoding="utf-8").lower()
        assert not any(fragment.lower() in raw_text for fragment in forbidden_fragments)


def test_agentflow_contract_registry_example_indexes_current_contracts() -> None:
    payload = json.loads(Path("examples/agentflow/contract_registry.example.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "0.1.0"
    assert payload["artifact_type"] == "agentflow_contract_registry"
    assert payload["registry_scope"] == "contract_discovery"
    assert payload["runtime_status"] == "not_implemented"
    assert payload["does_not_execute"] is True

    registered_types = {contract["artifact_type"] for contract in payload["contracts"]}
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
        "agentflow_narratostudio_asset_feedback_review_validation",
        "agentflow_narratostudio_asset_feedback_review_gate",
    }
    assert expected_types <= registered_types
    assert all(contract["example_path"] for contract in payload["contracts"])
    assert all(contract["doc_path"] for contract in payload["contracts"])


def test_agentflow_contract_registry_examples_exist_and_match_artifact_types() -> None:
    payload = json.loads(Path("examples/agentflow/contract_registry.example.json").read_text(encoding="utf-8"))
    json_examples = {path.as_posix() for path in AGENTFLOW_EXAMPLE_PATHS if path.suffix == ".json"}
    jsonl_examples = {path.as_posix() for path in AGENTFLOW_EXAMPLE_PATHS if path.suffix == ".jsonl"}

    for contract in payload["contracts"]:
        example_path = contract["example_path"]
        assert example_path in json_examples | jsonl_examples
        if example_path in json_examples:
            example_payload = json.loads(Path(example_path).read_text(encoding="utf-8"))
            assert example_payload["artifact_type"] == contract["artifact_type"]
        else:
            events = [
                json.loads(line)
                for line in Path(example_path).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            assert events
            assert {event["artifact_type"] for event in events} == {contract["artifact_type"]}


def test_agentflow_contract_registry_declares_validation_rules_without_runtime() -> None:
    payload = json.loads(Path("examples/agentflow/contract_registry.example.json").read_text(encoding="utf-8"))

    rule_ids = {rule["rule_id"] for rule in payload["validation_rules"]}
    assert {
        "schema_version_0_1_0",
        "example_path_exists",
        "no_private_paths_or_secrets",
        "router_decision_only",
        "candidate_memory_only",
    } <= rule_ids
    assert "execute_workflow" not in rule_ids
    assert "call_remote_provider" not in rule_ids
