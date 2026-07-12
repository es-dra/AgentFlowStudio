import { mergeImageAssets, resizeNodeForImagePreview } from "./node-image-assets.js";
import { visibleAssetForNode } from "./node-visible-assets.js";
import { firstCandidatePreview, updateNodeGenerationState } from "./node-generation-progress.js";
import { isKeyframeInProgress, keyframeResultText } from "./node-generation-results.js";
import { reconcileVisualAssetBadges } from "./node-generation-context.js";
import { keyframeSourceEvidenceTrace } from "./keyframe-source-evidence-trace.js";
import { redactUnsafeText } from "./safe-text-redaction.js";
const SAFE_PUBLIC_IDENTIFIER_RE = /^[a-zA-Z0-9_.:-]+$/;
const UNSAFE_PUBLIC_IDENTIFIER_FRAGMENT_RE = /(?:authorization|auth|token|secret|credential|api[_-]?key|cookie|session)/i;
const SAFE_PUBLIC_PREVIEW_ROUTE_RE = /^\/projects\/[a-zA-Z0-9_.-]+\/(?:image-assets\/[a-zA-Z0-9_.-]+\/preview|keyframe-generations\/[a-zA-Z0-9_.-]+\/candidates\/[a-zA-Z0-9_.-]+\/preview|video-generations\/[a-zA-Z0-9_.-]+\/candidates\/[a-zA-Z0-9_.-]+\/preview)$/;
const ALLOWED_PUBLIC_FAILURE_CLASSES = new Set([
  "provider_timeout",
  "provider_gate_closed",
  "provider_policy_block",
  "provider_http_error",
  "provider_not_ready",
  "provider_output_missing",
  "provider_failed",
  "provider_error",
  "validation_block",
  "skipped",
  "remote_vision_gate_closed",
  "remote_vision_provider_not_ready",
]);
export function applyKeyframeResponse(store, nodeId, response, request, options = {}) {
  const status = response?.job?.status || "blocked";
  const inProgress = isKeyframeInProgress(response);
  const kind = options.kind || "keyframe";
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    const reusableAsset = response?.reusable_image_assets?.[0] || null;
    const preview = firstCandidatePreview(response) || previewFromReusableAsset(reusableAsset);
    const outputCount = Number(response?.safe_manifest?.output_count || 0);
    const succeeded = status === "succeeded";
    const partial = !succeeded && !inProgress && Boolean(preview?.preview_url || reusableAsset?.preview_url || outputCount > 0);
    const jobId = response?.job?.job_id || null;
    const shouldRecordAsset = (succeeded || partial) && jobId && n.params.lastKeyframeCompletedJobId !== jobId;
    updateNodeGenerationState(n, response, { kind, retrying: Boolean(options.retrying) });
    n.params.lastKeyframeJobId = jobId || n.params.lastKeyframeJobId || null;
    n.status = succeeded ? "complete" : inProgress ? "generating" : partial ? "partial" : "error";
    if (preview?.preview_url) {
      n.previewUrl = preview.preview_url;
      resizeNodeForImagePreview(n, preview, request.aspect_ratio);
    }
    if (succeeded && reusableAsset?.asset_id) {
      n.params.uploads = mergeImageAssets(n.params.uploads || [], reusableAssetForNode(n, reusableAsset, kind)).slice(-4);
    }
    n.params.lastContextBundle = response?.context_bundle || n.params.lastContextBundle || null;
    n.params.lastGenerationBridge = response?.generation_bridge || n.params.lastGenerationBridge || null;
    n.params.lastGenerationBridgeArtifactId = response?.artifacts?.keyframe_generation_bridge?.artifact_id || n.params.lastGenerationBridgeArtifactId || "";
    n.params.lastGenerationManifest = publicGenerationManifest(response) || n.params.lastGenerationManifest || null;
    n.params.lastKeyframeSourceEvidenceTrace = keyframeSourceEvidenceTrace(n) || n.params.lastKeyframeSourceEvidenceTrace || null;
    reconcileVisualAssetBadges(n, response?.context_bundle || null);
    n.result = keyframeResultText(response, request, succeeded, { kind, partial });
    if (shouldRecordAsset) {
      n.params.lastKeyframeCompletedJobId = jobId;
      const asset = visibleAssetForNode(store, n);
      s.assets.unshift({
        ...asset,
        status: partial ? "partially_complete" : asset.status,
        safe_summary: (n.prompt || "").slice(0, 90),
        job_id: jobId,
        artifact_id: response?.artifacts?.keyframe_generation_safe_manifest?.artifact_id || null,
        asset_id: reusableAsset?.asset_id || null,
        preview_url: n.previewUrl,
        created_at: new Date().toISOString(),
      });
    }
  });
}
export function nodeGenerationKind(node) {
  return node?.params?.nodeRole === "asset_card_draft" ? "asset" : "keyframe";
}
export function submitLabel(kind) {
  return kind === "asset" ? "正在提交资产图生成" : "正在提交图片生成";
}
export function fallbackRequest(node) {
  return { aspect_ratio: node.params?.spec?.ratio || "9:16" };
}
function reusableAssetForNode(node, reusableAsset, kind) {
  if (kind !== "asset") return reusableAsset;
  const assetType = String(node?.params?.assetCardDraft?.asset_type || "");
  const role = { character: "character_reference", scene: "scene_reference", prop: "prop_reference" }[assetType] || "asset_reference";
  return { ...reusableAsset, role };
}
function previewFromReusableAsset(asset) {
  if (!asset?.preview_url) return null;
  return {
    preview_url: asset.preview_url,
    width: asset.width || null,
    height: asset.height || null,
    aspect_ratio: asset.aspect_ratio || null,
  };
}

