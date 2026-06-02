import { normalizeWorkspace, parseFiles } from "./artifact-workspace.js?v=m4-memory-canvas-tools";
import { buildDemoReadyChecklist } from "./memory-workbench-demo-checklist.js";
import { buildDemoEvidenceSummary } from "./memory-workbench-demo-summary.js";
import { buildMemoryFeedbackDraft } from "./memory-workbench-feedback.js";
import { memoryWorkbenchFixture } from "./memory-workbench-fixture.js";
import { buildCompanyKbFeedbackCandidatePacketView } from "./memory-workbench-company-kb-feedback.js";
import { buildMemoryArtifactInspector } from "./memory-workbench-inspector.js";
import { buildMemoryWorkbenchPackageView } from "./memory-workbench-package.js";
import { buildProductionMemoryAcceptanceFeedbackCandidateView } from "./memory-workbench-production-acceptance-feedback-candidate.js";
import { buildProductionMemoryAcceptanceFeedbackCandidatePromotionView } from "./memory-workbench-production-acceptance-feedback-candidate-promotion.js";
import { buildProductionMemoryAcceptanceFeedbackView } from "./memory-workbench-production-acceptance-feedback.js";
import { buildProductionMemoryLoopView } from "./memory-workbench-production-loop.js";
import { buildProductionMemoryNextContextHandoffView } from "./memory-workbench-production-next-context.js";
import { buildProductionMemoryNextOperatorStartPacketView } from "./memory-workbench-production-next-operator-start.js";
import { buildProductionMemoryNextPassPromotionView } from "./memory-workbench-production-next-pass-promotion.js";
import { buildProductionMemoryNextPassResultView } from "./memory-workbench-production-next-pass-result.js";
import { buildProductionMemoryNextPassReviewView } from "./memory-workbench-production-next-pass-review.js";
import { buildProductionMemoryNextTaskPacketView } from "./memory-workbench-production-next-task.js";
import { buildProductionMemoryOperatorFeedbackCandidateView } from "./memory-workbench-production-operator-feedback-candidate.js";
import { buildProductionMemoryOperatorFeedbackView } from "./memory-workbench-production-operator-feedback.js";
import { buildProductionMemoryOperatorHandoffView } from "./memory-workbench-production-operator-handoff.js";
import { buildProductionMemoryOperatorLoopView } from "./memory-workbench-production-operator-loop.js";
import { buildProductionMemoryOperatorManifestCheckView } from "./memory-workbench-production-operator-manifest-check.js";
import { buildProductionMemoryOperatorRunPackageCheckView } from "./memory-workbench-production-operator-run-package-check.js";
import { buildProductionMemoryOperatorRunPackageView } from "./memory-workbench-production-operator-run-package.js";
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
  const nextPassResultView = buildProductionMemoryNextPassResultView(workspace, nextTaskView);
  const nextPassReviewView = buildProductionMemoryNextPassReviewView(workspace, nextPassResultView);
  const nextPassPromotionView = buildProductionMemoryNextPassPromotionView(workspace, nextPassReviewView);
  const operatorFeedbackView = buildProductionMemoryOperatorFeedbackView(workspace, nextPassPromotionView);
  const operatorFeedbackCandidateView = buildProductionMemoryOperatorFeedbackCandidateView(workspace, operatorFeedbackView);
  const operatorManifestCheckView = buildProductionMemoryOperatorManifestCheckView(workspace, operatorFeedbackCandidateView);
  const operatorHandoffView = buildProductionMemoryOperatorHandoffView(workspace, operatorManifestCheckView);
  const operatorRunPackageView = buildProductionMemoryOperatorRunPackageView(workspace, operatorHandoffView);
  const operatorRunPackageCheckView = buildProductionMemoryOperatorRunPackageCheckView(workspace, operatorRunPackageView);
  const acceptanceFeedbackView = buildProductionMemoryAcceptanceFeedbackView(workspace, operatorRunPackageCheckView);
  const acceptanceFeedbackCandidateView = buildProductionMemoryAcceptanceFeedbackCandidateView(workspace, acceptanceFeedbackView);
  const acceptanceFeedbackCandidatePromotionView = buildProductionMemoryAcceptanceFeedbackCandidatePromotionView(workspace, acceptanceFeedbackCandidateView);
  const nextOperatorStartPacketView = buildProductionMemoryNextOperatorStartPacketView(workspace, acceptanceFeedbackCandidatePromotionView);
  nextOperatorStartPacketView.source_status = memorySourceStatus(source, workspace);
  nextOperatorStartPacketView.artifact_inspector = buildMemoryArtifactInspector(workspace, nextOperatorStartPacketView.artifact_inspector);
  nextOperatorStartPacketView.feedback_draft = buildMemoryFeedbackDraft(workspace);
  nextOperatorStartPacketView.demo_summary = buildDemoEvidenceSummary(nextOperatorStartPacketView);
  nextOperatorStartPacketView.demo_checklist = buildDemoReadyChecklist(nextOperatorStartPacketView);
  return nextOperatorStartPacketView;
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
