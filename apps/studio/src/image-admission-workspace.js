import { candidatePreviewItems } from "./node-generation-progress.js";

export function imageAdmissionProjection(runtimeValue = null, mediaStates = {}) {
  const manifest = runtimeValue?.manifest && typeof runtimeValue.manifest === "object"
    ? runtimeValue.manifest
    : null;
  const items = Array.isArray(manifest?.items) ? manifest.items : [];
  const counts = {};
  for (const state of ["planned", "reserved", "processing", "candidate", "approved", "rejected", "failed", "cancelled"]) {
    counts[state] = items.filter((item) => item?.state === state).length;
  }
  counts.media_load_failed = items.filter((item) => {
    if (!item?.candidate || !["candidate", "approved", "rejected"].includes(item.state)) return false;
    const key = imageAdmissionMediaKey(item, manifest?.project_id);
    return !item.candidate.preview_url || mediaStates[key] === "failed";
  }).length;
  const capability = runtimeValue?.capability || {};
  const budgetContract = manifest?.budget_contract || runtimeValue?.budget_contract || {};
  const historySummary = runtimeValue?.history_summary && typeof runtimeValue.history_summary === "object"
    ? runtimeValue.history_summary
    : {};
  const budget = manifest?.budget || {
    dispatches_reserved: 0,
    estimated_reserved_usd: "0.0000",
    remaining_dispatches: Number(budgetContract.max_dispatches || 1),
    remaining_estimated_usd: String(budgetContract.max_estimated_usd || ""),
  };
  return {
    status: manifest?.status || "empty",
    manifest,
    items,
    counts,
    capability,
    budget_contract: budgetContract,
    budget,
    history_summary: historySummary,
    ready_to_prepare: true,
    provider_dispatch_count: Number(manifest?.provider_dispatch_count || 0),
    actual_usd: manifest?.actual_usd ?? null,
    billing_verification_state: manifest?.billing_verification_state || "unverified",
  };
}

export function imageAdmissionMediaKey(item, projectId = "") {
  const candidate = item?.candidate;
  if (!candidate || typeof candidate !== "object") return "";
  return [
    String(projectId || ""),
    String(item?.item_id || ""),
    String(candidate.image_asset_id || ""),
    String(candidate.sha256 || ""),
  ].join(":");
}

export function imageAdmissionItemTypeLabel(value) {
  return {
    character_design: "角色设定",
    scene_plate: "场景净板",
    prop_design: "核心道具",
    shot_keyframe: "镜头关键帧",
  }[String(value || "")] || "图片项目";
}

export function imageAdmissionStateLabel(value) {
  return {
    planned: "待生成",
    reserved: "额度已占用 · 待发送",
    processing: "生成中 · 可恢复",
    candidate: "待审核",
    approved: "已批准",
    rejected: "已拒绝",
    failed: "失败可恢复",
    cancelled: "已停止",
  }[String(value || "")] || "待确认";
}

export function imageAdmissionFailureGuidance(item, manifest = {}) {
  if (item?.state !== "failed") return null;
  const category = String(item.error_category || "generation_failed");
  const copy = {
    blocked: {
      title: "图片结果未能安全接收",
      detail: "本次结果未通过安全接收检查，没有写入项目。旧尝试与费用记录会完整保留。",
      diagnostic: "安全接收受阻",
    },
    generation_failed: {
      title: "图片生成未完成",
      detail: "本次生成没有产生可审核图片，没有写入项目。旧尝试与费用记录会完整保留。",
      diagnostic: "生成未完成",
    },
    cancelled: {
      title: "图片任务未完成",
      detail: "本次任务结束时没有可审核图片，没有写入项目。旧尝试与费用记录会完整保留。",
      diagnostic: "任务未完成",
    },
    deterministic_fixture_failure: {
      title: "零费用测试未完成",
      detail: "测试结果已隔离，没有写入项目。测试记录会完整保留。",
      diagnostic: "测试失败",
    },
  }[category] || {
    title: "图片生成未完成",
    detail: "本次没有产生可安全审核的图片，没有写入项目。旧尝试与费用记录会完整保留。",
    diagnostic: "生成未完成",
  };
  const budget = manifest?.budget || {};
  const contract = manifest?.budget_contract || {};
  return {
    ...copy,
    can_create_recovery_manifest: (
      manifest?.status === "locked"
      && !manifest?.recovery_contract
      && Number(budget.dispatches_reserved || 0) === Number(contract.max_dispatches || 1)
      && Number(budget.remaining_dispatches || 0) === 0
    ),
  };
}