function publicGenerationManifest(response) {
  const manifest = response?.safe_manifest;
  if (!manifest || typeof manifest !== "object") return null;
  return {
    status: publicStatusText(manifest.status || response?.job?.status || "", 40),
    batch_status: publicBatchStatusText(manifest.batch_status || "", 60),
    stage: publicIdentifier(manifest.stage || manifest.provider_diagnostics?.provider_stage || "", 120),
    failure_class: publicFailureClass(manifest.failure_class || manifest.provider_diagnostics?.failure_class || ""),
    output_count: Number(manifest.output_count || 0),
    reference_image_count: Number(manifest.reference_image_count || 0),
    retry_count: Number(manifest.retry_count || 0),
    artifact_id: publicIdentifier(response?.artifacts?.keyframe_generation_safe_manifest?.artifact_id || "", 160),
    blocks: Array.isArray(manifest.blocks)
      ? manifest.blocks.map((block) => publicGenerationBlock(block)).filter(Boolean).slice(0, 8)
      : [],
    provider_diagnostics: publicProviderDiagnostics(manifest.provider_diagnostics),
    batch_summary: publicBatchSummary(manifest.batch_summary),
    retry: publicRetrySummary(manifest.retry),
    review_preview_refs: publicReviewPreviewRefs(manifest.review_preview_refs),
  };
}

function publicGenerationBlock(block) {
  if (!block || typeof block !== "object") return null;
  return {
    block_id: publicIdentifier(block.block_id || block.code || "", 100),
    candidate_id: publicIdentifier(block.candidate_id || "", 40),
    reason: publicManifestText(block.reason || block.message || block.error || "", 260),
    required_gate: publicIdentifier(block.required_gate || "", 80),
    failure_class: publicFailureClass(block.failure_class || block.block_id || block.reason || ""),
    provider_stage: publicIdentifier(block.provider_stage || "", 120),
    retry_count: Number(block.retry_count || 0),
    attempt_count: Number(block.attempt_count || 0),
    provider_elapsed_ms: Number(block.provider_elapsed_ms || 0),
  };
}

function publicProviderDiagnostics(value) {
  if (!value || typeof value !== "object") return null;
  return {
    provider_stage: publicIdentifier(value.provider_stage || "", 120),
    failure_class: publicFailureClass(value.failure_class || value.reason || ""),
    error_type: publicIdentifier(value.error_type || "", 120),
    reason: publicManifestText(value.reason || "", 260),
    required_gate: publicIdentifier(value.required_gate || "", 80),
    retry_count: Number(value.retry_count || 0),
    attempt_count: Number(value.attempt_count || 0),
    provider_elapsed_ms: Number(value.provider_elapsed_ms || 0),
  };
}

function publicBatchSummary(value) {
  if (!value) return null;
  if (typeof value !== "object" || Array.isArray(value)) return publicManifestText(value, 260);
  return {
    requested_count: safeCount(value.requested_count),
    complete_count: safeCount(value.complete_count),
    retryable_count: safeCount(value.retryable_count),
    needs_attention_count: safeCount(value.needs_attention_count),
  };
}

function publicRetrySummary(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return {
    retry_count: safeCount(value.retry_count),
    default_scope: publicIdentifier(value.default_scope || "", 80),
    retryable_item_ids: publicIdentifierList(value.retryable_item_ids, 16, 80),
    preserved_item_ids: publicIdentifierList(value.preserved_item_ids, 16, 80),
    preserve_successful_outputs: Boolean(value.preserve_successful_outputs),
  };
}

function publicReviewPreviewRefs(value) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => publicReviewPreviewRef(item)).filter(Boolean).slice(0, 8);
}

function publicReviewPreviewRef(item) {
  if (!item || typeof item !== "object") return null;
  return {
    job_id: publicIdentifier(item.job_id || "", 120),
    candidate_id: publicIdentifier(item.candidate_id || "", 40),
    safe_preview_ref: publicPreviewUrl(item.safe_preview_ref || ""),
    byte_count: safeCount(item.byte_count),
    sha256: publicIdentifier(item.sha256 || "", 100),
    width: safeCount(item.width),
    height: safeCount(item.height),
    aspect_ratio: publicAspectRatio(item.aspect_ratio || ""),
  };
}

