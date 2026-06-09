export function selectedCard(state) {
  if (!state.workbench) return null;
  return state.workbench.canvas_cards.find((card) => card.id === state.selectedCardId) || state.workbench.canvas_cards[0] || null;
}

export function selectedVariant(state) {
  const candidates = state.workbench?.review_room?.candidates || [];
  return candidates.find((candidate) => candidate.candidate_id === state.selectedVariantId) || candidates[0] || null;
}

export function latestJobId(state, action) {
  if (!state.workbench) return "";
  const events = state.workbench.events.filter((event) => event.action === action && event.job_id);
  return events.length ? events[events.length - 1].job_id : "";
}
