from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from tools import studio_main_path_browser_qa as main_path_qa
from tools.studio_delivery_readiness_gate import build_delivery_readiness
from tools.studio_asset_context_browser_qa_support import runtime_test_client


def test_main_path_browser_qa_screenshot_defaults_next_to_report(tmp_path) -> None:
    report = tmp_path / "evidence" / "main_path_report.json"

    screenshot = main_path_qa.resolve_screenshot_path(report, "")

    assert screenshot == report.with_suffix(".png")


def test_main_path_browser_qa_screenshot_can_be_overridden(tmp_path) -> None:
    report = tmp_path / "main_path_report.json"
    explicit = tmp_path / "screens" / "main-path.png"

    screenshot = main_path_qa.resolve_screenshot_path(report, str(explicit))

    assert screenshot == explicit.resolve()


def test_main_path_browser_qa_ignores_recovered_studio_state_conflict_only_with_saved_evidence() -> None:
    response_errors = [{"status": 409, "url": "http://127.0.0.1:8790/projects/demo/studio-state"}]
    console_error = "Failed to load resource: the server responded with a status of 409 (Conflict)"
    recovery = {"studio_state_conflict_recovered": True}

    ignored = [item for item in response_errors if main_path_qa.is_ignored_response_error(item, recovery)]
    actionable_console = [item for item in [console_error] if not main_path_qa.is_ignored_console_error(item, ignored, recovery)]

    assert ignored == response_errors
    assert actionable_console == []


def test_main_path_browser_qa_keeps_unrecovered_studio_state_conflict_actionable() -> None:
    response_errors = [{"status": 409, "url": "http://127.0.0.1:8790/projects/demo/studio-state"}]
    console_error = "Failed to load resource: the server responded with a status of 409 (Conflict)"
    recovery = {"studio_state_conflict_recovered": False}

    ignored = [item for item in response_errors if main_path_qa.is_ignored_response_error(item, recovery)]
    actionable_console = [item for item in [console_error] if not main_path_qa.is_ignored_console_error(item, ignored, recovery)]

    assert ignored == []
    assert actionable_console == [console_error]


def test_main_path_browser_qa_keeps_unrelated_409_actionable() -> None:
    response_error = {"status": 409, "url": "http://127.0.0.1:8790/projects/demo/other-route"}

    assert main_path_qa.is_ignored_response_error(response_error, {"studio_state_conflict_recovered": True}) is False


def test_main_path_browser_qa_keeps_non_recovered_console_and_network_failures_actionable() -> None:
    recovered = {"studio_state_conflict_recovered": True}
    ignored_studio_conflict = [{"status": 409, "url": "http://127.0.0.1:8790/projects/demo/studio-state"}]

    assert main_path_qa.is_ignored_response_error({"status": 500, "url": "http://127.0.0.1:8790/projects/demo/studio-state"}, recovered) is False
    assert main_path_qa.is_ignored_console_error("Failed to load resource: the server responded with a status of 500 (Internal Server Error)", ignored_studio_conflict, recovered) is False
    assert main_path_qa.is_ignored_console_error("Uncaught TypeError: Cannot read properties of undefined", ignored_studio_conflict, recovered) is False
    assert main_path_qa.is_ignored_console_error("Failed to load resource: the server responded with a status of 409 (Conflict)", [], recovered) is False


def test_main_path_browser_qa_recovery_evidence_requires_saved_keyframe_decision() -> None:
    state = {
        "nodes": {
            "node_keyframe": {
                "id": "node_keyframe",
                "params": {
                    "keyframeLayer": {"status": "ready_with_fixed_assets"},
                    "lastKeyframeJobId": "job_123",
                    "feedbackOverlayDecisions": [{"overlay_id": "overlay_123", "decision": "include_for_next_context"}],
                },
            }
        }
    }

    recovered = main_path_qa.studio_state_conflict_recovery_from_state(state, "node_keyframe", "overlay_123")
    missing_decision = main_path_qa.studio_state_conflict_recovery_from_state(state, "node_keyframe", "overlay_missing")

    assert recovered["studio_state_conflict_recovered"] is True
    assert recovered["saved_keyframe_job_id"] == "job_123"
    assert recovered["saved_feedback_overlay_decision"] is True
    assert recovered["saved_keyframe_layer"] is True
    assert missing_decision["studio_state_conflict_recovered"] is False


