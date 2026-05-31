import { clearNode, metaLine, node, row, statusPill } from "./render-helpers.js";

export function renderDemoEvidenceSummary(elements, summary, copy) {
  if (!elements.memoryDemoSummary) return;
  clearNode(elements.memoryDemoSummary);
  const header = node("article", "memory-demo-card memory-demo-card-hero");
  header.append(row(summary.title || "Demo Evidence Summary", statusPill(summary.status || "planned", copy)));
  for (const line of summary.talk_track || []) {
    header.append(metaLine(line));
  }
  elements.memoryDemoSummary.append(header);

  for (const card of summary.evidence_cards || []) {
    elements.memoryDemoSummary.append(summaryCard(card, copy));
  }
  for (const card of summary.comparison || []) {
    elements.memoryDemoSummary.append(summaryCard(card, copy, "comparison"));
  }
  for (const card of summary.non_claims || []) {
    elements.memoryDemoSummary.append(summaryCard(card, copy, "non-claim"));
  }
}

function summaryCard(card, copy, modifier = "") {
  const className = ["memory-demo-card", modifier && `memory-demo-${modifier}`].filter(Boolean).join(" ");
  const item = node("article", className);
  item.append(row(card.label, statusPill(card.status, copy)), metaLine(card.detail));
  return item;
}
