const ACTIVE_RUNTIME_STATUSES = new Set(["submitted", "pending", "running", "generating"]);
const COMPLETE_RUNTIME_STATUSES = new Set(["complete", "completed", "succeeded", "success", "generated"]);
const FAILED_RUNTIME_STATUSES = new Set(["error", "failed", "failure", "timeout", "timed_out"]);
const ATTENTION_RUNTIME_STATUSES = new Set(["blocked", "cancelled", "cancelled_local_only", "skipped", "needs_attention"]);

const POLICY_COPY = {
  complete: {
    title: "complete",
    detail: "Ready for review. Not yet accepted.",
    nextAction: "Review the output, then decide whether to use it in the next step.",
  },
  partially_complete: {
    title: "partially_complete",
    detail: "Partial result is preserved.",
    nextAction: "Review the partial result, then retry failed items only.",
  },
  failed: {
    title: "failed",
    detail: "No complete output is available.",
    nextAction: "Check the blocked reason, then retry failed items only.",
  },
  retrying: {
    title: "retrying",
    detail: "Retrying failed items. Preserved outputs remain visible.",
    nextAction: "Wait for Runtime status; provider quota may be used.",
  },
  needs_attention: {
    title: "needs_attention",
    detail: "The workflow is blocked or requires review before continuing.",
    nextAction: "Resolve the blocked reason, then retry failed items only if needed.",
  },
};

export function policyStatusForRuntimeStatus(status, options = {}) {
  const normalized = normalizeStatus(status || options.uiStatus);
  if (options.retrying || normalized === "retrying") return "retrying";
  if (normalized === "partial" || normalized === "partially_complete") return "partially_complete";
  if (COMPLETE_RUNTIME_STATUSES.has(normalized)) return "complete";
  if (options.hasPartialOutput && !ACTIVE_RUNTIME_STATUSES.has(normalized)) return "partially_complete";
  if (FAILED_RUNTIME_STATUSES.has(normalized)) return "failed";
  if (ATTENTION_RUNTIME_STATUSES.has(normalized)) return "needs_attention";
  return "";
}

export function isActiveRuntimeStatus(status) {
  return ACTIVE_RUNTIME_STATUSES.has(normalizeStatus(status));
}

export function responseStatusSummary(response, options = {}) {
  const runtimeStatus = normalizeStatus(
    response?.runtime_recovery?.status
      || response?.safe_manifest?.batch_status
      || response?.job?.status
      || response?.status
      || "blocked",
  );
  const hasPartialOutput = hasPartialGenerationOutput(response);
  const retrying = Boolean(options.retrying && isActiveRuntimeStatus(runtimeStatus));
  const policyStatus = policyStatusForRuntimeStatus(runtimeStatus, {
    hasPartialOutput,
    retrying,
  });
  return {
    runtimeStatus,
    policyStatus,
    displayStatus: policyStatus || (isActiveRuntimeStatus(runtimeStatus) ? "waiting" : "needs_attention"),
    tone: statusTone(policyStatus, runtimeStatus),
    title: statusTitle(policyStatus, runtimeStatus),
    detail: statusDetail(policyStatus, runtimeStatus, hasPartialOutput),
    blockedReason: blockedReasonFromResponse(response),
    nextAction: nextActionFor(policyStatus, runtimeStatus),
    safeRefs: safeGenerationRefs({ response }),
    hasPartialOutput,
  };
}

export function nodeStatusSummary(node) {
  const runtimeStatus = normalizeStatus(
    node?.params?.jobProgress?.status
      || node?.params?.lastSafeManifest?.status
      || node?.params?.lastGenerationManifest?.status
      || node?.status
      || "empty",
  );
  const hasPartialOutput = hasPartialGenerationOutput(node);
  const retrying = Boolean(node?.params?.retryFailedItemsOnly && node?.status === "generating");
  const policyStatus = node?.params?.generationPolicyStatus
    || policyStatusForRuntimeStatus(runtimeStatus, {
      hasPartialOutput,
      retrying,
      uiStatus: node?.status,
    });
  return {
    runtimeStatus,
    policyStatus,
    displayStatus: policyStatus || (isActiveRuntimeStatus(runtimeStatus) || node?.status === "generating" ? "waiting" : "draft"),
    tone: statusTone(policyStatus, runtimeStatus),
    title: statusTitle(policyStatus, runtimeStatus),
    detail: node?.params?.generationStatusDetail || statusDetail(policyStatus, runtimeStatus, hasPartialOutput),
    blockedReason: node?.params?.generationBlockedReason || blockedReasonFromNode(node),
    nextAction: node?.params?.generationNextAction || nextActionFor(policyStatus, runtimeStatus),
    safeRefs: safeGenerationRefs({ node }),
    hasPartialOutput,
  };
}

