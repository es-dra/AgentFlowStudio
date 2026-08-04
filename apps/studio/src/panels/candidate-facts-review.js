/** Minimal candidate-fact review panel for Asset Bible workspace. */

const ENTITY_KIND_LABELS = Object.freeze({
  character: "人物",
  scene: "场景",
  script_profile: "剧本档案",
  script_format_profile: "格式",
  beat: "节拍",
});

const STATUS_LABELS = Object.freeze({
  extracted_from_text: "原文提取",
  model_inferred: "模型推断",
  missing: "缺失",
  conflicting: "存在冲突",
  human_confirmed: "人工确认",
});

const DECISION_LABELS = Object.freeze({
  pending: "待审",
  accepted: "已确认",
  edited_and_confirmed: "已改确认",
  rejected: "已拒绝",
});

export async function probeCandidateReviewAvailable(runtime) {
  if (!runtime?.getCandidateFactReview) return { available: false, review: null };
  try {
    const review = await runtime.getCandidateFactReview();
    return { available: true, review };
  } catch (error) {
    if (Number(error?.status || 0) === 404) return { available: false, review: null };
    // Other errors (network, 5xx): treat as unavailable for the gate, but keep message for UI if needed.
    return { available: false, review: null, error };
  }
}

export function candidateReviewBinding(review, fallback = {}) {
  const bundle = review?.bundle || {};
  const revisionId = String(
    bundle.source_revision_id
    || fallback.revision_id
    || fallback.source_revision_id
    || "",
  ).trim();
  const digest = String(
    bundle.source_revision_digest
    || fallback.source_digest
    || fallback.source_revision_digest
    || "",
  ).trim();
  return { revision_id: revisionId, source_digest: digest };
}

export function buildCandidateFactsReviewPanel({
  review = null,
  busy = false,
  error = "",
  onRefresh = null,
  onAction = null,
} = {}) {
  const panel = el("section", "candidate-review-panel");
  const head = el("div", "candidate-review-head");
  head.appendChild(el("strong", "", "剧本候选审阅"));
  head.appendChild(el("p", "", "确认提取出的人物、场景等事实后，才会进入权威事实层。"));
  const refresh = el("button", "studio-secondary-button", busy ? "处理中…" : "刷新候选");
  refresh.type = "button";
  refresh.disabled = busy || !onRefresh;
  refresh.addEventListener("click", () => {
    if (!busy && onRefresh) void onRefresh();
  });
  head.appendChild(refresh);
  panel.appendChild(head);

  if (error) {
    const err = el("div", "candidate-review-error");
    err.appendChild(el("p", "", error));
    panel.appendChild(err);
  }

  const items = Array.isArray(review?.bundle?.items) ? review.bundle.items : [];
  if (!items.length) {
    const empty = el("div", "candidate-review-empty");
    empty.appendChild(el("p", "", "还没有候选事实。先保存剧本修订，再点「刷新候选」。"));
    panel.appendChild(empty);
    return panel;
  }

  const list = el("div", "candidate-review-list");
  for (const item of items) {
    list.appendChild(buildRow(item, { busy, onAction }));
  }
  panel.appendChild(list);
  return panel;
}

function buildRow(item, { busy, onAction }) {
  const row = el("div", `candidate-review-row decision-${safeToken(item.review_decision || "pending")}`);
  const meta = el("div", "candidate-review-meta");
  meta.appendChild(el("span", "candidate-review-kind", entityKindLabel(item.entity_kind)));
  meta.appendChild(el("span", "candidate-review-status", statusLabel(item.status)));
  meta.appendChild(el("span", "candidate-review-decision", decisionLabel(item.review_decision)));
  meta.appendChild(el("span", "candidate-review-confidence", confidenceLabel(item.confidence)));
  if (item.field_path) meta.appendChild(el("span", "candidate-review-field", String(item.field_path)));
  row.appendChild(meta);

  const text = el("div", "candidate-review-text", String(item.text || "").trim() || "（空）");
  row.appendChild(text);

  const decision = String(item.review_decision || "pending");
  const allowed = new Set(
    Array.isArray(item.allowed_actions) ? item.allowed_actions.map((value) => String(value)) : [],
  );
  if (decision !== "pending" || !onAction) return row;

  const actions = el("div", "candidate-review-actions");
  if (allowed.has("accept")) {
    actions.appendChild(actionButton("确认", () => onAction("accept", item), busy, "studio-primary-button"));
  }
  if (allowed.has("reject")) {
    actions.appendChild(actionButton("拒绝", () => onAction("reject", item), busy, "studio-secondary-button"));
  }
  if (allowed.has("edit_confirm")) {
    const editWrap = el("div", "candidate-review-edit");
    const input = document.createElement("input");
    input.type = "text";
    input.className = "candidate-review-edit-input";
    input.value = String(item.text || "");
    input.maxLength = 2000;
    input.disabled = busy;
    input.setAttribute("aria-label", "改写后确认");
    const confirm = actionButton("改写确认", () => {
      onAction("edit_confirm", item, { new_text: input.value });
    }, busy, "studio-secondary-button");
    editWrap.append(input, confirm);
    actions.appendChild(editWrap);
  }
  row.appendChild(actions);
  return row;
}

function actionButton(label, onClick, busy, className) {
  const button = el("button", className || "studio-secondary-button", label);
  button.type = "button";
  button.disabled = busy;
  button.addEventListener("click", () => {
    if (!busy) void onClick();
  });
  return button;
}

function entityKindLabel(value) {
  return ENTITY_KIND_LABELS[String(value || "")] || String(value || "未知");
}

function statusLabel(value) {
  return STATUS_LABELS[String(value || "")] || String(value || "未知");
}

function decisionLabel(value) {
  return DECISION_LABELS[String(value || "pending")] || String(value || "待审");
}

function confidenceLabel(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return "置信度 —";
  return `置信度 ${Math.round(num * 100)}%`;
}

function el(tag, className = "", text = "") {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== "") node.textContent = text;
  return node;
}

function safeToken(value) {
  return String(value || "").replace(/[^a-z0-9_-]+/gi, "_").slice(0, 40);
}
