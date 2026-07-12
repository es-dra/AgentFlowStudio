from __future__ import annotations

import json
import subprocess
from pathlib import Path


STUDIO_ROOT = Path("apps/studio")


def _run_node(script: str) -> dict:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
    )
    return json.loads(completed.stdout)


def test_direct_video_upload_is_explicit_first_frame_source() -> None:
    payload = _run_node(
        r'''
import { ensureVideoFirstFrameAsset, videoInputSourceForRequest } from "./apps/studio/src/video-node-flow.js";

const state = {
  nodes: {
    video_1: {
      id: "video_1",
      type: "video",
      prompt: "slow push in",
      params: {
        uploads: [{
          asset_id: "img_direct_upload",
          filename: "direct.png",
          role: "reference_image",
          preview_url: "/projects/p/image-assets/img_direct_upload/preview",
        }],
      },
      result: "",
    },
  },
  edges: {},
  assets: [],
};
const store = { get: () => state, set: (mutator) => mutator(state) };
const inferred = ensureVideoFirstFrameAsset(store, state.nodes.video_1);
const repeated = ensureVideoFirstFrameAsset(store, state.nodes.video_1);
const requestSource = videoInputSourceForRequest(state.nodes.video_1, repeated.asset_id);
process.stdout.write(JSON.stringify({ inferred, repeated, requestSource, node: state.nodes.video_1 }));
'''
    )

    assert payload["inferred"]["asset_id"] == "img_direct_upload"
    assert payload["inferred"]["source_mode"] == "uploaded_image"
    assert payload["repeated"]["source_mode"] == "uploaded_image"
    assert payload["requestSource"]["source_mode"] == "uploaded_image"
    assert payload["requestSource"]["source_node_id"] == "video_1"
    assert payload["requestSource"]["source_job_id"] is None
    assert payload["node"]["params"]["firstFrameImageAssetId"] == "img_direct_upload"
    assert payload["node"]["params"]["videoInputSource"] == payload["requestSource"]


def test_upstream_uploaded_image_node_is_video_first_frame_source() -> None:
    payload = _run_node(
        r'''
import { ensureVideoFirstFrameAsset, videoInputSourceForRequest } from "./apps/studio/src/video-node-flow.js";

const state = {
  nodes: {
    image_upload_1: {
      id: "image_upload_1",
      type: "image",
      params: {
        uploads: [{
          asset_id: "img_upstream_upload",
          filename: "upstream.png",
          role: "reference_image",
          preview_url: "/projects/p/image-assets/img_upstream_upload/preview",
        }],
      },
    },
    video_1: { id: "video_1", type: "video", params: {}, result: "" },
  },
  edges: { edge_1: { id: "edge_1", from: "image_upload_1", to: "video_1" } },
  assets: [],
};
const store = { get: () => state, set: (mutator) => mutator(state) };
const inferred = ensureVideoFirstFrameAsset(store, state.nodes.video_1);
const repeated = ensureVideoFirstFrameAsset(store, state.nodes.video_1);
const requestSource = videoInputSourceForRequest(state.nodes.video_1, repeated.asset_id);
process.stdout.write(JSON.stringify({ inferred, repeated, requestSource, node: state.nodes.video_1 }));
'''
    )

    assert payload["inferred"]["asset_id"] == "img_upstream_upload"
    assert payload["inferred"]["source_mode"] == "upstream_uploaded_image"
    assert payload["repeated"]["source_mode"] == "upstream_uploaded_image"
    assert payload["requestSource"]["source_mode"] == "upstream_uploaded_image"
    assert payload["requestSource"]["source_node_id"] == "image_upload_1"
    assert payload["requestSource"]["source_job_id"] is None
    assert payload["node"]["params"]["videoInputSource"] == payload["requestSource"]


def test_upstream_generated_image_node_is_video_first_frame_source() -> None:
    payload = _run_node(
        r'''
import { ensureVideoFirstFrameAsset } from "./apps/studio/src/video-node-flow.js";

const state = {
  nodes: {
    image_keyframe_1: {
      id: "image_keyframe_1",
      type: "image",
      params: { nodeRole: "keyframe_generation", lastKeyframeJobId: "job_keyframe_1" },
    },
    video_1: { id: "video_1", type: "video", params: {}, result: "" },
  },
  edges: { edge_1: { id: "edge_1", from: "image_keyframe_1", to: "video_1" } },
  assets: [{
    kind: "keyframe",
    asset_id: "img_generated_keyframe",
    source_node_id: "image_keyframe_1",
    role: "generated_keyframe_reference",
    status: "ready",
    preview_url: "/projects/p/image-assets/img_generated_keyframe/preview",
    created_at: "2026-07-02T09:00:00Z",
  }],
};
const store = { get: () => state, set: (mutator) => mutator(state) };
const inferred = ensureVideoFirstFrameAsset(store, state.nodes.video_1);
process.stdout.write(JSON.stringify({ inferred, node: state.nodes.video_1 }));
'''
    )

    assert payload["inferred"]["asset_id"] == "img_generated_keyframe"
    assert payload["inferred"]["source_mode"] == "upstream_generated_image"
    assert payload["node"]["params"]["videoInputSource"]["source_node_id"] == "image_keyframe_1"


