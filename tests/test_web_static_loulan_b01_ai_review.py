from __future__ import annotations

import json
import subprocess


def test_static_viewer_recognizes_loulan_b01_ai_director_pre_review() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const preReview = {
  schema_version: "0.1.0",
  artifact_type: "loulan_b01_ai_director_pre_review",
  status: "ai_recommendation_only_pending_human_decision",
  provider_calls_started: false,
  writes_long_term_memory: false,
  human_acceptance_recorded: false,
  block_id: "B01",
  recommendations: [
    { shot_id: "B01-S01", suggested_decision: "approve_anchor", confidence: "high" },
    { shot_id: "B01-S02", suggested_decision: "request_repair", confidence: "medium" },
    { shot_id: "B01-S03", suggested_decision: "approve_anchor", confidence: "high" },
    { shot_id: "B01-S04", suggested_decision: "approve_anchor", confidence: "high" },
    { shot_id: "B01-S05", suggested_decision: "approve_anchor_with_note", confidence: "medium" }
  ]
};
const artifacts = await parseFiles([
  { name: "ai_director_pre_review.json", text: async () => JSON.stringify(preReview) },
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
    payload = _run_script(script)

    assert payload["artifactType"] == "loulan_b01_ai_director_pre_review"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan B01 AI director pre-review"
    assert payload["memoryBundleCount"] == 1
    assert payload["inspector"]["title"] == "Loulan B01 AI director pre-review"
    assert payload["inspector"]["status"] == "ai_recommendation_only_pending_human_decision"
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["block_id"] == "B01"
    assert facts["recommendations"] == "5"
    assert facts["approve_anchor"] == "3"
    assert facts["request_repair"] == "1"
    assert facts["approve_anchor_with_note"] == "1"
    assert facts["human_acceptance_recorded"] == "false"
    assert facts["provider_calls_started"] == "false"
    assert facts["writes_long_term_memory"] == "false"


def test_static_viewer_recognizes_loulan_b01_ai_suggested_decision_starting_point() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const suggestions = {
  schema_version: "0.1.0",
  artifact_type: "loulan_b01_ai_suggested_decision_starting_point",
  status: "suggestion_only_not_human_acceptance",
  provider_calls_started: false,
  writes_long_term_memory: false,
  human_acceptance_recorded: false,
  items: [
    { target_shot_id: "B01-S01", suggested_decision: "approve_anchor", operator_final_decision: "pending_human_review" },
    { target_shot_id: "B01-S02", suggested_decision: "request_repair", operator_final_decision: "pending_human_review" },
    { target_shot_id: "B01-S03", suggested_decision: "approve_anchor", operator_final_decision: "pending_human_review" },
    { target_shot_id: "B01-S04", suggested_decision: "approve_anchor", operator_final_decision: "pending_human_review" },
    { target_shot_id: "B01-S05", suggested_decision: "approve_anchor_with_note", operator_final_decision: "pending_human_review" }
  ]
};
const artifacts = await parseFiles([
  { name: "ai_suggested_decision_starting_point.json", text: async () => JSON.stringify(suggestions) },
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
    payload = _run_script(script)

    assert payload["artifactType"] == "loulan_b01_ai_suggested_decision_starting_point"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan B01 AI suggestion starting point"
    assert payload["memoryBundleCount"] == 1
    assert payload["inspector"]["title"] == "Loulan B01 AI suggestion starting point"
    assert payload["inspector"]["status"] == "suggestion_only_not_human_acceptance"
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["items"] == "5"
    assert facts["pending_operator_decisions"] == "5"
    assert facts["approve_anchor"] == "3"
    assert facts["request_repair"] == "1"
    assert facts["approve_anchor_with_note"] == "1"
    assert facts["human_acceptance_recorded"] == "false"
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
