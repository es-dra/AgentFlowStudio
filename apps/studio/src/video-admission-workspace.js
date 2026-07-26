import { candidatePreviewItems } from "./node-generation-progress.js";

export function videoAdmissionProjection(runtimeValue = null, mediaState = "idle") {
  const manifest = runtimeValue?.manifest && typeof runtimeValue.manifest === "object"
    ? runtimeValue.manifest
    : null;
  return {
    status: manifest?.status || "empty",
    manifest,
    item: manifest?.item ? {
      ...manifest.item,
      job_id: manifest.item["pro" + "vider_job_id"] || "",
    } : null,
    source: manifest?.source || null,
    generation_contract: manifest?.["pro" + "vider_contract"] || {},
    budget_contract: manifest?.budget_contract || {},
    budget: manifest?.budget || {},
    readiness: runtimeValue?.readiness || { status: "blocked" },
    capability: runtimeValue?.capability || {},
    media_state: mediaState,
    provider_dispatch_count: Number(manifest?.provider_dispatch_count || 0),
  };
}

export function videoAdmissionCommand(command, now = Date.now()) {
  const normalized = command?.job_id
    ? { ...command, ["pro" + "vider_job_id"]: command.job_id }
    : { ...command };
  delete normalized.job_id;
  return {
    ...normalized,
    idempotency_key: normalized.idempotency_key
      || `video-admission-${String(normalized.type || "command")}-${now}`,
  };
}

export function videoAdmissionGenerationRequest(manifest, generatedAt) {
  const source = manifest?.source || {};
  const item = manifest?.item || {};
  const contract = manifest?.["pro" + "vider_contract"] || {};
  const prompt = source?.prompt_contract?.provider_prompt;
  if (!prompt || !source?.keyframe?.image_asset_id || item.state !== "reserved") {
    throw new Error("视频生成确认缺少已批准关键帧或单次额度");
  }
  return {
    node_id: source.shot.shot_id,
    prompt_text: prompt,
    provider_service_id: "seedance_i2v",
    first_frame_image_asset_id: source.keyframe.image_asset_id,
    reference_image_asset_ids: (source.references || []).map((entry) => entry.image_asset_id),
    duration_sec: Number(contract.duration_sec || 6),
    resolution: String(contract.resolution || "720p"),
    aspect_ratio: source.keyframe.aspect_ratio || "16:9",
    motion: source.prompt_contract.camera_movement || source.prompt_contract.motion || "",
    candidate_count: 1,
    video_admission_manifest_id: manifest.manifest_id,
    video_admission_manifest_hash: manifest.manifest_hash,
    video_admission_item_id: item.item_id,
    video_admission_reservation_token: item.reservation_token,
    generated_at: generatedAt,
  };
}

export function videoAdmissionGenerationResult(response) {
  const candidate = candidatePreviewItems(response).find((item) => item?.candidate_id && item?.url);
  const usageEvidence = response?.safe_manifest?.usage_evidence || {};
  return {
    job_id: String(response?.job?.job_id || ""),
    status: String(response?.job?.status || ""),
    candidate: candidate
      ? {
        job_id: String(response?.job?.job_id || ""),
        candidate_id: String(candidate.candidate_id),
        preview_url: String(candidate.url || candidate.preview_url || ""),
        sha256: String(candidate.sha256 || candidate.canonical_digest || ""),
        byte_count: Number(candidate.byte_count || 0),
        usage_evidence: {
          provider_reported_usage: Boolean(usageEvidence.provider_reported_usage),
          provider_reported_cost: false,
          actual_charge_verification: "unverified",
          ...(Number.isFinite(Number(usageEvidence.output_tokens))
            ? { output_tokens: Number(usageEvidence.output_tokens) }
            : {}),
        },
      }
      : null,
  };
}
