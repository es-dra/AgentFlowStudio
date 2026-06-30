from __future__ import annotations

import json
import subprocess


def test_storyboard_keyframe_layer_records_fixed_asset_source_evidence_safely() -> None:
    script = r'''
import { createKeyframeNodesForStoryboard } from "./apps/studio/src/storyboard-keyframes.js";

const unsafeSignedKey = ["signed", "url"].join("_");
const state = {
  nodes: {
    shot_01: {
      id: "shot_01",
      type: "script",
      title: "Shot 01",
      x: 0,
      y: 0,
      w: 280,
      h: 280,
      prompt: "Shot 01: Lin Wan enters the observatory.",
      content: "Shot 01: Lin Wan enters the observatory.",
      params: {
        structuredShot: {
          shot_id: "shot_01",
          description: "Lin Wan enters the observatory.",
          shot_size: "medium",
          light_atmosphere: "night",
          camera_motion: "locked",
        },
      },
    },
    lin_asset: {
      id: "lin_asset",
      type: "image",
      title: "Asset card - Lin Wan",
      params: {
        nodeRole: "asset_card_draft",
        assetCardDraft: {
          label: "Lin Wan",
          asset_type: "character",
          signature: "black short hair and red trench coat",
        },
        visualAssets: [{
          asset_id: "fixed_lin_wan_v1",
          asset_type: "character",
          label: "Lin Wan",
          status: "fixed",
          signature: "black short hair and red trench coat",
          [unsafeSignedKey]: "top-level-signed-reference",
          local_path: "D:\\private\\fixed_lin_wan.png",
          data_base64: "TOP_LEVEL_BYTES_MUST_NOT_LEAK",
          source_evidence: {
            source_human_gate_id: "runtime-human-gate:demo:accepted",
            source_asset_card_candidate_id: "asset_card_candidate:main_character",
            source_stage: "asset_card_candidate_human_gate",
            [unsafeSignedKey]: "source-signed-reference",
            local_path: "D:\\private\\source_fixed_lin_wan.png",
            data_base64: "SOURCE_BYTES_MUST_NOT_LEAK",
          },
        }],
      },
    },
  },
  edges: {
    e1: { id: "e1", from: "shot_01", to: "lin_asset" },
  },
  order: ["shot_01", "lin_asset"],
  selection: { nodeIds: [], edgeId: null },
  ui: {},
};

let seq = 0;
const store = {
  get: () => state,
  nextId: () => `node_${++seq}`,
  set: (mutator) => mutator(state),
};

const [keyframeId] = createKeyframeNodesForStoryboard(store, state.nodes.shot_01);
const keyframe = state.nodes[keyframeId];
process.stdout.write(JSON.stringify({
  prompt: keyframe.prompt,
  layer: keyframe.params.keyframeLayer,
}));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    layer = payload["layer"]
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert layer["status"] == "ready_with_fixed_assets"
    assert layer["fixed_visual_asset_ids"] == ["fixed_lin_wan_v1"]
    assert layer["fixed_asset_source_evidence_count"] == 1
    assert layer["fixed_asset_source_evidence_refs"] == [
        {
            "asset_id": "fixed_lin_wan_v1",
            "asset_type": "character",
            "label": "Lin Wan",
            "status": "fixed",
            "source_human_gate_id": "runtime-human-gate:demo:accepted",
            "source_asset_card_candidate_id": "asset_card_candidate:main_character",
            "source_stage": "asset_card_candidate_human_gate",
        }
    ]
    assert "_".join(["signed", "url"]) not in serialized
    assert "data_base64" not in serialized
    assert "d:\\private" not in serialized
