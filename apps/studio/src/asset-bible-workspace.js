import { legacyAppliedStoryboardProjection } from "./shot-truth-projection.js";

export function assetBibleProjection(studioState = {}, runtimeAssetBible = null) {
  const canonical = runtimeAssetBible?.authority_mode === "canonical_production_graph"
    ? runtimeAssetBible.asset_bible
    : null;
  const legacy = studioState?.assetBible;
  const bible = validBible(canonical) ? canonical : validBible(legacy) ? legacy : {};
  const authorityMode = validBible(canonical)
    ? "canonical_production_graph"
    : validBible(legacy)
      ? "legacy_studio_adapter"
      : runtimeAssetBible?.authority_mode || "legacy_studio_adapter";
  const assets = array(bible.assets).map(normalizeAsset).filter(Boolean);
  const activeAssets = assets.filter((asset) => !["rejected", "superseded"].includes(asset.review_state));
  const historyAssets = assets.filter((asset) => ["rejected", "superseded"].includes(asset.review_state));
  const coverage = normalizeCoverage(bible.coverage, bible.candidate_set);
  const recognitionQuality = normalizeRecognitionQuality(bible.recognition_quality, coverage);
  const counts = {
    total: activeAssets.length,
    approved: activeAssets.filter((asset) => asset.review_state === "approved").length,
    candidate: activeAssets.filter((asset) => asset.review_state === "candidate").length,
    rejected: assets.filter((asset) => asset.review_state === "rejected").length,
    superseded: assets.filter((asset) => asset.review_state === "superseded").length,
    character: activeAssets.filter((asset) => asset.asset_type === "character").length,
    scene: activeAssets.filter((asset) => asset.asset_type === "scene").length,
    prop: activeAssets.filter((asset) => asset.asset_type === "prop").length,
  };
  return {
    status: bible.status || "empty",
    authority_mode: authorityMode,
    version: Number(bible.version || 0),
    current_revision_id: String(bible.current_revision_id || ""),
    locked_revision_id: String(bible.locked_revision_id || ""),
    candidate_set: bible.candidate_set || {},
    art_direction: normalizeArtDirection(bible.art_direction),
    assets,
    active_assets: activeAssets,
    history_assets: historyAssets,
    counts,
    coverage,
    recognition_quality: recognitionQuality,
    resolution_ledger: array(bible.resolution_ledger),
    last_receipt: bible.last_receipt || {},
    raw: bible,
    provider_dispatch_count: 0,
    external_cost_usd: 0,
  };
}

export function assetBibleSourceContext(studioState = {}, sequenceWorkspace = null) {
  const graphSource = productionGraphAssetBibleSourceContext(sequenceWorkspace);
  if (sequenceWorkspace?.status === "ready") return graphSource;
  if (graphSource) return graphSource;
  const projection = legacyAppliedStoryboardProjection(studioState);
  if (projection.status !== "ready") return null;
  const sourceNode = studioState.nodes?.[projection.source_node_id];
  if (!sourceNode) return null;
  const action = sourceNode.params?.embeddedCreativeAction || {};
  const revisions = array(sourceNode.params?.revisions);
  const currentRevisionId = String(sourceNode.params?.currentRevisionId || projection.source_revision_id || "");
  const currentRevision = revisions.find((item) => item?.revision_id === currentRevisionId)
    || revisions.slice().reverse().find((item) => item?.screenplay_candidate);
  const sourceText = String(
    currentRevision?.screenplay_candidate?.screenplay_text
    || currentRevision?.screenplay_candidate?.content
    || currentRevision?.after_text
    || sourceNode.content
    || sourceNode.prompt
    || "",
  ).trim();
  const shotPlan = sourceNode.params?.shotPlanDraft
    || action.applied_subgraph?.shot_plan
    || action.preview?.shot_plan
    || null;
  if (!sourceText || !shotPlan?.scenes?.length) return null;
  const sourceContextTexts = [
    currentRevision?.source_text,
    currentRevision?.before_text,
    currentRevision?.screenplay_candidate?.source_text,
    sourceNode.content,
    sourceNode.prompt,
  ]
    .map((value) => String(value || "").trim())
    .filter((value, index, values) => value && value !== sourceText && values.indexOf(value) === index)
    .slice(0, 8);
  return {
    source_node_id: sourceNode.id,
    script_revision_id: currentRevisionId || projection.source_revision_id,
    shot_candidate_id: projection.candidate_id,
    source_text: sourceText,
    source_context_texts: sourceContextTexts,
    shot_plan: shotPlan,
    scene_count: projection.scene_count,
    shot_count: projection.shot_count,
    duration_sec: projection.duration_sec,
  };
}

