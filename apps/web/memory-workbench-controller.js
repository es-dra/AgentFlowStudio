import { buildCompanyKbFeedbackCandidatePacketView } from "./memory-workbench-company-kb-feedback.js";
import { buildMemoryArtifactInspector } from "./memory-workbench-inspector.js";
import { buildProjectManifestView } from "./memory-workbench-project-manifest.js";
import { buildProductionMemoryAcceptanceFeedbackCandidateView } from "./memory-workbench-production-acceptance-feedback-candidate.js";
import { buildProductionMemoryAcceptanceFeedbackCandidatePromotionView } from "./memory-workbench-production-acceptance-feedback-candidate-promotion.js";
import { buildProductionMemoryAcceptanceFeedbackView } from "./memory-workbench-production-acceptance-feedback.js";
import { buildProductionMemoryAssetCockpitView } from "./memory-workbench-production-assets.js";
import { buildProductionMemoryLoopView } from "./memory-workbench-production-loop.js";
import { buildProductionMemoryNextContextHandoffView } from "./memory-workbench-production-next-context.js";
import { buildProductionMemoryNextOperatorActionResultView } from "./memory-workbench-production-next-operator-action-result.js";
import { buildProductionMemoryNextOperatorStartEventView } from "./memory-workbench-production-next-operator-start-event.js";
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

export function attachMemoryWorkbenchHandlers(_elements, _handlers) {
  // Sample-bundle loading was retired; keep the hook so app wiring stays stable.
}

export function memorySourceForArtifacts(artifacts) {
  return artifacts.some((artifact) => artifact.artifactType.startsWith("agentflow_")) ? "selected_files" : "fixture";
}

export function buildMemoryWorkbenchView(workspace, source) {
  const memoryView = buildProductionMemoryLoopView(workspace, emptyMemoryWorkbenchView());
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
  const nextOperatorStartEventView = buildProductionMemoryNextOperatorStartEventView(workspace, nextOperatorStartPacketView);
  const nextOperatorActionResultView = buildProductionMemoryNextOperatorActionResultView(workspace, nextOperatorStartEventView);
  const assetCockpitView = buildProductionMemoryAssetCockpitView(workspace, nextOperatorActionResultView);
  const projectManifestView = buildProjectManifestView(workspace, assetCockpitView);
  projectManifestView.source_status = memorySourceStatus(source, workspace);
  projectManifestView.artifact_inspector = buildMemoryArtifactInspector(workspace, projectManifestView.artifact_inspector);
  projectManifestView.feedback_draft = emptyFeedbackDraft();
  return projectManifestView;
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
    detail: "No embedded sample bundle. Select explicit local JSON artifacts for read-only inspection.",
    status: "planned",
  };
}

function emptyMemoryWorkbenchView() {
  return {
    state: "empty",
    project: {
      title: "No selected artifact",
      brief: "Select Project Manifest or Production Memory JSON to inspect the local runtime state.",
      format: "local JSON only",
      route: "read-only artifact viewer",
    },
    workflow_actions: [],
    assets: [],
    bundle_summary: [],
    memory_loaded: [],
    lanes: [],
    protocol_summary: {
      title: "No runtime artifact loaded",
      status: "planned",
      controls: [],
      boundaries: [
        { label: "no provider call", status: "blocked", detail: "this view cannot start remote providers" },
        { label: "not acceptance", status: "blocked", detail: "runtime inspection is not human acceptance" },
        { label: "not durable memory", status: "blocked", detail: "selected JSON does not promote Company/COS memory" },
      ],
    },
    review: {
      storyboard_adherence: "not loaded",
      visual_consistency: "not loaded",
      boundary: "read-only selected JSON only",
    },
    feedback: {
      status: "planned",
      summary: "Feedback must be recorded by explicit deterministic CLI/runtime artifacts.",
    },
    next_pass: {
      status: "planned",
      action: "select_project_manifest_or_production_memory_artifact",
    },
    timeline: [],
    state_labels: ["empty", "review ready", "blocked"],
  };
}

function emptyFeedbackDraft() {
  return {
    title: "Feedback Draft Disabled",
    status: "blocked",
    detail: "Browser-generated feedback drafts were retired. Use explicit CLI/runtime feedback artifacts.",
    json_text: "",
    copy_enabled: false,
  };
}
