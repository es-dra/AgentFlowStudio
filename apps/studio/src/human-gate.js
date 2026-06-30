import { el, showPopover } from "./overlay.js";
import { icon } from "./icons.js";

export const HUMAN_GATE_DECISION_EVENT = "afs:human-gate-decision";
export const HUMAN_GATE_DECISION_RESULT_EVENT = "afs:human-gate-decision-result";

export function humanGateTargets(node) {
  const targets = [];
  targets.push(...assetCardCandidateTargets(node));
  const bridge = keyframeBridgeTarget(node);
  if (bridge) targets.push(bridge);
  return targets;
}

export function openHumanGateMenu(node, anchorOrPoint) {
  const targets = humanGateTargets(node);
  if (!targets.length) return;
  const pop = el("div", "human-gate-popover");
  pop.appendChild(humanGateView(node, targets));
  const anchor = resolveAnchor(anchorOrPoint);
  showPopover(anchor.el, pop, { place: "bottom", onClose: anchor.cleanup });
}

function humanGateView(node, targets) {
  const wrap = el("div", "human-gate");
  const head = el("div", "human-gate-head");
  head.innerHTML = `${icon("check", 13)}<strong>记录人工 Gate</strong><small>本地步骤证据，不固定资产</small>`;
  wrap.appendChild(head);

  for (const target of targets.slice(0, 12)) {
    const row = el("div", "human-gate-row");
    const targetInfo = el("div", "human-gate-target-info");
    targetInfo.appendChild(el("span", "human-gate-target", target.label));
    if (target.reuse_label) targetInfo.appendChild(el("span", "human-gate-target-meta", target.reuse_label));
    if (target.graph_reuse_label) targetInfo.appendChild(el("span", "human-gate-target-meta", target.graph_reuse_label));
    row.appendChild(targetInfo);
    const actions = el("div", "human-gate-actions");
    actions.appendChild(decisionButton(node, target, "accepted_for_next_step", "下一步"));
    actions.appendChild(decisionButton(node, target, "needs_revision", "需修订"));
    row.appendChild(actions);
    wrap.appendChild(row);
  }

  const status = el("div", "human-gate-status", "不会打开 provider，也不会写入长期记忆。");
  wrap.appendChild(status);
  wrap.addEventListener("afs:human-gate-status", (event) => {
    status.textContent = String(event.detail?.message || "");
  });
  return wrap;
}

function decisionButton(node, target, decision, label) {
  const button = el("button", "human-gate-submit", label);
  button.type = "button";
  button.addEventListener("click", () => submitHumanGateDecision(node, target, decision, button));
  return button;
}