export function productionGraphAssetBibleSourceContext(workspace = null) {
  if (!workspace || workspace.status !== "ready") return null;
  const graphVersion = Number(workspace.graph_version || 0);
  const graphDigest = String(workspace.graph_digest || "");
  if (
    !graphVersion
    || !graphDigest
    || Number(workspace.storyboard?.graph_version || 0) !== graphVersion
    || String(workspace.storyboard?.graph_digest || "") !== graphDigest
  ) return null;

  const sequence = workspace.sequence || {};
  const active = (value) => array(value).filter((item) => item?.state !== "invalidated");
  const revisions = active(sequence.script_revisions);
  if (revisions.length !== 1) return null;
  const relations = array(sequence.dependencies);
  const revisionId = String(revisions[0].node_id || "");
  const sourceNodeIds = new Set(
    relations
      .filter((relation) => relation.relation_type === "derived_from"
        && String(relation.from_id || "") === revisionId)
      .map((relation) => String(relation.to_id || "")),
  );
  const scenes = active(sequence.scenes).filter(
    (item) => sourceNodeIds.has(String(item.node_id || "")),
  );
  const sceneIds = new Set(scenes.map((item) => String(item.node_id || "")));
  const shots = active(sequence.shots).filter((shot) => relations.some(
    (relation) => relation.relation_type === "contains"
      && sceneIds.has(String(relation.from_id || ""))
      && String(relation.to_id || "") === String(shot.node_id || ""),
  ));
  if (!scenes.length || !shots.length) return null;
  const shotsByScene = new Map(
    scenes.map((scene) => [
      String(scene.node_id || ""),
      shots.filter((shot) => relations.some(
        (relation) => relation.relation_type === "contains"
          && String(relation.from_id || "") === String(scene.node_id || "")
          && String(relation.to_id || "") === String(shot.node_id || ""),
      )),
    ]),
  );
  if ([...shotsByScene.values()].flat().length !== shots.length) return null;

  const shotPlan = {
    candidate_id: graphDigest,
    source_graph_version: graphVersion,
    source_graph_digest: graphDigest,
    scenes: scenes.map((scene, sceneIndex) => ({
      scene_id: String(scene.node_id || ""),
      name: String(scene.metadata?.name || ""),
      number: sceneIndex + 1,
      description: String(scene.metadata?.space || scene.metadata?.action || ""),
      shots: (shotsByScene.get(String(scene.node_id || "")) || []).map((shot, shotIndex) => ({
        shot_id: String(shot.node_id || ""),
        number: shotIndex + 1,
        title: String(shot.metadata?.title || shot.metadata?.intent || `镜头 ${shotIndex + 1}`),
        description: String(shot.metadata?.blocking || shot.metadata?.intent || ""),
        duration_sec: Number(shot.metadata?.duration_seconds || 0),
        narrative_purpose: String(shot.metadata?.narrative_purpose || ""),
        shot_size: String(shot.metadata?.shot_size || ""),
        camera_angle: String(shot.metadata?.camera_angle || ""),
        camera_movement: String(shot.metadata?.camera_movement || ""),
        blocking: String(shot.metadata?.blocking || ""),
        sound: String(shot.metadata?.sound || ""),
        transition: String(shot.metadata?.transition || ""),
      })),
    })),
    total_shots: shots.length,
  };
  const canonicalAssets = [
    ...active(sequence.characters)
      .filter((item) => sourceNodeIds.has(String(item.node_id || "")))
      .map((item) => sourceAsset(item, "character")),
    ...scenes.map((item) => sourceAsset(item, "scene")),
    ...active(sequence.props)
      .filter((item) => sourceNodeIds.has(String(item.node_id || "")))
      .map((item) => sourceAsset(item, "prop")),
  ].filter((item) => item.display_name);
  return {
    authority_mode: "canonical_production_graph",
    source_node_id: revisionId,
    script_revision_id: revisionId,
    shot_candidate_id: graphDigest,
    shot_plan: shotPlan,
    scene_count: scenes.length,
    shot_count: shots.length,
    duration_sec: shots.reduce(
      (total, shot) => total + Number(shot.metadata?.duration_seconds || 0),
      0,
    ),
    canonical_assets: canonicalAssets,
    production_aids: active(sequence.production_aids)
      .filter((item) => sourceNodeIds.has(String(item.node_id || "")))
      .map((item) => ({
        source_node_id: String(item.node_id || ""),
        display_name: String(item.metadata?.name || item.metadata?.display_name || ""),
        classification: "production_aid",
      })),
    graph_version: graphVersion,
    graph_digest: graphDigest,
    provider_dispatch_count: 0,
    external_cost_usd: 0,
  };
}

