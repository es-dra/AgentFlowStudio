from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools"
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from tools import studio_main_path_browser_qa as main_path_qa
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
