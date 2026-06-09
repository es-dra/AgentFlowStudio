import { statusTone } from "./workbench-state.js";
import { badge, button, el, sectionTitle } from "./dom.js";

function selectedCandidate(reviewRoom, selectedVariantId) {
  const candidates = reviewRoom && Array.isArray(reviewRoom.candidates) ? reviewRoom.candidates : [];
  return candidates.find((item) => item.candidate_id === selectedVariantId) || candidates[0] || null;
}

function renderCandidate(candidate, selectedVariantId) {
  const selected = candidate.candidate_id === selectedVariantId;
  return el(
    "article",
    {
      className: `variant-card ${selected ? "selected" : ""}`,
      dataset: { variantId: candidate.candidate_id, artifactId: candidate.artifact_id },
    },
    [
      el("div", { className: "card-head" }, [el("h3", { text: candidate.title }), badge(candidate.label, "ready")]),
      el("p", { className: "card-summary", text: candidate.summary }),
      el("div", { className: "chips" }, [
        badge(candidate.status, statusTone(candidate.status)),
        candidate.latest_decision ? badge(candidate.latest_decision, candidate.latest_decision === "reject" ? "blocked" : "good") : null,
      ]),
      candidate.artifact_id ? el("code", { text: candidate.artifact_id }) : null,
    ],
  );
}

function renderComparison(candidate) {
  if (!candidate) return el("p", { className: "muted", text: "No candidates ready for review." });
  const points = Array.isArray(candidate.compare_points) && candidate.compare_points.length
    ? candidate.compare_points
    : ["No comparison points yet."];
  return el("div", { className: "variant-detail" }, [
    el("div", { className: "card-head" }, [
      el("h3", { text: candidate.title }),
      badge(candidate.status, statusTone(candidate.status)),
    ]),
    el("p", { className: "card-summary", text: candidate.summary }),
    el("ul", { className: "memory-list" }, points.map((item) => el("li", { text: item }))),
    candidate.latest_decision_note ? el("p", { className: "artifact-note", text: candidate.latest_decision_note }) : null,
    candidate.artifact_id ? button("Open Evidence", "open-artifact-ref", "secondary", { artifactId: candidate.artifact_id }) : null,
  ]);
}

function renderDecisionCounts(counts) {
  const value = counts || {};
  return el("div", { className: "memory-facts" }, [
    badge(`${value.keep || 0} keep`, value.keep ? "good" : "quiet"),
    badge(`${value.revise || 0} revise`, value.revise ? "ready" : "quiet"),
    badge(`${value.reject || 0} reject`, value.reject ? "blocked" : "quiet"),
  ]);
}

export function renderReviewRoom(reviewRoom, selectedVariantId) {
  const value = reviewRoom || { candidates: [], decision_counts: {} };
  const selected = selectedCandidate(value, selectedVariantId);
  const activeVariantId = selected ? selected.candidate_id : "";
  return el("section", { className: "review-room" }, [
    sectionTitle("Review Room", value.status || "not_started"),
    el("p", { className: "card-summary", text: value.summary || "Add candidates before review." }),
    renderDecisionCounts(value.decision_counts),
    el(
      "div",
      { className: "variant-grid" },
      (value.candidates || []).map((candidate) => renderCandidate(candidate, activeVariantId)),
    ),
    renderComparison(selected),
  ]);
}
