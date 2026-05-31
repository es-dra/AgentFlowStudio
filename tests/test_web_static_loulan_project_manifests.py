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
