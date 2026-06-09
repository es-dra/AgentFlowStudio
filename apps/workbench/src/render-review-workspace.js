import { badge, button, el, sectionTitle } from "./dom.js";
import { displayList, displayStatus, displayText } from "./display-labels.js";
import { statusTone } from "./workbench-state.js";

export function renderReviewWorkspace(reviewRoom, memoryWorkspace, state) {
  const review = reviewRoom || { candidates: [], decision_counts: {}, latest_decisions: [], non_claims: [] };
  const candidates = Array.isArray(review.candidates) ? review.candidates : [];
  const selectedId = selectedCandidateId(candidates, state.selectedVariantId);
  const selected = candidates.find((candidate) => candidate.candidate_id === selectedId) || candidates[0] || null;
  return el("section", { className: "review-workspace" }, [
    renderReviewQueue(review, candidates, selectedId),
    renderCandidateStage(selected),
    renderDecisionDock(selected, review.decision_counts || {}, memoryWorkspace?.feedback_controls || {}),
    renderLatestDecisions(review.latest_decisions || []),
    review.non_claims?.length ? el("div", { className: "chips" }, displayList(review.non_claims).map((item) => badge(item, "quiet"))) : null,
  ]);
}

function selectedCandidateId(candidates, stateCandidateId) {
  if (candidates.some((candidate) => candidate.candidate_id === stateCandidateId)) return stateCandidateId;
  return candidates[0]?.candidate_id || "";
}

function renderReviewQueue(review, candidates, selectedId) {
  return el("div", { className: "review-queue" }, [
    sectionTitle("审片队列", displayStatus(review.status)),
    review.summary ? el("p", { className: "card-summary", text: displayText(review.summary) }) : null,
    candidates.length
      ? el("div", { className: "review-candidate-strip" }, candidates.map((candidate) => renderCandidateChip(candidate, selectedId)))
      : el("p", { className: "muted", text: "生成画布草稿或首轮检查后，这里会出现可审片候选。" }),
  ]);
}

function renderCandidateChip(candidate, selectedId) {
  const selected = candidate.candidate_id === selectedId;
  return el("button", {
    className: `review-candidate-chip ${selected ? "selected" : ""}`,
    dataset: { variantId: candidate.candidate_id, artifactId: candidate.artifact_id },
  }, [
    badge(displayText(candidate.label, "候选"), statusTone(candidate.status)),
    el("strong", { text: displayText(candidate.title, "审片候选") }),
    el("small", { text: displayStatus(candidate.status) }),
  ]);
}

function isEnglishFallback(value) {
  return typeof value === "string" && /[A-Za-z]/.test(value) && /^[\x00-\x7F\s.,:;'"!?()/-]+$/.test(value);
}

function candidateSummary(candidate) {
  const summary = displayText(candidate.summary || "");
  if (summary && summary !== candidate.summary) return summary;
  if (!isEnglishFallback(candidate.summary)) return summary;
  if (candidate.stage === "planned_scene") return "分镜候选已就绪，可在检查器中继续微调后进入审片。";
  if (candidate.stage === "first_generation_check") return "首轮确定性检查已有运行证据，可用于判断是否进入下一轮。";
  if (candidate.stage === "next_round") return "下一轮上下文复用已有验证证据，可检查是否延续当前方向。";
  return "候选已准备好，可记录保留、修改或拒绝决定。";
}

function renderCandidateStage(candidate) {
  if (!candidate) {
    return el("div", { className: "review-stage" }, [
      sectionTitle("当前候选", "empty"),
      el("p", { className: "muted", text: "还没有候选可以审片。" }),
    ]);
  }
  return el("div", { className: "review-stage" }, [
    el("div", { className: "review-stage-head" }, [
      badge(displayText(candidate.stage, "候选"), "quiet"),
      badge(displayStatus(candidate.status), statusTone(candidate.status)),
      candidate.latest_decision ? badge(displayText(candidate.latest_decision), candidate.latest_decision === "reject" ? "blocked" : "good") : null,
    ]),
    el("h3", { text: displayText(candidate.title, "审片候选") }),
    candidate.summary ? el("p", { className: "card-summary", text: candidateSummary(candidate) }) : null,
    renderComparePoints(candidate.compare_points || []),
    candidate.artifact_id ? button("打开证据", "open-artifact-ref", "secondary", { artifactId: candidate.artifact_id }) : null,
    candidate.latest_decision_note ? el("p", { className: "artifact-note", text: displayText(candidate.latest_decision_note) }) : null,
  ]);
}

function renderComparePoints(points) {
  const items = Array.isArray(points) && points.length ? points : ["暂无对比点。"];
  return el("ul", { className: "review-points" }, items.map((item) => el("li", { text: displayText(item) })));
}

function renderDecisionDock(candidate, counts, controls) {
  return el("aside", { className: "review-decision-dock" }, [
    sectionTitle("审片决定", displayText(controls.primary_label, "记录审片反馈")),
    el("div", { className: "review-counts" }, [
      badge(`保留 ${counts.keep || 0}`, counts.keep ? "good" : "quiet"),
      badge(`修改 ${counts.revise || 0}`, counts.revise ? "active" : "quiet"),
      badge(`拒绝 ${counts.reject || 0}`, counts.reject ? "blocked" : "quiet"),
    ]),
    controls.summary ? el("p", { className: "card-summary", text: displayText(controls.summary) }) : null,
    candidate ? renderDecisionButtons(candidate) : el("p", { className: "muted", text: "选择候选后记录决定。" }),
    controls.blocked_reason ? badge(displayText(controls.blocked_reason), "blocked") : null,
  ]);
}

function renderDecisionButtons(candidate) {
  const data = { variantId: candidate.candidate_id, artifactId: candidate.artifact_id, cardId: candidate.card_id };
  return el("div", { className: "review-decision-buttons" }, [
    button("保留方向", "set-review-intent", "ghost", { ...data, decision: "keep" }),
    button("标记修改", "set-review-intent", "ghost", { ...data, decision: "revise" }),
    button("拒绝候选", "set-review-intent", "ghost", { ...data, decision: "reject" }),
    button("记录决定", "record-review-decision", "primary"),
  ]);
}

function renderLatestDecisions(decisions) {
  return el("div", { className: "review-history" }, [
    sectionTitle("最近审片", `${decisions.length}`),
    decisions.length
      ? el("div", { className: "review-history-list" }, decisions.map(renderDecisionRow))
      : el("p", { className: "muted", text: "还没有记录过审片决定。" }),
  ]);
}

function renderDecisionRow(decision) {
  return el("div", { className: "review-history-row" }, [
    badge(displayText(decision.decision || "unknown"), decision.decision === "reject" ? "blocked" : "good"),
    el("span", { text: displayText(decision.note || "无说明") }),
    decision.artifact_id ? button("查看证据", "open-artifact-ref", "ghost", { artifactId: decision.artifact_id }) : null,
  ]);
}
