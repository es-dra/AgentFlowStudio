from __future__ import annotations

import json
import subprocess


def test_storyboard_keyframe_layer_records_safe_production_graph_review() -> None:
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
        },
        storyboardBreakdown: {
          productionGraphArtifactId: "artifact_production_graph_snapshot",
          productionGraph: {
            summary: { fixed_visual_asset_count: 1 },
            nodes: [{
              node_type: "fixed_visual_asset",
              asset_id: "fixed_lin_wan_v1",
              [unsafeSignedKey]: "must-not-leak",
              local_path: "D:\\private\\graph_fixed_lin_wan.png",
              data_base64: "GRAPH_BYTES_MUST_NOT_LEAK",
            }],
          },
        },
      },
    },
    lin_asset: {
      id: "lin_asset",
      type: "image",
      title: "Asset card - Lin Wan",
      params: {
        nodeRole: "asset_card_draft",
        assetCardDraft: { label: "Lin Wan", asset_type: "character" },
        visualAssets: [{
          asset_id: "fixed_lin_wan_v1",
          asset_type: "character",
          label: "Lin Wan",
          status: "fixed",
          source_evidence: {
            source_human_gate_id: "runtime-human-gate:demo:accepted",
            source_asset_card_candidate_id: "asset_card_candidate:main_character",
            source_stage: "asset_card_candidate_human_gate",
          },
        }],
      },
    },
  },
  edges: { e1: { id: "e1", from: "shot_01", to: "lin_asset" } },
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
process.stdout.write(JSON.stringify(state.nodes[keyframeId].params.keyframeLayer.production_graph_review));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    review = json.loads(completed.stdout)
    serialized = json.dumps(review, ensure_ascii=False).lower()

    assert review == {
        "artifact_id": "artifact_production_graph_snapshot",
        "fixed_asset_reuse_count": 1,
        "fixed_visual_asset_ids": ["fixed_lin_wan_v1"],
    }
    assert "_".join(["signed", "url"]) not in serialized
    assert "data_base64" not in serialized
    assert "d:\\private" not in serialized


def test_keyframe_source_evidence_trace_includes_safe_production_graph_review() -> None:
    script = r'''
import { keyframeSourceEvidenceTrace, keyframeSourceEvidenceTraceSummaryText } from "./apps/studio/src/keyframe-source-evidence-trace.js";

const unsafeSignedKey = ["signed", "url"].join("_");
const node = {
  id: "keyframe_01",
  type: "image",
  params: {
    keyframeLayer: {
      fixed_asset_source_evidence_refs: [{
        asset_id: "fixed_lin_wan_v1",
        asset_type: "character",
        label: "Lin Wan",
        status: "fixed",
        source_asset_card_candidate_id: "asset_card_candidate:main_character",
      }],
      production_graph_review: {
        artifact_id: "artifact_production_graph_snapshot",
        fixed_asset_reuse_count: 1,
        fixed_visual_asset_ids: ["fixed_lin_wan_v1"],
        [unsafeSignedKey]: "must-not-leak",
        local_path: "D:\\private\\graph_fixed_lin_wan.png",
        data_base64: "GRAPH_BYTES_MUST_NOT_LEAK",
      },
    },
  },
};

const trace = keyframeSourceEvidenceTrace(node);
process.stdout.write(JSON.stringify({
  trace,
  summary: keyframeSourceEvidenceTraceSummaryText(trace),
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
    trace = payload["trace"]
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert trace["provider_prompt_inclusion_policy"] == "excluded_by_default"
    assert trace["production_graph_review"] == {
        "artifact_id": "artifact_production_graph_snapshot",
        "fixed_asset_reuse_count": 1,
        "fixed_visual_asset_ids": ["fixed_lin_wan_v1"],
    }
    assert "production_graph fixed_reuse=1" in payload["summary"]
    assert "artifact=artifact_production_graph_snapshot" in payload["summary"]
    assert "_".join(["signed", "url"]) not in serialized
    assert "data_base64" not in serialized
    assert "d:\\private" not in serialized
