// Studio model presets describe the current MVP execution surface.
// Only MiniMax text enhancement and MiniMax image keyframes are wired to Runtime providers.

export const TEXT_MODELS = [
  {
    id: "local-creative-agent",
    name: "Local Agent",
    desc: "deterministic prompt assembly",
    eta: "0s",
    cost: 0,
    provider: "local",
  },
  {
    id: "minimax-m3-enhance",
    name: "MiniMax-M3",
    desc: "prompt enhancement",
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
    id: "local-video-preview",
    name: "Video preview",
    desc: "provider disabled",
    eta: "local",
    cost: 0,
    provider: "local",
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
