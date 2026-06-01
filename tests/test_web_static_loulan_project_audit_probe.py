from __future__ import annotations

import json
import subprocess


def test_static_viewer_recognizes_loulan_project_audit_package_probe() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const probe = {
  schema_version: "0.1.0",
  artifact_type: "loulan_afs_project_audit_package_probe",
  status: "pass_b01_still_blocked",
  afs_package_probe: {
    project_audits: {
      manifest_reference: { status: "pass" },
      text_encoding: { status: "pass" },
      phase_gate: { status: "blocked_until_b01_human_review" }
    },
    promotion_gate: "blocked",
    eligible_memory_refs: 3,
    blocked_memory_refs: 90,
    b01_feedback_loop_gate: "blocked_pending_human_review",
    b01_pending_decisions: 5,
    b01_operator_entrypoint: "blocked_pending_human_review",
    b01_operator_pending_decisions: 5,
    b01_operator_steps: 6,
    b01_operator_blocked_until_count: 4,
    b01_operator_recommendations: 5,
    b01_operator_pending_operator_decisions: 5,
    provider_calls_started: false,
    writes_long_term_memory: false
  },
  claim_boundary: {
    human_acceptance: "not_recorded",
    business_validation: "not_validated",
    durable_memory_runtime: "not_written"
  }
};
const artifacts = await parseFiles([
  { name: "afs_project_audit_package_probe.json", text: async () => JSON.stringify(probe) },
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

    assert payload["artifactType"] == "loulan_afs_project_audit_package_probe"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan AFS project audit package probe"
    assert payload["memoryBundleCount"] == 1
    assert payload["sourceStatus"]["label"] == "Selected files"
    assert payload["inspector"]["title"] == "Loulan AFS project audit package probe"
    assert payload["inspector"]["status"] == "pass_b01_still_blocked"
    assert payload["inspector"]["focus_targets"] == ["project", "review", "next-pass"]
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["manifest_reference_audit"] == "pass"
    assert facts["text_encoding_audit"] == "pass"
    assert facts["phase_gate_audit"] == "blocked_until_b01_human_review"
    assert facts["promotion_gate"] == "blocked"
    assert facts["b01_feedback_loop_gate"] == "blocked_pending_human_review"
    assert facts["b01_pending_decisions"] == "5"
    assert facts["b01_operator_entrypoint"] == "blocked_pending_human_review"
    assert facts["b01_operator_pending_decisions"] == "5"
    assert facts["b01_operator_steps"] == "6"
    assert facts["b01_operator_blocked_until_count"] == "4"
    assert facts["b01_operator_recommendations"] == "5"
    assert facts["b01_operator_pending_operator_decisions"] == "5"
    assert facts["eligible_refs"] == "3"
    assert facts["blocked_refs"] == "90"
    assert facts["provider_calls_started"] == "false"
    assert facts["writes_long_term_memory"] == "false"
