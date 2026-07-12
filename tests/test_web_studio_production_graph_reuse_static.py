from __future__ import annotations

import json
import subprocess

from studio_static_helpers import STUDIO_ROOT


def test_studio_storyboard_persists_production_graph_for_reuse_surface() -> None:
    script_breakdown = (STUDIO_ROOT / "src" / "script-breakdown.js").read_text(encoding="utf-8")

    assert "productionGraph: breakdown.production_graph || null" in script_breakdown
    assert "productionGraphArtifactId" in script_breakdown
    assert "payload?.production_graph || null" in script_breakdown


def test_human_gate_targets_include_production_graph_fixed_asset_reuse_summary() -> None:
    script = r'''
import { humanGateTargets } from "./apps/studio/src/human-gate.js";

const node = {
  id: "script_001",
  params: {
    storyboardBreakdown: {
      assetCardCandidateArtifactId: "artifact_asset_candidates",
      productionGraphArtifactId: "artifact_production_graph",
      productionGraph: {
        summary: { fixed_visual_asset_count: 1 },
        nodes: [{ node_type: "fixed_visual_asset", asset_id: "vas_fixed_001" }],
      },
      assetCardCandidates: {
        candidates: [{
          candidate_id: "asset_card_candidate:hero",
          asset_type: "character",
          draft_fields: { display_name: "Hero" },
          reuse_policy: { suggested_reuse_scope: "project_reuse_candidate", shot_ref_count: 3 },
        }],
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

    assert targets[0]["graph_reuse_label"] == "Fixed reuse / 1 asset"
    assert "fixed_asset_reuse_count=1" in targets[0]["note"]
    assert "production_graph_artifact_id=artifact_production_graph" in targets[0]["note"]
