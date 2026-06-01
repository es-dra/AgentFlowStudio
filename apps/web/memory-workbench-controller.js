import { normalizeWorkspace, parseFiles } from "./artifact-workspace.js?v=m4-memory-canvas-tools";
import { buildDemoReadyChecklist } from "./memory-workbench-demo-checklist.js";
import { buildDemoEvidenceSummary } from "./memory-workbench-demo-summary.js";
import { buildMemoryFeedbackDraft } from "./memory-workbench-feedback.js";
import { memoryWorkbenchFixture } from "./memory-workbench-fixture.js";
import { buildCompanyKbFeedbackCandidatePacketView } from "./memory-workbench-company-kb-feedback.js";
import { buildMemoryArtifactInspector } from "./memory-workbench-inspector.js";
import { buildMemoryWorkbenchPackageView } from "./memory-workbench-package.js";
import { buildProductionMemoryLoopView } from "./memory-workbench-production-loop.js";
import { buildProductionMemoryNextContextHandoffView } from "./memory-workbench-production-next-context.js";
import { buildProductionMemoryNextPassPromotionView } from "./memory-workbench-production-next-pass-promotion.js";
import { buildProductionMemoryNextPassReviewView } from "./memory-workbench-production-next-pass-review.js";
import { buildProductionMemoryNextTaskPacketView } from "./memory-workbench-production-next-task.js";
import { buildProductionMemoryOperatorFeedbackCandidateView } from "./memory-workbench-production-operator-feedback-candidate.js";
import { buildProductionMemoryOperatorFeedbackView } from "./memory-workbench-production-operator-feedback.js";
import { buildProductionMemoryOperatorLoopView } from "./memory-workbench-production-operator-loop.js";
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
  const operatorLoopView = buildProductionMemoryOperatorLoopView(workspace, companyKbView);
  const nextContextView = buildProductionMemoryNextContextHandoffView(workspace, operatorLoopView);
  const nextTaskView = buildProductionMemoryNextTaskPacketView(workspace, nextContextView);
  const nextPassReviewView = buildProductionMemoryNextPassReviewView(workspace, nextTaskView);
  const nextPassPromotionView = buildProductionMemoryNextPassPromotionView(workspace, nextPassReviewView);
  const operatorFeedbackView = buildProductionMemoryOperatorFeedbackView(workspace, nextPassPromotionView);
  const operatorFeedbackCandidateView = buildProductionMemoryOperatorFeedbackCandidateView(workspace, operatorFeedbackView);
  operatorFeedbackCandidateView.source_status = memorySourceStatus(source, workspace);
  operatorFeedbackCandidateView.artifact_inspector = buildMemoryArtifactInspector(workspace, operatorFeedbackCandidateView.artifact_inspector);
  operatorFeedbackCandidateView.feedback_draft = buildMemoryFeedbackDraft(workspace);
  operatorFeedbackCandidateView.demo_summary = buildDemoEvidenceSummary(operatorFeedbackCandidateView);
  operatorFeedbackCandidateView.demo_checklist = buildDemoReadyChecklist(operatorFeedbackCandidateView);
  return operatorFeedbackCandidateView;
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
