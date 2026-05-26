import { normalizeWorkspace, parseFiles } from "./artifact-workspace.js";
import { applyStaticCopy, collectAppElements } from "./app-elements.js";
import { attachFeedbackHandlers } from "./feedback-wiring.js";
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
import { initializeProductionMode, productionState, recordRunFeedbackCaptured, recordSupervisionIntent, renderProductionState } from "./production-mode.js";
import { renderLocalVideoPreview, revokeCurrentVideoUrl } from "./video-preview.js";

const state = {
  language: "zh",
  mode: "review",
  workspace: normalizeWorkspace([]),
};

const elements = collectAppElements();

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

elements.modeReview.addEventListener("click", () => setMode("review"));
elements.modeProduction.addEventListener("click", () => setMode("production"));
elements.supervisionActions.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-supervision]");
  if (!button) return;
  recordSupervisionIntent(button.dataset.supervision, elements, getCopy(state.language));
});

attachFeedbackHandlers(elements, {
  getCopyForLanguage: () => getCopy(state.language),
  productionState,
  onRunFeedbackCaptured: () => recordRunFeedbackCaptured(elements, getCopy(state.language)),
});

window.addEventListener("beforeunload", revokeCurrentVideoUrl);

initializeProductionMode(elements, getCopy(state.language));
render();

function setMode(mode) {
  state.mode = mode;
  render();
}

function render() {
  const copy = getCopy(state.language);
  document.documentElement.lang = state.language === "zh" ? "zh-CN" : "en";
  applyStaticCopy(copy, elements);
  renderMode();
  renderWorkspace(state.workspace, copy);
  renderProductionState(elements, copy, state.workspace);
}

function renderMode() {
  const production = state.mode === "production";
  elements.reviewWorkbench.hidden = production;
  elements.productionWorkbench.hidden = !production;
  elements.modeReview.classList.toggle("active", !production);
  elements.modeProduction.classList.toggle("active", production);
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
  renderReportTabs(workspace, copy);
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
  const report = selectedReport(workspace);
  elements.reportContent.textContent = report ? report.rawText : copy.emptyReport;
}

function renderReportTabs(workspace, copy) {
  const tabs = elements.reportTabs;
  if (!tabs) return;
  clearNode(tabs);
  if (workspace.reports.length <= 1) {
    tabs.hidden = true;
    return;
  }
  tabs.hidden = false;
  const currentReport = selectedReport(workspace);
  workspace.reports.forEach((report) => {
    const button = node("button", `report-tab${report === currentReport ? " active" : ""}`, report.fileName);
    button.type = "button";
    button.addEventListener("click", () => {
      for (const item of tabs.querySelectorAll(".report-tab")) item.classList.remove("active");
      button.classList.add("active");
      elements.reportContent.textContent = report.rawText || copy.emptyReport;
    });
    tabs.append(button);
  });
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

function selectedReport(workspace) {
  return workspace.reports.find((report) => report.fileName === "package_report.md") || workspace.reports[0];
}
