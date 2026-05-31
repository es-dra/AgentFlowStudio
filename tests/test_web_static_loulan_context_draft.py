from __future__ import annotations

import json
import subprocess


def test_static_viewer_recognizes_loulan_next_context_bundle_draft() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const draft = {
  schema_version: "0.1.0",
  artifact_type: "loulan_next_generation_context_bundle_draft",
  project_id: "loulan_scene_assets",
  target_next_block: "B02",
  status: "blocked_until_b01_human_review",
  claim_boundary: {
    provider_calls_started: false,
    new_media_generated: false,
    durable_memory_write: false
  },
  eligible_context_refs: [
    { memory_ref: "asset:character_zhou_tong_qipao_front_v2" },
    { memory_ref: "asset:character_zhou_tong_qipao_three_view_v4" },
    { memory_ref: "asset:character_zhou_tong_school_v1" }
  ],
  blocked_context_refs_by_status: {
    candidate: Array.from({ length: 60 }, (_, i) => `asset:candidate_${i}`),
    needs_repair: Array.from({ length: 14 }, (_, i) => `asset:repair_${i}`),
    route_failed: Array.from({ length: 4 }, (_, i) => `asset:route_${i}`),
    superseded: Array.from({ length: 4 }, (_, i) => `asset:superseded_${i}`)
  },
  review_evidence_refs: Array.from({ length: 28 }, (_, i) => ({ memory_ref: `asset:review_${i}` })),
  gates: {
    b01_keyframe_human_review: "blocked",
    provider_image_gate: "blocked_not_authorized",
    provider_video_gate: "blocked_not_authorized"
  },
  afs_projection_check: {
    eligible_refs_match_package: true
  }
};
const artifacts = await parseFiles([
  { name: "next_context_bundle_draft.json", text: async () => JSON.stringify(draft) },
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

    assert payload["artifactType"] == "loulan_next_generation_context_bundle_draft"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan next context bundle draft"
    assert payload["memoryBundleCount"] == 1
    assert payload["sourceStatus"]["label"] == "Selected files"
    assert payload["inspector"]["title"] == "Loulan next context bundle draft"
    assert payload["inspector"]["status"] == "blocked_until_b01_human_review"
    facts = {item["label"]: item["value"] for item in payload["inspector"]["facts"]}
    assert facts["target_next_block"] == "B02"
    assert facts["eligible_context_refs"] == "3"
    assert facts["blocked_refs_by_status"] == "candidate: 60, needs_repair: 14, route_failed: 4, superseded: 4"
    assert facts["review_evidence_refs"] == "28"
    assert facts["b01_keyframe_human_review"] == "blocked"
    assert facts["provider_image_gate"] == "blocked_not_authorized"
    assert facts["provider_video_gate"] == "blocked_not_authorized"
    assert facts["provider_calls_started"] == "false"
    assert facts["new_media_generated"] == "false"
    assert facts["durable_memory_write"] == "false"
    assert facts["eligible_refs_match_package"] == "true"