function submitHumanGateDecision(node, target, decision, button) {
  const requestId = `human-gate-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  const payload = {
    target_type: target.target_type,
    target_id: target.target_id,
    decision,
    artifact_id: target.artifact_id || "",
    node_id: safeToken(node?.id),
    scope: target.scope,
    note: target.note || "Studio local step gate decision.",
    reviewed_at: new Date().toISOString(),
  };
  const root = button.closest(".human-gate");
  button.disabled = true;
  root?.dispatchEvent(new CustomEvent("afs:human-gate-status", { detail: { message: "记录中..." } }));
  const onResult = (event) => {
    if (event.detail?.request_id !== requestId) return;
    window.removeEventListener(HUMAN_GATE_DECISION_RESULT_EVENT, onResult);
    button.disabled = false;
    const ok = Boolean(event.detail?.ok);
    root?.dispatchEvent(new CustomEvent("afs:human-gate-status", {
      detail: { message: ok ? `已记录：${event.detail?.human_gate_id || "human_gate"}` : `记录失败：${safeText(event.detail?.error)}` },
    }));
  };
  window.addEventListener(HUMAN_GATE_DECISION_RESULT_EVENT, onResult);
  window.dispatchEvent(new CustomEvent(HUMAN_GATE_DECISION_EVENT, { detail: { request_id: requestId, payload } }));
}

function assetCardCandidateTargets(node) {
  const breakdown = node?.params?.storyboardBreakdown || {};
  const candidateSet = breakdown.assetCardCandidates || node?.params?.assetCardCandidates || null;
  const candidates = Array.isArray(candidateSet?.candidates) ? candidateSet.candidates : [];
  const artifactId = breakdown.assetCardCandidateArtifactId || node?.params?.assetCardCandidateArtifactId || "";
  const productionGraph = productionGraphFromBreakdown(breakdown);
  const graphReuseCount = productionGraphFixedAssetCount(productionGraph);
  return candidates.map((candidate, index) => ({
    target_type: "asset_card_candidate",
    target_id: safeToken(candidate?.candidate_id || `asset_card_candidate:${index + 1}`),
    artifact_id: safeToken(artifactId),
    scope: "asset_card_candidate_review",
    reuse_policy: assetCandidateReusePolicy(candidate),
    reuse_label: assetCandidateReuseLabel(assetCandidateReusePolicy(candidate)),
    graph_reuse_label: productionGraphReuseLabel(productionGraph),
    note: `${assetCandidateReuseNote(candidate)}; fixed_asset_reuse_count=${graphReuseCount}`,
    label: `${assetTypeLabel(candidate?.asset_type)} · ${safeText(candidate?.draft_fields?.display_name || candidate?.source_asset_id || `候选 ${index + 1}`)}`,
  }));
}

function keyframeBridgeTarget(node) {
  const bridge = node?.params?.lastGenerationBridge || null;
  const artifactId = node?.params?.lastGenerationBridgeArtifactId || "";
  if (!bridge && !artifactId) return null;
  return {
    target_type: "keyframe_generation_bridge",
    target_id: safeToken(artifactId || node?.params?.lastKeyframeJobId || node?.id || "keyframe_generation_bridge"),
    artifact_id: safeToken(artifactId),
    scope: "keyframe_generation_bridge_review",
    label: "关键帧请求链 · provider 前确认",
  };
}

function assetTypeLabel(value) {
  return { character: "角色", scene: "场景", prop: "道具" }[String(value || "")] || "资产";
}

function safeToken(value) {
  return String(value || "").replace(/[^a-zA-Z0-9_.:-]+/g, "_").slice(0, 160);
}

function assetCandidateReusePolicy(candidate) {
  const policy = candidate?.reuse_policy || {};
  const shotRefCount = Math.max(0, Math.min(Number(policy.shot_ref_count) || 0, 99));
  return {
    suggested_reuse_scope: safeReuseScope(policy.suggested_reuse_scope),
    shot_ref_count: shotRefCount,
    requires_human_confirmation: policy.requires_human_confirmation !== false,
    writes_fixed_asset: false,
  };
}

function assetCandidateReuseNote(candidate) {
  const policy = assetCandidateReusePolicy(candidate);
  return `Studio local step gate decision. reuse_scope=${policy.suggested_reuse_scope}; shot_ref_count=${policy.shot_ref_count}; writes_fixed_asset=false`;
}

function safeReuseScope(value) {
  return value === "project_reuse_candidate" ? "project_reuse_candidate" : "shot_local_candidate";
}

function assetCandidateReuseLabel(policy) {
  if (!policy) return "";
  const scopeLabel = policy.suggested_reuse_scope === "project_reuse_candidate" ? "Project reuse" : "Shot local";
  return `${scopeLabel} / ${policy.shot_ref_count} shots`;
}

function productionGraphFromBreakdown(breakdown) {
  return breakdown?.productionGraph || breakdown?.production_graph || null;
}

function productionGraphFixedAssetCount(graph) {
  const summaryCount = Number(graph?.summary?.fixed_visual_asset_count);
  if (Number.isFinite(summaryCount) && summaryCount > 0) return Math.min(summaryCount, 99);
  const nodes = Array.isArray(graph?.nodes) ? graph.nodes : [];
  return Math.min(nodes.filter((node) => node?.node_type === "fixed_visual_asset").length, 99);
}

function productionGraphReuseLabel(graph) {
  const count = productionGraphFixedAssetCount(graph);
  if (!count) return "";
  return `Fixed reuse / ${count} ${count === 1 ? "asset" : "assets"}`;
}

function safeText(value) {
  return String(value || "").replace(/\s+/g, " ").slice(0, 160);
}

function resolveAnchor(anchorOrPoint) {
  if (anchorOrPoint instanceof Element) return { el: anchorOrPoint, cleanup: undefined };
  const point = anchorOrPoint || { x: window.innerWidth / 2, y: window.innerHeight / 2 };
  const ghost = el("div");
  ghost.style.cssText = `position:fixed;left:${point.x}px;top:${point.y}px;width:1px;height:1px;pointer-events:none;`;
  document.body.appendChild(ghost);
  return { el: ghost, cleanup: () => ghost.remove() };
}
