// Studio model presets describe the current MVP execution surface.
// User-facing prompt optimization is always remote-gated; local assembly remains backend-internal.

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
    desc: "keyframe image generation",
    eta: "60s",
    cost: 1,
    provider: "codex",
    capability: "image_keyframe",
    providerServiceId: "codex_image",
  },
];

export const VIDEO_MODELS = [
  {
    id: "kling-i2v",
    name: "Kling I2V",
    desc: "image to video",
    eta: "2m",
    cost: 0,
    provider: "kling",
    capability: "video_i2v",
    providerServiceId: "kling_i2v",
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
  return findModel("image", modelId).providerServiceId || "codex_image";
}

export function isRemoteVideoModel(modelId) {
  return Boolean(findModel("video", modelId).providerServiceId);
}

export function providerServiceForVideoModel(modelId) {
  return findModel("video", modelId).providerServiceId || "kling_i2v";
}