function sourceAsset(item, assetType) {
  return {
    source_node_id: String(item?.node_id || ""),
    asset_type: assetType,
    display_name: String(item?.metadata?.display_name || item?.metadata?.name || ""),
  };
}

export function deriveProductionCopilotState({
  studioState = {},
  runtimeAssetBible = null,
  capabilityGates = {},
  section = "canvas",
  selectedAsset = null,
  imageAdmission = null,
  mediaOperations = null,
  productionGraph = null,
  planningRun = null,
} = {}) {
  const shotTruth = legacyAppliedStoryboardProjection(studioState);
  const bible = assetBibleProjection(studioState, runtimeAssetBible);
  const mediaReviewReady = mediaOperations?.schema_version === "afs.media_operations_review.v0.1"
    && array(mediaOperations.shots).length > 0;
  if (mediaReviewReady) {
    const shotCount = Number(mediaOperations.summary?.shot_count || mediaOperations.shots.length);
    const readyShotCount = Number(mediaOperations.summary?.ready_shot_count || 0);
    const nextReason = String(
      mediaOperations.stage?.next_action
      || "从故事板选择镜头，审看画面、动作和连续性。",
    );
    return {
      stage: "media_review",
      dependencies: [
        { key: "script", label: "当前剧本", state: "ready" },
        { key: "shots", label: "已应用分镜", state: "ready" },
        { key: "media", label: "可审看片段", state: readyShotCount === shotCount ? "ready" : "pending" },
      ],
      blockers: [],
      gate: {
        llm: capabilityGates.llm === true,
        image: capabilityGates.image === true,
        video: capabilityGates.video === true,
        admission: "ready",
        cost_state: "available_in_details",
      },
      next_valid_action: {
        action: "review_current_shot",
        label: section === "storyboard" ? "播放当前镜头" : "审看片段",
        reason: nextReason,
        enabled: readyShotCount > 0,
      },
      ready_summary: `${readyShotCount}/${shotCount} 个镜头可以审看。`,
      needs_input: nextReason,
      asset_bible: bible,
      provider_dispatch_count: Number(mediaOperations.advanced_evidence?.provider_dispatch_count || 0),
      external_cost_usd: mediaOperations.cost?.conservative_estimated_usd ?? null,
    };
  }
  const graphReady = productionGraph?.status === "ready" && array(productionGraph.shots).length > 0;
  if (graphReady && bible.counts.total === 0) {
    const summary = productionGraph.summary || {};
    const shotCount = array(productionGraph.shots).length;
    if (Number(summary.scriptRevisions || 0) !== 1) {
      return {
        stage: "production_plan_revision_conflict",
        dependencies: [
          { key: "script", label: "当前剧本", state: "pending" },
          { key: "shots", label: "已应用分镜", state: "ready" },
          { key: "assets", label: "角色、场景与道具", state: "pending" },
        ],
        blockers: ["制作方案版本需要确认"],
        gate: {
          llm: capabilityGates.llm === true,
          image: capabilityGates.image === true,
          video: capabilityGates.video === true,
          admission: "blocked",
          cost_state: "not_admitted",
        },
        next_valid_action: {
          action: "resolve_script_revision",
          label: "等待版本确认",
          reason: "当前存在多个已应用剧本版本，确认唯一版本后才能整理资产。",
          enabled: false,
        },
        ready_summary: "制作方案版本需要确认，现有项目内容未改变。",
        needs_input: "确认唯一的已应用剧本版本。",
        asset_bible: bible,
        provider_dispatch_count: 0,
        external_cost_usd: null,
      };
    }
    const assetCount = Number(summary.characters || 0)
      + Number(summary.locations || 0)
      + Number(summary.props || 0)
      + Number(summary.referenceSets || 0)
      + Number(summary.productionAids || 0);
    const assetBibleOpen = section === "asset_bible";
    const nextReason = assetBibleOpen
      ? "基于已保存的角色、场景、道具和镜头建立可审核资产候选。"
      : "先审看镜头顺序、时长和画面意图，再继续资产与图片制作。";
    return {
      stage: "production_plan_ready",
      dependencies: [
        { key: "script", label: "当前剧本", state: "ready" },
        { key: "shots", label: "已应用分镜", state: "ready" },
        { key: "assets", label: "角色、场景与道具", state: assetCount > 0 ? "ready" : "pending" },
      ],
      blockers: [],
      gate: {
        llm: capabilityGates.llm === true,
        image: capabilityGates.image === true,
        video: capabilityGates.video === true,
        admission: "structure_ready_media_disabled",
        cost_state: "not_admitted",
      },
      next_valid_action: {
        action: assetBibleOpen ? "generate_asset_candidates" : "open_storyboard",
        label: assetBibleOpen
          ? "识别资产候选"
          : section === "storyboard"
            ? "审看当前镜头"
            : "查看故事板",
        reason: nextReason,
        enabled: true,
      },
      ready_summary: `制作方案已保存：${Number(summary.characters || 0)} 个角色、${Number(summary.locations || 0)} 个场景、${shotCount} 个镜头。`,
      needs_input: nextReason,
      asset_bible: bible,
      provider_dispatch_count: 0,
      external_cost_usd: null,
    };
  }
  const scriptReady = Boolean(
    assetBibleSourceContext(studioState)?.script_revision_id
    || bible.candidate_set?.script_revision_id,
  );
  const planningPhase = String(planningRun?.phase || "");
  if (!scriptReady && ["queued", "running", "running_cancel_requested"].includes(planningPhase)) {
    const stopping = planningPhase === "running_cancel_requested";
    return {
      stage: "plan_in_progress",
      dependencies: [
        { key: "script", label: "制作方案", state: "pending" },
        { key: "project", label: "现有项目内容", state: "ready" },
      ],
      blockers: [],
      gate: {
        llm: capabilityGates.llm === true,
        image: capabilityGates.image === true,
        video: capabilityGates.video === true,
        admission: "planning_in_progress",
        cost_state: "not_admitted",
      },
      next_valid_action: {
        action: "view_plan_progress",
        label: "查看制作进度",
        reason: stopping
          ? "停止请求已记录；查看同一任务的最新状态。"
          : "制作方案正在准备；可以查看同一任务的进度。",
        enabled: true,
      },
      ready_summary: stopping ? "正在停止制作方案任务。" : "制作方案正在准备。",
      needs_input: stopping ? "等待当前任务返回最终状态。" : "当前无需重复提交创作想法。",
      asset_bible: bible,
      provider_dispatch_count: Number(planningRun?.dispatch_count || 0),
      external_cost_usd: planningRun?.cost?.actual_usd ?? null,
    };
  }
  if (!scriptReady && ["failed", "unknown"].includes(planningPhase)) {
    return {
      stage: "plan_recovery_required",
      dependencies: [
        { key: "script", label: "制作方案", state: "pending" },
        { key: "project", label: "现有项目内容", state: "ready" },
      ],
      blockers: ["制作方案需要检查；现有项目内容未改变"],
      gate: {
        llm: capabilityGates.llm === true,
        image: capabilityGates.image === true,
        video: capabilityGates.video === true,
        admission: "blocked",
        cost_state: "not_admitted",
      },
      next_valid_action: {
        action: "recover_plan_preview",
        label: "恢复制作方案",
        reason: "查看同一任务的失败状态和原始输入，不会再次提交文本任务。",
        enabled: Boolean(planningRun?.run_id),
      },
      ready_summary: "制作方案未通过检查，现有项目内容未改变。",
      needs_input: "检查失败原因并恢复同一预览。",
      asset_bible: bible,
      provider_dispatch_count: Number(planningRun?.dispatch_count || 0),
      external_cost_usd: planningRun?.cost?.actual_usd ?? null,
    };
  }
  const shotReady = shotTruth.status === "ready" || Number(bible.candidate_set?.shot_count || 0) > 0;
  const candidatesReady = bible.counts.total > 0;
  const visualBlockers = bible.active_assets
    .filter((asset) => ["candidate", "approved"].includes(asset.review_state))
    .flatMap((asset) => assetVisualBlockers(asset).map((label) => `${asset.display_name}：${label}`));
  const artDirectionReady = bible.art_direction.status === "confirmed";
  const bibleLocked = bible.status === "locked" && Boolean(bible.locked_revision_id);
  const contentReady = bibleLocked && bible.coverage.coverage_pass && artDirectionReady && visualBlockers.length === 0;
  const imageEnabled = capabilityGates.image === true;
  const admissionStatus = String(imageAdmission?.status || "empty");
  const admissionCounts = imageAdmission?.counts || {};
  const mediaLoadFailures = Number(admissionCounts.media_load_failed || 0);
  const qualityIssues = bible.recognition_quality.issues;
  let next = {
    action: "start_idea",
    label: "输入创作想法",
    reason: "先描述故事、角色或一个画面，AI 创作搭档会和画布一起继续。",
    enabled: true,
  };
  if (scriptReady && !shotReady) {
    next = { action: "open_storyboard", label: "拆分分镜", reason: "剧本已就绪，下一步是建立镜头计划。", enabled: true };
  } else if (shotReady && !candidatesReady) {
    next = { action: "generate_asset_candidates", label: "识别资产候选", reason: "分镜已应用，可执行本地确定性资产识别，不调用外部能力。", enabled: true };
  } else if (candidatesReady && qualityIssues.length > 0) {
    next = {
      action: "regenerate_asset_candidates",
      label: "重新识别资产",
      reason: `识别质量门有 ${qualityIssues.length} 项阻塞；先修复具名资产、别名或场景镜头覆盖。`,
      enabled: !bibleLocked,
    };
  } else if (candidatesReady && visualBlockers.length > 0) {
    next = {
      action: "complete_asset_visual_identity",
      label: "补全视觉身份",
      reason: `${visualBlockers.length} 项视觉依据未完成；候选不能批准，先编辑正向特征、视觉身份和连续性状态。`,
      enabled: true,
    };
  } else if (candidatesReady && bible.counts.candidate > 0) {
    next = {
      action: selectedAsset?.review_state === "candidate" ? "approve_selected_asset" : "review_asset_candidates",
      label: selectedAsset?.review_state === "candidate" ? "批准当前资产" : "继续审核资产",
      reason: `仍有 ${bible.counts.candidate} 个候选待确认。`,
      enabled: true,
    };
  } else if (candidatesReady && bible.coverage.unresolved_required > 0) {
    next = {
      action: "resolve_required_occurrences",
      label: "解决资产引用",
      reason: `${bible.coverage.unresolved_required} 个必要出现范围尚未解决，涉及 ${bible.coverage.unresolved_shot_count} 个镜头。`,
      enabled: true,
    };
  } else if (candidatesReady && !bible.coverage.coverage_pass) {
    next = {
      action: "review_asset_coverage",
      label: "检查镜头覆盖",
      reason: `${bible.coverage.shot_covered}/${bible.coverage.shot_total} 镜头已完成资产需求检查。`,
      enabled: true,
    };
  } else if (candidatesReady && !artDirectionReady) {
    next = {
      action: "set_art_direction",
      label: "确认统一美术方向",
      reason: "图片准入需要先审核视觉风格、媒介质感、色彩方案和光线规则。",
      enabled: true,
    };
  } else if (candidatesReady && !bibleLocked) {
    next = { action: "lock_asset_bible", label: "锁定 Asset Bible", reason: "资产审核与镜头覆盖已完成，可以锁定当前版本。", enabled: true };
  } else if (contentReady && admissionStatus === "empty") {
    next = {
      action: "image_admission_ready",
      label: "准备首张图片",
      reason: "锁定资产与镜头覆盖已就绪；先审核首张图片清单和单次费用硬门，不会调用外部能力。",
      enabled: true,
    };
  } else if (contentReady && mediaLoadFailures > 0) {
    next = {
      action: "reload_image_candidate",
      label: "重新加载候选图片",
      reason: `${mediaLoadFailures} 个候选图片未能加载；批准已禁用，请先恢复可见预览。`,
      enabled: true,
    };
  } else if (contentReady && Number(admissionCounts.failed || 0) > 0) {
    next = {
      action: "recover_image_admission",
      label: "恢复失败项目",
      reason: `${Number(admissionCounts.failed)} 个图片项目失败且已隔离；先审阅失败原因和替换影响。`,
      enabled: true,
    };
  } else if (contentReady && Number(admissionCounts.candidate || 0) > 0) {
    next = {
      action: "review_image_candidates",
      label: "审核图片候选",
      reason: `${Number(admissionCounts.candidate)} 个图片候选待人工查看；批准前不会写入制作图。`,
      enabled: true,
    };
  } else if (contentReady && Number(admissionCounts.processing || 0) > 0) {
    next = {
      action: "resume_image_admission",
      label: "恢复图片任务",
      reason: `${Number(admissionCounts.processing)} 个任务可继续检查；刷新不会重复发送。`,
      enabled: true,
    };
  } else if (contentReady && admissionStatus === "draft") {
    next = {
      action: "review_image_admission",
      label: "锁定图片清单",
      reason: "首张图片清单已编译，锁定后才可占用一次预算并生成。",
      enabled: true,
    };
  } else if (contentReady && admissionStatus === "cancelled") {
    next = {
      action: "review_image_admission",
      label: "审阅已停止批次",
      reason: "未发送项目已停止；已完成和已拒绝记录仍保留。",
      enabled: true,
    };
  } else if (contentReady && !imageEnabled) {
    next = {
      action: "media_gate_closed",
      label: "图片能力未启用",
      reason: Number(admissionCounts.approved || 0) > 0
        ? "已批准图片已写回 Asset Bible / ProductionGraph；当前环境未开放图片媒体能力。"
        : "结构已就绪，但当前环境未开放图片媒体能力。",
      enabled: false,
    };
  } else if (
    contentReady
    && admissionStatus === "locked"
    && Number(admissionCounts.approved || 0) + Number(admissionCounts.rejected || 0) > 0
    && Number(admissionCounts.planned || 0) === 0
    && Number(admissionCounts.reserved || 0) === 0
    && Number(admissionCounts.processing || 0) === 0
    && Number(admissionCounts.candidate || 0) === 0
  ) {
    next = {
      action: "image_admission_ready",
      label: "准备下一批图片",
      reason: "当前批次已完成；可以从同一项目事实中选择尚未发送的场景、道具或镜头图片。",
      enabled: true,
    };
  } else if (contentReady) {
    next = { action: "image_admission_ready", label: "进入图片准入", reason: "结构与锁定版本已满足图片生产前置条件。", enabled: true };
  }
  return {
    stage: !scriptReady ? "script_required"
      : !shotReady ? "shot_plan_required"
        : !candidatesReady ? "asset_recognition_ready"
          : !contentReady ? "asset_review"
            : admissionStatus === "empty" ? "image_admission_ready"
              : mediaLoadFailures ? "image_candidate_media_recovery"
                : Number(admissionCounts.failed || 0) ? "image_admission_recovery"
                : Number(admissionCounts.candidate || 0) ? "image_candidate_review"
                  : Number(admissionCounts.processing || 0) ? "image_admission_processing"
                    : imageEnabled ? "image_admission_ready" : "media_gate_closed",
    dependencies: [
      { key: "script", label: "当前剧本", state: scriptReady ? "ready" : "blocked" },
      { key: "shots", label: "已应用分镜", state: shotReady ? "ready" : "blocked" },
      { key: "assets", label: "资产候选", state: candidatesReady ? "ready" : "blocked" },
      { key: "quality", label: "识别质量", state: bible.recognition_quality.status === "pass" ? "ready" : "blocked" },
      { key: "coverage", label: "镜头覆盖", state: bible.coverage.coverage_pass ? "ready" : "blocked" },
      { key: "visual_identity", label: "视觉身份", state: visualBlockers.length ? "blocked" : "ready" },
      { key: "art_direction", label: "美术方向", state: artDirectionReady ? "ready" : "blocked" },
      { key: "bible", label: "Bible 锁定", state: bibleLocked ? "ready" : "blocked" },
    ],
    blockers: [
      ...(!scriptReady ? ["缺少当前剧本版本"] : []),
      ...(scriptReady && !shotReady ? ["分镜尚未应用"] : []),
      ...qualityIssues.slice(0, 3).map((item) => item.message),
      ...(candidatesReady && bible.counts.candidate ? [`${bible.counts.candidate} 个资产待确认`] : []),
      ...visualBlockers.slice(0, 3),
      ...(candidatesReady && !artDirectionReady ? ["统一美术方向尚未审核确认"] : []),
      ...(candidatesReady && bible.coverage.unresolved_required ? [
        `${bible.coverage.unresolved_required} 个必要出现范围未解决（${bible.coverage.unresolved_shot_count} 镜头）`,
      ] : []),
      ...(bible.coverage.alias_collision_count ? [`${bible.coverage.alias_collision_count} 组别名冲突`] : []),
      ...(mediaLoadFailures ? [`${mediaLoadFailures} 个候选图片加载失败，批准已禁用`] : []),
      ...(Number(admissionCounts.failed || 0) ? [`${Number(admissionCounts.failed)} 个图片项目失败且已隔离`] : []),
      ...(contentReady && !imageEnabled ? ["内容结构已就绪；图片能力未启用"] : []),
    ],
    gate: {
      llm: capabilityGates.llm === true,
      image: imageEnabled,
      video: capabilityGates.video === true,
      admission: contentReady ? (imageEnabled ? "ready" : "structure_ready_media_disabled") : "blocked",
      cost_state: Number(imageAdmission?.budget?.dispatches_reserved || 0) > 0 ? "estimated_reserved" : "not_admitted",
    },
    next_valid_action: next,
    ready_summary: creatorReadySummary({
      scriptReady,
      shotReady,
      candidatesReady,
      bible,
      contentReady,
      admissionStatus,
      admissionCounts,
    }),
    needs_input: next.reason,
    asset_bible: bible,
    provider_dispatch_count: Number(imageAdmission?.provider_dispatch_count || 0),
    external_cost_usd: imageAdmission?.actual_usd ?? null,
  };
}

