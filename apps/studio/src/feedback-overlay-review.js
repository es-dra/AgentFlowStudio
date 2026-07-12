import {
  feedbackContextOverlaysFromBundle,
  feedbackOverlayDecisionForNode,
  feedbackOverlaySummaryText,
} from "./feedback-context-overlays.js";
import { icon } from "./icons.js";
import { el, showPopover } from "./overlay.js";

export function feedbackOverlayReviewTargets(node) {
  return dedupeTargets(feedbackContextOverlaysFromBundle(node?.params?.lastContextBundle));
}

export function openFeedbackOverlayReviewMenu(store, node, anchorOrPoint) {
  const targets = feedbackOverlayReviewTargets(node);
  if (!targets.length) return;
  const pop = el("div", "human-gate-popover");
  pop.appendChild(feedbackOverlayReviewView(store, node, targets));
  const anchor = resolveAnchor(anchorOrPoint);
  showPopover(anchor.el, pop, { place: "bottom", onClose: anchor.cleanup });
}

function feedbackOverlayReviewView(store, node, targets) {
  const wrap = el("div", "human-gate");
  const head = el("div", "human-gate-head");
  head.innerHTML = `${icon("layers", 13)}<strong>选择反馈上下文</strong><small>本地决定下一次上下文使用</small>`;
  wrap.appendChild(head);

  for (const target of targets.slice(0, 8)) {
    const row = el("div", "human-gate-row");
    const current = feedbackOverlayDecisionForNode(node, target.overlay_id);
    const label = current ? `${feedbackOverlaySummaryText(target)} / ${decisionLabel(current.decision)}` : feedbackOverlaySummaryText(target);
    row.appendChild(el("span", "human-gate-target", label));
    const actions = el("div", "human-gate-actions");
    actions.appendChild(decisionButton(store, node, target, "include_for_next_context", "纳入"));
    actions.appendChild(decisionButton(store, node, target, "reject_for_next_context", "拒绝"));
    row.appendChild(actions);
    wrap.appendChild(row);
  }

  const status = el("div", "human-gate-status", "不会打开 provider，也不会写入长期记忆或公司资料。");
  wrap.appendChild(status);
  wrap.addEventListener("afs:feedback-overlay-status", (event) => {
    status.textContent = String(event.detail?.message || "");
  });
  return wrap;
}

function decisionButton(store, node, target, decision, label) {
  const button = el("button", "human-gate-submit", label);
  button.type = "button";
  button.addEventListener("click", () => {
    recordFeedbackOverlayDecision(store, node?.id, target, decision);
    button.closest(".human-gate")?.dispatchEvent(new CustomEvent("afs:feedback-overlay-status", {
      detail: { message: `已记录：${decisionLabel(decision)}` },
    }));
  });
  return button;
}

function recordFeedbackOverlayDecision(store, nodeId, target, decision) {
  const overlayId = safeToken(target?.overlay_id);
  if (!overlayId) return;
  store.set((state) => {
    const node = state.nodes[nodeId];
    if (!node) return;
    node.params = node.params || {};
    const prior = Array.isArray(node.params.feedbackOverlayDecisions) ? node.params.feedbackOverlayDecisions : [];
    node.params.feedbackOverlayDecisions = prior
      .filter((item) => safeToken(item?.overlay_id) !== overlayId)
      .concat({
        overlay_id: overlayId,
        candidate_id: safeToken(target?.candidate_id),
        decision,
        reviewed_at: new Date().toISOString(),
        provider_calls_started: false,
        writes_long_term_memory: false,
        writes_company_kb: false,
      })
      .slice(-20);
  });
}

function dedupeTargets(targets) {
  const seen = new Set();
  const result = [];
  for (const target of targets) {
    const overlayId = safeToken(target?.overlay_id);
    if (!overlayId || seen.has(overlayId)) continue;
    seen.add(overlayId);
    result.push({ ...target, overlay_id: overlayId });
  }
  return result;
}

function decisionLabel(value) {
  if (value === "include_for_next_context") return "纳入下一次上下文";
  if (value === "reject_for_next_context") return "拒绝下一次上下文";
  return "未选择";
}

function safeToken(value) {
  return String(value || "").replace(/[^a-zA-Z0-9_.:-]+/g, "_").slice(0, 180);
}

function resolveAnchor(anchorOrPoint) {
  if (anchorOrPoint instanceof Element) return { el: anchorOrPoint, cleanup: undefined };
  const point = anchorOrPoint || { x: window.innerWidth / 2, y: window.innerHeight / 2 };
  const ghost = el("div");
  ghost.style.cssText = `position:fixed;left:${point.x}px;top:${point.y}px;width:1px;height:1px;pointer-events:none;`;
  document.body.appendChild(ghost);
  return { el: ghost, cleanup: () => ghost.remove() };
}
