import { buildFeedbackEvent, buildRunFeedbackEvent, copyFeedbackText, formatFeedbackEvent } from "./feedback-event.js";

export function attachFeedbackHandlers(elements, { getCopyForLanguage, productionState, onRunFeedbackCaptured }) {
  elements.feedbackCopy.addEventListener("click", async () => {
    const copy = getCopyForLanguage();
    const event = buildFeedbackEvent({
      artifactFile: elements.feedbackArtifact.value,
      decision: elements.feedbackDecision.value,
      riskCategory: elements.feedbackRisk.value,
      note: elements.feedbackNote.value,
      videoTimeSec: elements.feedbackTime.value,
    });
    await copyFeedbackText(formatFeedbackEvent(event), elements.feedbackOutput, elements.feedbackStatus, copy);
  });

  elements.runFeedbackCopy.addEventListener("click", async () => {
    const copy = getCopyForLanguage();
    const selectedWorkflow = productionState.workflows.find((workflow) => workflow.path === productionState.selectedWorkflowPath);
    const event = buildRunFeedbackEvent({
      run: productionState.run,
      workflow: selectedWorkflow,
      review: productionState.review,
      decision: elements.runFeedbackDecision.value,
      riskCategory: elements.runFeedbackRisk.value,
      note: elements.runFeedbackNote.value,
      videoTimeSec: elements.runFeedbackTime.value,
    });
    await copyFeedbackText(formatFeedbackEvent(event), elements.runFeedbackOutput, elements.runFeedbackStatus, copy);
    if (onRunFeedbackCaptured) onRunFeedbackCaptured(event);
  });
}
