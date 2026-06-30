from __future__ import annotations

import json
import subprocess
from pathlib import Path


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


def test_keyframe_source_evidence_trace_summary_is_safe_for_output_record() -> None:
    script = r'''
import { keyframeSourceEvidenceTraceSummaryText } from "./apps/studio/src/keyframe-source-evidence-trace.js";

const unsafeSignedKey = ["signed", "url"].join("_");
const trace = {
  trace_type: "studio_keyframe_layer_source_evidence",
  provider_prompt_inclusion_policy: "excluded_by_default",
  fixed_asset_source_evidence_refs: [{
    asset_id: "fixed_lin_wan_v1",
    asset_type: "character",
    label: "Lin Wan",
    status: "fixed",
    source_asset_card_candidate_id: "asset_card_candidate:main_character",
    [unsafeSignedKey]: "must-not-leak",
    local_path: "D:\\private\\fixed_lin_wan.png",
    data_base64: "BYTES_MUST_NOT_LEAK",
  }],
};

process.stdout.write(JSON.stringify({ text: keyframeSourceEvidenceTraceSummaryText(trace) }));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)
    serialized = json.dumps(payload, ensure_ascii=False).lower()

    assert "关键帧来源证据：1 项" in payload["text"]
    assert "Lin Wan" in payload["text"]
    assert "excluded_by_default" in payload["text"]
    assert "_".join(["signed", "url"]) not in serialized
    assert "data_base64" not in serialized
    assert "d:\\private" not in serialized


def test_inspector_output_record_wires_keyframe_source_evidence_trace_summary() -> None:
    inspector = Path("apps/studio/src/panels/inspector-panel.js").read_text(encoding="utf-8")

    assert "keyframeSourceEvidenceTraceSummaryText" in inspector
    assert "keyframeEvidenceTraceSummary(node)" in inspector
    assert "lastKeyframeSourceEvidenceTrace" in inspector


def test_inspector_context_summary_surfaces_keyframe_layer_source_evidence() -> None:
    script = r'''
import { nodeContextSummaryText } from "./apps/studio/src/panels/inspector-context-summary.js";

const node = {
  id: "keyframe_01",
  type: "image",
  params: {
    keyframeLayer: {
      fixed_asset_source_evidence_count: 1,
      fixed_asset_source_evidence_refs: [{
        asset_id: "fixed_lin_wan_v1",
        asset_type: "character",
        label: "Lin Wan",
        status: "fixed",
        source_human_gate_id: "runtime-human-gate:demo:accepted",
        source_asset_card_candidate_id: "asset_card_candidate:main_character",
        source_stage: "asset_card_candidate_human_gate",
      }],
    },
  },
};

process.stdout.write(JSON.stringify({ text: nodeContextSummaryText(node) }));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    payload = json.loads(completed.stdout)

    assert "关键帧来源证据" in payload["text"]
    assert "Lin Wan" in payload["text"]
    assert "asset_card_candidate:main_character" in payload["text"]


def test_keyframe_response_records_local_source_evidence_trace_safely() -> None:
    script = r'''
import { applyKeyframeResponse } from "./apps/studio/src/node-keyframe-response.js";

const unsafeSignedKey = ["signed", "url"].join("_");
const state = {
  nodes: {
    keyframe_01: {
      id: "keyframe_01",
      type: "image",
      status: "generating",
      prompt: "Generate Lin Wan keyframe",
      params: {
        keyframeLayer: {
          fixed_asset_source_evidence_refs: [{
            asset_id: "fixed_lin_wan_v1",
            asset_type: "character",
            label: "Lin Wan",
            status: "fixed",
            source_human_gate_id: "runtime-human-gate:demo:accepted",
            source_asset_card_candidate_id: "asset_card_candidate:main_character",
            source_stage: "asset_card_candidate_human_gate",
            [unsafeSignedKey]: "must-not-leak",
            local_path: "D:\\private\\fixed_lin_wan.png",
            data_base64: "BYTES_MUST_NOT_LEAK",
          }],
        },
      },
    },
  },
  assets: [],
};
const store = {
  get: () => state,
  set: (mutator) => mutator(state),
};
const response = { job: { job_id: "job_001", status: "blocked" }, safe_manifest: { status: "blocked" } };

applyKeyframeResponse(store, "keyframe_01", response, { aspect_ratio: "16:9" });

process.stdout.write(JSON.stringify(state.nodes.keyframe_01.params.lastKeyframeSourceEvidenceTrace));
'''
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    trace = json.loads(completed.stdout)
    serialized = json.dumps(trace, ensure_ascii=False).lower()

    assert trace["trace_type"] == "studio_keyframe_layer_source_evidence"
    assert trace["provider_prompt_inclusion_policy"] == "excluded_by_default"
    assert trace["fixed_asset_source_evidence_count"] == 1
    assert trace["fixed_asset_source_evidence_refs"][0]["asset_id"] == "fixed_lin_wan_v1"
    assert trace["fixed_asset_source_evidence_refs"][0]["source_asset_card_candidate_id"] == "asset_card_candidate:main_character"
    assert "_".join(["signed", "url"]) not in serialized
    assert "data_base64" not in serialized
    assert "d:\\private" not in serialized
