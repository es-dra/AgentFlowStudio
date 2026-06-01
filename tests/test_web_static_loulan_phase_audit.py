from __future__ import annotations

import json
import subprocess


def test_static_viewer_recognizes_loulan_asset_governance_phase_audit() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const phaseAudit = {
  schema_version: "0.1.0",
  artifact_type: "loulan_asset_governance_phase_audit",
  project_id: "loulan_scene_assets",
  status: "blocked_until_b01_human_review",
  provider_calls_started: false,
  writes_long_term_memory: false,
  new_media_generated: false,
  summary: {
    phases: 5,
    passed: 4,
    blocked_expected: 1,
    failures: 0,
    registry_assets: 86,
    eligible_context_refs: 3,
    blocked_context_refs: 83,
    pending_b01_decisions: 5
  },
  claim_boundary: {
    human_acceptance: "not_recorded",
    business_validation: "not_validated",
    durable_memory_runtime: "not_written"
  }
};
const artifacts = await parseFiles([
  { name: "asset_governance_phase_audit.json", text: async () => JSON.stringify(phaseAudit) },
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

    assert payload["artifactType"] == "loulan_asset_governance_phase_audit"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan asset governance phase audit"
    assert payload["memoryBundleCount"] == 1
    assert payload["sourceStatus"]["label"] == "Selected files"
    assert payload["inspector"]["title"] == "Loulan asset governance phase audit"
    assert payload["inspector"]["status"] == "blocked_until_b01_human_review"
    assert payload["inspector"]["focus_targets"] == ["project", "review", "next-pass"]
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["phases"] == "5"
    assert facts["passed"] == "4"
    assert facts["blocked_expected"] == "1"
    assert facts["failures"] == "0"
    assert facts["registry_assets"] == "86"
    assert facts["eligible_context_refs"] == "3"
    assert facts["blocked_context_refs"] == "83"
    assert facts["pending_b01_decisions"] == "5"
    assert facts["provider_calls_started"] == "false"
    assert facts["writes_long_term_memory"] == "false"
    assert facts["new_media_generated"] == "false"