function creatorReadySummary({
  scriptReady,
  shotReady,
  candidatesReady,
  bible,
  contentReady,
  admissionStatus,
  admissionCounts,
}) {
  if (!scriptReady) return "项目已创建，可以从一个想法开始。";
  if (!shotReady) return "剧本已选定，可以继续安排镜头。";
  if (!candidatesReady) return "剧本和镜头已准备，可以整理角色、场景和道具。";
  if (!contentReady) {
    const confirmed = Number(bible.counts.approved || 0);
    const total = Number(bible.counts.total || 0);
    return `已整理 ${total} 项创作资产${confirmed ? `，其中 ${confirmed} 项已确认` : ""}。`;
  }
  if (Number(admissionCounts.candidate || 0) > 0) {
    return `${Number(admissionCounts.candidate)} 张候选图片可以审看。`;
  }
  if (Number(admissionCounts.approved || 0) > 0) {
    return `${Number(admissionCounts.approved)} 张图片已确认并保存到当前项目。`;
  }
  if (admissionStatus !== "empty") return "角色、场景、道具和图片清单已准备。";
  return "角色、场景、道具和美术方向已准备。";
}

export function assetTypeLabel(value) {
  return {
    character: "角色",
    scene: "场景",
    prop: "道具",
    wardrobe: "服化",
    continuity_object: "连续性物件",
  }[String(value || "")] || "资产";
}

