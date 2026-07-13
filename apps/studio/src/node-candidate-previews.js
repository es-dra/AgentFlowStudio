import { redactUnsafeText } from "./safe-text-redaction.js";
import { selectReusableAssetAuthority, validatedCandidatePreviewRoute } from "./reusable-asset-authority.js";

export function candidatePreviewsFromNode(node) {
  const raw = node?.params?.candidatePreviewUrls || node?.params?.candidate_previews || node?.params?.candidates || [];
  const result = [];
  const byKey = new Map();
  if (Array.isArray(raw)) {
    for (const item of raw) addCandidate(result, byKey, normalizeStoredCandidate(item));
  }
  for (const item of manifestCandidateItems(node?.params?.lastGenerationManifest || node?.params?.lastSafeManifest)) {
    addCandidate(result, byKey, item);
  }
  return result.filter(hasCandidateEvidence);
}

function normalizeStoredCandidate(item) {
  if (typeof item === "string") {
    return {
      candidate_id: candidateIdFromUrl(item),
      url: item,
      preview_url: item,
      status: "succeeded",
      state: "complete",
      preserved: true,
    };
  }
  if (!item || typeof item !== "object") return null;
  const candidateId = safeCandidateId(
    item.candidate_id || item.item_id || item.id
    || candidateIdFromUrl(item.url || item.preview_url || item.previewUrl || item.image_asset_preview_url || item.imageAssetPreviewUrl),
  );
  const route = validatedCandidatePreviewRoute({
    candidate_id: candidateId,
    parent_job_id: item.parent_job_id,
    project_id: item.project_id,
    preview_url: item.preview_url,
    url: item.url,
    previewUrl: item.previewUrl,
    image_asset_preview_url: item.image_asset_preview_url,
    imageAssetPreviewUrl: item.imageAssetPreviewUrl,
  });
  const url = route?.preview_url || "";
  const status = candidateStatus(item.status || item.state || (url ? "succeeded" : ""));
  const candidate = {
    candidate_id: candidateId,
    canonical_digest: safeSha256(item.canonical_digest || item.sha256),
    parent_job_id: safeToken(item.parent_job_id, 160),
    project_id: safeToken(item.project_id, 160),
    parent_candidate_id: safeToken(item.parent_candidate_id, 160),
    shot_id: safeToken(item.shot_id, 160),
    url,
    preview_url: url,
    width: safeOptionalCount(item.width),
    height: safeOptionalCount(item.height),
    aspect_ratio: safeToken(item.aspect_ratio, 20),
    artifact_id: safeToken(item.artifact_id, 160),
    byte_count: safeOptionalCount(item.byte_count),
    status,
    state: item.state || (status === "succeeded" ? "complete" : status),
    preserved: Boolean(item.preserved || status === "succeeded"),
    failure_class: safeToken(item.failure_class || item.block_id, 80),
    reason: safeReason(item.reason || item.message || item.error),
  };
  const authority = selectReusableAssetAuthority({
    ...candidate,
    preview_url: item.preview_url,
    url: item.url,
    previewUrl: item.previewUrl,
    image_asset_preview_url: item.image_asset_preview_url,
    imageAssetPreviewUrl: item.imageAssetPreviewUrl,
  }, [item.reusable_asset_authority]);
  return authority
    ? { ...candidate, reusable_asset_authority: authority, image_asset_id: authority.asset_id }
    : candidate;
}

function manifestCandidateItems(manifest) {
  if (!manifest || typeof manifest !== "object") return [];
  const items = [];
  const blocks = Array.isArray(manifest.blocks) ? manifest.blocks : [];
  for (const block of blocks) {
    if (!block || typeof block !== "object") continue;
    const candidateId = safeCandidateId(block.candidate_id || block.item_id || block.id);
    if (!candidateId) continue;
    items.push({
      candidate_id: candidateId,
      status: "failed",
      state: "failed",
      preserved: false,
      failure_class: safeToken(block.failure_class || block.block_id, 80),
      reason: safeReason(block.reason || block.message || block.error),
    });
  }
  const retryable = Array.isArray(manifest.retry?.retryable_item_ids) ? manifest.retry.retryable_item_ids : [];
  for (const candidateId of retryable) {
    items.push({
      candidate_id: safeCandidateId(candidateId),
      status: "retryable",
      state: "retryable",
      preserved: false,
    });
  }
  return items;
}

function addCandidate(result, byKey, candidate) {
  if (!hasCandidateEvidence(candidate)) return;
  const key = candidate.candidate_id || candidate.url || candidate.preview_url;
  if (key && byKey.has(key)) {
    Object.assign(byKey.get(key), mergeCandidate(byKey.get(key), candidate));
    return;
  }
  if (key) byKey.set(key, candidate);
  result.push(candidate);
}

function mergeCandidate(current, next) {
  const merged = { ...current, ...next };
  if (!next.url && current.url) merged.url = current.url;
  if (!next.preview_url && current.preview_url) merged.preview_url = current.preview_url;
  if (current.status === "succeeded" || next.status === "succeeded") merged.status = "succeeded";
  else if (current.status === "failed" || next.status === "failed") merged.status = "failed";
  if (current.state === "complete" || next.state === "complete") merged.state = "complete";
  else if (current.state === "failed" || next.state === "failed") merged.state = "failed";
  merged.preserved = Boolean(current.preserved || next.preserved || merged.status === "succeeded");
  return merged;
}

function hasCandidateEvidence(candidate) {
  return Boolean(candidate && (candidate.url || candidate.preview_url || candidate.candidate_id || candidate.status || candidate.state));
}

function candidateStatus(value) {
  const status = String(value || "").trim().toLowerCase();
  if (["complete", "completed", "success", "succeeded", "preserved"].includes(status)) return "succeeded";
  if (["failed", "failure", "error", "timeout", "timed_out"].includes(status)) return "failed";
  if (["blocked", "needs_attention", "cancelled", "retryable", "partial"].includes(status)) return status;
  return "";
}

function candidateIdFromUrl(url) {
  const match = String(url || "").match(/\/candidates\/([^/]+)\/preview$/);
  return safeCandidateId(match?.[1]);
}

function safeCandidateId(value) {
  return safeToken(value, 40);
}

function safeToken(value, limit) {
  return String(value || "").replace(/[^a-zA-Z0-9_.:-]+/g, "_").replace(/^_+|_+$/g, "").slice(0, limit);
}

function safeSha256(value) {
  const digest = String(value || "").trim().toLowerCase();
  return /^[a-f0-9]{64}$/.test(digest) ? digest : "";
}

function safeOptionalCount(value) {
  if (value == null || value === "") return null;
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return Math.max(0, Math.min(999999, Math.round(number)));
}

function safeReason(value) {
  return redactUnsafeText(value, 180);
}
