import { statusTone } from "./workbench-state.js";
import { badge, button, el, sectionTitle } from "./dom.js";

export function renderMemoryWorkspace(memoryWorkspace, state) {
  const value = memoryWorkspace || { candidates: [], counts: {}, style_profile: {}, non_claims: [] };
  const selectedCandidateId = selectedCandidateIdFor(value.candidates || [], value, state);
  const selected = selectedCandidate(value.candidates || [], selectedCandidateId);
  return el("section", { className: "memory-workspace" }, [
    sectionTitle("Memory Workspace", value.status || "not_started"),
    value.summary ? el("p", { className: "card-summary", text: value.summary }) : null,
    renderMemoryMetrics(value.counts || {}),
    renderMemoryControls(value.feedback_controls || {}, value.next_round_controls || {}),
    renderCandidateGrid(value.candidates || [], selectedCandidateId),
    renderCandidateDetail(selected),
    renderStyleProfile(value.style_profile || {}),
    value.non_claims && value.non_claims.length ? el("div", { className: "chips" }, value.non_claims.map((item) => badge(item, "quiet"))) : null,
  ]);
}

function selectedCandidateIdFor(candidates, memoryWorkspace, state) {
  const stateCandidateId = state && state.selectedVariantId;
  if (candidates.some((candidate) => candidate.candidate_id === stateCandidateId)) return stateCandidateId;
  return memoryWorkspace.selected_candidate_id || candidates[0]?.candidate_id || "";
}

function selectedCandidate(candidates, selectedCandidateId) {
  return candidates.find((candidate) => candidate.candidate_id === selectedCandidateId) || candidates[0] || null;
}

function renderMemoryMetrics(counts) {
  return el("div", { className: "memory-facts" }, [
    badge(`${counts.candidates || 0} candidates`, counts.candidates ? "ready" : "quiet"),
    badge(`${counts.feedback_refs || 0} feedback refs`, counts.feedback_refs ? "active" : "quiet"),
    badge(`${counts.profile_versions || 0} profiles`, counts.profile_versions ? "good" : "quiet"),
    badge(`${counts.reusable_preferences || 0} preferences`, counts.reusable_preferences ? "good" : "quiet"),
  ]);
}

function renderMemoryControls(feedbackControls, nextRoundControls) {
  return el("div", { className: "memory-controls" }, [
    controlButton(feedbackControls, "Record Review"),
    controlButton(nextRoundControls, "Run Next Round"),
    feedbackControls.summary ? el("p", { className: "card-summary", text: feedbackControls.summary }) : null,
  ]);
}

function controlButton(control, fallbackLabel) {
  if (control.enabled && control.ui_action) {
    return button(control.primary_label || fallbackLabel, control.ui_action, "primary");
  }
  return el("button", {
    className: "btn ghost disabled",
    text: control.primary_label || fallbackLabel,
    attrs: { disabled: "disabled" },
  });
}

function renderCandidateGrid(candidates, selectedCandidateId) {
  if (!candidates.length) return el("p", { className: "muted", text: "No review candidates yet." });
  return el("div", { className: "variant-grid" }, candidates.map((candidate) => renderCandidate(candidate, selectedCandidateId)));
}

function renderCandidate(candidate, selectedCandidateId) {
  const selected = candidate.candidate_id === selectedCandidateId;
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

function renderCandidateDetail(candidate) {
  if (!candidate) return el("p", { className: "muted", text: "No candidate selected." });
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

function renderStyleProfile(profile) {
  const preferences = Array.isArray(profile.reusable_preferences) ? profile.reusable_preferences : [];
  return el("div", { className: "memory-profile-panel" }, [
    sectionTitle("Style Profile", profile.status || "not_started"),
    el("p", { className: "card-summary", text: profile.summary || "No project style profile yet." }),
    preferences.length
      ? el("ul", { className: "memory-list" }, preferences.map((item) => el("li", { text: item })))
      : el("p", { className: "muted", text: "Record review evidence before reusable preferences appear." }),
    profile.latest_profile_artifact_id ? button("Open Profile", "open-artifact-ref", "ghost", { artifactId: profile.latest_profile_artifact_id }) : null,
    profile.next_pass_usage ? el("p", { className: "artifact-note", text: profile.next_pass_usage }) : null,
  ]);
}
