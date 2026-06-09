export const PROJECT_TEMPLATES = [
  {
    id: "short-video",
    label: "Short Video",
    projectType: "short_video_campaign",
    goal: "Create a short-video content production pass with review and style reuse.",
  },
  {
    id: "product-launch",
    label: "Product Launch",
    projectType: "product_launch_clip",
    goal: "Prepare launch content with references, first check, review, and next-pass reuse.",
  },
  {
    id: "knowledge-clip",
    label: "Knowledge Clip",
    projectType: "knowledge_clip",
    goal: "Turn source notes into a reviewed content sequence with reusable style memory.",
  },
];

export const SOURCE_PRESETS = [
  {
    id: "brief",
    assetType: "brief",
    label: "Campaign brief",
    summary: "Audience, offer, tone, constraints, and success criteria summary.",
  },
  {
    id: "reference",
    assetType: "reference",
    label: "Visual reference",
    summary: "Approved visual style, framing, palette, and quality bar summary.",
  },
  {
    id: "script",
    assetType: "script",
    label: "Script outline",
    summary: "Scene outline, voice, key claims, and required beats summary.",
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
