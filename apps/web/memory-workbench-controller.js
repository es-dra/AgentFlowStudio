import { normalizeWorkspace, parseFiles } from "./artifact-workspace.js?v=m4-memory-canvas-tools";
import { buildDemoReadyChecklist } from "./memory-workbench-demo-checklist.js";
import { buildDemoEvidenceSummary } from "./memory-workbench-demo-summary.js";
import { buildMemoryFeedbackDraft } from "./memory-workbench-feedback.js";
import { memoryWorkbenchFixture } from "./memory-workbench-fixture.js";
import { buildMemoryArtifactInspector } from "./memory-workbench-inspector.js";
import { buildLoulanWorkbenchPackageView } from "./memory-workbench-loulan-package.js";
import { buildMemoryWorkbenchPackageView } from "./memory-workbench-package.js";
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
  const memoryView = buildLoulanWorkbenchPackageView(
    workspace,
    buildMemoryWorkbenchPackageView(workspace, memoryWorkbenchFixture),
  );
  memoryView.source_status = memorySourceStatus(source, workspace);
  memoryView.artifact_inspector = buildMemoryArtifactInspector(workspace, memoryView.artifact_inspector);
  if (!workspace?.loulanPackage) {
    memoryView.feedback_draft = buildMemoryFeedbackDraft(workspace);
  }
  memoryView.demo_summary = buildDemoEvidenceSummary(memoryView);
  memoryView.demo_checklist = buildDemoReadyChecklist(memoryView);
  return memoryView;
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
