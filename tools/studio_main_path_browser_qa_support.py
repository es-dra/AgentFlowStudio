from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from tools.studio_asset_context_browser_qa_support import browser_qa_provider_context, runtime_test_client

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tests.runtime_main_loop_e2e_support import build_main_loop_e2e_state  # noqa: E402


SCRIPT_NODE_ID = "script-main-path-browser-qa"
ASSET_NODE_ID = "asset-card-lin-wan-main-path"


def make_project_id() -> str:
    return f"studio-main-path-browser-qa-{int(time.time())}"


def storage_key(project_id: str) -> str:
    return f"afs_studio_canvas_v2:{project_id}"


def prepare_project(runtime_root: Path, *, project_id: str, repo: Path = REPO_ROOT) -> dict[str, Any]:
    client = runtime_test_client(runtime_root)
    previous_cwd = Path.cwd()
    try:
        os.chdir(repo)
        with browser_qa_provider_context():
            state = build_main_loop_e2e_state(client, project_id)
    finally:
        os.chdir(previous_cwd)
    image_assets = client.get(f"/projects/{project_id}/image-assets").json()["assets"]
    studio_state = seeded_studio_state(project_id, state, image_assets)
    saved = client.put(f"/projects/{project_id}/studio-state", json={"state": studio_state})
    if saved.status_code != 200:
        raise AssertionError(f"studio-state setup failed: {saved.status_code} {saved.text}")
    return {
        "project_id": project_id,
        "script_node_id": SCRIPT_NODE_ID,
        "asset_node_id": ASSET_NODE_ID,
        "overlay_id": state.overlay["overlay_id"],
        "fixed_asset_id": state.fixed_asset["asset_id"],
        "production_graph_artifact_id": state.storyboard_payload["artifacts"]["production_graph_snapshot"]["artifact_id"],
        "asset_card_candidate_id": state.candidate["candidate_id"],
    }


def seeded_studio_state(project_id: str, state: Any, image_assets: list[dict[str, Any]]) -> dict[str, Any]:
    payload = state.storyboard_payload
    candidate = state.candidate
    fixed_asset = studio_visual_asset_projection(state.fixed_asset)
    first_shot = payload["shots"][0]
    image_asset = next((item for item in image_assets if item["asset_id"] in fixed_asset.get("image_asset_refs", [])), {})
    graph_artifact_id = payload["artifacts"]["production_graph_snapshot"]["artifact_id"]
    candidate_artifact_id = payload["artifacts"]["asset_card_candidates"]["artifact_id"]
    return {
        "meta": {"projectId": project_id, "projectName": "Studio Main Path Browser QA", "canvasName": "T47 QA", "seq": 10, "updated_at": ""},
        "viewport": {"x": 0, "y": 0, "scale": 1},
        "nodes": {
            SCRIPT_NODE_ID: {
                "id": SCRIPT_NODE_ID,
                "type": "script",
                "title": "Baseline storyboard shot",
                "x": 120,
                "y": 220,
                "w": 280,
                "h": 300,
                "prompt": "",
                "content": first_shot["description"],
                "status": "complete",
                "result": "Runtime storyboard baseline is structure-verified and still needs human review.",
                "params": {
                    "model": None,
                    "attachments": [],
                    "structuredShot": first_shot,
                    "storyboardBreakdown": {
                        "shots": payload["shots"],
                        "assetGraph": payload["asset_graph"],
                        "assetCardCandidates": [candidate],
                        "assetCardCandidateArtifactId": candidate_artifact_id,
                        "contentQualityReport": content_quality_report_projection(payload["content_quality_report"]),
                        "productionGraph": payload["production_graph"],
                        "productionGraphArtifactId": graph_artifact_id,
                    },
                },
            },
            ASSET_NODE_ID: {
                "id": ASSET_NODE_ID,
                "type": "image",
                "title": "Lin Wan fixed asset card",
                "x": 520,
                "y": 250,
                "w": 280,
                "h": 300,
                "prompt": "",
                "content": "",
                "status": "complete",
                "result": "Fixed visual asset reused from runtime human-gate evidence.",
                "previewUrl": image_asset.get("preview_url", ""),
                "params": {
                    "model": "local-image-fixture",
                    "attachments": [],
                    "spec": {"ratio": "1:1"},
                    "uploads": [image_asset] if image_asset else [],
                    "nodeRole": "asset_card_draft",
                    "assetCardDraft": {
                        "asset_type": candidate["asset_type"],
                        "label": candidate["draft_fields"]["display_name"],
                        "signature": fixed_asset.get("signature", ""),
                        "feature_card": {"appearance": candidate["draft_fields"].get("visual_description_seed", "")},
                        "status": "accepted_for_next_step",
                    },
                    "humanGateDecisions": [human_gate_decision_projection(state.gate_payload["human_gate_decision"])],
                    "visualAssets": [fixed_asset],
                },
            },
        },
        "edges": {
            "edge_script_to_asset": {
                "id": "edge_script_to_asset",
                "from": SCRIPT_NODE_ID,
                "to": ASSET_NODE_ID,
                "relation_type": "generation",
            }
        },
        "groups": {},
        "assets": [],
        "order": [SCRIPT_NODE_ID, ASSET_NODE_ID],
    }






