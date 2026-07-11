from __future__ import annotations

import json
import subprocess


def _run_node(script: str) -> dict:
    completed = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8-sig",
    )
    return json.loads(completed.stdout)


def test_video_duration_controls_keep_afs_contract_but_constrain_model_support() -> None:
    payload = _run_node(
        r'''
import { VIDEO_DURATIONS } from "./apps/studio/src/presets/specs.js";
import {
  normalizeVideoCapabilities,
  supportedVideoDurationLabels,
  videoDurationOptions,
} from "./apps/studio/src/presets/video-capabilities.js";
import {
  applyGenerationProfileSettings,
  generationProfile,
} from "./apps/studio/src/panels/generation-panel-profile.js";

const capabilities = normalizeVideoCapabilities({ supportedDurationsSec: [5, 10] });
const durationOptions = videoDurationOptions(capabilities);
const node = { type: "video", params: { model: "seedance-i2v", spec: { duration: "7s" } } };
const profile = generationProfile(node);
const target = JSON.parse(JSON.stringify(node));
applyGenerationProfileSettings(target, profile, {
  ratio: { value: "9:16" },
  resolution: { value: "720P" },
  duration: { value: "7s" },
  motion: { value: "fixed" },
});

process.stdout.write(JSON.stringify({
  contractDurations: VIDEO_DURATIONS,
  supportedDurations: supportedVideoDurationLabels(capabilities),
  promptOptions: durationOptions,
  profileOptions: profile.fields.find((field) => field.key === "duration")?.options || [],
  appliedDuration: target.params.spec.duration,
}));
'''
    )

    assert payload["contractDurations"] == [f"{second}s" for second in range(1, 16)]
    assert payload["supportedDurations"] == ["5s", "10s"]
    assert payload["profileOptions"] == ["5s", "10s"]
    assert payload["appliedDuration"] == "5s"
    disabled = {item["value"]: item for item in payload["promptOptions"] if item["disabled"]}
    assert "1s" in disabled
    assert "15s" in disabled
    assert "unsupported" in disabled["1s"]["label"]
    enabled = {item["value"]: item for item in payload["promptOptions"] if not item["disabled"]}
    assert sorted(enabled) == ["10s", "5s"]


def test_video_preflight_duration_block_stops_before_runtime_generate_video() -> None:
    payload = _run_node(
        r'''
import { startRemoteVideoGeneration } from "./apps/studio/src/node-video-actions.js";

const state = {
  nodes: {
    video_1: {
      id: "video_1",
      type: "video",
      prompt: "A slow camera push in.",
      status: "empty",
      result: "",
      params: {
        model: "seedance-i2v",
        firstFrameImageAssetId: "img_first",
        videoInputSource: {
          source_mode: "explicit_first_frame_selection",
          source_asset_id: "img_first",
          source_node_id: "video_1",
          role: "first_frame",
        },
        uploads: [{ asset_id: "img_first", role: "first_frame" }],
        spec: { duration: "7s", resolution: "720P", ratio: "9:16" },
      },
    },
  },
  edges: {},
  assets: [],
};

const store = {
  get: () => state,
  set: (mutator) => mutator(state),
  flushRuntimeSave: async () => {},
};
let generateCalls = 0;
const runtime = {
  preflightVideo: async () => ({
    provider_calls_started: false,
    provider_capability_limits: {
      provider_service_id: "seedance_i2v",
      source: "provider_descriptor",
      provider_calls_started: false,
      duration_seconds: {
        requested: 7,
        allowed: [5, 10],
        supported: false,
      },
    },
    preflight_blocked: true,
    blocked_unsupported_combinations: [{
      error: "unsupported_duration",
      field: "duration_sec",
      stage: "provider_capability_check",
      provider_calls_started: false,
      details: {
        requested: 7,
        allowed: [5, 10],
        provider_service_id: "seedance_i2v",
        provider_calls_started: false,
      },
    }],
    preflight_token: "blocked-token",
  }),
  generateVideo: async () => {
    generateCalls += 1;
    return {};
  },
};

await startRemoteVideoGeneration(store, runtime, state.nodes.video_1);
process.stdout.write(JSON.stringify({ generateCalls, node: state.nodes.video_1 }));
'''
    )

    assert payload["generateCalls"] == 0
    assert payload["node"]["status"] == "error"
    assert "Video preflight blocked" in payload["node"]["result"]
    assert payload["node"]["params"]["videoProviderCapabilities"]["durationSeconds"]["allowed"] == [5, 10]
    assert payload["node"]["params"]["videoProviderCapabilityBlocks"][0]["error"] == "unsupported_duration"


def test_studio_video_capabilities_project_generation_path_contracts() -> None:
    payload = _run_node(
        r'''
import {
  DEFAULT_STUDIO_VIDEO_CAPABILITIES,
  VIDEO_GENERATION_PATH_CONTRACTS,
  generationPathContract,
  normalizeVideoCapabilities,
} from "./apps/studio/src/presets/video-capabilities.js";

const capabilities = normalizeVideoCapabilities({});
const t2v = generationPathContract("t2v");
const i2v = generationPathContract("i2v_first_frame");

process.stdout.write(JSON.stringify({
  pathIds: Object.keys(VIDEO_GENERATION_PATH_CONTRACTS).sort(),
  defaultSupportedPaths: DEFAULT_STUDIO_VIDEO_CAPABILITIES.supportedGenerationPaths,
  normalizedSupportedPaths: capabilities.supportedGenerationPaths,
  t2v,
  i2v,
}));
'''
    )

    assert payload["pathIds"] == [
        "director_to_keyframe",
        "director_to_video",
        "i2v_first_frame",
        "i2v_first_last",
        "reference_video",
        "t2v",
    ]
    assert payload["defaultSupportedPaths"] == ["i2v_first_frame", "i2v_first_last"]
    assert payload["normalizedSupportedPaths"] == ["i2v_first_frame", "i2v_first_last"]
    assert payload["t2v"]["adoptionState"] == "planned"
    assert payload["t2v"]["safePreflight"]["providerCallsStarted"] is False
    assert "first_frame_image_asset_id" not in payload["t2v"]["requiredInputs"]
    assert payload["i2v"]["adoptionState"] == "supported"
    assert "first_frame_image_asset_id" in payload["i2v"]["requiredInputs"]
