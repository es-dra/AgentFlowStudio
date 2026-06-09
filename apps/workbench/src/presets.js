export const PROJECT_TEMPLATES = [
  {
    id: "short-video",
    label: "短视频内容",
    projectType: "short_video_campaign",
    goal: "完成一轮短视频内容制作、审片反馈和风格记忆复用。",
  },
  {
    id: "product-launch",
    label: "产品发布",
    projectType: "product_launch_clip",
    goal: "基于参考素材准备产品发布内容，并完成首轮检查、审片和下一轮复用。",
  },
  {
    id: "knowledge-clip",
    label: "知识切片",
    projectType: "knowledge_clip",
    goal: "把源笔记转成可审片的内容序列，并沉淀可复用的项目风格记忆。",
  },
];

export const SOURCE_PRESETS = [
  {
    id: "brief",
    assetType: "brief",
    label: "内容需求",
    summary: "受众、目标、语气、约束和成功标准摘要。",
  },
  {
    id: "reference",
    assetType: "reference",
    label: "视觉参考",
    summary: "已确认的视觉风格、构图、色彩和质量标准摘要。",
  },
  {
    id: "script",
    assetType: "script",
    label: "脚本提纲",
    summary: "场景结构、表达语气、关键主张和必要节奏摘要。",
  },
];

export function applyProjectTemplate(state, templateId) {
  const template = PROJECT_TEMPLATES.find((item) => item.id === templateId) || PROJECT_TEMPLATES[0];
  state.projectType = template.projectType;
  state.projectGoal = template.goal;
  state.importManifestJson = JSON.stringify(manifestTemplate(state, template), null, 2);
}

export function applySourcePreset(state, presetId) {
  const preset = SOURCE_PRESETS.find((item) => item.id === presetId) || SOURCE_PRESETS[0];
  state.sourceAssetType = preset.assetType;
  state.sourceAssetLabel = preset.label;
  state.sourceAssetSummary = preset.summary;
  state.sourceAssetId = `${preset.assetType}-main`;
}

function manifestTemplate(state, template) {
  const projectId = state.projectId || `${template.id}-project`;
  return {
    artifact_type: "agentflow_project_manifest",
    schema_version: "0.1.0",
    project_id: projectId,
    project_type: template.projectType,
    goal: template.goal,
    source_assets: [],
    content_cards: [],
    runs: [],
    packages: [],
    feedback_refs: [],
    profile_version_refs: [],
    status: "in_progress",
    does_not_store_secrets: true,
    does_not_store_private_asset_bytes: true,
    does_not_auto_sync: true,
  };
}