function publicIdentifierList(value, maxItems, limit) {
  if (!Array.isArray(value)) return [];
  return value.map((item) => publicIdentifier(item, limit)).filter(Boolean).slice(0, maxItems);
}

function publicManifestText(value, limit) {
  return redactUnsafeText(value, limit);
}

function publicStatusText(value, limit) {
  const text = redactUnsafeText(value, limit).toLowerCase();
  const normalized = text.replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  if (["complete", "completed", "success", "succeeded"].includes(normalized)) return "succeeded";
  if (["partially_complete", "partial"].includes(normalized)) return "partially_complete";
  if (["failed", "failure", "error", "timeout", "timed_out", "poll_failed"].includes(normalized)) return "failed";
  if (["blocked", "needs_attention", "cancelled", "retrying", "submitted", "pending", "running"].includes(normalized)) return normalized;
  if (/\bpartial/.test(text)) return "partially_complete";
  if (/\b(?:failed|failure|error|timeout|timed out)\b/.test(text)) return "failed";
  if (/\b(?:complete|completed|success|succeeded)\b/.test(text)) return "succeeded";
  if (/\bneeds[_\s-]?attention\b/.test(text)) return "needs_attention";
  if (/\bblocked\b/.test(text)) return "blocked";
  if (/\bcancel/.test(text)) return "cancelled";
  if (/\brunning\b/.test(text)) return "running";
  if (/\bpending\b/.test(text)) return "pending";
  if (/\bsubmitted\b/.test(text)) return "submitted";
  return "";
}

function publicBatchStatusText(value, limit) {
  const text = redactUnsafeText(value, limit).toLowerCase();
  const normalized = text.replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  if (["complete", "completed", "success", "succeeded"].includes(normalized)) return "complete";
  if (["partially_complete", "partial"].includes(normalized)) return "partially_complete";
  if (["failed", "failure", "error", "timeout", "timed_out", "poll_failed"].includes(normalized)) return "failed";
  if (["needs_attention", "retrying"].includes(normalized)) return normalized;
  if (/\bpartial/.test(text)) return "partially_complete";
  if (/\b(?:failed|failure|error|timeout|timed out)\b/.test(text)) return "failed";
  if (/\b(?:complete|completed|success|succeeded)\b/.test(text)) return "complete";
  if (/\bneeds[_\s-]?attention\b/.test(text)) return "needs_attention";
  if (/\bretry/.test(text)) return "retrying";
  return "";
}

function publicIdentifier(value, limit) {
  const original = String(value || "").trim();
  if (!original || original.length > limit) return "";
  const redacted = redactUnsafeText(original, 512);
  if (redacted !== original) return "";
  if (UNSAFE_PUBLIC_IDENTIFIER_FRAGMENT_RE.test(original)) return "";
  return SAFE_PUBLIC_IDENTIFIER_RE.test(original) ? original : "";
}

function publicFailureClass(value) {
  const text = redactUnsafeText(value, 140).toLowerCase();
  if (!text) return "";
  const normalized = text.replace(/<redacted>/g, "").replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  if (ALLOWED_PUBLIC_FAILURE_CLASSES.has(normalized)) return normalized;
  if (text.includes("timeout") || text.includes("timed out")) return "provider_timeout";
  if (text.includes("gate_closed") || text.includes("gate closed")) return "provider_gate_closed";
  if (text.includes("policy") || text.includes("copyright")) return "provider_policy_block";
  if (text.includes("validation") || text.includes("invalid") || text.includes("unsupported")) return "validation_block";
  if (text.includes("not_ready") || text.includes("not ready") || text.includes("service_not_found")) return "provider_not_ready";
  if (text.includes("missing")) return "provider_output_missing";
  if (text.includes("http")) return "provider_http_error";
  if (text.includes("skipped")) return "skipped";
  return "provider_failed";
}

function publicPreviewUrl(value) {
  const original = String(value || "").trim();
  if (!original) return "";
  const redacted = redactUnsafeText(original, 512);
  if (redacted !== original) return "";
  return SAFE_PUBLIC_PREVIEW_ROUTE_RE.test(original) ? original : "";
}

function publicAspectRatio(value) {
  const original = String(value || "").trim();
  if (!original || original.length > 20) return "";
  const redacted = redactUnsafeText(original, 80);
  if (redacted !== original) return "";
  const match = original.match(/^([1-9]\d?):([1-9]\d?)$/);
  return match ? `${Number(match[1])}:${Number(match[2])}` : "";
}

function safeCount(value) {
  const number = Number(value || 0);
  return Number.isFinite(number) ? Math.max(0, Math.round(number)) : 0;
}
