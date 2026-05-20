import { normalizeWorkspace, parseFiles } from "./artifact-workspace.js";
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
  reportContent: document.querySelector("#report-content"),
  overallStatus: document.querySelector("#overall-status"),
  statusLabel: document.querySelector("#overall-status-label"),
  statusValue: document.querySelector("#overall-status-value"),
  statArtifacts: document.querySelector("#stat-artifacts"),
  statKnown: document.querySelector("#stat-known"),
  statWarnings: document.querySelector("#stat-warnings"),
  statErrors: document.querySelector("#stat-errors"),
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
  renderReport(workspace, copy);
  renderOverallStatus(workspace, copy);
}

function renderStats(workspace, copy) {
  const known = workspace.artifacts.filter((artifact) => artifact.artifactClass === "known_contract").length;
  elements.statArtifacts.textContent = formatCount(workspace.artifacts.length, copy);
  elements.statKnown.textContent = formatCount(known, copy);
  elements.statWarnings.textContent = formatCount(workspace.warnings.length, copy);
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
      metaLine(
        `${copy.labels.summary}: ${
          artifact.participatesInSummary ? copy.summaryIncluded : copy.summaryExcluded
        }`,
      ),
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
    metricCard(
      copy.summaryCards.package,
      workspace.package?.packageId || copy.notLoaded,
      workspace.package?.manifestPath || copy.prompts.package,
    ),
    metricCard(
      copy.summaryCards.review,
      workspace.review?.deliveryStatus || copy.notLoaded,
      workspace.review?.qualityLevel || copy.prompts.review,
    ),
    metricCard(
      copy.summaryCards.delivery,
      workspace.readiness?.status || copy.notLoaded,
      readinessSummary(workspace.readiness, copy),
    ),
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

function renderReport(workspace, copy) {
  const report = workspace.reports[0];
  elements.reportContent.textContent = report ? report.rawText : copy.emptyReport;
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
