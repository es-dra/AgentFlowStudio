import { clearNode, metaLine, node, row, statusPill } from "./render-helpers.js";

export function renderDemoReadyChecklist(elements, checklist, copy) {
  if (!elements.memoryDemoChecklist) return;
  clearNode(elements.memoryDemoChecklist);
  const header = node("article", "memory-checklist-card memory-checklist-header");
  header.append(row(checklist.title || "Demo-ready checklist", statusPill(checklist.status || "planned", copy)));
  if (checklist.summary) {
    header.append(
      metaLine(checklist.summary.headline),
      metaLine(
        `${checklist.summary.ready_count}/${checklist.summary.total_count} rehearsal gates ready; ${checklist.summary.gap_count} evidence gaps; ${checklist.summary.boundary_count} boundaries visible.`,
      ),
    );
  }
  elements.memoryDemoChecklist.append(header);

  if (Array.isArray(checklist.groups) && checklist.groups.length) {
    for (const group of checklist.groups) {
      const section = node("section", `memory-checklist-group ${group.id || ""}`);
      const groupHeader = node("div", "memory-checklist-group-heading");
      groupHeader.append(row(group.title, statusPill(group.status, copy)), metaLine(group.detail));
      section.append(groupHeader);
      const list = node("div", "memory-checklist-group-items");
      for (const item of group.items || []) {
        list.append(checklistCard(item, copy));
      }
      section.append(list);
      elements.memoryDemoChecklist.append(section);
    }
    return;
  }

  for (const item of checklist.items || []) {
    elements.memoryDemoChecklist.append(checklistCard(item, copy));
  }
}

function checklistCard(item, copy) {
  const card = node("article", "memory-checklist-card");
  card.append(row(item.label, statusPill(item.status, copy)), metaLine(item.detail));
  return card;
}
