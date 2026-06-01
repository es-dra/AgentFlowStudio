import { normalizeWorkspace, parseFiles } from "./artifact-workspace.js?v=m4-memory-canvas-tools";
import { buildDemoReadyChecklist } from "./memory-workbench-demo-checklist.js";
import { buildDemoEvidenceSummary } from "./memory-workbench-demo-summary.js";
import { buildMemoryFeedbackDraft } from "./memory-workbench-feedback.js";
import { memoryWorkbenchFixture } from "./memory-workbench-fixture.js";
import { buildCompanyKbFeedbackCandidatePacketView } from "./memory-workbench-company-kb-feedback.js";
import { buildMemoryArtifactInspector } from "./memory-workbench-inspector.js";
import { buildMemoryWorkbenchPackageView } from "./memory-workbench-package.js";
import { buildProductionMemoryLoopView } from "./memory-workbench-production-loop.js";
import { buildProductionMemorySessionReportView } from "./memory-workbench-production-session.js";
import { memoryWorkbenchSampleFiles } from "./memory-workbench-sample.js";

export function attachMemoryWorkbenchHandlers(elements, { onWorkspaceLoaded, setMode }) {
  elements.memorySampleBundle.addEventListener("click", async () => {
    const artifacts = await parseFiles(memoryWorkbenchSampleFiles());
    onWorkspaceLoaded(normalizeWorkspace(artifacts), "sample_bundle");
    setMode("memory");
  });
}

export function memorySourceForArtifacts(artifacts) {
  return artifacts.some((artifact) => artifact.artifactType.startsWith("agentflow_")) ? "selected_files" : "fixture";
}

export function buildMemoryWorkbenchView(workspace, source) {
  const packageView = buildMemoryWorkbenchPackageView(workspace, memoryWorkbenchFixture);
  const memoryView = buildProductionMemoryLoopView(workspace, packageView);
  const sessionView = buildProductionMemorySessionReportView(workspace, memoryView);
  const companyKbView = buildCompanyKbFeedbackCandidatePacketView(workspace, sessionView);
  companyKbView.source_status = memorySourceStatus(source, workspace);
  companyKbView.artifact_inspector = buildMemoryArtifactInspector(workspace, companyKbView.artifact_inspector);
  companyKbView.feedback_draft = buildMemoryFeedbackDraft(workspace);
  companyKbView.demo_summary = buildDemoEvidenceSummary(companyKbView);
  companyKbView.demo_checklist = buildDemoReadyChecklist(companyKbView);
  return companyKbView;
}

function memorySourceStatus(source, workspace) {
  const bundleCount = Array.isArray(workspace?.memoryBundle) ? workspace.memoryBundle.length : 0;
  if (source === "sample_bundle") {
    return {
      label: "Sample bundle",
      detail: `${bundleCount} embedded sanitized memory artifacts loaded in browser memory.`,
      status: "review ready",
    };
  }
  if (source === "selected_files" && bundleCount) {
    return {
      label: "Selected files",
      detail: `${bundleCount} explicit local memory artifacts selected by the operator.`,
      status: "review ready",
    };
  }
  return {
    label: "Fixture",
    detail: "Built-in static fixture only; select files or load the sample bundle for evidence-backed inspection.",
    status: "planned",
  };
}
