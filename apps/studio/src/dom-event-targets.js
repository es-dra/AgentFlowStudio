export function closestFromEvent(event, selector) {
  const targetMatch = event?.target instanceof Element ? event.target.closest(selector) : null;
  if (targetMatch) return targetMatch;
  for (const item of event?.composedPath?.() || []) {
    if (item instanceof Element) {
      const match = item.matches(selector) ? item : item.closest(selector);
      if (match) return match;
    }
  }
  const pointMatch = document.elementFromPoint?.(event.clientX, event.clientY);
  return pointMatch?.closest?.(selector) || null;
}