export function assetReviewLabel(value) {
  return {
    candidate: "待确认",
    approved: "已批准",
    rejected: "已拒绝",
    superseded: "已取代",
  }[String(value || "")] || "待确认";
}

export function localizedNegativeLock(value) {
  return {
    "no text, captions, watermarks, interface elements, or borders": "禁止添加文字、水印、界面元素或边框",
    "do not add text/watermark/ui/borders": "禁止添加文字、水印、界面元素或边框",
    "do not change character identity": "禁止改变角色身份",
    "do not change identity": "禁止改变角色身份",
    "do not add unrequested characters": "禁止添加未要求的角色",
    "do not add chairs or stools unless approved": "未经确认，禁止添加椅子或凳子",
    "do not add eaves unless approved": "未经确认，禁止添加屋檐元素",
    "do not add unrequested set pieces": "禁止添加未要求的场景陈设",
    "do not change prop function": "禁止改变道具功能",
    "do not duplicate the prop unless scripted": "剧本未要求时，禁止复制该道具",
    "do not move to a different location": "禁止移动到其他场景",
  }[String(value || "").trim().toLowerCase()] || String(value || "");
}

export function pendingFieldLabel(value) {
  return {
    positive_traits: "正向视觉特征",
    visual_identity: "视觉身份",
    continuity_state: "连续性状态",
  }[String(value || "")] || "待人工确认属性";
}

