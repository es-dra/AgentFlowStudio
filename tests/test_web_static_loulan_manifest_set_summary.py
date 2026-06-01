from __future__ import annotations

import json
import subprocess


def test_web_memory_workbench_summarizes_selected_loulan_manifest_set() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const files = [
  {
    name: "asset_registry.json",
    payload: {
      artifact_type: "loulan_unified_asset_registry",
      project_id: "loulan_time_control_scene_assets",
      summary: {
        total_assets: 87,
        type_counts: { character: 26, feedback: 21, keyframe: 5, prop: 3, run_evidence: 29, scene: 1, vfx: 2 },
        status_counts: { approved_anchor: 3, candidate: 62, needs_repair: 14, route_failed: 4, superseded: 4 },
        missing_sha256_count: 0,
        missing_ref_count: 0
      },
      claim_boundary: {
        provider_calls_started: false,
        writes_long_term_memory: false
      }
    }
  },
  {
    name: "next_context_bundle_draft.json",
    payload: {
      artifact_type: "loulan_next_generation_context_bundle_draft",
      project_id: "loulan_time_control_scene_assets",
      status: "blocked_until_b01_human_review",
      target_next_block: "B02",
      eligible_context_refs: ["asset:character_zhou_tong_school_v1", "scene:loulan_ruins_v1", "vfx:blue_time_v1"],
      blocked_context_refs_by_status: {
        candidate: Array.from({ length: 62 }, (_, index) => `asset:candidate_${index}`),
        needs_repair: Array.from({ length: 14 }, (_, index) => `asset:repair_${index}`),
        route_failed: Array.from({ length: 4 }, (_, index) => `asset:route_failed_${index}`),
        superseded: Array.from({ length: 4 }, (_, index) => `asset:superseded_${index}`)
      },
      review_evidence_refs: ["feedback:director_b01", "motion:b01_s03"],
      gates: {
        b01_keyframe_human_review: "blocked_pending_human_review",
        provider_image_gate: "blocked_no_call",
        provider_video_gate: "blocked_no_call"
      },
      claim_boundary: {
        provider_calls_started: false,
        new_media_generated: false,
        durable_memory_write: false
      }
    }
  },
  {
    name: "b01_human_review_decision_template.json",
    payload: {
      artifact_type: "loulan_b01_human_review_decision_template",
      status: "blocked_pending_human_review",
      decision_items: [
        { target_shot_id: "B01-S01", decision: "pending_human_review" },
        { target_shot_id: "B01-S02", decision: "pending_human_review" },
        { target_shot_id: "B01-S03", decision: "pending_human_review" },
        { target_shot_id: "B01-S04", decision: "pending_human_review" },
        { target_shot_id: "B01-S05", decision: "pending_human_review" }
      ],
      provider_calls_started: false,
      human_acceptance_recorded: false
    }
  },
  {
    name: "image2_requests.json",
    payload: {
      artifact_type: "loulan_image2_request_manifest",
      requests: Array.from({ length: 38 }, (_, index) => ({ shot_id: `S${index}`, model: "chatgpt_image2", status: index ? "planned" : "horizontal_keyframe_candidate_pending_review", aspect_ratio: "16:9" }))
    }
  },
  {
    name: "kling_i2v_requests.json",
    payload: {
      artifact_type: "loulan_kling_i2v_request_manifest",
      requests: Array.from({ length: 38 }, (_, index) => ({ shot_id: `S${index}`, model: "kling-v3", status: index ? "blocked_until_keyframe_exists" : "generated_from_chatgpt_image2_refined_v2_pending_human_review", duration: 4 }))
    }
  },
  {
    name: "character_assets.json",
    payload: {
      artifact_type: "loulan_character_asset_manifest",
      claim_level: "candidate_assets_pending_human_review",
      writes_long_term_memory: false,
      assets: [
        { asset_id: "zhou_tong_school_v1", character: "Zhou Tong", status: "candidate_pending_human_review" }
      ]
    }
  },
  {
    name: "character_asset_versions.json",
    payload: {
      artifact_type: "loulan_character_asset_versions",
      assets: [
        { asset_id: "zhou_tong_school_v1", character: "Zhou Tong", status: "approved_character_memory" },
        { asset_id: "guan_pingping_v6", character: "Guan Pingping", status: "repair_target_refined_current" }
      ]
    }
  },
  {
    name: "prop_asset_versions.json",
    payload: {
      artifact_type: "loulan_prop_asset_versions",
      assets: [
        { asset_id: "chitu_bag_v1", prop: "Chitu horse crossbody bag", status: "provider_route_failure" }
      ]
    }
  },
  {
    name: "shot_list.json",
    payload: {
      shots: [
        ...Array.from({ length: 38 }, (_, index) => ({ shot_id: `S${index}`, generation_block: index < 5 ? 1 : 2, quality_status: index ? "planned" : "horizontal_keyframe_candidate_pending_review", target_format: "horizontal_16_9" }))
      ]
    }
  }
];

const artifacts = await parseFiles(files.map((item) => ({ name: item.name, text: async () => JSON.stringify(item.payload) })));
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, memorySourceForArtifacts(artifacts));

console.log(JSON.stringify({
  contract_type: view.contract_type,
  state: view.state,
  project: view.project,
  bundle_summary: view.bundle_summary,
  memory_loaded: view.memory_loaded,
  lanes: view.lanes,
  protocol_summary: view.protocol_summary,
  next_pass: view.next_pass,
  artifactInspectorCount: view.artifact_inspector.length,
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        encoding="utf-8",
        text=True,
    )
    payload = json.loads(result.stdout)
    bundle = {item["id"]: item for item in payload["bundle_summary"]}
    controls = {item["label"]: item for item in payload["protocol_summary"]["controls"]}

    assert payload["contract_type"] == "loulan_manifest_set"
    assert payload["state"] == "blocked_until_b01_human_review"
    assert "Loulan manifest set" in payload["project"]["title"]
    assert "9 selected Loulan manifests" in payload["project"]["brief"]
    assert bundle["asset-registry"]["detail"] == "87 assets; 3 eligible, 84 blocked"
    assert bundle["b01-human-review"]["status"] == "blocked_pending_human_review"
    assert bundle["b01-human-review"]["detail"] == "5 pending B01 decisions"
    assert bundle["request-manifests"]["detail"] == "38 Image2 requests; 38 Kling I2V requests"
    assert bundle["project-manifests"]["detail"] == "38 shots; character assets selected: true; prop assets selected: true"
    assert payload["next_pass"]["status"] == "blocked_until_b01_human_review"
    assert "B02" in payload["next_pass"]["action"]
    assert "3 eligible refs, 84 blocked refs" in payload["next_pass"]["action"]
    assert "B01 human review" in payload["next_pass"]["action"]
    assert payload["memory_loaded"][0]["id"] == "asset:character_zhou_tong_school_v1"
    assert payload["memory_loaded"][0]["promotion_status"] == "eligible_context_ref"
    assert any(item["promotion_status"] == "blocked_candidate" for item in payload["memory_loaded"])
    assert payload["lanes"][1]["status"] == "blocked"
    assert controls["manifest coverage"]["status"] == "review ready"
    assert controls["B01 human review"]["status"] == "blocked_pending_human_review"
    assert controls["provider image gate"]["status"] == "blocked_no_call"
    assert controls["provider video gate"]["status"] == "blocked_no_call"
    assert controls["durable memory write"]["detail"] == "false"
    assert payload["artifactInspectorCount"] == 9