def content_quality_report_projection(report: dict[str, Any]) -> dict[str, Any]:
    checks = []
    for item in report.get("checks", []) if isinstance(report.get("checks"), list) else []:
        if not isinstance(item, dict):
            continue
        checks.append({
            "id": item.get("id", ""),
            "status": item.get("status", ""),
            "human_review_needed": bool(item.get("human_review_needed", False)),
        })
    return {
        "summary": dict(report.get("summary") or {}),
        "checks": checks[:12],
    }


def human_gate_decision_projection(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "human_gate_id": decision.get("human_gate_id", ""),
        "target_type": decision.get("target_type", ""),
        "target_id": decision.get("target_id", ""),
        "decision": decision.get("decision", ""),
        "status": decision.get("status", "succeeded"),
        "recorded_at": decision.get("recorded_at", decision.get("reviewed_at", "")),
        "provider_calls_started": bool(decision.get("provider_calls_started", False)),
        "writes_long_term_memory": bool(decision.get("writes_long_term_memory", False)),
        "writes_company_kb": bool(decision.get("writes_company_kb", False)),
    }

def studio_visual_asset_projection(asset: dict[str, Any]) -> dict[str, Any]:
    evidence = asset.get("source_evidence") if isinstance(asset.get("source_evidence"), dict) else {}
    gate = asset.get("promotion_gate") if isinstance(asset.get("promotion_gate"), dict) else {}
    return {
        "asset_id": asset.get("asset_id", ""),
        "asset_type": asset.get("asset_type", ""),
        "label": asset.get("label", ""),
        "status": asset.get("status", "fixed"),
        "version": asset.get("version"),
        "signature": asset.get("signature", ""),
        "image_asset_refs": list(asset.get("image_asset_refs") or []),
        "source_node_id": asset.get("source_node_id", ""),
        "source_evidence": {
            "source_human_gate_id": evidence.get("source_human_gate_id", gate.get("source_human_gate_id", "")),
            "source_asset_card_candidate_id": evidence.get("source_asset_card_candidate_id", gate.get("source_asset_card_candidate_id", "")),
            "source_stage": evidence.get("source_stage", "runtime_human_gate_decision"),
            "provider_calls_started": bool(evidence.get("provider_calls_started", gate.get("provider_calls_started", False))),
            "generated_media_claimed": bool(evidence.get("generated_media_claimed", gate.get("generated_media_claimed", False))),
            "human_creative_acceptance_claimed": bool(evidence.get("human_creative_acceptance_claimed", gate.get("human_creative_acceptance_claimed", False))),
            "business_validation_claimed": bool(evidence.get("business_validation_claimed", gate.get("business_validation_claimed", False))),
        },
        "promotion_gate": {
            "scope": gate.get("scope", "manual_fixed_asset_promotion"),
            "source_contract": gate.get("source_contract", "runtime_human_gate_decision"),
            "source_human_gate_id": gate.get("source_human_gate_id", ""),
            "source_asset_card_candidate_id": gate.get("source_asset_card_candidate_id", ""),
            "provider_calls_started": bool(gate.get("provider_calls_started", False)),
            "generated_media_claimed": bool(gate.get("generated_media_claimed", False)),
            "human_creative_acceptance_claimed": bool(gate.get("human_creative_acceptance_claimed", False)),
            "business_validation_claimed": bool(gate.get("business_validation_claimed", False)),
        },
        "reviewed_at": asset.get("reviewed_at", ""),
    }

def assert_main_path_evidence(
    seed: dict[str, Any],
    keyframe_layer: dict[str, Any],
    first: dict[str, Any],
    second: dict[str, Any],
    plan: dict[str, Any],
    final_node: dict[str, Any],
) -> None:
    for item in (first, second):
        assert item["generation"]["job"]["status"] == "blocked"
        assert item["generation"]["provider_calls_started"] is False
        assert item["generation"]["generation_bridge"]["provider_evidence"]["provider_gate"]["status"] == "blocked"
    assert keyframe_layer["production_graph_review"]["artifact_id"] == seed["production_graph_artifact_id"]
    assert keyframe_layer["fixed_asset_source_evidence_refs"][0]["source_asset_card_candidate_id"] == seed["asset_card_candidate_id"]
    assert second["preflight"]["context_bundle"]["trace_summary"]["feedback_context_overlay_selected_ids"] == [seed["overlay_id"]]
    assert second["request"]["context_subgraph"]["target_node_id"] == final_node["id"]
    target = next(node for node in second["request"]["context_subgraph"]["nodes"] if node["id"] == final_node["id"])
    assert target["node_parameters"]["feedback_context_overlay_decisions"][0]["overlay_id"] == seed["overlay_id"]
    assert plan["context_bundle"]["included_assets"][0]["asset_id"] == seed["fixed_asset_id"]
    assert plan["context_bundle"]["feedback_context_overlays"][0]["overlay_id"] == seed["overlay_id"]
    assert plan["context_bundle"]["feedback_context_overlay_prompt_policy"]["provider_prompt_includes_context_overlays"] is False
    trace = final_node["params"]["lastKeyframeSourceEvidenceTrace"]
    assert trace["production_graph_review"]["artifact_id"] == seed["production_graph_artifact_id"]
    assert trace["provider_prompt_inclusion_policy"] == "excluded_by_default"


def unsafe_marker(value: Any) -> bool:
    text = json.dumps(value, ensure_ascii=False).lower()
    return any(marker in text for marker in ('"provider_raw"', '"signed_url"', "data_base64", "d:\\", "bearer secret"))
