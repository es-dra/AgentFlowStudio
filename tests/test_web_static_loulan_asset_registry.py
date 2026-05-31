from __future__ import annotations

import json
import subprocess


def test_static_viewer_recognizes_loulan_unified_asset_registry() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const registry = {
  schema_version: "0.1.0",
  artifact_type: "loulan_unified_asset_registry",
  project_id: "loulan_scene_assets",
  claim_boundary: {
    provider_calls_started: false,
    writes_long_term_memory: false,
    b01_keyframes_human_acceptance: "pending"
  },
  promotion_rule: {
    eligible_for_next_context: ["approved_anchor", "promoted_reusable"],
    blocked_from_next_context: ["candidate", "needs_repair", "rejected", "route_failed", "source_reference", "superseded"]
  },
  summary: {
    total_assets: 85,
    type_counts: { character: 26, feedback: 20, keyframe: 5, prop: 3, run_evidence: 28, scene: 1, vfx: 2 },
    status_counts: { approved_anchor: 3, candidate: 60, needs_repair: 14, route_failed: 4, superseded: 4 },
    missing_sha256_count: 1,
    missing_ref_count: 7,
    source_quality_issue_count: 10
  },
  assets: [
    { asset_id: "character_zhou_tong_school_v1", asset_type: "character", status: "approved_anchor" },
    { asset_id: "keyframe_b01_s01_h1", asset_type: "keyframe", status: "candidate" }
  ]
};
const artifacts = await parseFiles([
  { name: "asset_registry.json", text: async () => JSON.stringify(registry) },
]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, memorySourceForArtifacts(artifacts));

console.log(JSON.stringify({
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
  sourceStatus: view.source_status,
  inspector: view.artifact_inspector[0],
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["artifactType"] == "loulan_unified_asset_registry"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan unified asset registry"
    assert payload["memoryBundleCount"] == 1
    assert payload["sourceStatus"]["label"] == "Selected files"
    assert payload["inspector"]["title"] == "Loulan unified asset registry"
    assert payload["inspector"]["status"] == "blocked"
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["total_assets"] == "85"
    assert facts["type_counts"] == "character: 26, feedback: 20, keyframe: 5, prop: 3, run_evidence: 28, scene: 1, vfx: 2"
    assert facts["status_counts"] == "approved_anchor: 3, candidate: 60, needs_repair: 14, route_failed: 4, superseded: 4"
    assert facts["missing_sha256"] == "1"
    assert facts["missing_refs"] == "7"
    assert facts["provider_calls_started"] == "false"
    assert facts["writes_long_term_memory"] == "false"