export function assetVisualBlockers(asset = {}) {
  const pending = new Set(array(asset.pending_fields));
  const blockers = [];
  if (pending.has("visual_identity") || !String(asset.visual_identity || "").trim()) blockers.push("视觉身份");
  if (pending.has("positive_traits") || !array(asset.positive_traits).length) blockers.push("正向视觉特征");
  const continuityReady = array(asset.continuity_states).some(
    (item) => item?.status === "confirmed" && String(item?.label || "").trim(),
  );
  if (pending.has("continuity_state") || !continuityReady) blockers.push("连续性状态");
  return blockers;
}

export function assetOccurrenceLabel(candidateSet = {}, kind, id) {
  if (kind === "scene") {
    const item = array(candidateSet.scene_index).find((entry) => entry?.scene_id === id);
    return item ? `场景 ${item.number} · ${item.name}` : "未命名场景";
  }
  const item = array(candidateSet.shot_index).find((entry) => entry?.shot_id === id);
  return item ? `镜头 ${String(item.number).padStart(2, "0")} · ${item.title}` : "未命名镜头";
}

function normalizeAsset(value) {
  if (!value?.stable_id || !value?.asset_type) return null;
  return {
    ...value,
    stable_id: String(value.stable_id),
    asset_type: String(value.asset_type),
    display_name: String(value.display_name || "待确认资产"),
    aliases: array(value.aliases),
    review_state: String(value.review_state || "candidate"),
    occurrences: {
      scene_ids: array(value.occurrences?.scene_ids),
      shot_ids: array(value.occurrences?.shot_ids),
    },
    positive_traits: array(value.positive_traits),
    visual_identity: String(value.visual_identity || ""),
    continuity_states: array(value.continuity_states),
    negative_locks: array(value.negative_locks),
    pending_fields: array(value.pending_fields),
    source_evidence: array(value.source_evidence),
    superseded_by_ids: array(value.superseded_by_ids),
  };
}

