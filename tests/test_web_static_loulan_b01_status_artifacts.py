from __future__ import annotations

import json
import subprocess


def test_static_viewer_recognizes_loulan_b01_decision_validation_report() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const validation = {
  schema_version: "0.1.0",
  artifact_type: "loulan_b01_decision_validation_report",
  status: "blocked_pending_human_review",
  provider_calls_started: false,
  writes_long_term_memory: false,
  human_acceptance_recorded: false,
  summary: {
    decision_items: 5,
    pending: 5,
    approved: 0,
    request_repair: 0,
    rejected: 0,
    errors: 0,
    warnings: 0
  }
};
const artifacts = await parseFiles([
  { name: "human_review_decision_validation_report.json", text: async () => JSON.stringify(validation) },
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
    payload = _run_script(script)

    assert payload["artifactType"] == "loulan_b01_decision_validation_report"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan B01 decision validation report"
    assert payload["memoryBundleCount"] == 1
    assert payload["sourceStatus"]["label"] == "Selected files"
    assert payload["inspector"]["title"] == "Loulan B01 decision validation report"
    assert payload["inspector"]["status"] == "blocked_pending_human_review"
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["decision_items"] == "5"
    assert facts["pending_decisions"] == "5"
    assert facts["approved_decisions"] == "0"
    assert facts["repair_requested"] == "0"
    assert facts["rejected_decisions"] == "0"
    assert facts["human_acceptance_recorded"] == "false"
    assert facts["provider_calls_started"] == "false"


def test_static_viewer_recognizes_loulan_b01_decision_apply_result() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const applyResult = {
  schema_version: "0.1.0",
  artifact_type: "loulan_b01_decision_apply_result",
  status: "blocked_validation_not_ready",
  apply_requested: false,
  applied: false,
  validation_status: "blocked_pending_human_review",
  provider_calls_started: false,
  writes_long_term_memory: false,
  next_step: "operator must fill approve_anchor, request_repair, or reject for every B01 decision item"
};
const artifacts = await parseFiles([
  { name: "b01_decision_apply_result.json", text: async () => JSON.stringify(applyResult) },
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
    payload = _run_script(script)

    assert payload["artifactType"] == "loulan_b01_decision_apply_result"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan B01 decision apply result"
    assert payload["memoryBundleCount"] == 1
    assert payload["sourceStatus"]["label"] == "Selected files"
    assert payload["inspector"]["title"] == "Loulan B01 decision apply result"
    assert payload["inspector"]["status"] == "blocked_validation_not_ready"
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["apply_requested"] == "false"
    assert facts["applied"] == "false"
    assert facts["validation_status"] == "blocked_pending_human_review"
    assert facts["provider_calls_started"] == "false"
    assert facts["writes_long_term_memory"] == "false"


def _run_script(script: str) -> dict:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)
