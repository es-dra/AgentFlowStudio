import { icon } from "./icons.js";
import { nodeStatusSummary, safePublicText } from "./generation-status-policy.js";

export function statusTokenForNode(node) {
  const summary = nodeStatusSummary(node);
  return summary.canonicalStatus || summary.displayStatus;
}

export function statusLineForNode(node) {
  const summary = nodeStatusSummary(node);
  return `${summary.displayLabel || summary.displayStatus} · ${summary.detail}`;
}

export function nextActionForNode(node) {
  return nodeStatusSummary(node).nextAction;
}

export function blockedReasonForNode(node) {
  return nodeStatusSummary(node).blockedReason;
}

export function generationStatusCard(node, options = {}) {
  const summary = nodeStatusSummary(node);
  const card = document.createElement("div");
  card.className = `generation-status-card ${summary.tone}${options.compact ? " compact" : ""}`;
  const head = document.createElement("div");
  head.className = "generation-status-card-head";
  head.innerHTML = [
    `<span>${icon(iconForTone(summary.tone), 12)}</span>`,
    `<strong>${escapeHtml(summary.displayLabel || summary.displayStatus)}</strong>`,
  ].join("");
  card.appendChild(head);
  card.appendChild(row("State", summary.detail));
  if (summary.blockedReason) card.appendChild(row("Blocked reason", summary.blockedReason));
  card.appendChild(row("Next action", summary.nextAction));
  if (summary.hasPartialOutput) card.appendChild(row("Preserved outputs", "partial result / preserved outputs remain visible"));
  if (options.refs !== false && summary.safeRefs.length) {
    const refs = document.createElement("div");
    refs.className = "generation-status-refs";
    for (const ref of summary.safeRefs) {
      const item = document.createElement("span");
      item.textContent = `${ref.label}: ${ref.value}`;
      refs.appendChild(item);
    }
    card.appendChild(refs);
  }
  return card;
}

function row(label, value) {
  const item = document.createElement("div");
  item.className = "generation-status-row";
  item.innerHTML = `<small>${escapeHtml(label)}</small><span>${escapeHtml(safePublicText(value, 180))}</span>`;
  return item;
}

function iconForTone(tone) {
  if (tone === "complete") return "check";
  if (tone === "failed") return "x";
  if (tone === "retrying") return "retry";
  if (tone === "waiting") return "clock";
  return "lock";
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}
