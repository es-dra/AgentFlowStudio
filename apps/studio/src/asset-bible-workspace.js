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
    assets,
    active_assets: activeAssets,
    history_assets: historyAssets,
    counts,
    coverage,
    resolution_ledger: array(bible.resolution_ledger),
    last_receipt: bible.last_receipt || {},
    raw: bible,
    provider_dispatch_count: 0,
    external_cost_usd: 0,
  };
}

export function assetBibleSourceContext(studioState = {}) {
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
  return {
    source_node_id: sourceNode.id,
    script_revision_id: currentRevisionId || projection.source_revision_id,
    shot_candidate_id: projection.candidate_id,
    source_text: sourceText,
    shot_plan: shotPlan,
    scene_count: projection.scene_count,
    shot_count: projection.shot_count,
    duration_sec: projection.duration_sec,
  };
}

export function deriveProductionCopilotState({
  studioState = {},
  runtimeAssetBible = null,
  capabilityGates = {},
  section = "canvas",
  selectedAsset = null,
} = {}) {
  const shotTruth = legacyAppliedStoryboardProjection(studioState);
  const bible = assetBibleProjection(studioState, runtimeAssetBible);
  const scriptReady = Boolean(
    assetBibleSourceContext(studioState)?.script_revision_id
    || bible.candidate_set?.script_revision_id,
  );
  const shotReady = shotTruth.status === "ready" || Number(bible.candidate_set?.shot_count || 0) > 0;
  const candidatesReady = bible.counts.total > 0;
  const bibleLocked = bible.status === "locked" && Boolean(bible.locked_revision_id);
  const contentReady = bibleLocked && bible.coverage.coverage_pass;
  const imageEnabled = capabilityGates.image === true;
  let next = {
    action: "open_script",
    label: "选择当前剧本",
    reason: "需要先确认当前剧本版本。",
    enabled: section !== "canvas",
  };
  if (scriptReady && !shotReady) {
    next = { action: "open_storyboard", label: "拆分分镜", reason: "剧本已就绪，下一步是建立镜头计划。", enabled: true };
  } else if (shotReady && !candidatesReady) {
    next = { action: "generate_asset_candidates", label: "识别资产候选", reason: "分镜已应用，可执行本地确定性资产识别，不调用外部能力。", enabled: true };
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
  } else if (candidatesReady && !bibleLocked) {
    next = { action: "lock_asset_bible", label: "锁定 Asset Bible", reason: "资产审核与镜头覆盖已完成，可以锁定当前版本。", enabled: true };
  } else if (contentReady && !imageEnabled) {
    next = {
      action: "media_gate_closed",
      label: "图片能力未启用",
      reason: "结构已就绪，但当前环境未开放图片媒体能力。",
      enabled: false,
    };
  } else if (contentReady) {
    next = { action: "image_admission_ready", label: "进入图片准入", reason: "结构与锁定版本已满足图片生产前置条件。", enabled: true };
  }
  return {
    stage: !scriptReady ? "script_required"
      : !shotReady ? "shot_plan_required"
        : !candidatesReady ? "asset_recognition_ready"
          : !contentReady ? "asset_review"
            : imageEnabled ? "image_admission_ready" : "media_gate_closed",
    dependencies: [
      { key: "script", label: "当前剧本", state: scriptReady ? "ready" : "blocked" },
      { key: "shots", label: "已应用分镜", state: shotReady ? "ready" : "blocked" },
      { key: "assets", label: "资产候选", state: candidatesReady ? "ready" : "blocked" },
      { key: "coverage", label: "镜头覆盖", state: bible.coverage.coverage_pass ? "ready" : "blocked" },
      { key: "bible", label: "Bible 锁定", state: bibleLocked ? "ready" : "blocked" },
    ],
    blockers: [
      ...(!scriptReady ? ["缺少当前剧本版本"] : []),
      ...(scriptReady && !shotReady ? ["分镜尚未应用"] : []),
      ...(candidatesReady && bible.counts.candidate ? [`${bible.counts.candidate} 个资产待确认`] : []),
      ...(candidatesReady && bible.coverage.unresolved_required ? [
        `${bible.coverage.unresolved_required} 个必要出现范围未解决（${bible.coverage.unresolved_shot_count} 镜头）`,
      ] : []),
      ...(bible.coverage.alias_collision_count ? [`${bible.coverage.alias_collision_count} 组别名冲突`] : []),
      ...(contentReady && !imageEnabled ? ["内容结构已就绪；图片能力未启用"] : []),
    ],
    gate: {
      llm: capabilityGates.llm === true,
      image: imageEnabled,
      video: capabilityGates.video === true,
      admission: contentReady ? (imageEnabled ? "ready" : "structure_ready_media_disabled") : "blocked",
      cost_state: "not_admitted",
    },
    next_valid_action: next,
    asset_bible: bible,
    provider_dispatch_count: 0,
    external_cost_usd: 0,
  };
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
    negative_locks: array(value.negative_locks),
    pending_fields: array(value.pending_fields),
    source_evidence: array(value.source_evidence),
    superseded_by_ids: array(value.superseded_by_ids),
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
    coverage_pass: value.coverage_pass === true,
  };
}

function validBible(value) {
  return value?.schema_version === "afs.asset_bible.v0.1";
}

function array(value) {
  return Array.isArray(value) ? value : [];
}
