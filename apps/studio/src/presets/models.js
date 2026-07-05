// Studio model presets describe the current MVP execution surface.
// User-facing prompt optimization is always remote-gated; local assembly remains backend-internal.

import { DEFAULT_STUDIO_VIDEO_CAPABILITIES, normalizeVideoCapabilities } from "./video-capabilities.js";

export const IMAGE_RELAY_SERVICE_ID = "image_relay";
export const VIDEO_RELAY_SERVICE_ID = "seedance_i2v";

export const TEXT_MODELS = [
  {
    id: "prompt-optimizer",
    name: "提示词优化",
    desc: "context-aware prompt enhancement",
    eta: "15s",
    cost: 1,
    provider: "runtime",
    capability: "llm_prompt_enhancement",
    llmProvider: "prompt_optimizer",
  },
];

export const IMAGE_MODELS = [
  {
    id: "image2-keyframe",
    name: "Image2",
    desc: "external relay image generation",
    eta: "60s",
    cost: 1,
    provider: "relay",
    capability: "image_keyframe",
    providerServiceId: IMAGE_RELAY_SERVICE_ID,
  },
];

export const VIDEO_MODELS = [
  {
    id: "seedance-i2v",
    name: "Seedance 2.0 Fast",
    desc: "image to video",
    eta: "2m",
    cost: 1,
    provider: "relay",
    capability: "video_i2v",
    providerServiceId: VIDEO_RELAY_SERVICE_ID,
    videoCapabilities: DEFAULT_STUDIO_VIDEO_CAPABILITIES,
  },
];

export const AUDIO_MODELS = [
  {
    id: "local-audio-preview",
    name: "Audio preview",
    desc: "provider disabled",
    eta: "local",
    cost: 0,
    provider: "local",
  },
];

export const MODELS_BY_NODE_TYPE = {
  text: TEXT_MODELS,
  script: TEXT_MODELS,
  image: IMAGE_MODELS,
  video: VIDEO_MODELS,
  video_merge: VIDEO_MODELS,
  audio: AUDIO_MODELS,
};

export function defaultModel(nodeType) {
  return (MODELS_BY_NODE_TYPE[nodeType] || TEXT_MODELS)[0];
}

export function findModel(nodeType, modelId) {
  return (MODELS_BY_NODE_TYPE[nodeType] || TEXT_MODELS).find((m) => m.id === modelId) || defaultModel(nodeType);
}

export function isRemoteImageModel(modelId) {
  return Boolean(findModel("image", modelId).providerServiceId);
}

export function providerServiceForImageModel(modelId) {
  return findModel("image", modelId).providerServiceId || IMAGE_RELAY_SERVICE_ID;
}

export function isRemoteVideoModel(modelId) {
  return Boolean(findModel("video", modelId).providerServiceId);
}

export function providerServiceForVideoModel(modelId) {
  return findModel("video", modelId).providerServiceId || VIDEO_RELAY_SERVICE_ID;
}

export function videoCapabilitiesForVideoModel(modelId) {
  return normalizeVideoCapabilities(findModel("video", modelId).videoCapabilities || {});
}
