// 模型清单为本地预置展示数据：名称 / 描述 / 耗时标签 / 单次 ⚡ 展示值。
// 不代表真实 provider 接入；发送动作在 v1 只产生本地安全预览。

export const TEXT_MODELS = [
  { id: "gvlm-3.1", name: "GVLM 3.1", desc: "多模态文本模型Pro", eta: "20s", cost: 1 },
  { id: "cvlm-5.5", name: "CVLM 5.5", desc: "", eta: "10s", cost: 1 },
  { id: "gvlm-3.1-flash", name: "GVLM 3.1 Flash", desc: "", eta: "15s", cost: 1 },
  { id: "qwen-3-vl-flash", name: "Qwen 3 VL Flash", desc: "", eta: "10s", cost: 1 },
];

export const IMAGE_MODELS = [
  { id: "lib-image", name: "Lib Image", desc: "最新图片模型，长文本能力突出", eta: "60s", cost: 18 },
  { id: "lib-navo-pro", name: "Lib Navo Pro", desc: "", eta: "50s", cost: 14 },
  { id: "lib-navo-2", name: "Lib Navo 2", desc: "", eta: "25s", cost: 8 },
  { id: "midjourney-v8.1", name: "Midjourney V8.1", desc: "风格上新", eta: "50s", cost: 20 },
  { id: "midjourney-v7", name: "Midjourney V7", desc: "风格上新", eta: "50s", cost: 16 },
  { id: "midjourney-niji-7", name: "Midjourney Niji 7", desc: "风格上新", eta: "50s", cost: 16 },
  { id: "seedream-4.6", name: "Seedream 4.6", desc: "", eta: "20s", cost: 10 },
];

export const VIDEO_MODELS = [
  { id: "seedance-2.0", name: "Seedance 2.0", desc: "VIP", eta: "120s", cost: 135 },
  { id: "seedance-2.0-fast", name: "Seedance 2.0 Fast", desc: "", eta: "60s", cost: 60 },
  { id: "lib-video-1.5", name: "Lib Video 1.5", desc: "", eta: "90s", cost: 45 },
];

export const AUDIO_MODELS = [
  { id: "lib-audio", name: "Lib Audio", desc: "音乐 / 音效 / 语音", eta: "30s", cost: 6 },
  { id: "lib-voice", name: "Lib Voice", desc: "文字转语音", eta: "15s", cost: 3 },
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
