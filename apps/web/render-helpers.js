import { asText, normalizeStatus } from "./artifact-values.js";

export function statusPill(status, copy) {
  const normalized = normalizeStatus(status);
  return node("span", `status-pill status-${normalized}`, copy.statusLabels[normalized] || normalized);
}

export function sectionBlock(title, status, children, copy) {
  const block = node("section", "stack");
  block.append(row(title, statusPill(status, copy)), ...(children.length ? children : [metaLine(copy.noDetails)]));
  return block;
}

export function metricCard(label, value, detail) {
  const card = node("article", "metric");
  card.append(node("span", "", label), node("strong", "", asText(value, "")), metaLine(detail));
  return card;
}

export function wideBlock(title, children) {
  const block = node("article", "metric metric-wide");
  block.append(node("span", "", title), ...children);
  return block;
}

export function row(left, rightNode) {
  const item = node("div", "check-row");
  item.append(node("strong", "", left), rightNode);
  return item;
}

export function metaLine(text) {
  return node("p", "meta", text);
}

export function clearNode(element) {
  element.replaceChildren();
}

export function node(tagName, className = "", text = "") {
  const element = document.createElement(tagName);
  if (className) element.className = className;
  if (text) element.textContent = text;
  return element;
}

export function formatCount(value, copy) {
  return copy.countUnit ? `${value} ${copy.countUnit}` : String(value);
}
