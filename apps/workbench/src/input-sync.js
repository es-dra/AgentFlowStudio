import { normalizeBaseUrl } from "./runtime-client.js";

function value(root, id, fallback = "") {
  const node = root.querySelector(`#${id}`);
  return String(node ? node.value : fallback).trim();
}

export function syncInputs(root, state) {
  state.baseUrl = normalizeBaseUrl(value(root, "runtime-url", state.baseUrl));
  state.projectId = value(root, "project-id-action", value(root, "project-id", state.projectId));
  state.projectGoal = value(root, "project-goal", state.projectGoal);
  state.projectType = value(root, "project-type", state.projectType);
  state.importManifestJson = value(root, "import-manifest-json", state.importManifestJson);
  state.sourceAssetId = value(root, "source-asset-id", state.sourceAssetId);
  state.sourceAssetType = value(root, "source-asset-type", state.sourceAssetType);
  state.sourceAssetLabel = value(root, "source-asset-label", state.sourceAssetLabel);
  state.sourceAssetSummary = value(root, "source-asset-summary", state.sourceAssetSummary);
  state.sceneCardId = value(root, "scene-card-id", state.sceneCardId);
  state.sceneCardType = value(root, "scene-card-type", state.sceneCardType);
  state.sceneTitle = value(root, "scene-title", state.sceneTitle);
  state.sceneSummary = value(root, "scene-summary", state.sceneSummary);
  state.sceneTargetPlatform = value(root, "scene-target-platform", state.sceneTargetPlatform);
  state.reviewDecision = value(root, "review-decision", state.reviewDecision);
  state.reviewDecisionNote = value(root, "review-decision-note", state.reviewDecisionNote);
  state.inspectorPrompt = value(root, "inspector-prompt", state.inspectorPrompt);
  state.inspectorReferenceSummary = value(root, "inspector-reference-summary", state.inspectorReferenceSummary);
  state.inspectorStyleDirection = value(root, "inspector-style-direction", state.inspectorStyleDirection);
  state.inspectorRetryIntent = value(root, "inspector-retry-intent", state.inspectorRetryIntent);
  state.assetProfileSeed = value(root, "asset-profile-seed", state.assetProfileSeed);
  state.promotionDecision = value(root, "promotion-decision", state.promotionDecision);
  state.promotionRationale = value(root, "promotion-rationale", state.promotionRationale);
  state.feedbackNote = value(root, "feedback-note", state.feedbackNote);
}
