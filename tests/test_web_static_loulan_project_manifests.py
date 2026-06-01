from __future__ import annotations

import json
import subprocess


def test_static_viewer_recognizes_loulan_project_manifests() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const files = [
  {
    name: "character_assets.json",
    payload: {
      artifact_type: "loulan_character_asset_manifest",
      claim_level: "candidate_assets_pending_human_review",
      provider_route: "ChatGPT built-in image generation / image2",
      writes_long_term_memory: false,
      assets: [
        { asset_id: "zhou_tong_school_v1", character: "Zhou Tong", status: "candidate_pending_human_review" },
        { asset_id: "zhou_tong_qipao_front_v1", character: "Zhou Tong", status: "candidate_pending_human_review" }
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
        { asset_id: "chitu_bag_v0", prop: "Chitu horse crossbody bag", status: "candidate_superseded_by_sketch_reference" },
        { asset_id: "chitu_bag_v1", prop: "Chitu horse crossbody bag", status: "provider_route_failure" }
      ]
    }
  },
  {
    name: "shot_list.json",
    payload: {
      shots: [
        { shot_id: "B01-S01", generation_block: 1, scene: "Loulan ruins", quality_status: "horizontal_keyframe_candidate_pending_review", target_format: "horizontal_16_9" },
        { shot_id: "B02-S01", generation_block: 2, scene: "School corridor", quality_status: "planned", target_format: "horizontal_16_9" }
      ]
    }
  }
];
const artifacts = await parseFiles(files.map((item) => ({ name: item.name, text: async () => JSON.stringify(item.payload) })));
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, memorySourceForArtifacts(artifacts));
const inspectors = Object.fromEntries(view.artifact_inspector.map((item) => [item.artifact_type, item]));
const factsFor = (type) => Object.fromEntries(inspectors[type].facts.map((item) => [item.label, item.value]));