function normalizeArtDirection(value = {}) {
  const result = {
    visual_style: String(value?.visual_style || ""),
    medium: String(value?.medium || ""),
    palette: String(value?.palette || ""),
    lighting: String(value?.lighting || ""),
    confirmed_at: String(value?.confirmed_at || ""),
  };
  return {
    ...result,
    status: Object.values(result).every(Boolean) ? "confirmed" : "pending",
  };
}

function normalizeCoverage(value = {}, candidateSet = {}) {
  const shotTotal = Number(value.shot_total ?? candidateSet?.shot_count ?? 0);
  const sceneTotal = Number(value.scene_total ?? candidateSet?.scene_count ?? 0);
  return {
    scene_total: sceneTotal,
    scene_covered: Number(value.scene_covered || 0),
    shot_total: shotTotal,
    shot_covered: Number(value.shot_covered || 0),
    required_occurrence_total: Number(value.required_occurrence_total || 0),
    resolved_required: Number(value.resolved_required || 0),
    unresolved_required: Number(value.unresolved_required || 0),
    unresolved_scene_count: Number(value.unresolved_scene_count || 0),
    unresolved_shot_count: Number(value.unresolved_shot_count || 0),
    unresolved_asset_ids: array(value.unresolved_asset_ids),
    alias_collision_count: Number(value.alias_collision_count || 0),
    missing_anchor_count: Number(value.missing_anchor_count || 0),
    orphan_scene_coverage_count: Number(value.orphan_scene_coverage_count || 0),
    recognition_ambiguity_count: Number(value.recognition_ambiguity_count || 0),
    quality_issue_count: Number(value.quality_issue_count || 0),
    quality_pass: value.quality_pass === true,
    asset_shot_covered: Number(value.asset_shot_covered || 0),
    missing_source_evidence_shot_count: Number(value.missing_source_evidence_shot_count || 0),
    coverage_pass: value.coverage_pass === true,
  };
}

