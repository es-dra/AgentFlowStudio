from __future__ import annotations

import json
import subprocess


def test_static_viewer_recognizes_loulan_b01_operator_entrypoint() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const entrypoint = {
  schema_version: "0.1.0",
  artifact_type: "loulan_b01_operator_entrypoint",
  project_id: "loulan_scene_assets",
  block_id: "B01",
  status: "blocked_pending_human_review",
  provider_calls_started: false,
  writes_long_term_memory: false,
  human_acceptance_recorded: false,
  new_media_generated: false,
  current_gate_summary: {
    decision_items: 5,
    pending_decisions: 5,
    approved_decisions: 0,
    repair_requested: 0,
    rejected_decisions: 0,
    validation_status: "blocked_pending_human_review",
    apply_status: "blocked_validation_not_ready",
    next_context_status: "blocked_until_b01_human_review"
  },
  ai_recommendation_summary: {
    recommendations: 5,
    approve_anchor: 3,
    request_repair: 1,
    approve_anchor_with_note: 1,
    operator_decisions_still_pending: 5
  },
  operator_sequence: [
    { step_id: "open_review_packet" },
    { step_id: "compare_ai_suggestions" },
    { step_id: "fill_decision_template" },
    { step_id: "validate_decisions" },
    { step_id: "dry_run_apply" },
    { step_id: "apply_after_ready" }
  ],
  blocked_until: [
    "all five B01 decision_items are filled by the human operator",
    "Loulan validation returns ready_for_apply",
    "Loulan apply dry-run returns ready_dry_run",
    "operator explicitly requests apply"
  ]
};
const artifacts = await parseFiles([
  { name: "b01_operator_entrypoint.json", text: async () => JSON.stringify(entrypoint) },
]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, memorySourceForArtifacts(artifacts));

console.log(JSON.stringify({
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
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

    assert payload["artifactType"] == "loulan_b01_operator_entrypoint"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan B01 operator entrypoint"
    assert payload["memoryBundleCount"] == 1
    assert payload["inspector"]["title"] == "Loulan B01 operator entrypoint"
    assert payload["inspector"]["status"] == "blocked_pending_human_review"
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["block_id"] == "B01"
    assert facts["decision_items"] == "5"
    assert facts["pending_decisions"] == "5"
    assert facts["validation_status"] == "blocked_pending_human_review"
    assert facts["apply_status"] == "blocked_validation_not_ready"
    assert facts["next_context_status"] == "blocked_until_b01_human_review"
    assert facts["operator_steps"] == "6"
    assert facts["blocked_until"] == "4"
    assert facts["recommendations"] == "5"
    assert facts["pending_operator_decisions"] == "5"
    assert facts["human_acceptance_recorded"] == "false"
    assert facts["provider_calls_started"] == "false"
    assert facts["writes_long_term_memory"] == "false"
