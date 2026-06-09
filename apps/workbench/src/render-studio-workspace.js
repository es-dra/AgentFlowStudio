import { badge, button, el, sectionTitle, textareaField } from "./dom.js";
import { statusTone } from "./workbench-state.js";

export function renderStudioWorkspace(workspace, state) {
  const value = workspace || { canvas: { cards: [] }, counts: {}, side_rail: {}, operations_summary: {} };
  const cards = Array.isArray(value.canvas?.cards) ? value.canvas.cards : [];
  const selectedCardId = selectedCardIdFor(cards, value, state);
  const inspector = selectedInspector(cards, selectedCardId, value.inspector || {});
  return el("section", { className: "studio-workspace" }, [
    renderCommandStrip(value),
    el("div", { className: "studio-layout" }, [
      renderSideRail(value.side_rail || {}, value.counts || {}),
      renderCanvas(value, selectedCardId),
      renderInspector(inspector, state),
    ]),
    renderFilmstrip(value.filmstrip || []),
    renderOperationsSummary(value.operations_summary || {}, value.provider_status),
  ]);
}

function selectedCardIdFor(cards, workspace, state) {
  const stateCardId = state && state.selectedCardId;
  if (cards.some((card) => card.card_id === stateCardId)) return stateCardId;
  return workspace.canvas?.selected_card_id || cards[0]?.card_id || "";
}

function selectedInspector(cards, selectedCardId, fallback) {
  const card = cards.find((item) => item.card_id === selectedCardId);
  if (!card) return fallback;
  return {
    card_id: card.card_id,
    mode: card.kind === "scene_card" ? "scene" : "setup",
    title: card.title || "No card selected",
    status: card.status || "not_started",
    summary: card.summary || "",
    primary_artifact_id: card.primary_artifact_id || "",
    fields: card.inspector || {},
    refs: card.refs || [],
    blockers: card.blockers || [],
  };
}

function renderCommandStrip(workspace) {
  const command = workspace.primary_command || {};
  const counts = workspace.counts || {};
  const canRunHere = command.ui_action && command.enabled && (!command.view || command.view === "Create");
  return el("div", { className: "studio-command-strip" }, [
    el("div", { className: "studio-project-lockup" }, [
      el("span", { text: "Studio Workspace" }),
      el("strong", { text: workspace.active_project?.goal || workspace.active_project?.project_id || "Open project" }),
      el("small", { text: workspace.summary || "Safe production workspace." }),
    ]),
    el("div", { className: "studio-strip-metrics" }, [
      badge(workspace.status || "not_started", statusTone(workspace.status)),
      badge(`${counts.canvas_cards || 0} cards`, counts.canvas_cards ? "ready" : "quiet"),
      badge(`${counts.review_candidates || 0} review`, counts.review_candidates ? "active" : "quiet"),
      badge(`provider ${workspace.provider_status || "ready_not_run"}`, workspace.provider_status === "blocked" ? "blocked" : "quiet"),
    ]),
    canRunHere
      ? button(command.label || "Continue", command.ui_action, "primary")
      : el("button", { className: "btn ghost disabled", text: commandLabel(command), attrs: { disabled: "disabled" } }),
  ]);
}

function commandLabel(command) {
  if (command.blocked_reason) return command.blocked_reason;
  if (command.view && command.view !== "Create") return `Open ${command.view} to continue`;
  return command.label || "Continue";
}

function renderSideRail(sideRail, counts) {
  const assets = Array.isArray(sideRail.assets) ? sideRail.assets : [];
  const candidates = Array.isArray(sideRail.review_candidates) ? sideRail.review_candidates : [];
  const styleProfile = sideRail.style_profile || {};
  return el("aside", { className: "studio-side-rail" }, [
    sectionTitle("References", `${counts.assets || 0}`),
    assets.length ? el("div", { className: "studio-asset-list" }, assets.map(renderAsset)) : el("p", { className: "muted", text: "Add safe summaries before production." }),
    sectionTitle("Style Memory", styleProfile.status || "not_started"),
    styleProfile.summary ? el("p", { className: "card-summary", text: styleProfile.summary }) : el("p", { className: "muted", text: "Review decisions will shape the next pass." }),
    renderPreferences(styleProfile.reusable_preferences || []),
    sectionTitle("Review Queue", `${candidates.length}`),
    candidates.length ? el("div", { className: "studio-review-list" }, candidates.map(renderCandidate)) : el("p", { className: "muted", text: "No review candidates yet." }),
  ]);
}

function renderAsset(asset) {
  return el("article", { className: "studio-asset-card" }, [
    el("span", { text: asset.asset_type || "reference" }),
    el("strong", { text: asset.label || "Asset" }),
    el("small", { text: asset.summary || "safe summary" }),
  ]);
}

