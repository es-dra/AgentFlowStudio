import { badge, button, el, sectionTitle, textareaField } from "./dom.js";
import { statusTone } from "./workbench-state.js";

export function renderCreationWorkspace(workspace, state) {
  const value = workspace || { canvas_cards: [], filmstrip: [], non_claims: [] };
  const cards = Array.isArray(value.canvas_cards) ? value.canvas_cards : [];
  const selectedCardId = selectedCardIdFor(cards, value, state);
  return [
    renderCanvas(value, selectedCardId),
    renderInspector(selectedInspector(cards, selectedCardId, value.inspector || {}), state),
    renderRunControls(value.run_controls || {}, value.counts || {}),
    renderFilmstrip(value.filmstrip || []),
  ];
}

function selectedCardIdFor(cards, workspace, state) {
  const stateCardId = state && state.selectedCardId;
  if (cards.some((card) => card.card_id === stateCardId)) return stateCardId;
  return workspace.selected_card_id || cards[0]?.card_id || "";
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
    actions: card.actions || [],
    refs: card.refs || [],
    blockers: card.blockers || [],
  };
}

function renderCanvas(workspace, selectedCardId) {
  const cards = Array.isArray(workspace.canvas_cards) ? workspace.canvas_cards : [];
  return el("section", { className: "creation-canvas" }, [
    sectionTitle("Creation Workspace", workspace.status || "not_started"),
    workspace.summary ? el("p", { className: "card-summary", text: workspace.summary }) : null,
    cards.length
      ? el("div", { className: "creation-card-grid" }, cards.map((card) => renderCard(card, workspace.selected_card_id)))
      : el("p", { className: "muted", text: "No creation cards yet." }),
    workspace.non_claims && workspace.non_claims.length ? el("div", { className: "chips" }, workspace.non_claims.map((item) => badge(item, "quiet"))) : null,
  ]);
}

function renderCard(card, selectedCardId) {
  const tone = statusTone(card.status);
  return el("article", { className: `creation-card ${tone}${card.card_id === selectedCardId ? " selected" : ""}`, dataset: { cardId: card.card_id } }, [
    el("div", { className: "creation-card-head" }, [
      el("h3", { text: card.title || "Untitled" }),
      badge(card.status || "not_started", tone),
    ]),
    card.summary ? el("p", { className: "card-summary", text: card.summary }) : null,
    card.blockers && card.blockers.length ? el("div", { className: "chips" }, card.blockers.map((item) => badge(item.message || item.blocker_id, "blocked"))) : null,
    card.primary_artifact_id ? button("Open Artifact", "open-artifact-ref", "ghost", { artifactId: card.primary_artifact_id }) : null,
  ]);
}

function renderInspector(inspector, state) {
  const fields = inspector.fields || {};
  return el("aside", { className: "creation-inspector" }, [
    sectionTitle("Inspector", inspector.status || "empty"),
    el("h3", { text: inspector.title || "No card selected" }),
    inspector.summary ? el("p", { className: "card-summary", text: inspector.summary }) : null,
    inspector.actions && inspector.actions.length
      ? el("div", { className: "action-list" }, inspector.actions.map((item) => badge(item, "ready")))
      : el("p", { className: "muted", text: "No queued action." }),
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
  if (!refs.length) return el("p", { className: "muted", text: "No preview refs." });
  return el("div", { className: "ref-list" }, refs.map((ref) =>
    el("div", { className: "ref-row" }, [
      el("span", { text: ref.label }),
      el("code", { text: ref.artifact_type || "artifact" }),
      el("code", { text: ref.artifact_id || "pending" }),
    ]),
  ));
}

function renderRunControls(runControls, counts) {
  const tone = runControls.blocked_reason ? "blocked" : statusTone(runControls.enabled ? "running" : "ready_not_run");
  return el("section", { className: "creation-run-controls" }, [
    sectionTitle("Run Controls", runControls.handoff_view || "Create"),
    el("p", { className: "card-summary", text: runControls.summary || "Continue the current creation step." }),
    el("div", { className: "creation-metrics" }, [
      badge(`${counts.canvas_cards || 0} cards`, counts.canvas_cards ? "ready" : "quiet"),
      badge(`${counts.filmstrip_items || 0} scenes`, counts.filmstrip_items ? "ready" : "quiet"),
      badge(`${counts.artifact_refs || 0} refs`, counts.artifact_refs ? "active" : "quiet"),
    ]),
    runControls.blocked_reason ? badge(runControls.blocked_reason, "blocked") : null,
    runControls.enabled && runControls.ui_action
      ? button(runControls.primary_label || "Run", runControls.ui_action, "primary")
      : el("button", { className: `btn ghost disabled ${tone}`, text: runControls.primary_label || "Pending", attrs: { disabled: "disabled" } }),
  ]);
}

function renderFilmstrip(filmstrip) {
  const items = Array.isArray(filmstrip) ? filmstrip : [];
  return el("section", { className: "creation-filmstrip" }, [
    sectionTitle("Filmstrip", `${items.length} scenes`),
    items.length
      ? el("div", { className: "creation-filmstrip-row" }, items.map((item, index) =>
          el("button", { className: "creation-filmstrip-item", dataset: { cardId: item.card_id } }, [
            el("span", { text: String(index + 1).padStart(2, "0") }),
            el("strong", { text: item.title }),
            el("small", { text: item.summary || item.status }),
          ]),
        ))
      : el("p", { className: "muted", text: "Add scene cards to build the production sequence." }),
  ]);
}