console.log(JSON.stringify({
  artifactTypes: artifacts.map((artifact) => artifact.artifactType),
  artifactClasses: Object.fromEntries(artifacts.map((artifact) => [artifact.fileName, artifact.artifactClass])),
  sourceRoles: Object.fromEntries(artifacts.map((artifact) => [artifact.fileName, artifact.sourceRole])),
  memoryBundleCount: workspace.memoryBundle.length,
  sourceStatus: view.source_status,
  inspectors,
  characterFacts: factsFor("loulan_character_asset_manifest"),
  versionFacts: factsFor("loulan_character_asset_versions"),
  propFacts: factsFor("loulan_prop_asset_versions"),
  shotFacts: factsFor("loulan_shot_list_manifest"),
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["artifactTypes"] == [
        "loulan_character_asset_manifest",
        "loulan_character_asset_versions",
        "loulan_prop_asset_versions",
        "loulan_shot_list_manifest",
    ]
    assert set(payload["artifactClasses"].values()) == {"known_contract"}
    assert payload["sourceRoles"]["character_assets.json"] == "Loulan character asset manifest"
    assert payload["sourceRoles"]["character_asset_versions.json"] == "Loulan character asset versions"
    assert payload["sourceRoles"]["prop_asset_versions.json"] == "Loulan prop asset versions"
    assert payload["sourceRoles"]["shot_list.json"] == "Loulan shot list manifest"
    assert payload["memoryBundleCount"] == 4
    assert payload["sourceStatus"]["label"] == "Selected files"
    assert payload["inspectors"]["loulan_character_asset_manifest"]["status"] == "candidate_assets_pending_human_review"
    assert payload["characterFacts"]["assets"] == "2"
    assert payload["characterFacts"]["characters"] == "Zhou Tong"
    assert payload["characterFacts"]["status_counts"] == "candidate_pending_human_review: 2"
    assert payload["characterFacts"]["writes_long_term_memory"] == "false"
    assert payload["versionFacts"]["assets"] == "2"
    assert payload["versionFacts"]["characters"] == "Zhou Tong, Guan Pingping"
    assert payload["propFacts"]["assets"] == "2"
    assert payload["propFacts"]["status_counts"] == "candidate_superseded_by_sketch_reference: 1, provider_route_failure: 1"
    assert payload["shotFacts"]["shots"] == "2"
    assert payload["shotFacts"]["blocks"] == "1, 2"
    assert payload["shotFacts"]["quality_status_counts"] == "horizontal_keyframe_candidate_pending_review: 1, planned: 1"
    assert payload["shotFacts"]["target_formats"] == "horizontal_16_9"


def test_static_viewer_recognizes_loulan_root_project_manifest() -> None:
    script = """
import { parseFiles, normalizeWorkspace } from "./apps/web/artifact-workspace.js";
import { buildMemoryWorkbenchView, memorySourceForArtifacts } from "./apps/web/memory-workbench-controller.js";

const manifest = {
  schema_version: "0.1.0",
  project_id: "loulan_scene_assets",
  title: "Loulan time-control scene asset project",
  target_format: "horizontal_16_9",
  shot_count: 38,
  current_phase: "keyframe_only_horizontal_16_9",
  current_claim_level: "asset_registry_ready_b01_keyframes_pending_human_review",
  video_generation_status: "deferred_until_keyframe_approval",
  manifest_reference_audit_status: "pass",
  text_encoding_audit_status: "pass",
  asset_governance_phase_audit_status: "blocked_until_b01_human_review",
  afs_feedback_loop_status: "project_phase_gate_visible_in_afs_no_call_package_b01_pending_review",
  afs_package_audit_summary_status: "pass_b01_still_blocked",
  afs_package_audit_summary_direct_probe_status: "pass_b01_still_blocked",
  afs_package_audit_summary_cli_status: "pass_b01_still_blocked",
  afs_package_audit_summary_cli_direct_probe_status: "pass_b01_still_blocked",
  afs_package_gate_facts_web_direct_probe_status: "pass_b01_still_blocked",
  afs_project_audit_gate_facts_web_direct_probe_status: "pass_b01_still_blocked",
  afs_root_project_audit_gate_facts_web_direct_probe_status: "blocked_until_b01_human_review",
  b01_human_review_validation_status: "blocked_pending_human_review",
  next_context_status: "blocked_until_b01_human_review"
};
const artifacts = await parseFiles([
  { name: "project_manifest.json", text: async () => JSON.stringify(manifest) },
]);
const workspace = normalizeWorkspace(artifacts);
const view = buildMemoryWorkbenchView(workspace, memorySourceForArtifacts(artifacts));
const inspector = view.artifact_inspector[0];
const facts = Object.fromEntries(inspector.facts.map((item) => [item.label, item.value]));

console.log(JSON.stringify({
  artifactType: artifacts[0].artifactType,
  artifactClass: artifacts[0].artifactClass,
  sourceRole: artifacts[0].sourceRole,
  memoryBundleCount: workspace.memoryBundle.length,
  sourceStatus: view.source_status,
  inspector,
  facts,
}));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)

    assert payload["artifactType"] == "loulan_root_project_manifest"
    assert payload["artifactClass"] == "known_contract"
    assert payload["sourceRole"] == "Loulan root project manifest"
    assert payload["memoryBundleCount"] == 1
    assert payload["sourceStatus"]["label"] == "Selected files"
    assert payload["inspector"]["title"] == "Loulan root project manifest"
    assert payload["inspector"]["status"] == "blocked_until_b01_human_review"
    assert payload["inspector"]["focus_targets"] == ["project", "assets", "review", "next-pass"]
    assert payload["facts"]["project_id"] == "loulan_scene_assets"
    assert payload["facts"]["target_format"] == "horizontal_16_9"
    assert payload["facts"]["shots"] == "38"
    assert payload["facts"]["current_phase"] == "keyframe_only_horizontal_16_9"
    assert payload["facts"]["manifest_reference_audit"] == "pass"
    assert payload["facts"]["text_encoding_audit"] == "pass"
    assert payload["facts"]["phase_gate_audit"] == "blocked_until_b01_human_review"
    assert payload["facts"]["package_audit_summary"] == "pass_b01_still_blocked"
    assert payload["facts"]["package_audit_summary_direct"] == "pass_b01_still_blocked"
    assert payload["facts"]["package_audit_summary_cli"] == "pass_b01_still_blocked"
    assert payload["facts"]["package_audit_summary_cli_direct"] == "pass_b01_still_blocked"
    assert payload["facts"]["package_gate_facts"] == "pass_b01_still_blocked"
    assert payload["facts"]["project_audit_gate_facts"] == "pass_b01_still_blocked"
    assert payload["facts"]["latest_gate_facts"] == "blocked_until_b01_human_review"
    assert payload["facts"]["b01_validation"] == "blocked_pending_human_review"
    assert payload["facts"]["next_context"] == "blocked_until_b01_human_review"