export function generationReadinessSummary(node, profile, promptValue = "") {
  if (profile?.runsGeneration === false) {
    return {
      blocked: false,
      status: "complete",
      title: "complete",
      detail: "Settings can be saved without a provider submit.",
      nextAction: "Save settings; no provider quota is used.",
      rows: [],
    };
  }
  const type = node?.type === "video" ? "video" : "image";
  const rows = [
    {
      label: "Auth gate",
      status: "complete",
      detail: "A Studio account session is required when Runtime auth is enabled.",
    },
    {
      label: "Provider gate",
      status: "needs_attention",
      detail: type === "video"
        ? "Video generation requires task-level provider authorization; provider quota may be used."
        : "Image generation requires the Runtime image provider gate; provider quota may be used.",
    },
    {
      label: "Runtime readiness",
      status: "needs_attention",
      detail: "Runtime Service must expose preflight and generation routes for this branch.",
    },
  ];
  const blockers = [];
  if (type === "video" && !String(node?.params?.firstFrameImageAssetId || "").trim()) {
    blockers.push("First frame is required before video submit.");
  }
  if (type === "video" && !String(promptValue || node?.prompt || "").trim()) {
    blockers.push("Video motion prompt is required before submit.");
  }
  const blocked = blockers.length > 0;
  rows.push({
    label: "Node readiness",
    status: blocked ? "needs_attention" : "complete",
    detail: blocked ? blockers.join(" ") : "Required local node inputs are present.",
  });
  return {
    blocked,
    status: blocked ? "needs_attention" : "complete",
    title: blocked ? "needs_attention" : "complete",
    detail: blocked ? "Blocked before submit." : "Gate check is visible before submit.",
    blockedReason: blockers.join(" "),
    nextAction: blocked ? blockers[0] : "Submit only after reviewing gates; provider quota may be used.",
    rows,
  };
}

export function capturePreservedOutputs(node) {
  const refs = safeGenerationRefs({ node });
  return {
    preview_present: Boolean(node?.previewUrl),
    result_present: Boolean(node?.result),
    candidate_count: Array.isArray(node?.params?.candidatePreviewUrls) ? node.params.candidatePreviewUrls.length : 0,
    safe_refs: refs,
    preserved_at: new Date().toISOString(),
  };
}

