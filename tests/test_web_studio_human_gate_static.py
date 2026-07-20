from __future__ import annotations

import json
import subprocess

from studio_static_helpers import STUDIO_ROOT, _styles


def test_studio_human_gate_hook_uses_runtime_contract_without_promotion() -> None:
    human_gate = STUDIO_ROOT / "src" / "human-gate.js"
    node_menu = (STUDIO_ROOT / "src" / "panels" / "node-menu.js").read_text(encoding="utf-8")
    main = (STUDIO_ROOT / "src" / "main.js").read_text(encoding="utf-8")
    runtime_events = (STUDIO_ROOT / "src" / "studio-runtime-events.js").read_text(encoding="utf-8")
    script_breakdown = (STUDIO_ROOT / "src" / "script-breakdown.js").read_text(encoding="utf-8")
    keyframe_response = (STUDIO_ROOT / "src" / "node-keyframe-response.js").read_text(encoding="utf-8")
    runtime_client = (STUDIO_ROOT / "src" / "runtime-client.js").read_text(encoding="utf-8")
    styles = _styles()

    assert human_gate.is_file()
    human_gate_source = human_gate.read_text(encoding="utf-8")
    assert "HUMAN_GATE_DECISION_EVENT" in human_gate_source
    assert "accepted_for_next_step" in human_gate_source
    assert "needs_revision" in human_gate_source
    assert "asset_card_candidate" in human_gate_source
    assert "keyframe_generation_bridge" in human_gate_source
    assert "accepted_generation_plan_packet" in human_gate_source
    assert "human-gate-target-meta" in human_gate_source
    assert "promoteVisualAsset" not in human_gate_source
    assert "AFS_ALLOW_REMOTE" not in human_gate_source

    assert "openHumanGateMenu" in node_menu
    assert "记录人工 Gate" in node_menu
    assert "humanGateTargets" in node_menu
    assert "bindHumanGateDecisionEvents" in main
    assert "getRuntime().recordHumanGateDecision(payload)" in runtime_events
    assert "assetCardCandidates" in script_breakdown
    assert "lastGenerationBridge" in keyframe_response
    assert "recordHumanGateDecision(payload)" in runtime_client
    assert "human-gate-popover" in styles
    assert "human-gate-target-meta" in styles


def test_studio_human_gate_targets_expose_asset_reuse_policy_summary() -> None:
    script = r'''
import { humanGateTargets } from "./apps/studio/src/human-gate.js";

const node = {
  id: "script_001",
  params: {
    storyboardBreakdown: {
      assetCardCandidateArtifactId: "artifact_asset_candidates",
      assetCardCandidates: {
        candidates: [
          {
            candidate_id: "asset_card_candidate:hero",
            asset_type: "character",
            draft_fields: { display_name: "Hero" },
            reuse_policy: {
              suggested_reuse_scope: "project_reuse_candidate",
              shot_ref_count: 3,
              requires_human_confirmation: true,
              writes_fixed_asset: false,
            },
          },
        ],
      },
    },
  },
};

process.stdout.write(JSON.stringify(humanGateTargets(node)));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    targets = json.loads(completed.stdout)

    assert targets[0]["target_type"] == "asset_card_candidate"
    assert targets[0]["reuse_policy"]["suggested_reuse_scope"] == "project_reuse_candidate"
    assert targets[0]["reuse_policy"]["shot_ref_count"] == 3
    assert targets[0]["reuse_policy"]["requires_human_confirmation"] is True
    assert targets[0]["reuse_policy"]["writes_fixed_asset"] is False
    assert targets[0]["reuse_label"] == "Project reuse / 3 shots"
    assert "reuse_scope=project_reuse_candidate" in targets[0]["note"]


def test_studio_human_gate_targets_include_accepted_generation_plan_packet() -> None:
    script = r'''
import { humanGateTargets } from "./apps/studio/src/human-gate.js";

const node = {
  id: "plan_review_001",
  params: {
    acceptedGenerationPlanArtifactId: "runs-plan-review-source",
    acceptedGenerationPlanPacket: { packet_state: "accepted_project_generation_plan_packet" },
  },
};

process.stdout.write(JSON.stringify(humanGateTargets(node)));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    targets = json.loads(completed.stdout)

    assert targets[0]["target_type"] == "accepted_generation_plan_packet"
    assert targets[0]["target_id"] == "runs-plan-review-source"
    assert targets[0]["artifact_id"] == "runs-plan-review-source"
    assert targets[0]["scope"] == "accepted_generation_plan_packet_review"
    assert "human_creative_acceptance=false" in targets[0]["note"]
