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
  afs_package_audit_summary_sync: {
    status: "pass_b01_still_blocked",
    manifest_reference_audit: {
      status: "pass",
      errors: 0,
      invalid_asset_types: 0,
      invalid_statuses: 0,
      registry_assets: 87,
      json_files_checked: 14
    },
    text_encoding_audit: {
      status: "pass",
      errors: 0,
      text_files_checked: 268
    },
    phase_gate_audit: {
      status: "blocked_until_b01_human_review",
      failures: 0,
      pending_b01_decisions: 5,
      eligible_context_refs: 3,
      blocked_context_refs: 84
    },
    eligible_memory_refs: 3,
    blocked_memory_refs: 90,
    provider_calls_started: false,
    writes_long_term_memory: false
  },
  afs_package_audit_summary_cli_probe: {
    status: "pass_b01_still_blocked",
    surface: "loulan_memory_package_cli_stdout",
    stdout_lines: [
      "Manifest audit: pass; errors 0; invalid asset types 0; invalid statuses 0",
      "Text encoding audit: pass; errors 0",
      "Phase gate audit: blocked_until_b01_human_review; failures 0; pending B01 5"
    ],
    eligible_memory_refs: 3,
    blocked_memory_refs: 90,
    provider_calls_started: false,
    writes_long_term_memory: false
  },
  afs_package_gate_facts_web_direct_probe: {
    status: "pass_b01_still_blocked",
    artifact_type: "agentflow_loulan_memory_package",
    inspector_status: "review ready",
    inspector_facts: {
      promotion_gate: "blocked",
      next_context_status: "promotion_decision_required",
      b01_apply_status: "blocked_validation_not_ready",
      b01_operator_next_context: "blocked_until_b01_human_review"
    },
    provider_calls_started: false,
    writes_long_term_memory: false
  },
  afs_root_gate_facts_web_direct_probe: {
    status: "blocked_until_b01_human_review",
    artifact_type: "loulan_root_project_manifest",
    inspector_status: "blocked_until_b01_human_review",
    inspector_facts: {
      package_gate_facts: "pass_b01_still_blocked",
      b01_validation: "blocked_pending_human_review",
      next_context: "blocked_until_b01_human_review"
    },
    provider_calls_started: false,
    writes_long_term_memory: false
  },
  afs_latest_gate_facts_web_direct_probe: {
    artifact_type: "loulan_root_project_manifest",
    inspector_status: "blocked_until_b01_human_review",
    inspector_facts: {
      latest_gate_facts: "blocked_until_b01_human_review",
      package_gate_facts: "pass_b01_still_blocked",
      project_audit_gate_facts: "pass_b01_still_blocked",
      b01_validation: "blocked_pending_human_review",
      next_context: "blocked_until_b01_human_review"
    },
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
    assert facts["latest_gate_facts"] == "blocked_until_b01_human_review"
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
    assert facts["package_audit_summary_sync"] == "pass_b01_still_blocked"
    assert facts["package_manifest_errors"] == "0"
    assert facts["package_invalid_asset_types"] == "0"
    assert facts["package_invalid_statuses"] == "0"
    assert facts["package_text_errors"] == "0"
    assert facts["package_phase_failures"] == "0"
    assert facts["package_phase_pending_b01"] == "5"
    assert facts["package_summary_eligible_refs"] == "3"
    assert facts["package_summary_blocked_refs"] == "90"
    assert facts["package_summary_provider_calls_started"] == "false"
    assert facts["package_summary_writes_long_term_memory"] == "false"
    assert facts["package_audit_summary_cli"] == "pass_b01_still_blocked"
    assert facts["package_cli_stdout_lines"] == "3"
    assert facts["package_cli_eligible_refs"] == "3"
    assert facts["package_cli_blocked_refs"] == "90"
    assert facts["package_cli_provider_calls_started"] == "false"
    assert facts["package_cli_writes_long_term_memory"] == "false"
    assert facts["package_gate_facts"] == "pass_b01_still_blocked"
    assert facts["package_gate_next_context"] == "promotion_decision_required"
    assert facts["package_gate_b01_apply"] == "blocked_validation_not_ready"
    assert facts["package_gate_b01_operator_next_context"] == "blocked_until_b01_human_review"
    assert facts["package_gate_provider_calls_started"] == "false"
    assert facts["package_gate_writes_long_term_memory"] == "false"
    assert facts["root_gate_facts"] == "blocked_until_b01_human_review"
    assert facts["root_gate_b01_validation"] == "blocked_pending_human_review"
    assert facts["root_gate_next_context"] == "blocked_until_b01_human_review"
    assert facts["root_gate_provider_calls_started"] == "false"
    assert facts["root_gate_writes_long_term_memory"] == "false"