export function safePublicText(value, maxLength = 220) {
  return String(value || "")
    .replace(/Bearer\s+\S+/gi, "Bearer <redacted>")
    .replace(/Authorization\s*[:=]\s*\S+/gi, "Authorization=<redacted>")
    .replace(/\b(?:token|secret|credential)\s*[:=]\s*\S+/gi, "<redacted>")
    .replace(/[A-Za-z]:\\[^\s"'<>]+/g, "<local-path-redacted>")
    .replace(/\/(?:home|Users|mnt|var|tmp|opt)\/[^\s"'<>]+/g, "<local-path-redacted>")
    .replace(/https?:\/\/[^\s"'<>]+/g, "<url-redacted>")
    .slice(0, maxLength);
}

function statusTone(policyStatus, runtimeStatus) {
  if (policyStatus === "complete") return "complete";
  if (policyStatus === "partially_complete") return "partial";
  if (policyStatus === "failed") return "failed";
  if (policyStatus === "retrying") return "retrying";
  if (policyStatus === "needs_attention") return "attention";
  if (isActiveRuntimeStatus(runtimeStatus)) return "waiting";
  return "draft";
}

function statusTitle(policyStatus, runtimeStatus) {
  if (policyStatus && POLICY_COPY[policyStatus]) return POLICY_COPY[policyStatus].title;
  if (isActiveRuntimeStatus(runtimeStatus)) return "waiting";
  return "draft";
}

function statusDetail(policyStatus, runtimeStatus, hasPartialOutput) {
  if (policyStatus && POLICY_COPY[policyStatus]) return POLICY_COPY[policyStatus].detail;
  if (isActiveRuntimeStatus(runtimeStatus)) return "Waiting for generation status. Keep the page open.";
  if (hasPartialOutput) return POLICY_COPY.partially_complete.detail;
  return "No generation result yet.";
}

function nextActionFor(policyStatus, runtimeStatus) {
  if (policyStatus && POLICY_COPY[policyStatus]) return POLICY_COPY[policyStatus].nextAction;
  if (isActiveRuntimeStatus(runtimeStatus)) return "Wait for Runtime status; completed outputs will remain visible.";
  return "Add prompt or references, then open generation settings.";
}

function blockedReasonFromResponse(response) {
  const block = response?.safe_manifest?.blocks?.[0] || response?.blocks?.[0] || {};
  return safePublicText(
    block.reason
      || response?.job?.error
      || response?.error
      || response?.job?.status_detail
      || "",
  );
}

function blockedReasonFromNode(node) {
  const manifest = node?.params?.lastSafeManifest || node?.params?.lastGenerationManifest || {};
  const block = manifest.blocks?.[0] || {};
  const resultReason = String(node?.result || "").split(/\n/).find((line) => /原因|Reason|blocked/i.test(line));
  return safePublicText(
    block.reason
      || node?.params?.jobProgress?.blockedReason
      || resultReason
      || "",
  );
}

function hasPartialGenerationOutput(source) {
  if (!source) return false;
  if (Array.isArray(source.runtime_recovery?.outputs)) {
    return source.runtime_recovery.outputs.some((item) => item?.state === "complete" || item?.preserved);
  }
  if (source.previewUrl) return true;
  if (Array.isArray(source.candidate_previews) && source.candidate_previews.length) return true;
  if (Array.isArray(source.reusable_image_assets) && source.reusable_image_assets.length) return true;
  if (Number(source.safe_manifest?.output_count || 0) > 0) return true;
  const params = source.params || {};
  return Boolean(
    params.lastVideoPreviewUrl
      || params.lastVideoArtifactId
      || (Array.isArray(params.candidatePreviewUrls) && params.candidatePreviewUrls.length)
      || (Array.isArray(params.preservedGenerationOutputs) && params.preservedGenerationOutputs.length),
  );
}

function safeGenerationRefs({ node = null, response = null }) {
  const refs = [];
  pushRef(refs, "job", response?.runtime_recovery?.job_id || response?.job?.job_id || node?.params?.lastKeyframeJobId || node?.params?.lastVideoJobId);
  pushRef(refs, "artifact", response?.safe_manifest?.artifact_id || node?.params?.lastSafeManifest?.artifact_id);
  pushRef(refs, "artifact", node?.params?.lastVideoArtifactId);
  pushRef(refs, "bridge", node?.params?.lastGenerationBridgeArtifactId);
  const artifacts = response?.artifacts && typeof response.artifacts === "object" ? Object.values(response.artifacts) : [];
  for (const artifact of artifacts) pushRef(refs, "artifact", artifact?.artifact_id);
  const recoveryPointers = Array.isArray(response?.runtime_recovery?.safe_artifact_pointers)
    ? response.runtime_recovery.safe_artifact_pointers
    : [];
  for (const pointer of recoveryPointers) pushRef(refs, pointer?.role || "artifact", pointer?.artifact_id);
  return refs.slice(0, 6);
}

function pushRef(refs, label, value) {
  const token = safeToken(value);
  if (!token || refs.some((item) => item.value === token)) return;
  refs.push({ label, value: token });
}

function safeToken(value) {
  const text = String(value || "").trim();
  if (!text || /https?:\/\//i.test(text) || /Bearer\s+/i.test(text)) return "";
  if (/[A-Za-z]:\\|\/(?:home|Users|mnt|var|tmp|opt)\//.test(text)) return "";
  return text.replace(/[^a-zA-Z0-9_.:-]+/g, "_").slice(0, 120);
}

function normalizeStatus(status) {
  return String(status || "").trim().toLowerCase();
}