function normalizeRecognitionQuality(value = {}, coverage = {}) {
  const persistedIssues = array(value.issues).map((item) => ({
    code: String(item?.code || "recognition_quality_issue"),
    asset_type: String(item?.asset_type || ""),
    display_name: String(item?.display_name || "待确认资产"),
    scene_count: Number(item?.scene_count || 0),
    shot_count: Number(item?.shot_count || 0),
    message: String(item?.message || "资产识别需要复核。"),
    action: String(item?.action || "重新识别或人工修复"),
  }));
  const qualityPassed = value.status === "pass" && persistedIssues.length === 0 && coverage.quality_pass;
  const issues = qualityPassed || persistedIssues.length
    ? persistedIssues
    : [{
        code: "recognition_evidence_missing",
        asset_type: "",
        display_name: "当前识别版本",
        scene_count: Number(coverage.scene_total || 0),
        shot_count: Number(coverage.shot_total || 0),
        message: "当前版本缺少具名资产与出现范围的质量证据。",
        action: "预览重新识别并确认替换",
      }];
  return {
    status: qualityPassed ? "pass" : "blocked",
    issues,
    missing_anchor_count: Number(value.missing_anchor_count || coverage.missing_anchor_count || 0),
    orphan_scene_coverage_count: Number(value.orphan_scene_coverage_count || coverage.orphan_scene_coverage_count || 0),
    alias_collision_count: Number(value.alias_collision_count || coverage.alias_collision_count || 0),
    recognition_ambiguity_count: Number(value.recognition_ambiguity_count || coverage.recognition_ambiguity_count || 0),
    missing_source_evidence_shot_count: Number(
      value.missing_source_evidence_shot_count || coverage.missing_source_evidence_shot_count || 0
    ),
  };
}

function validBible(value) {
  return value?.schema_version === "afs.asset_bible.v0.1";
}

function array(value) {
  return Array.isArray(value) ? value : [];
}