export function imageAdmissionCommand(command, now = Date.now()) {
  return {
    ...command,
    idempotency_key: command.idempotency_key
      || `image-admission-${String(command.type || "command")}-${String(command.item_id || "manifest")}-${now}`,
  };
}

const IMAGE_ADMISSION_MANIFEST_SOURCE_COMMANDS = new Set([
  "create_recovery_manifest",
  "create_next_batch_manifest",
  "inspect_next_batch",
  "cancel_batch",
]);

export function imageAdmissionCommandSourceMatchesManifest(command, source, manifest) {
  if (!IMAGE_ADMISSION_MANIFEST_SOURCE_COMMANDS.has(String(command?.type || ""))) {
    return true;
  }
  const manifestSource = manifest?.source;
  if (!manifestSource || typeof manifestSource !== "object") return true;
  if (
    manifestSource.production_graph_version
    && Number(source?.production_graph_version || 0) !== Number(manifestSource.production_graph_version || 0)
  ) {
    return false;
  }
  if (
    manifestSource.production_graph_digest
    && String(source?.production_graph_digest || "") !== String(manifestSource.production_graph_digest || "")
  ) {
    return false;
  }
  return true;
}

export function imageAdmissionItemJobId(item) {
  return String(item?.provider_job_id || "");
}

export function imageAdmissionJobCommand(itemId, jobId) {
  return {
    type: "record_job",
    item_id: itemId,
    provider_job_id: jobId,
  };
}

export function imageAdmissionGenerationRequest(item, manifestId, generatedAt) {
  const promptContract = item?.prompt_contract || {};
  const providerPrompt = String(promptContract.provider_prompt || "");
  const visualStyle = String(promptContract.art_direction?.visual_style || "");
  if (!providerPrompt || !visualStyle) {
    throw new Error("图片项目缺少已锁定的创意提示合同");
  }
  return {
    node_id: item.target_shot_id || item.target_asset_ids?.[0] || item.item_id,
    prompt_text: providerPrompt,
    target_platform: "short_video",
    style: visualStyle,
    aspect_ratio: item.aspect_ratio,
    candidate_count: 1,
    provider_service_id: "image_relay",
    asset_refs: item.reference_media_ids || [],
    node_parameters: {
      disable_provider_retry: true,
      image_admission: {
        manifest_id: manifestId,
        item_id: item.item_id,
        reservation_token: item.reservation_token || "",
      },
    },
    generated_at: generatedAt,
  };
}

export function imageAdmissionGenerationResult(response) {
  const candidate = candidatePreviewItems(response).find((item) => item?.reusable_asset_authority);
  const authority = candidate?.reusable_asset_authority;
  const mediaEvidenceComplete = (
    (authority?.mime_type === "image/png" || authority?.mime_type === "image/jpeg")
    && Number.isInteger(authority?.width)
    && authority.width > 0
    && Number.isInteger(authority?.height)
    && authority.height > 0
    && typeof authority?.preview_url === "string"
    && authority.preview_url.length > 0
  );
  return {
    job_id: String(response?.job?.job_id || ""),
    status: String(response?.job?.status || ""),
    candidate: mediaEvidenceComplete
      ? {
        image_asset_id: authority.asset_id,
        sha256: authority.sha256,
        format: authority.mime_type === "image/jpeg" ? "jpeg" : "png",
        width: authority.width,
        height: authority.height,
        preview_url: authority.preview_url,
      }
      : null,
  };
}
