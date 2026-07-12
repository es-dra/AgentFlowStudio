import { redactUnsafeText } from "./safe-text-redaction.js";

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
  const url = item.url || item.preview_url || "";
  const status = candidateStatus(item.status || item.state || (url ? "succeeded" : ""));
  return {
    candidate_id: safeCandidateId(item.candidate_id || item.item_id || item.id || candidateIdFromUrl(url)),
    url,
    preview_url: item.preview_url || url,
    width: safeOptionalCount(item.width),
    height: safeOptionalCount(item.height),
    aspect_ratio: safeToken(item.aspect_ratio, 20),
    artifact_id: safeToken(item.artifact_id, 160),
    image_asset_id: safeToken(item.image_asset_id || item.asset_id, 160),
    byte_count: safeOptionalCount(item.byte_count),
    status,
    state: item.state || (status === "succeeded" ? "complete" : status),
    preserved: Boolean(item.preserved || status === "succeeded"),
    failure_class: safeToken(item.failure_class || item.block_id, 80),
    reason: safeReason(item.reason || item.message || item.error),
  };
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

function safeOptionalCount(value) {
  if (value == null || value === "") return null;
  const number = Number(value);
  if (!Number.isFinite(number)) return null;
  return Math.max(0, Math.min(999999, Math.round(number)));
}

function safeReason(value) {
  return redactUnsafeText(value, 180);
}
