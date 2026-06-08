export function collectAppElements() {
  return {
    fileInput: document.querySelector("#artifact-files"),
    languageToggle: document.querySelector("#language-toggle"),
    artifactCount: document.querySelector("#artifact-count"),
    inventoryList: document.querySelector("#inventory-list"),
    summaryContent: document.querySelector("#summary-content"),
    inspectorContent: document.querySelector("#inspector-content"),
    evidenceMapContent: document.querySelector("#evidence-map-content"),
    riskLedgerContent: document.querySelector("#risk-ledger-content"),
    assetLedgerContent: document.querySelector("#asset-ledger-content"),
    videoPreviewContent: document.querySelector("#video-preview-content"),
    reportContent: document.querySelector("#report-content"),
    reportTabs: document.querySelector("#report-tabs"),
    overallStatus: document.querySelector("#overall-status"),
    statusLabel: document.querySelector("#overall-status-label"),
    statusValue: document.querySelector("#overall-status-value"),
    statArtifacts: document.querySelector("#stat-artifacts"),
    statKnown: document.querySelector("#stat-known"),
    statWarnings: document.querySelector("#stat-warnings"),
    statErrors: document.querySelector("#stat-errors"),
    feedbackArtifact: document.querySelector("#feedback-artifact"),
    feedbackDecision: document.querySelector("#feedback-decision"),
    feedbackRisk: document.querySelector("#feedback-risk"),
    feedbackTime: document.querySelector("#feedback-time"),
    feedbackNote: document.querySelector("#feedback-note"),
    feedbackOutput: document.querySelector("#feedback-output"),
    feedbackStatus: document.querySelector("#feedback-status"),
    feedbackCopy: document.querySelector("#feedback-copy"),
    modeReview: document.querySelector("#mode-review"),
    modeMemory: document.querySelector("#mode-memory"),
    reviewWorkbench: document.querySelector("#review-workbench"),
    memoryWorkbench: document.querySelector("#memory-workbench"),
    memoryStudioStatus: document.querySelector(".memory-studio-status"),
    memorySourceStatus: document.querySelector("#memory-source-status"),
    memoryProjectSummary: document.querySelector("#memory-project-summary"),
    memoryBundleSummary: document.querySelector("#memory-bundle-summary"),
    memoryArtifactInspector: document.querySelector("#memory-artifact-inspector"),
    memoryFeedbackPreview: document.querySelector("#memory-feedback-preview"),
    memoryFeedbackCopy: document.querySelector("#memory-feedback-copy"),
    memoryFeedbackOutput: document.querySelector("#memory-feedback-output"),
    memoryFeedbackStatus: document.querySelector("#memory-feedback-status"),
    memoryFocusSummary: document.querySelector("#memory-focus-summary"),
    memoryToolbar: document.querySelector(".memory-toolbar"),
    memoryViewButtons: document.querySelectorAll("[data-memory-view]"),
    memoryOperatorDock: document.querySelector("#memory-operator-dock"),
    memoryActionStrip: document.querySelector("#memory-action-strip"),
    memoryAssetSummary: document.querySelector("#memory-asset-summary"),
    memoryStateStrip: document.querySelector("#memory-state-strip"),
    memoryCanvasStage: document.querySelector("#memory-canvas-stage"),
    memoryProtocolSummary: document.querySelector("#memory-protocol-summary"),
    memoryLaneGrid: document.querySelector("#memory-lane-grid"),
    memoryRunTimeline: document.querySelector("#memory-run-timeline"),
    memoryProvenancePanel: document.querySelector("#memory-provenance-panel"),
  };
}

export function applyStaticCopy(copy, elements) {
  for (const [key, value] of Object.entries(copy.staticText)) {
    const target = document.querySelector(`[data-copy="${key}"]`);
    if (target) target.textContent = value;
  }
  elements.languageToggle.textContent = copy.languageToggle;
  elements.fileInput.setAttribute("aria-label", copy.fileInputLabel);
}
