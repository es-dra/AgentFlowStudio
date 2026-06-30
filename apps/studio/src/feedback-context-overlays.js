const MAX_FEEDBACK_OVERLAYS = 5;

export function feedbackContextOverlaysFromBundle(bundle) {
  const raw = Array.isArray(bundle?.feedback_context_overlays) ? bundle.feedback_context_overlays : [];
  return raw.slice(0, MAX_FEEDBACK_OVERLAYS).map(normalizeFeedbackOverlay).filter((item) => item.overlay_id);
}

export function feedbackOverlayCount(bundle) {
  return feedbackContextOverlaysFromBundle(bundle).length;
}

export function feedbackOverlayPromptPolicyFromBundle(bundle) {
  const raw = bundle?.feedback_context_overlay_prompt_policy;
  const policy = raw && typeof raw === "object" ? raw : {};
  const policyId = safeText(policy.policy_id, 180);
  if (!policyId) return null;
  return {
    policy_id: policyId,
    default_action: safeText(policy.default_action, 120),
    provider_prompt_includes_context_overlays: Boolean(policy.provider_prompt_includes_context_overlays),
    overlay_text_channel: safeText(policy.overlay_text_channel, 120),
    requires_explicit_prompt_policy_gate: Boolean(policy.requires_explicit_prompt_policy_gate),
    context_overlay_count: safeCount(policy.context_overlay_count),
    selected_overlay_ids: safeIdList(policy.selected_overlay_ids),
    rejected_overlay_ids: safeIdList(policy.rejected_overlay_ids),
  };
}

export function feedbackOverlayPromptPolicySummaryText(policy) {
  const item = feedbackOverlayPromptPolicyFromBundle({ feedback_context_overlay_prompt_policy: policy });
  if (!item) return "";
  if (item.provider_prompt_includes_context_overlays) return "需复核提示词边界";
  if (item.requires_explicit_prompt_policy_gate) return "本地上下文，不注入生成提示词";
  return "本地上下文";
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

export function feedbackOverlayDecisionsForRequest(value) {
  const raw = Array.isArray(value) ? value : [];
  return raw.slice(-20).map(normalizeFeedbackOverlayDecision).filter((item) => item.overlay_id);
}

export function feedbackOverlayDecisionForNode(node, overlayId) {
  const targetId = safeText(overlayId, 180);
  if (!targetId) return null;
  const decisions = feedbackOverlayDecisionsForRequest(node?.params?.feedbackOverlayDecisions);
  return [...decisions].reverse().find((item) => item.overlay_id === targetId) || null;
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

function normalizeFeedbackOverlayDecision(value) {
  const item = value && typeof value === "object" ? value : {};
  const decision = safeText(item.decision, 80);
  if (!["include_for_next_context", "reject_for_next_context"].includes(decision)) return {};
  return {
    overlay_id: safeText(item.overlay_id, 180),
    candidate_id: safeText(item.candidate_id, 180),
    decision,
    reviewed_at: safeText(item.reviewed_at, 80),
    provider_calls_started: false,
    writes_long_term_memory: false,
    writes_company_kb: false,
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

function safeIdList(value) {
  const raw = Array.isArray(value) ? value : [];
  return raw.map((item) => safeText(item, 180)).filter(Boolean).slice(0, 20);
}

function safeCount(value) {
  const count = Number(value);
  return Number.isFinite(count) ? Math.max(0, Math.min(1000, Math.round(count))) : 0;
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
