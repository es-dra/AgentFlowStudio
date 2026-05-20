import { asText, normalizeStatus, normalizeWorkspace, parseFiles } from "./artifact-workspace.js";

const state = normalizeWorkspace([]);

const elements = {
  fileInput: document.querySelector("#artifact-files"),
  artifactCount: document.querySelector("#artifact-count"),
  inventoryList: document.querySelector("#inventory-list"),
  summaryContent: document.querySelector("#summary-content"),
  inspectorContent: document.querySelector("#inspector-content"),
  reportContent: document.querySelector("#report-content"),
  overallStatus: document.querySelector("#overall-status"),
};

elements.fileInput.addEventListener("change", async (event) => {
  const files = Array.from(event.target.files || []);
  const artifacts = await parseFiles(files);
  const workspace = normalizeWorkspace(artifacts);
  Object.assign(state, workspace);
  renderWorkspace(state);
});

renderWorkspace(state);

function renderWorkspace(workspace) {
  renderInventory(workspace);
  renderSummary(workspace);
  renderInspector(workspace);
  renderReport(workspace);
  renderOverallStatus(workspace);
}

function renderInventory(workspace) {
  elements.artifactCount.textContent = String(workspace.artifacts.length);
  clearNode(elements.inventoryList);
  if (!workspace.artifacts.length) {
    elements.inventoryList.textContent = "Select local artifacts to build a read-only inspection view.";
    return;
  }
  for (const artifact of workspace.artifacts) {
    const item = node("article", "item");
    item.append(
      row(artifact.fileName, statusPill(artifact.parseStatus)),
      metaLine(`type: ${artifact.artifactType}`),
      metaLine(`class: ${artifact.artifactClass}`),
      metaLine(`schema: ${artifact.schemaVersion} | ${artifact.schemaStatus}`),
      metaLine(`role: ${artifact.sourceRole}`),
      metaLine(`summary: ${artifact.participatesInSummary ? "included" : "not included"}`),
    );
    for (const warning of artifact.schemaWarnings) {
      item.append(metaLine(`warning: ${warning}`));
    }
    elements.inventoryList.append(item);
  }
}

function renderSummary(workspace) {
  clearNode(elements.summaryContent);
  const cards = [
    metric("Run", workspace.run?.runId || "not loaded", workspace.run?.workflow || "Select run_manifest.json"),
    metric("Package", workspace.package?.packageId || "not loaded", workspace.package?.manifestPath || "Select package manifest"),
    metric("Review", workspace.review?.deliveryStatus || "not loaded", workspace.review?.qualityLevel || "Select review_report.json"),
    metric("Delivery", workspace.readiness?.status || "not loaded", readinessSummary(workspace.readiness)),
  ];
  elements.summaryContent.append(...cards);
  if (workspace.package?.assets?.length) {
    elements.summaryContent.append(wideBlock("Assets", workspace.package.assets.map(renderAssetRow)));
  }
  if (workspace.errors.length || workspace.warnings.length) {
    elements.summaryContent.append(wideBlock("Load Notes", [...workspace.errors, ...workspace.warnings].map((text) => metaLine(text))));
  }
}

function renderInspector(workspace) {
  clearNode(elements.inspectorContent);
  if (!workspace.quality && !workspace.review && !workspace.readiness) {
    elements.inspectorContent.textContent = "Select quality, review, or delivery readiness artifacts to inspect checks.";
    return;
  }
  if (workspace.quality) {
    elements.inspectorContent.append(sectionBlock("Quality Report", workspace.quality.status, [
      ...workspace.quality.checks.map(renderCheckRow),
      ...workspace.quality.errors.map((text) => metaLine(`error: ${text}`)),
      ...workspace.quality.warnings.map((text) => metaLine(`warning: ${text}`)),
    ]));
  }
  if (workspace.review) {
    const sectionNodes = workspace.review.sections.flatMap((section) => [
      metaLine(`${section.name}: ${section.status}`),
      ...section.checks.slice(0, 12).map(renderCheckRow),
    ]);
    elements.inspectorContent.append(sectionBlock("Review Report", workspace.review.status, [
      ...sectionNodes,
      ...workspace.review.recommendations.map((text) => metaLine(`recommendation: ${text}`)),
    ]));
  }
  if (workspace.readiness) {
    elements.inspectorContent.append(sectionBlock("Delivery Readiness", workspace.readiness.status, workspace.readiness.runs.map(renderReadinessRun)));
  }
}

function renderReport(workspace) {
  const report = workspace.reports[0];
  if (!report) {
    elements.reportContent.textContent = "Markdown reports are displayed as escaped text. Select `package_report.md` or `delivery_readiness.md`.";
    return;
  }
  elements.reportContent.textContent = report.rawText;
}

function renderOverallStatus(workspace) {
  const status = normalizeStatus(
    workspace.readiness?.status || workspace.review?.deliveryStatus || workspace.quality?.status || workspace.package?.status || workspace.run?.status,
  );
  elements.overallStatus.className = `status-card status-${status}`;
  elements.overallStatus.querySelector("strong").textContent = status;
}

function metric(label, value, detail) {
  const card = node("article", "metric");
  card.append(node("span", "", label), node("strong", "", value), metaLine(detail));
  return card;
}

function wideBlock(title, children) {
  const block = node("article", "metric");
  block.style.gridColumn = "1 / -1";
  block.append(node("span", "", title), ...children);
  return block;
}

function sectionBlock(title, status, children) {
  const block = node("section", "stack");
  block.append(row(title, statusPill(status)), ...(children.length ? children : [metaLine("No detailed checks found.")]));
  return block;
}

function renderAssetRow(asset) {
  return row(`${asset.role}: ${asset.path}`, statusPill(asset.exists ? "pass" : asset.required ? "missing" : "optional"));
}

function renderCheckRow(check) {
  return row(asText(check.id || check.name || check.message, "check"), statusPill(normalizeStatus(check.status)));
}

function renderReadinessRun(run) {
  const detail = `${run.runId} | ${run.mode} | failures ${run.failures.length} | warnings ${run.warnings.length}`;
  return row(detail, statusPill(run.status));
}

function readinessSummary(readiness) {
  if (!readiness) return "Select delivery_readiness.json";
  const summary = readiness.summary || {};
  return `${summary.total_runs ?? readiness.runs.length} runs, ${summary.failed ?? 0} failed, ${summary.warning ?? 0} warning`;
}

function statusPill(status) {
  return node("span", `status-pill status-${normalizeStatus(status)}`, normalizeStatus(status));
}

function row(left, rightNode) {
  const item = node("div", "check-row");
  item.append(node("strong", "", left), rightNode);
  return item;
}

function metaLine(text) {
  return node("p", "meta", text);
}

function clearNode(element) {
  element.replaceChildren();
}

function node(tagName, className = "", text = "") {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  if (text) element.textContent = text;
  return element;
}
