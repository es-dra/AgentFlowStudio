export const QUALITY_FEEDBACK_EVENT = "afs:studio-quality-feedback";
export const QUALITY_FEEDBACK_RESULT_EVENT = "afs:studio-quality-feedback-result";

const METRICS = [
  ["identity_similarity", "身份相似"],
  ["wardrobe_consistency", "服饰一致"],
  ["scene_continuity", "场景连续"],
  ["text_or_watermark", "文字水印"],
  ["target_change_success", "目标变化"],
];

export function qualityFeedbackView(node) {
  if (!shouldShowFeedback(node)) return null;
  const wrap = document.createElement("div");
  wrap.className = "quality-feedback";
  wrap.dataset.nodeId = String(node.id || "");

  const head = document.createElement("div");
  head.className = "quality-feedback-head";
  head.textContent = node.type === "video" ? "视频质量反馈" : "图像质量反馈";
  wrap.appendChild(head);

  const grid = document.createElement("div");
  grid.className = "quality-feedback-grid";
  for (const [id, label] of METRICS) {
    const field = document.createElement("label");
    field.className = "quality-feedback-field";
    field.appendChild(document.createElement("span")).textContent = label;
    const select = document.createElement("select");
    select.dataset.feedbackMetric = id;
    for (const [value, text] of [["", "未评"], ["1", "1"], ["2", "2"], ["3", "3"], ["4", "4"], ["5", "5"]]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = text;
      select.appendChild(option);
    }
    field.appendChild(select);
    grid.appendChild(field);
  }
  wrap.appendChild(grid);

  const notes = document.createElement("textarea");
  notes.className = "quality-feedback-notes";
  notes.dataset.feedbackNotes = "drift_notes";
  notes.maxLength = 600;
  notes.placeholder = "偏差记录：例如灯光、入场方式、刀疤细节、无关部分漂移";
  wrap.appendChild(notes);

  const foot = document.createElement("div");
  foot.className = "quality-feedback-foot";
  const status = document.createElement("span");
  status.className = "quality-feedback-status";
  status.textContent = "原始证据，不写入长期记忆";
  const submit = document.createElement("button");
  submit.className = "quality-feedback-submit";
  submit.textContent = "记录反馈";
  submit.addEventListener("click", () => submitFeedback(node, wrap, status, submit));
  foot.append(status, submit);
  wrap.appendChild(foot);

  return wrap;
}

export function buildQualityFeedbackPayload(node, values = {}) {
  const ratings = {};
  for (const [id] of METRICS) {
    const rating = numberOrNull(values[id]);
    if (rating != null) ratings[id] = rating;
  }
  // Read only presence; never copy the preview URL into the feedback payload.
  const hasPreview = Boolean(node?.previewUrl);
  return {
    kind: "studio_quality_feedback",
    node_id: safeToken(node?.id),
    node_type: safeToken(node?.type),
    video_job_id: safeToken(node?.params?.lastVideoJobId),
    video_revision_job_id: safeToken(node?.params?.videoRevision?.lastRevisionJobId),
    artifact_ref: safeToken(node?.params?.lastSafeManifest?.artifact_id),
    safe_preview_ref: hasPreview ? "runtime_preview_endpoint" : "none",
    ratings,
    target_change_success: numberOrNull(values.target_change_success),
    drift_notes: sanitizeFeedbackText(values.drift_notes),
    prompt_char_count: String(node?.prompt || "").length,
    result_char_count: String(node?.result || "").length,
    raw_evidence_policy: "raw_evidence_not_memory",
    feedback_is_memory: false,
    writes_long_term_memory: false,
    writes_company_kb: false,
    safety_boundary: {
      no_provider_raw: true,
      no_private_external_link: true,
      no_local_path: true,
      no_media_bytes: true,
    },
  };
}

function shouldShowFeedback(node) {
  if (!node || !["image", "video"].includes(node.type)) return false;
  if (node.status !== "complete") return false;
  return Boolean(node.result || node?.previewUrl);
}

function submitFeedback(node, wrap, status, submit) {
  const requestId = `quality-feedback-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const feedback = buildQualityFeedbackPayload(node, collectValues(wrap));
  submit.disabled = true;
  status.textContent = "记录中...";
  const onResult = (event) => {
    if (event.detail?.request_id !== requestId) return;
    window.removeEventListener(QUALITY_FEEDBACK_RESULT_EVENT, onResult);
    submit.disabled = false;
    status.textContent = event.detail?.ok
      ? `已记录：${event.detail.feedback_id || "runtime_feedback_event"}`
      : `记录失败：${sanitizeFeedbackText(event.detail?.error || "unknown")}`;
  };
  window.addEventListener(QUALITY_FEEDBACK_RESULT_EVENT, onResult);
  window.dispatchEvent(new CustomEvent(QUALITY_FEEDBACK_EVENT, { detail: { request_id: requestId, feedback } }));
}

function collectValues(wrap) {
  const values = {};
  for (const input of wrap.querySelectorAll("[data-feedback-metric]")) {
    values[input.dataset.feedbackMetric] = input.value;
  }
  const notes = wrap.querySelector("[data-feedback-notes]");
  values.drift_notes = notes?.value || "";
  return values;
}

function numberOrNull(value) {
  const number = Number(value);
  return Number.isInteger(number) && number >= 1 && number <= 5 ? number : null;
}

function safeToken(value) {
  return String(value || "").replace(/[^a-zA-Z0-9_.:-]+/g, "_").slice(0, 120);
}

function sanitizeFeedbackText(value) {
  return String(value || "")
    .replace(/Bearer\s+\S+/gi, "Bearer <redacted>")
    .replace(/[A-Za-z]:\\[^\s"'<>]+/g, "<local-path-redacted>")
    .replace(/https?:\/\/[^\s"'<>]+/g, "<url-redacted>")
    .slice(0, 600);
}
