import { icon } from "../icons.js";
import { el, showModal } from "../overlay.js";

const DEFAULT_FIXTURE_MODE = "default_unconfirmed";
const CONFIRMED_FIXTURE_MODE = "confirmed_local_fixture";
const NON_CLAIM_BOUNDARY_LABELS = [
  "not_package_complete",
  "not_provider_smoke",
  "not_provider_pass",
  "not_generated_media_qa",
  "not_human_acceptance",
  "not_product_readiness",
  "not_human_creative_acceptance",
  "not_business_validation",
];

export function openAcceptedGenerationPlanPanel(runtime) {
  const modal = el("div", "modal compact accepted-generation-plan-modal");
  const head = el("div", "modal-head accepted-generation-plan-head");
  head.appendChild(el("strong", "", "Generation plan review"));
  head.appendChild(el("small", "", "Provider-closed / not yet accepted"));
  const closeBtn = el("button", "modal-close");
  closeBtn.type = "button";
  closeBtn.innerHTML = icon("x", 15);
  head.appendChild(el("span", "head-spacer"));
  head.appendChild(closeBtn);

  const body = el("div", "modal-body accepted-generation-plan-body");
  const controls = el("div", "accepted-plan-controls");
  const defaultBtn = modeButton("Default package (blocked)", DEFAULT_FIXTURE_MODE);
  const confirmedBtn = modeButton("Fixture demo (blocked)", CONFIRMED_FIXTURE_MODE);
  controls.append(defaultBtn, confirmedBtn);
  const content = el("div", "accepted-plan-content");
  body.append(controls, content);
  modal.append(head, body);

  const close = showModal(modal);
  closeBtn.addEventListener("click", close);

  const load = async (fixtureMode) => {
    setActiveMode(controls, fixtureMode);
    renderLoading(content, fixtureMode);
    try {
      const response = await runtime.previewAcceptedGenerationPlanPacket({
        fixture_mode: fixtureMode,
        generated_at: new Date().toISOString(),
      });
      renderPlan(content, response);
    } catch (error) {
      renderError(content, error);
    }
  };
  defaultBtn.addEventListener("click", () => load(DEFAULT_FIXTURE_MODE));
  confirmedBtn.addEventListener("click", () => load(CONFIRMED_FIXTURE_MODE));
  load(DEFAULT_FIXTURE_MODE);
  return close;
}

function modeButton(label, fixtureMode) {
  const button = el("button", "accepted-plan-mode", label);
  button.type = "button";
  button.dataset.fixtureMode = fixtureMode;
  return button;
}

function setActiveMode(controls, fixtureMode) {
  for (const button of controls.querySelectorAll(".accepted-plan-mode")) {
    button.classList.toggle("active", button.dataset.fixtureMode === fixtureMode);
  }
}

function renderLoading(content, fixtureMode) {
  content.replaceChildren();
  const panel = el("div", "accepted-plan-empty");
  panel.innerHTML = `${icon("layers", 20)}<strong>Loading ${escapeHtml(fixtureMode)}</strong><small>Plan preview only. No provider call is started; not yet accepted.</small>`;
  content.appendChild(panel);
}

function renderError(content, error) {
  content.replaceChildren();
  const panel = el("div", "accepted-plan-error");
  panel.innerHTML = `${icon("x", 18)}<strong>needs_attention</strong><small>${escapeHtml(error?.message || "Runtime request failed")}</small>`;
  content.appendChild(panel);
}

function renderPlan(content, response) {
  content.replaceChildren();
  const evidence = response?.operator_evidence || {};
  const state = evidence.state || {};
  const provenance = evidence.provenance || {};
  const blockers = evidence.residual_blockers || {};
  const nonClaims = evidence.non_claim_boundaries || {};
  const packet = response?.packet || {};

  const status = el("section", `accepted-plan-status ${state.accepted ? "accepted" : "blocked"}`);
  const acceptedTitle = provenance.source_mode === "project_artifact"
    ? "Plan step-gate evidence recorded for review"
    : "Local fixture demo remains blocked and not accepted";
  const statusCopy = state.accepted
    ? `${acceptedTitle}; not package complete, not human acceptance`
    : "needs_attention · Blocked pending prerequisites";
  status.innerHTML = [
    `<span>${icon(state.accepted ? "check" : "lock", 18)}</span>`,
    `<div><strong>${escapeHtml(statusCopy)}</strong>`,
    `<small>${escapeHtml(packet.packet_state || state.packet_state || "unknown")}</small></div>`,
  ].join("");
  content.appendChild(status);

  content.appendChild(metricGrid([
    ["Plan review state", state.accepted ? "step-gate evidence recorded" : "needs_attention"],
    ["State", state.packet_state || ""],
    ["Request", state.request_state || ""],
    ["Source", provenance.source_mode || provenance.evidence_origin || ""],
  ]));
  content.appendChild(listSection("Blocked reasons / next actions", [
    ...(blockers.blocked_reasons || []),
    ...(blockers.pending_branch_asset_refs || []),
    ...(blockers.unresolved_open_question_refs || []),
  ], "No blocked reason returned in this preview packet."));
  content.appendChild(listSection("Residual closure refs", blockers.residual_closure_refs || [], "No residual closures are recorded."));
  content.appendChild(listSection(
    "Non-claim boundaries",
    nonClaims.explicit_non_claims || NON_CLAIM_BOUNDARY_LABELS,
    "No non-claim boundary was returned.",
  ));
  content.appendChild(metricGrid([
    ["Provider calls", nonClaims.provider_calls_started ? "started" : "not started"],
    ["Provider pass", "not claimed"],
    ["Media QA", "not claimed"],
    ["Human acceptance", "not claimed"],
    ["Package complete", "not claimed"],
    ["Product readiness", "not claimed"],
    ["Business validation", "not claimed"],
  ]));
}

function metricGrid(items) {
  const grid = el("div", "accepted-plan-metrics");
  for (const [label, value] of items) {
    const item = el("div", "accepted-plan-metric");
    item.appendChild(el("small", "", label));
    item.appendChild(el("strong", "", value || "-"));
    grid.appendChild(item);
  }
  return grid;
}

function listSection(title, items, emptyCopy) {
  const section = el("section", "accepted-plan-section");
  section.appendChild(el("h4", "", title));
  const list = el("div", "accepted-plan-list");
  const values = Array.isArray(items) ? items.filter(Boolean) : [];
  if (!values.length) {
    list.appendChild(el("p", "accepted-plan-list-empty", emptyCopy));
  } else {
    for (const value of values.slice(0, 10)) list.appendChild(el("span", "", value));
  }
  section.appendChild(list);
  return section;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}