def test_prepare_project_seeds_runtime_main_path_studio_contract(tmp_path) -> None:
    project_id = "studio-main-path-seed-test"

    seed = main_path_qa.prepare_project(tmp_path, project_id=project_id)

    client = runtime_test_client(tmp_path)
    state = client.get(f"/projects/{project_id}/studio-state").json()["state"]
    script = state["nodes"][main_path_qa.SCRIPT_NODE_ID]
    asset = state["nodes"][main_path_qa.ASSET_NODE_ID]
    edge = state["edges"]["edge_script_to_asset"]
    serialized = json.dumps(state, ensure_ascii=False).lower()

    assert seed["project_id"] == project_id
    assert seed["case_id"] == "multi_role_prop_exchange_chase"
    assert seed["shot_count"] == 6
    assert seed["content_quality_human_review_needed"] is True
    assert seed["asset_card_candidate_count"] >= 3
    assert seed["production_graph_relationship_count"] >= 1
    assert seed["overlay_id"].startswith("runtime-feedback-context-overlay:")
    assert seed["fixed_asset_id"]
    assert state["order"] == [main_path_qa.SCRIPT_NODE_ID, main_path_qa.ASSET_NODE_ID]
    assert edge["from"] == main_path_qa.SCRIPT_NODE_ID
    assert edge["to"] == main_path_qa.ASSET_NODE_ID
    assert script["type"] == "script"
    assert script["params"]["storyboardBreakdown"]["productionGraphArtifactId"] == seed["production_graph_artifact_id"]
    assert script["params"]["storyboardBreakdown"]["productionGraph"]["summary"]["fixed_visual_asset_count"] == 1
    assert asset["params"]["nodeRole"] == "asset_card_draft"
    assert asset["params"]["visualAssets"][0]["asset_id"] == seed["fixed_asset_id"]
    assert asset["params"]["visualAssets"][0]["promotion_gate"]["provider_calls_started"] is False
    assert asset["params"]["humanGateDecisions"][0]["provider_calls_started"] is False
    assert "data_base64" not in serialized
    assert "signed_url" not in serialized
    assert "provider_raw" not in serialized
    assert "d:\\" not in serialized


def test_main_path_evidence_assertion_accepts_blocked_overlay_selected_chain() -> None:
    seed = {
        "overlay_id": "runtime-feedback-context-overlay:seed",
        "fixed_asset_id": "vas_seed",
        "production_graph_artifact_id": "artifact_production_graph_seed",
        "asset_card_candidate_id": "asset_card_candidate:seed",
    }
    keyframe_layer = {
        "production_graph_review": {"artifact_id": seed["production_graph_artifact_id"]},
        "fixed_asset_source_evidence_refs": [
            {"source_asset_card_candidate_id": seed["asset_card_candidate_id"]},
        ],
    }
    blocked = {
        "preflight": {"context_bundle": {"trace_summary": {}}},
        "generation": {
            "job": {"status": "blocked"},
            "provider_calls_started": False,
            "generation_bridge": {"provider_evidence": {"provider_gate": {"status": "blocked"}}},
        },
        "request": {},
    }
    second = {
        **blocked,
        "preflight": {
            "context_bundle": {
                "trace_summary": {"feedback_context_overlay_selected_ids": [seed["overlay_id"]]},
            }
        },
        "request": {
            "context_subgraph": {
                "target_node_id": "node_keyframe",
                "nodes": [
                    {
                        "id": "node_keyframe",
                        "node_parameters": {
                            "feedback_context_overlay_decisions": [
                                {"overlay_id": seed["overlay_id"], "decision": "include_for_next_context"}
                            ]
                        },
                    }
                ],
            }
        },
    }
    plan = {
        "context_bundle": {
            "included_assets": [{"asset_id": seed["fixed_asset_id"]}],
            "feedback_context_overlays": [{"overlay_id": seed["overlay_id"]}],
            "feedback_context_overlay_prompt_policy": {"provider_prompt_includes_context_overlays": False},
        }
    }
    final_node = {
        "id": "node_keyframe",
        "params": {
            "lastKeyframeSourceEvidenceTrace": {
                "production_graph_review": {"artifact_id": seed["production_graph_artifact_id"]},
                "provider_prompt_inclusion_policy": "excluded_by_default",
            }
        },
    }

    main_path_qa.assert_main_path_evidence(seed, keyframe_layer, blocked, second, plan, final_node)


