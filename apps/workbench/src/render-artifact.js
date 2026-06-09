import { badge, button, el, sectionTitle } from "./dom.js";

function payloadOf(artifact) {
  return artifact ? artifact.payload ?? artifact.text ?? artifact : null;
}

function artifactTitle(artifact) {
  if (!artifact) return "No artifact loaded";
  return artifact.artifact_type || artifact.role || "artifact";
}

function artifactMeta(artifact) {
  if (!artifact) return [];
  return [
    artifact.artifact_id ? badge(artifact.artifact_id, "ready") : null,
    artifact.role ? badge(artifact.role, "quiet") : null,
    artifact.media_type ? badge(artifact.media_type, "quiet") : null,
  ].filter(Boolean);
}

function fact(label, value, tone = "quiet") {
  return el("div", { className: "fact-row" }, [el("span", { text: label }), badge(value ?? "unknown", tone)]);
}

function listItems(title, items, key = "block_id") {
  const rows = Array.isArray(items) && items.length
    ? items.map((item) => el("li", { text: typeof item === "object" ? item[key] || item.reason || item.ref || JSON.stringify(item) : item }))
    : [el("li", { text: "none" })];
  return el("div", { className: "report-section" }, [el("h3", { text: title }), el("ul", {}, rows)]);
}

function projectManifestView(payload) {
  return [
    fact("status", payload.status, payload.status === "blocked" ? "blocked" : "good"),
    fact("source assets", Array.isArray(payload.source_assets) ? payload.source_assets.length : 0, "ready"),
    fact("content cards", Array.isArray(payload.content_cards) ? payload.content_cards.length : 0, "ready"),
    fact("runs", Array.isArray(payload.runs) ? payload.runs.length : 0, "ready"),
    fact("feedback", Array.isArray(payload.feedback_refs) ? payload.feedback_refs.length : 0, "ready"),
  ];
}

function assetTestView(payload) {
  return [
    fact("run", payload.run_status || payload.status, payload.blocks?.length ? "blocked" : "good"),
    fact("provider calls", payload.provider_calls_started === true ? "started" : "not started", "quiet"),
    fact("long-term memory", payload.writes_long_term_memory === true ? "written" : "not written", "quiet"),
    listItems("Blocks", payload.blocks || [], "block_id"),
  ];
}

function twoRoundView(payload) {
  return [
    fact("verification", payload.runtime_verification_status || payload.status, "good"),
    fact("assessment", payload.improvement_assessment || "unknown", "ready"),
    listItems("Included refs", payload.included_refs || [], "ref"),
    listItems("Blocked refs", payload.blocked_refs || [], "ref"),
  ];
}

function feedbackView(payload) {
  const feedback = payload.feedback || {};
  return [
    fact("feedback is memory", payload.feedback_is_memory === true ? "yes" : "no", "quiet"),
    fact("result", feedback.result || "unknown", "ready"),
    el("p", { className: "artifact-note", text: feedback.note || "" }),
  ];
}

function reviewDecisionView(payload) {
  return [
    fact("decision", payload.decision || "unknown", payload.decision === "reject" ? "blocked" : "ready"),
    fact("card", payload.card_id || "unknown", "quiet"),
    fact("long-term memory", payload.writes_long_term_memory === true ? "written" : "not written", "quiet"),
    el("p", { className: "artifact-note", text: payload.note || "" }),
  ];
}

function providerView(payload) {
  return [
    fact("status", payload.status || "unknown", payload.status === "blocked" ? "blocked" : "good"),
    fact("provider calls", payload.provider_calls_started === true ? "started" : "not started", "quiet"),
    listItems("Provider blockers", payload.blockers || payload.blocks || [], "blocker_id"),
  ];
}

function reportView(artifact) {
  const payload = payloadOf(artifact);
  if (!payload || typeof payload !== "object") return [];
  const type = artifact.artifact_type || payload.artifact_type || payload.kind || "";
  if (type === "agentflow_project_manifest") return projectManifestView(payload);
  if (type === "agentflow_real_asset_test_report") return assetTestView(payload);
  if (type === "agentflow_two_round_context_runtime_report") return twoRoundView(payload);
  if (type === "agentflow_runtime_feedback_event") return feedbackView(payload);
  if (type === "agentflow_runtime_review_decision") return reviewDecisionView(payload);
  if (type === "agentflow_provider_safe_manifest") return providerView(payload);
  return [];
}

function artifactBody(artifact) {
  if (!artifact) return el("p", { className: "muted", text: "Select a card with a safe artifact ref." });
  const payload = payloadOf(artifact);
  const serialized = JSON.stringify(payload, null, 2);
  return el("details", { className: "artifact-details" }, [
    el("summary", { text: "JSON Detail" }),
    el("pre", { className: "artifact-json", text: serialized.slice(0, 6000) }),
  ]);
}

export function renderArtifactPanel(state) {
  return el("section", { className: "artifact-panel" }, [
    sectionTitle("Safe Artifact", artifactTitle(state.artifact)),
    el("div", { className: "chips" }, artifactMeta(state.artifact)),
    el("div", { className: "report-view" }, reportView(state.artifact)),
    artifactBody(state.artifact),
    state.selectedArtifactId ? button("Reload Artifact", "open-selected-artifact", "ghost") : null,
  ]);
}