def test_explicit_first_frame_selection_preserves_source_contract() -> None:
    payload = _run_node(
        r'''
import { ensureVideoFirstFrameAsset } from "./apps/studio/src/video-node-flow.js";

const state = {
  nodes: {
    video_1: {
      id: "video_1",
      type: "video",
      params: {
        firstFrameImageAssetId: "img_manual_first_frame",
        videoInputSource: {
          source_mode: "explicit_first_frame_selection",
          source_asset_id: "img_manual_first_frame",
          source_node_id: "video_1",
          role: "first_frame",
        },
      },
      result: "",
    },
  },
  edges: {},
  assets: [],
};
const store = { get: () => state, set: (mutator) => mutator(state) };
const inferred = ensureVideoFirstFrameAsset(store, state.nodes.video_1);
process.stdout.write(JSON.stringify({ inferred, node: state.nodes.video_1 }));
'''
    )

    assert payload["inferred"]["asset_id"] == "img_manual_first_frame"
    assert payload["inferred"]["source_mode"] == "explicit_first_frame_selection"
    assert payload["node"]["params"]["videoInputSource"]["source_mode"] == "explicit_first_frame_selection"


def test_keyframe_selected_first_frame_overrides_stale_explicit_source() -> None:
    payload = _run_node(
        r'''
import { ensureVideoFirstFrameAsset, videoInputSourceForRequest } from "./apps/studio/src/video-node-flow.js";

const state = {
  nodes: {
    video_1: {
      id: "video_1",
      type: "video",
      params: {
        sourceKeyframeNodeId: "keyframe_01",
        sourceKeyframeJobId: "kf_job_001",
        sourceKeyframeAssetId: "img_keyframe_001",
        firstFrameImageAssetId: "img_keyframe_001",
        videoInputSource: {
          source_mode: "explicit_first_frame_selection",
          source_asset_id: "img_keyframe_001",
          source_node_id: "video_1",
          role: "first_frame",
        },
        uploads: [{
          asset_id: "img_keyframe_001",
          filename: "keyframe_01.png",
          role: "first_frame",
          source_role: "generated_keyframe_reference",
          source_node_id: "keyframe_01",
          source_job_id: "kf_job_001",
          preview_url: "/projects/p/image-assets/img_keyframe_001/preview",
        }],
      },
      result: "",
    },
  },
  edges: {},
  assets: [],
};
const store = { get: () => state, set: (mutator) => mutator(state) };
const firstFrame = ensureVideoFirstFrameAsset(store, state.nodes.video_1);
const repeated = ensureVideoFirstFrameAsset(store, state.nodes.video_1);
const requestSource = videoInputSourceForRequest(state.nodes.video_1, repeated.asset_id);
process.stdout.write(JSON.stringify({ firstFrame, repeated, requestSource, node: state.nodes.video_1 }));
'''
    )

    assert payload["firstFrame"]["source_mode"] == "upstream_generated_image"
    assert payload["repeated"]["source_mode"] == "upstream_generated_image"
    assert payload["requestSource"]["source_mode"] == "upstream_generated_image"
    assert payload["requestSource"]["source_node_id"] == "keyframe_01"
    assert payload["requestSource"]["source_job_id"] == "kf_job_001"
    assert payload["node"]["params"]["videoInputSource"] == payload["requestSource"]


def test_keyframe_continuation_request_preserves_generated_image_provenance() -> None:
    payload = _run_node(
        r'''
import { createVideoNodeFromKeyframe } from "./apps/studio/src/keyframe-video-continuation.js";
import { ensureVideoFirstFrameAsset, videoInputSourceForRequest } from "./apps/studio/src/video-node-flow.js";

const state = {
  nodes: {
    keyframe_01: {
      id: "keyframe_01",
      type: "image",
      title: "Keyframe - shot 01",
      x: 120,
      y: 80,
      w: 420,
      h: 320,
      prompt: "Generated keyframe",
      status: "complete",
      previewUrl: "/projects/p/image-assets/img_keyframe_001/preview",
      params: {
        nodeRole: "keyframe_generation",
        lastKeyframeJobId: "kf_job_001",
        spec: { ratio: "16:9", duration: "5s", resolution: "720P" },
        uploads: [{
          asset_id: "img_keyframe_001",
          filename: "keyframe_01.png",
          preview_url: "/projects/p/image-assets/img_keyframe_001/preview",
          role: "generated_keyframe_reference",
        }],
      },
    },
  },
  edges: {},
  order: ["keyframe_01"],
  selection: { nodeIds: ["keyframe_01"], edgeId: null },
  ui: {},
};
let seq = 0;
const store = {
  get: () => state,
  nextId: (prefix) => `${prefix}_${++seq}`,
  set: (mutator) => mutator(state),
};

const video = createVideoNodeFromKeyframe(store, state.nodes.keyframe_01);
const firstFrame = ensureVideoFirstFrameAsset(store, video);
const requestSource = videoInputSourceForRequest(video, firstFrame.asset_id);
process.stdout.write(JSON.stringify({ video, firstFrame, requestSource }));
'''
    )

    source = payload["requestSource"]
    assert payload["firstFrame"]["asset_id"] == "img_keyframe_001"
    assert source["source_mode"] == "upstream_generated_image"
    assert source["source_asset_id"] == "img_keyframe_001"
    assert source["source_node_id"] == "keyframe_01"
    assert source["source_job_id"] == "kf_job_001"
    assert source["role"] == "first_frame"
    assert payload["video"]["params"]["videoInputSource"] == source


def test_video_submit_payload_carries_source_and_duration_contract_markers() -> None:
    source = (STUDIO_ROOT / "src" / "node-video-actions.js").read_text(encoding="utf-8")

    assert "input_source: videoInputSourceForRequest(node, firstFrame)" in source
    assert "duration_sec: parseDuration(node.params?.spec?.duration)" in source
