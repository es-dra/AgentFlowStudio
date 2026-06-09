import { latestJobId, selectedCard, selectedVariant } from "./app-selection.js";

function nowIso() {
  return new Date().toISOString();
}

export function createActionHandlers({ state, client, refreshWorkbench }) {
  async function createProject() {
    state.lastResult = await client().createProject({
      project_id: state.projectId,
      project_type: state.projectType || "short_video_campaign",
      goal: state.projectGoal || "Runtime Service workbench project.",
      status: "in_progress",
    });
    await refreshWorkbench();
  }

  async function importProject() {
    const manifest = JSON.parse(state.importManifestJson || "{}");
    state.lastResult = await client().importProject(manifest);
    state.projectId = state.lastResult.project_id || state.projectId;
    await refreshWorkbench();
  }

  async function exportProject() {
    state.lastResult = await client().exportProject(state.projectId);
    state.artifact = state.lastResult;
    state.selectedArtifactId = state.lastResult.artifact?.artifact_id || "";
  }

  async function registerSourceAsset() {
    state.lastResult = await client().registerSourceAsset(state.projectId, {
      asset_id: state.sourceAssetId,
      asset_type: state.sourceAssetType || "reference",
      label: state.sourceAssetLabel,
      summary: state.sourceAssetSummary,
    });
    await refreshWorkbench();
  }

  async function registerContentCard() {
    state.lastResult = await client().registerContentCard(state.projectId, {
      card_id: state.sceneCardId,
      card_type: state.sceneCardType || "scene",
      title: state.sceneTitle,
      summary: state.sceneSummary,
      target_platform: state.sceneTargetPlatform || "short_video",
    });
    await refreshWorkbench();
  }

  async function draftCanvas() {
    state.lastResult = await client().draftCanvas(state.projectId, {
      generated_at: nowIso(),
    });
    await refreshWorkbench();
  }

  async function recordReviewDecision() {
    const card = selectedCard(state);
    const variant = selectedVariant(state);
    if (!card) throw new Error("Select a scene or canvas card before marking review.");
    state.lastResult = await client().recordReviewDecision(state.projectId, {
      card_id: variant?.card_id || card.id,
      candidate_id: variant?.candidate_id || "",
      artifact_id: variant?.artifact_id || "",
      decision: state.reviewDecision || "keep",
      note: state.reviewDecisionNote,
      generated_at: nowIso(),
    });
    await refreshWorkbench();
  }

  async function updateSceneInspector() {
    const card = selectedCard(state);
    if (!card) throw new Error("Select a scene or canvas card before saving inspector details.");
    state.lastResult = await client().updateSceneInspector(state.projectId, {
      card_id: card.id,
      prompt: state.inspectorPrompt,
      reference_summary: state.inspectorReferenceSummary,
      style_direction: state.inspectorStyleDirection,
      retry_intent: state.inspectorRetryIntent,
    });
    await refreshWorkbench();
  }

  async function runAssetTest() {
    state.lastResult = await client().runAssetTest({
      project_id: state.projectId,
      asset_profile_seed: state.assetProfileSeed,
      promotion_decision: state.promotionDecision || "promoted",
      promotion_rationale: state.promotionRationale || "Workbench deterministic flow.",
      generated_at: nowIso(),
      decided_at: nowIso(),
      reviewed_at: nowIso(),
    });
    await refreshWorkbench();
  }

  async function recordFeedback() {
    state.lastResult = await client().recordFeedback({
      project_id: state.projectId,
      feedback: {
        channel: "workbench",
        result: "partially_kept",
        note: state.feedbackNote,
        feedback_is_memory: false,
      },
      generated_at: nowIso(),
    });
    await refreshWorkbench();
  }

  async function runTwoRound() {
    const roundOneJobId = latestJobId(state, "asset_test_run") || state.latestAssetTestJobId;
    if (!roundOneJobId) throw new Error("Run the first check before preparing the next round.");
    state.lastResult = await client().runTwoRoundValidate({
      project_id: state.projectId,
      round_1_job_id: roundOneJobId,
      generated_at: nowIso(),
      reviewed_at: nowIso(),
    });
    await refreshWorkbench();
  }

  async function runProviderPreflight() {
    state.lastResult = await client().providerValidationPlan({
      project_id: state.projectId,
      asset_profile_seed: state.assetProfileSeed,
      generated_at: nowIso(),
    });
    await refreshWorkbench();
  }

  async function openSelectedArtifact() {
    const artifactId = state.selectedArtifactId || selectedCard(state)?.primary_artifact_id;
    if (!artifactId) throw new Error("No safe artifact ref is selected.");
    state.selectedArtifactId = artifactId;
    state.artifact = await client().artifact(artifactId);
  }

  return {
    "create-project": createProject,
    "import-project": importProject,
    "export-project": exportProject,
    "register-source-asset": registerSourceAsset,
    "register-content-card": registerContentCard,
    "draft-canvas": draftCanvas,
    "record-review-decision": recordReviewDecision,
    "update-scene-inspector": updateSceneInspector,
    "run-asset-test": runAssetTest,
    "record-feedback": recordFeedback,
    "run-two-round": runTwoRound,
    "run-provider-preflight": runProviderPreflight,
    "open-selected-artifact": openSelectedArtifact,
  };
}
