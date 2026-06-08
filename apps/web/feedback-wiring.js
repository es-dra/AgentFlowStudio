import { buildFeedbackEvent, copyFeedbackText, formatFeedbackEvent } from "./feedback-event.js";

export function attachFeedbackHandlers(elements, { getCopyForLanguage }) {
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
}
