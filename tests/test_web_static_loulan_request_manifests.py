from __future__ import annotations

import json
import subprocess


def test_static_viewer_recognizes_loulan_image2_request_manifest() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const manifest = {
  requests: [
    { shot_id: "B01-S01", model: "chatgpt_image2", aspect_ratio: "16:9", status: "horizontal_keyframe_candidate_pending_review" },
    { shot_id: "B01-S02", model: "chatgpt_image2", aspect_ratio: "16:9", status: "horizontal_keyframe_candidate_pending_review" },
    { shot_id: "B02-S01", model: "chatgpt_image2", aspect_ratio: "16:9", status: "planned" }
  ]
};
const artifacts = await parseFiles([
  { name: "image2_requests.json", text: async () => JSON.stringify(manifest) },
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

    assert payload["artifactType"] == "loulan_image2_request_manifest"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan Image2 request manifest"
    assert payload["memoryBundleCount"] == 1
    assert payload["sourceStatus"]["label"] == "Selected files"
    assert payload["inspector"]["title"] == "Loulan Image2 request manifest"
    assert payload["inspector"]["status"] == "review ready"
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["requests"] == "3"
    assert facts["models"] == "chatgpt_image2"
    assert facts["blocks"] == "B01, B02"
    assert facts["status_counts"] == "horizontal_keyframe_candidate_pending_review: 2, planned: 1"
    assert facts["aspect_ratios"] == "16:9"
    assert facts["provider_calls_started"] == "false"


def test_static_viewer_recognizes_loulan_kling_i2v_request_manifest() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const manifest = {
  requests: [
    { shot_id: "B01-S01", model: "kling-v3", duration: "3", status: "generated_from_chatgpt_image2_refined_v2_pending_human_review" },
    { shot_id: "B01-S02", model: "kling-v3", duration: "3", status: "blocked_until_keyframe_exists" },
    { shot_id: "B02-S01", model: "kling-v3", duration: "4", status: "blocked_until_keyframe_exists" }
  ]
};
const artifacts = await parseFiles([
  { name: "kling_i2v_requests.json", text: async () => JSON.stringify(manifest) },
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

    assert payload["artifactType"] == "loulan_kling_i2v_request_manifest"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan Kling I2V request manifest"
    assert payload["memoryBundleCount"] == 1
    assert payload["sourceStatus"]["label"] == "Selected files"
    assert payload["inspector"]["title"] == "Loulan Kling I2V request manifest"
    assert payload["inspector"]["status"] == "blocked"
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["requests"] == "3"
    assert facts["models"] == "kling-v3"
    assert facts["blocks"] == "B01, B02"
    assert facts["status_counts"] == "generated_from_chatgpt_image2_refined_v2_pending_human_review: 1, blocked_until_keyframe_exists: 2"
    assert facts["durations"] == "3, 4"
    assert facts["provider_calls_started"] == "false"


def _run_script(script: str) -> dict:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)
