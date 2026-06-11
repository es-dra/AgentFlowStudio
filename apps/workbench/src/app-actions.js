import { latestJobId, selectedCard, selectedVariant } from "./app-selection.js";
import {
  buildFallbackPromptOptimization,
  buildRuntimePromptOptimizationRequest,
  normalizeRuntimePromptOptimization,
} from "./prompt-optimizer-runtime.js";

function nowIso() {
  return new Date().toISOString();
}

export function createActionHandlers({ state, client, refreshWorkbench }) {
  async function createProject() {
    state.lastResult = await client().createProject({
      project_id: state.projectId,
      project_type: state.projectType || "short_video_campaign",
      goal: state.projectGoal || "上传剧本，生成分镜、关键帧和视频片段。",
      status: "in_progress",
    });
    state.projectId = state.lastResult.project_id || state.projectId;
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
    state.lastResult = await client().draftCanvas(state.projectId, { generated_at: nowIso() });
    await refreshWorkbench();
  }

  async function recordReviewDecision() {
    const card = selectedCard(state);
    const variant = selectedVariant(state);
    if (!card) throw new Error("请先选择一个镜头或画布节点。");
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
    state.lastResult = await client().updateSceneInspector(state.projectId, {
      card_id: selectedCard(state)?.id || state.selectedCardId || "script-input",
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
    if (!roundOneJobId) throw new Error("请先完成第一轮检查。");
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

  async function optimizeCurrentPrompt() {
    const request = buildRuntimePromptOptimizationRequest(state, selectedCard(state));
    try {
      const result = await client().optimizePrompt(state.projectId, request);
      state.promptOptimizationResult = normalizeRuntimePromptOptimization(result, request);
      const briefRef = result?.artifacts?.creative_brief?.artifact_id;
      state.selectedArtifactId = briefRef || state.selectedArtifactId;
    } catch (error) {
      state.promptOptimizationResult = buildFallbackPromptOptimization(request, error);
    }
    state.promptOptimizationOpen = true;
    state.lastResult = state.promptOptimizationResult;
  }

  function currentPromptOptimizationResult() {
    return state.promptOptimizationResult || buildFallbackPromptOptimization(
      buildRuntimePromptOptimizationRequest(state, selectedCard(state)),
      new Error("Runtime prompt optimization has not run yet."),
    );
  }

  async function replaceCurrentPrompt() {
    const result = currentPromptOptimizationResult();
    setActivePrompt(result.optimized_prompt);
    state.promptOptimizationResult = result;
    state.promptOptimizationOpen = true;
    state.lastResult = { applied: "replace", artifact_type: "prompt_optimization_result" };
  }

  async function appendCurrentPrompt() {
    const result = currentPromptOptimizationResult();
    setActivePrompt([activePrompt(), result.optimized_prompt].filter(Boolean).join("\n\n"));
    state.promptOptimizationResult = result;
    state.promptOptimizationOpen = true;
    state.lastResult = { applied: "append", artifact_type: "prompt_optimization_result" };
  }

  async function copyOptimizedPrompt() {
    const result = currentPromptOptimizationResult();
    await navigator.clipboard?.writeText?.(result.optimized_prompt);
    state.promptOptimizationResult = result;
    state.promptOptimizationOpen = true;
    state.lastResult = { applied: "copy", artifact_type: "prompt_optimization_result" };
  }

  async function applyOptimizedToNode() {
    const result = currentPromptOptimizationResult();
    setActivePrompt(result.optimized_prompt);
    state.inspectorReferenceSummary = "已结合当前项目风格；已参考角色/场景设定。";
    state.promptOptimizationResult = result;
    state.promptOptimizationOpen = true;
    state.lastResult = { applied: "node", artifact_type: "prompt_optimization_result" };
  }

  async function runNodeGenerationPreview(dataset = {}) {
    const surface = dataset.nodeGenerateSurface || "node";
    const prompt = activePrompt().trim();
    await new Promise((resolve) => setTimeout(resolve, 180));
    const status = prompt ? "complete" : "error";
    state.nodeGenerationStatus = {
      ...state.nodeGenerationStatus,
      [surface]: {
        status,
        message: prompt ? "本地预览完成，未启动模型生成" : "请先输入提示词",
        updatedAt: nowIso(),
      },
    };
    state.pendingNodeGenerationSurface = "";
    state.lastResult = {
      status: prompt ? "node_preview_ready" : "node_prompt_required",
      surface,
      artifact_type: "safe_node_generation_preview",
    };
  }

  async function runScriptDraftPlan() {
    const goal = [
      state.scriptDraftGoal,
      state.scriptDraftDurationSeconds ? `目标时长 ${state.scriptDraftDurationSeconds} 秒` : "",
      state.scriptDraftFeedbackNote ? `本轮反馈：${state.scriptDraftFeedbackNote}` : "",
    ].filter(Boolean).join("\n");
    state.lastResult = await client().providerScriptDraftPlan({
      project_id: state.projectId,
      goal,
      target_platform: "short_video",
      style: state.scriptDraftTone || "cinematic_storyboard",
      review_feedback_artifact_id: state.scriptDraftReviewFeedbackArtifactId || null,
      previous_script_artifact_id: state.scriptDraftPreviousArtifactId || null,
      generated_at: nowIso(),
    });
    const scriptRef = state.lastResult?.artifacts?.script_storyboard_safe_artifact;
    state.selectedArtifactId = scriptRef?.artifact_id || state.selectedArtifactId;
    state.scriptDraftPreviousArtifactId = state.selectedArtifactId;
    state.artifact = state.selectedArtifactId ? await client().artifact(state.selectedArtifactId) : state.artifact;
    await refreshWorkbench();
  }

  async function openSelectedArtifact() {
    const artifactId = state.selectedArtifactId || selectedCard(state)?.primary_artifact_id;
    if (!artifactId) throw new Error("没有选中的结果。");
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
    "optimize-current-prompt": optimizeCurrentPrompt,
    "replace-current-prompt": replaceCurrentPrompt,
    "append-current-prompt": appendCurrentPrompt,
    "copy-optimized-prompt": copyOptimizedPrompt,
    "apply-optimized-to-node": applyOptimizedToNode,
    "run-node-generation-preview": runNodeGenerationPreview,
    "run-two-round": runTwoRound,
    "run-provider-preflight": runProviderPreflight,
    "run-script-draft-plan": runScriptDraftPlan,
    "open-selected-artifact": openSelectedArtifact,
  };

  function activePrompt() {
    if (state.studioStarterKind === "script") return state.scriptDraftGoal;
    return state.inspectorPrompt;
  }

  function setActivePrompt(value) {
    if (state.studioStarterKind === "script") {
      state.scriptDraftGoal = value;
      return;
    }
    state.inspectorPrompt = value;
  }
}