def test_main_path_browser_qa_tool_stays_provider_closed() -> None:
    source = (REPO_ROOT / "tools" / "studio_main_path_browser_qa.py").read_text(encoding="utf-8")

    assert "allow_live_llm" not in source
    assert '"provider_calls_started": False' in source
    assert "AFS_ALLOW_REMOTE" not in source
    assert "not provider smoke" in source


def test_delivery_readiness_gate_reports_internal_provider_closed_tryout_ready() -> None:
    report = {
        "case_id": "multi_role_prop_exchange_chase",
        "fixed_asset_id": "visual_asset:seed",
        "production_graph_artifact_id": "artifact_production_graph_seed",
        "second_request_plan_artifact_id": "artifact_keyframe_request_plan_seed",
        "second_bridge_artifact_id": "artifact_keyframe_bridge_seed",
        "overlay_id": "runtime-feedback-context-overlay:seed",
        "feedback_overlay_decision_recorded": True,
        "provider_calls_started": False,
        "console_error_count": 0,
        "response_error_count": 0,
    }
    seed = {
        "case_id": "multi_role_prop_exchange_chase",
        "shot_count": 6,
        "expected_shot_range": [6, 6],
        "content_quality_human_review_needed": True,
        "asset_card_candidate_count": 9,
        "production_graph_relationship_count": 21,
        "fixed_visual_asset_count": 1,
    }

    readiness = build_delivery_readiness(report, seed)

    assert readiness["verdict"] == "internal_provider_closed_tryout_ready"
    assert readiness["product_readiness"] == "provider_closed_internal_tryout_path_ready"
    assert {item["status"] for item in readiness["checks"]} == {"passed"}
    assert "human_creative_acceptance_not_claimed" in readiness["remaining_gates"]
    assert "provider_smoke_requires_explicit_authorization" in readiness["remaining_gates"]


def test_delivery_readiness_gate_blocks_missing_provider_closed_signal() -> None:
    report = {
        "case_id": "multi_role_prop_exchange_chase",
        "fixed_asset_id": "visual_asset:seed",
        "production_graph_artifact_id": "artifact_production_graph_seed",
        "second_request_plan_artifact_id": "artifact_keyframe_request_plan_seed",
        "second_bridge_artifact_id": "artifact_keyframe_bridge_seed",
        "overlay_id": "runtime-feedback-context-overlay:seed",
        "feedback_overlay_decision_recorded": True,
        "provider_calls_started": True,
        "console_error_count": 0,
        "response_error_count": 0,
    }
    seed = {
        "case_id": "multi_role_prop_exchange_chase",
        "shot_count": 6,
        "expected_shot_range": [6, 6],
        "content_quality_human_review_needed": True,
        "asset_card_candidate_count": 9,
        "production_graph_relationship_count": 21,
        "fixed_visual_asset_count": 1,
    }

    readiness = build_delivery_readiness(report, seed)

    assert readiness["verdict"] == "not_ready_with_blockers"
    assert any(item["check_id"] == "provider_closed_browser_runtime" and item["status"] == "blocked" for item in readiness["checks"])
