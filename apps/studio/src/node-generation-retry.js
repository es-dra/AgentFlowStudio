import { capturePreservedOutputs } from "./generation-status-policy.js";

export function shouldRetryFailedItemsOnly(node) {
  const policyStatus = String(node?.params?.generationPolicyStatus || "");
  return ["error", "partial", "cancelled"].includes(node?.status)
    || ["failed", "partially_complete", "needs_attention"].includes(policyStatus);
}

export function retryFailedItemsPlan(node) {
  const retrying = shouldRetryFailedItemsOnly(node);
  return {
    retrying,
    preserved: retrying ? capturePreservedOutputs(node) : null,
  };
}

export function appendPreservedOutput(node, preserved) {
  if (!preserved) return;
  node.params.preservedGenerationOutputs = [
    ...(Array.isArray(node.params.preservedGenerationOutputs) ? node.params.preservedGenerationOutputs : []),
    preserved,
  ].filter(Boolean).slice(-4);
}

export function retrySubmittingOptions(label) {
  return {
    label: "正在重试失败项",
    hint: "partial result / preserved outputs remain visible; retry targets failed items only.",
    percent: 8,
    clearPreview: false,
    retrying: true,
    fallbackLabel: label,
  };
}

export function retryResultText() {
  return "retrying\nRetrying failed items. Preserved outputs remain visible; provider quota may be used.";
}

export function isPartialTerminalResponse(response, preview) {
  const status = String(response?.job?.status || "");
  return status !== "succeeded"
    && !["submitted", "pending", "running"].includes(status)
    && Boolean(preview?.url || preview?.preview_url || Number(response?.safe_manifest?.output_count || 0) > 0);
}

export function nodeStatusFromTerminalResponse(status, partial) {
  if (status === "succeeded") return "complete";
  if (status === "cancelled_local_only") return "cancelled";
  if (["submitted", "pending", "running"].includes(status)) return "generating";
  return partial ? "partial" : "error";
}
