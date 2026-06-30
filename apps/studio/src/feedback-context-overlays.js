const MAX_FEEDBACK_OVERLAYS = 5;

export function feedbackContextOverlaysFromBundle(bundle) {
  const raw = Array.isArray(bundle?.feedback_context_overlays) ? bundle.feedback_context_overlays : [];
  return raw.slice(0, MAX_FEEDBACK_OVERLAYS).map(normalizeFeedbackOverlay).filter((item) => item.overlay_id);
}

export function feedbackOverlayCount(bundle) {
  return feedbackContextOverlaysFromBundle(bundle).length;
}

export function feedbackOverlaySummaryText(overlay) {
  const item = normalizeFeedbackOverlay(overlay);
  const effect = feedbackEffectLabel(item.decision_effect);
  const target = item.safe_target.node_id || item.safe_target.kind || shortId(item.candidate_id) || shortId(item.overlay_id);
  const boundary = item.provider_calls_started || item.writes_long_term_memory || item.writes_company_kb
    ? "需复核边界"
    : "本地上下文";
  return [effect, target, boundary].filter(Boolean).join(" / ");
}

function normalizeFeedbackOverlay(value) {
  const item = value && typeof value === "object" ? value : {};
  return {
    overlay_id: safeText(item.overlay_id, 180),
    candidate_id: safeText(item.candidate_id, 180),
    candidate_scope: safeText(item.candidate_scope, 120),
    overlay_scope: safeText(item.overlay_scope, 120),
    overlay_intent: safeText(item.overlay_intent, 160),
    decision_effect: safeText(item.decision_effect, 120),
    context_overlay_consumed: Boolean(item.context_overlay_consumed),
    candidate_feedback_included_in_context: Boolean(item.candidate_feedback_included_in_context),
    provider_calls_started: Boolean(item.provider_calls_started),
    writes_long_term_memory: Boolean(item.writes_long_term_memory),
    writes_company_kb: Boolean(item.writes_company_kb),
    safe_target: safeTarget(item.safe_target),
  };
}

function safeTarget(value) {
  const target = value && typeof value === "object" ? value : {};
  return {
    kind: safeText(target.kind, 80),
    node_id: safeText(target.node_id, 120),
    node_type: safeText(target.node_type, 80),
    artifact_ref: safeText(target.artifact_ref, 160),
  };
}

function feedbackEffectLabel(value) {
  const effect = String(value || "");
  if (effect === "included_in_context") return "已纳入";
  if (effect === "blocked_from_context") return "未纳入";
  return "反馈上下文";
}

function shortId(value) {
  const text = safeText(value, 120);
  return text.length > 12 ? `${text.slice(0, 7)}…${text.slice(-4)}` : text;
}

function safeText(value, maxLength) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, maxLength);
}
