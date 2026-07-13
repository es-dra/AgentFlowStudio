import { productionDeliverySummary } from "./production-delivery-controller.js";

const SHA256_RE = /^[a-f0-9]{64}$/;
const SAFE_ID_RE = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$/;
const CHECKS = [
  ["story_intent_preserved", "故事意图已核对"],
  ["character_continuity_checked", "角色连续性已核对"],
  ["shot_coverage_checked", "镜头覆盖已核对"],
  ["revision_addressed", "本轮修订已核对"],
];

export function productionDeliveryView(node, candidates) {
  if (!Array.isArray(candidates) || candidates.length < 2) return null;
  const selection = selectionSummary(node);
  const delivery = productionDeliverySummary(node);
  const selectionIdentity = canonicalAuthorityTuple({
    run_id: selection.run_id,
    parent_job_id: selection.selected_parent_job_id,
    candidate_id: selection.selected_candidate_id,
    candidate_digest: selection.selected_candidate_digest,
    revision_id: selection.selected_revision_id,
    revision_digest: selection.selected_revision_digest,
  });
  const deliveryIdentity = canonicalAuthorityTuple({
    run_id: delivery.run_id,
    parent_job_id: delivery.parent_job_id,
    candidate_id: delivery.selected_candidate_id,
    candidate_digest: delivery.selected_candidate_digest,
    revision_id: delivery.selected_revision_id,
    revision_digest: delivery.selected_revision_digest,
  });
  const selected = Boolean(selectionIdentity);
  const exactDeliveryIdentity = authorityTuplesMatch(selectionIdentity, deliveryIdentity);
  const busy = exactDeliveryIdentity && ["quality_saving", "exporting", "refreshing"].includes(delivery.status);
  const exactApproval = exactDeliveryIdentity && delivery.quality_decision === "approve";

  const panel = document.createElement("section");
  panel.className = "production-delivery-panel";
  panel.dataset.busy = busy ? "true" : "false";
  panel.setAttribute("aria-busy", busy ? "true" : "false");
  panel.setAttribute("aria-label", "生产交付质量审批与精确导出");

  const head = document.createElement("div");
  head.className = "production-delivery-head";
  const heading = document.createElement("div");
  const title = document.createElement("strong");
  title.textContent = "生产交付";
  const scope = document.createElement("span");
  scope.className = "production-delivery-scope";
  scope.textContent = selected ? "已绑定精确候选与修订" : "等待候选选择";
  heading.append(title, scope);
  const refresh = document.createElement("button");
  refresh.type = "button";
  refresh.dataset.action = "production-delivery-refresh";
  refresh.textContent = "刷新门禁";
  refresh.disabled = busy || !selected;
  head.append(heading, refresh);
  panel.appendChild(head);

  panel.appendChild(identityView(selectionIdentity, delivery, exactDeliveryIdentity));

  const checklist = document.createElement("fieldset");
  checklist.className = "production-delivery-checklist";
  checklist.disabled = busy || !selected || exactApproval;
  const legend = document.createElement("legend");
  legend.textContent = exactApproval ? "质量门禁已通过" : "质量审批清单";
  checklist.appendChild(legend);
  for (const [name, label] of CHECKS) {
    const field = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.dataset.deliveryCheck = name;
    input.checked = exactApproval;
    const text = document.createElement("span");
    text.textContent = label;
    field.append(input, text);
    checklist.appendChild(field);
  }
  panel.appendChild(checklist);

  const actions = document.createElement("div");
  actions.className = "production-delivery-actions";
  const approve = document.createElement("button");
  approve.type = "button";
  approve.dataset.action = "production-quality-approve";
  approve.textContent = exactApproval ? "质量已批准" : "批准当前修订";
  approve.disabled = busy || !selected || exactApproval;
  const exportButton = document.createElement("button");
  exportButton.type = "button";
  exportButton.className = "production-export-action";
  exportButton.dataset.action = "production-export";
  exportButton.textContent = exactDeliveryIdentity && delivery.status === "exported" ? "再次读取精确导出" : "导出已批准修订";
  exportButton.disabled = busy || !exactApproval;
  actions.append(approve, exportButton);
  panel.appendChild(actions);

  const status = document.createElement("p");
  status.className = "production-delivery-status";
  status.dataset.productionDeliveryStatus = "true";
  status.dataset.state = (exactDeliveryIdentity && delivery.status) || (selected ? "ready" : "selection_required");
  status.setAttribute("aria-live", "polite");
  status.textContent = deliveryMessage(delivery, selected, exactDeliveryIdentity);
  panel.appendChild(status);

  const boundary = document.createElement("small");
  boundary.className = "production-delivery-boundary";
  boundary.textContent = "此处批准的是当前工作流质量门禁，不代表媒体质量、人类接受或商业验证。";
  panel.appendChild(boundary);
  return panel;
}

function identityView(selectionIdentity, delivery, exactDeliveryIdentity) {
  const summary = document.createElement("dl");
  summary.className = "production-delivery-identity";
  const fields = [
    ["Candidate", selectionIdentity?.candidate_id],
    ["Revision", selectionIdentity?.revision_id],
    ["Lineage job", selectionIdentity?.parent_job_id],
    ...(exactDeliveryIdentity ? [
      ["Quality review", delivery.quality_review_id],
      ["Export", delivery.last_export_id],
      ["SHA-256", delivery.delivery_sha256],
    ] : []),
  ].filter(([, value]) => String(value || "").trim());
  if (!fields.length) fields.push(["State", "先从上方候选中选择一个生产基线"]);
  for (const [label, value] of fields) {
    const term = document.createElement("dt");
    term.textContent = label;
    const detail = document.createElement("dd");
    detail.textContent = compact(value);
    detail.title = String(value);
    summary.append(term, detail);
  }
  return summary;
}

function deliveryMessage(delivery, selected, exactDeliveryIdentity) {
  if (exactDeliveryIdentity && delivery.message) return String(delivery.message);
  if (!selected) return "尚未选择可交付候选；审批与导出保持关闭。";
  return "当前候选和修订已绑定。完成四项检查后批准，再执行精确导出。";
}

function selectionSummary(node) {
  const value = node?.params?.creatorSelection;
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function canonicalAuthorityTuple(value) {
  const tuple = {
    run_id: canonicalIdentifier(value?.run_id),
    parent_job_id: canonicalIdentifier(value?.parent_job_id),
    candidate_id: canonicalIdentifier(value?.candidate_id),
    candidate_digest: canonicalDigest(value?.candidate_digest),
    revision_id: canonicalIdentifier(value?.revision_id),
    revision_digest: canonicalDigest(value?.revision_digest),
  };
  return Object.values(tuple).every(Boolean) ? tuple : null;
}

function authorityTuplesMatch(selection, delivery) {
  if (!selection || !delivery) return false;
  return selection.run_id === delivery.run_id
    && selection.parent_job_id === delivery.parent_job_id
    && selection.candidate_id === delivery.candidate_id
    && selection.candidate_digest === delivery.candidate_digest
    && selection.revision_id === delivery.revision_id
    && selection.revision_digest === delivery.revision_digest;
}

function canonicalIdentifier(value) {
  if (typeof value !== "string") return "";
  const identifier = value.trim();
  return SAFE_ID_RE.test(identifier) ? identifier : "";
}

function canonicalDigest(value) {
  if (typeof value !== "string") return "";
  const digest = value.trim().toLowerCase();
  return SHA256_RE.test(digest) ? digest : "";
}

function compact(value) {
  const text = String(value || "");
  return text.length > 38 ? `${text.slice(0, 20)}…${text.slice(-12)}` : text;
}
