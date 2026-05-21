import { normalizeWorkspace, parseFiles } from "./artifact-workspace.js";
import { buildFeedbackEvent, copyFeedbackText, formatFeedbackEvent } from "./feedback-event.js";
import {
  clearNode,
  formatCount,
  metaLine,
  metricCard,
  node,
  row,
  sectionBlock,
  statusPill,
  wideBlock,
} from "./render-helpers.js";
import { getCopy } from "./ui-copy.js";
import { renderLocalVideoPreview, revokeCurrentVideoUrl } from "./video-preview.js";

const state = {
  language: "zh",
  workspace: normalizeWorkspace([]),
};

const elements = {
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
};

elements.fileInput.addEventListener("change", async (event) => {
  const files = Array.from(event.target.files || []);
  const artifacts = await parseFiles(files);
  state.workspace = normalizeWorkspace(artifacts);
  render();
});

elements.languageToggle.addEventListener("click", () => {
  state.language = state.language === "zh" ? "en" : "zh";
  render();
});

elements.feedbackCopy.addEventListener("click", async () => {
  const copy = getCopy(state.language);
  const event = buildFeedbackEvent({
    artifactFile: elements.feedbackArtifact.value,
    decision: elements.feedbackDecision.value,
    riskCategory: elements.feedbackRisk.value,
    note: elements.feedbackNote.value,
    videoTimeSec: elements.feedbackTime.value,
  });
  await copyFeedbackText(formatFeedbackEvent(event), elements.feedbackOutput, elements.feedbackStatus, copy);
});

window.addEventListener("beforeunload", revokeCurrentVideoUrl);

render();

function render() {
  const copy = getCopy(state.language);
  document.documentElement.lang = state.language === "zh" ? "zh-CN" : "en";
  renderStaticCopy(copy);
  renderWorkspace(state.workspace, copy);
}

function renderStaticCopy(copy) {
  for (const [key, value] of Object.entries(copy.staticText)) {
    const target = document.querySelector(`[data-copy="${key}"]`);
    if (target) target.textContent = value;
  }
  elements.languageToggle.textContent = copy.languageToggle;
  elements.fileInput.setAttribute("aria-label", copy.fileInputLabel);
}

function renderWorkspace(workspace, copy) {
  renderStats(workspace, copy);
  renderInventory(workspace, copy);
  renderSummary(workspace, copy);
  renderInspector(workspace, copy);
  renderEvidenceMap(workspace, copy);
  renderRiskLedger(workspace, copy);
  renderAssetLedger(workspace, copy);
  renderVideoPreview(workspace, copy);
  renderReport(workspace, copy);
  renderFeedbackArtifacts(workspace, copy);
  renderOverallStatus(workspace, copy);
}

function renderStats(workspace, copy) {
  const known = workspace.artifacts.filter((artifact) => artifact.artifactClass === "known_contract").length;
  const riskCount = workspace.riskLedger.length || workspace.warnings.length;
  elements.statArtifacts.textContent = formatCount(workspace.artifacts.length, copy);
  elements.statKnown.textContent = formatCount(known, copy);
  elements.statWarnings.textContent = formatCount(riskCount, copy);
  elements.statErrors.textContent = formatCount(workspace.errors.length, copy);
}

function renderInventory(workspace, copy) {
  elements.artifactCount.textContent = String(workspace.artifacts.length);
  clearNode(elements.inventoryList);
  if (!workspace.artifacts.length) {
    elements.inventoryList.textContent = copy.emptyInventory;
    return;
  }
  for (const artifact of workspace.artifacts) {
    const item = node("article", "item");
    item.append(
      row(artifact.fileName, statusPill(artifact.parseStatus, copy)),
      metaLine(`${copy.labels.type}: ${artifact.artifactType}`),
      metaLine(`${copy.labels.class}: ${artifact.artifactClass}`),
      metaLine(`${copy.labels.schema}: ${artifact.schemaVersion} | ${artifact.schemaStatus}`),
      metaLine(`${copy.labels.role}: ${artifact.sourceRole}`),
      metaLine(`${copy.labels.summary}: ${artifact.participatesInSummary ? copy.summaryIncluded : copy.summaryExcluded}`),
    );
    for (const warning of artifact.schemaWarnings) {
      item.append(metaLine(`${copy.labels.warning}: ${warning}`));
    }
    elements.inventoryList.append(item);
  }
}

function renderSummary(workspace, copy) {
  clearNode(elements.summaryContent);
  const cards = [
    metricCard(copy.summaryCards.run, workspace.run?.runId || copy.notLoaded, workspace.run?.workflow || copy.prompts.run),
    metricCard(copy.summaryCards.package, workspace.package?.packageId || copy.notLoaded, workspace.package?.manifestPath || copy.prompts.package),
    metricCard(copy.summaryCards.review, workspace.review?.deliveryStatus || copy.notLoaded, workspace.review?.qualityLevel || copy.prompts.review),
    metricCard(copy.summaryCards.delivery, workspace.readiness?.status || copy.notLoaded, readinessSummary(workspace.readiness, copy)),
  ];
  elements.summaryContent.append(...cards);
  if (workspace.package?.assets?.length) {
    elements.summaryContent.append(wideBlock(copy.assetsTitle, workspace.package.assets.map((asset) => renderAssetRow(asset, copy))));
  }
  if (workspace.errors.length || workspace.warnings.length) {
    elements.summaryContent.append(wideBlock(copy.loadNotesTitle, [...workspace.errors, ...workspace.warnings].map((text) => metaLine(text))));
  }
}

