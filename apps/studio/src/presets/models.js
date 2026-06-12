// Studio model presets describe the current MVP execution surface.
// User-facing prompt optimization is always remote-gated; local assembly remains backend-internal.

export const TEXT_MODELS = [
  {
    id: "minimax-m3-enhance",
    name: "提示词优化",
    desc: "remote prompt enhancement",
    eta: "15s",
    cost: 1,
    provider: "minimax",
    capability: "llm_prompt_enhancement",
    llmProvider: "minimax_m3",
  },
];

export const IMAGE_MODELS = [
  {
    id: "minimax-image-01",
    name: "MiniMax image-01",
    desc: "keyframe provider",
    eta: "60s",
    cost: 1,
    provider: "minimax",
    capability: "image_keyframe",
    providerServiceId: "minimax_image",
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
  return IMAGE_MODELS.some((m) => m.id === modelId && m.providerServiceId);
}

export function providerServiceForImageModel(modelId) {
  return findModel("image", modelId).providerServiceId || "minimax_image";
}

export function isRemoteVideoModel(modelId) {
  return VIDEO_MODELS.some((m) => m.id === modelId && m.providerServiceId);
}

export function providerServiceForVideoModel(modelId) {
  return findModel("video", modelId).providerServiceId || "kling_i2v";
}
