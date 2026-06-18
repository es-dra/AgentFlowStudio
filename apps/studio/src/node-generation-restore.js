export function generationRestoreSnapshot(node) {
  return {
    status: node.status,
    result: node.result,
    previewUrl: node.previewUrl,
    jobProgress: node.params?.jobProgress ? { ...node.params.jobProgress } : null,
    terminalProgress: node.params?.terminalProgress ? { ...node.params.terminalProgress } : null,
    progressPercent: node.params?.progressPercent ?? null,
    candidatePreviewUrls: Array.isArray(node.params?.candidatePreviewUrls) ? [...node.params.candidatePreviewUrls] : null,
  };
}

export function restoreCancelledGeneration(store, nodeId, previous = null) {
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    if (previous) {
      n.status = previous.status || ((previous.previewUrl || previous.result) ? "complete" : "empty");
      n.result = previous.result || "";
      n.previewUrl = previous.previewUrl || null;
      n.params.jobProgress = previous.jobProgress || null;
      n.params.terminalProgress = previous.terminalProgress || null;
      n.params.progressPercent = previous.progressPercent;
      n.params.candidatePreviewUrls = previous.candidatePreviewUrls || [];
      return;
    }
    n.status = (n.previewUrl || n.result) ? "complete" : "empty";
    n.result = n.result || "";
  }, { history: false });
}

export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