function renderCandidate(candidate) {
  return el("button", { className: "studio-review-card", dataset: { variantId: candidate.candidate_id, artifactId: candidate.artifact_id } }, [
    el("strong", { text: candidate.title || "Review candidate" }),
    el("small", { text: candidate.summary || candidate.stage || candidate.status }),
  ]);
}

function renderPreferences(items) {
  if (!items.length) return el("p", { className: "muted", text: "No reusable preference recorded." });
  return el("ul", { className: "studio-memory-list" }, items.slice(0, 4).map((item) => el("li", { text: item })));
}

function renderCanvas(workspace, selectedCardId) {
  const cards = Array.isArray(workspace.canvas?.cards) ? workspace.canvas.cards : [];
  return el("div", { className: "studio-canvas" }, [
    sectionTitle("Production Canvas", workspace.status || "not_started"),
    cards.length ? el("div", { className: "studio-card-grid" }, cards.map((card) => renderCard(card, selectedCardId))) : el("p", { className: "muted", text: "No canvas cards yet." }),
  ]);
}

function renderCard(card, selectedCardId) {
  const tone = statusTone(card.status);
  return el("article", { className: `studio-card ${tone}${card.card_id === selectedCardId ? " selected" : ""}`, dataset: { cardId: card.card_id } }, [
    el("div", { className: "studio-card-head" }, [
      el("h3", { text: card.title || "Untitled" }),
      badge(card.status || "not_started", tone),
    ]),
    card.summary ? el("p", { className: "card-summary", text: card.summary }) : null,
    card.blockers?.length ? el("div", { className: "chips" }, card.blockers.map((item) => badge(item.message || item.blocker_id, "blocked"))) : null,
    card.primary_artifact_id ? button("Open Artifact", "open-artifact-ref", "ghost", { artifactId: card.primary_artifact_id }) : null,
  ]);
}

function renderInspector(inspector, state) {
  const fields = inspector.fields || {};
  return el("aside", { className: "studio-inspector" }, [
    sectionTitle("Inspector", inspector.status || "empty"),
    el("h3", { text: inspector.title || "No card selected" }),
    inspector.summary ? el("p", { className: "card-summary", text: inspector.summary }) : null,
    renderRefs(inspector.refs || []),
    inspector.primary_artifact_id ? button("Open Artifact", "open-artifact-ref", "secondary", { artifactId: inspector.primary_artifact_id }) : null,
    inspector.mode === "scene"
      ? el("div", { className: "inspector-editor" }, [
          textareaField("Prompt", "inspector-prompt", fields.prompt || state.inspectorPrompt, { rows: "4" }),
          textareaField("Reference summary", "inspector-reference-summary", fields.reference_summary || state.inspectorReferenceSummary, { rows: "3" }),
          textareaField("Style direction", "inspector-style-direction", fields.style_direction || state.inspectorStyleDirection, { rows: "3" }),
          textareaField("Retry intent", "inspector-retry-intent", fields.retry_intent || state.inspectorRetryIntent, { rows: "3" }),
          button("Save Inspector", "update-scene-inspector", "primary"),
        ])
      : null,
  ]);
}

function renderRefs(refs) {
  if (!refs.length) return el("p", { className: "muted", text: "No safe preview refs." });
  return el("div", { className: "ref-list" }, refs.map((ref) =>
    el("div", { className: "ref-row" }, [
      el("span", { text: ref.label }),
      el("code", { text: ref.artifact_type || "artifact" }),
      el("code", { text: ref.artifact_id || "pending" }),
    ]),
  ));
}

function renderFilmstrip(items) {
  return el("div", { className: "studio-filmstrip" }, [
    sectionTitle("Filmstrip", `${items.length} scenes`),
    items.length ? el("div", { className: "studio-filmstrip-row" }, items.map(renderFilmstripItem)) : el("p", { className: "muted", text: "Scene sequence appears after cards are drafted." }),
  ]);
}

function renderFilmstripItem(item, index) {
  return el("button", { className: "studio-filmstrip-item", dataset: { cardId: item.card_id } }, [
    el("span", { text: String(index + 1).padStart(2, "0") }),
    el("strong", { text: item.title }),
    el("small", { text: item.summary || item.status }),
  ]);
}

function renderOperationsSummary(summary, providerStatus) {
  const counts = summary.counts || {};
  return el("div", { className: "studio-ops-summary" }, [
    sectionTitle("Runtime", summary.status || "not_started"),
    el("div", { className: "studio-strip-metrics" }, [
      badge(`${counts.jobs || 0} jobs`, counts.jobs ? "ready" : "quiet"),
      badge(`${counts.blocked || 0} blocked`, counts.blocked ? "blocked" : "quiet"),
      badge(`provider ${providerStatus || "ready_not_run"}`, providerStatus === "blocked" ? "blocked" : "quiet"),
    ]),
    summary.primary_artifact_id ? button("Open Provider Artifact", "open-artifact-ref", "ghost", { artifactId: summary.primary_artifact_id }) : null,
  ]);
}
