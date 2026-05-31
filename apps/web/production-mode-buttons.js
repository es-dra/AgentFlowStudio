export function renderProductionButtons(elements, run) {
  const running = ["pending", "running"].includes(run?.status || "");
  elements.runWorkflowButton.disabled = running;
  elements.createPlanButton.disabled = running;
  elements.refreshReviewButton.disabled = running;
}