function renderInspector(workspace, copy) {
  clearNode(elements.inspectorContent);
  if (!workspace.quality && !workspace.review && !workspace.readiness) {
    elements.inspectorContent.textContent = copy.emptyInspector;
    return;
  }
  if (workspace.quality) {
    elements.inspectorContent.append(sectionBlock(copy.qualityTitle, workspace.quality.status, [
      ...workspace.quality.checks.map((check) => renderCheckRow(check, copy)),
      ...workspace.quality.errors.map((text) => metaLine(`${copy.labels.error}: ${text}`)),
      ...workspace.quality.warnings.map((text) => metaLine(`${copy.labels.warning}: ${text}`)),
    ], copy));
  }
  if (workspace.review) {
    const sectionNodes = workspace.review.sections.flatMap((section) => [
      metaLine(`${section.name}: ${section.status}`),
      ...section.checks.slice(0, 12).map((check) => renderCheckRow(check, copy)),
    ]);
    elements.inspectorContent.append(sectionBlock(copy.reviewTitle, workspace.review.status, [
      ...sectionNodes,
      ...workspace.review.recommendations.map((text) => metaLine(`${copy.labels.recommendation}: ${text}`)),
    ], copy));
  }
  if (workspace.readiness) {
    elements.inspectorContent.append(
      sectionBlock(copy.readinessTitle, workspace.readiness.status, workspace.readiness.runs.map((run) => renderReadinessRun(run, copy)), copy),
    );
  }
}

function renderEvidenceMap(workspace, copy) {
  clearNode(elements.evidenceMapContent);
  if (!workspace.evidenceMap.length) {
    elements.evidenceMapContent.textContent = copy.emptyEvidenceMap;
    return;
  }
  for (const item of workspace.evidenceMap.slice(0, 18)) {
    elements.evidenceMapContent.append(
      row(`${item.artifactType} -> ${item.fileName}`, statusPill(item.status, copy)),
      metaLine(`${item.relation} | ${item.sourceRole}`),
    );
  }
}

function renderRiskLedger(workspace, copy) {
  clearNode(elements.riskLedgerContent);
  if (!workspace.riskLedger.length) {
    elements.riskLedgerContent.textContent = copy.emptyRiskLedger;
    return;
  }
  for (const risk of workspace.riskLedger.slice(0, 16)) {
    elements.riskLedgerContent.append(row(`${risk.source}: ${risk.message}`, statusPill(risk.severity, copy)));
  }
}

function renderAssetLedger(workspace, copy) {
  clearNode(elements.assetLedgerContent);
  if (!workspace.assetLedger.length) {
    elements.assetLedgerContent.textContent = copy.emptyAssetLedger;
    return;
  }
  for (const asset of workspace.assetLedger.slice(0, 16)) {
    elements.assetLedgerContent.append(metricCard(asset.role, asset.path || copy.notLoaded, `${asset.source}${asset.detail ? ` | ${asset.detail}` : ""}`));
  }
}

function renderVideoPreview(workspace, copy) {
  renderLocalVideoPreview(elements.videoPreviewContent, workspace.videos[0], copy);
}

function renderReport(workspace, copy) {
  const report = workspace.reports[0];
  elements.reportContent.textContent = report ? report.rawText : copy.emptyReport;
}

function renderFeedbackArtifacts(workspace, copy) {
  const previous = elements.feedbackArtifact.value;
  clearNode(elements.feedbackArtifact);
  elements.feedbackArtifact.append(node("option", "", copy.feedbackNoArtifact));
  for (const artifact of workspace.artifacts) {
    const option = node("option", "", artifact.fileName);
    option.value = artifact.fileName;
    elements.feedbackArtifact.append(option);
  }
  elements.feedbackArtifact.value = [...elements.feedbackArtifact.options].some((option) => option.value === previous) ? previous : "";
}

function renderOverallStatus(workspace, copy) {
  const status =
    workspace.readiness?.status ||
    workspace.review?.deliveryStatus ||
    workspace.quality?.status ||
    workspace.package?.status ||
    workspace.run?.status ||
    "unknown";
  elements.overallStatus.className = `status-card status-${status}`;
  elements.statusLabel.textContent = copy.overallLabel;
  elements.statusValue.textContent = copy.statusLabels[status] || `${copy.statusLabels.unknown}`;
}

function renderAssetRow(asset, copy) {
  return row(`${asset.role}: ${asset.path}`, statusPill(asset.exists ? "pass" : asset.required ? "missing" : "optional", copy));
}

function renderCheckRow(check, copy) {
  return row(String(check.id || check.name || check.message || "check"), statusPill(check.status, copy));
}

function renderReadinessRun(run, copy) {
  const detail = `${run.runId} | ${run.mode} | ${copy.labels.failures} ${run.failures.length} | ${copy.labels.warnings} ${run.warnings.length}`;
  return row(detail, statusPill(run.status, copy));
}

function readinessSummary(readiness, copy) {
  if (!readiness) return copy.prompts.readiness;
  const summary = readiness.summary || {};
  return `${summary.total_runs ?? readiness.runs.length} ${copy.labels.runs}, ${summary.failed ?? 0} ${copy.labels.failed}, ${
    summary.warning ?? 0
  } ${copy.labels.warning}`;
}
