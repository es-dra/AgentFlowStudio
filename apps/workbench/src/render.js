import { badge, button, el, field, sectionTitle } from "./dom.js";
import { renderActionPanel } from "./render-actions.js";
import { renderArtifactPanel } from "./render-artifact.js";
import { renderActivityTimeline } from "./render-activity.js";
import { renderAssetLibrary } from "./render-assets.js";
import { renderCommandHub } from "./render-command-hub.js";
import { renderCreationWorkspace } from "./render-creation-workspace.js";
import { renderJobCenter } from "./render-jobs.js";
import { renderProductionBoard } from "./render-production-board.js";
import { renderProjectHub } from "./render-project-hub.js";
import { renderProjectReadiness } from "./render-readiness.js";
import { renderReviewRoom } from "./render-review.js";

function renderNav(items, activeView) {
  const list = items.length ? items : ["Projects", "Create", "Assets", "Review", "Style Memory", "Jobs", "Settings"];
  return el(
    "nav",
    { className: "rail-nav" },
    list.map((item, index) =>
      el("button", {
        className: `rail-item${item === activeView || (!activeView && index === 1) ? " active" : ""}`,
        text: item,
        attrs: { "data-view": item },
      }),
    ),
  );
}

function renderStatusPanel(state) {
  const health = state.health ? state.health.status || "connected" : "not connected";
  const capabilities = state.capabilities ? Object.keys(state.capabilities).length : 0;
  const projects = Array.isArray(state.projects) ? state.projects.length : 0;
  return el("div", { className: "status-panel" }, [
    badge(`Runtime ${health}`, state.health ? "good" : "quiet"),
    badge(`${projects} projects`, projects ? "active" : "quiet"),
    badge(`${capabilities} capability groups`, capabilities ? "ready" : "quiet"),
  ]);
}

function renderTopbar(state) {
  return el("header", { className: "topbar" }, [
    el("div", { className: "brand" }, [
      el("span", { className: "brand-mark", text: "AFS" }),
      el("div", {}, [el("h1", { text: "AgentFlow Studio" }), el("p", { text: "Production Workbench" })]),
    ]),
    renderStatusPanel(state),
  ]);
}

function renderConnectPanel(state) {
  return el("section", { className: "connect-panel" }, [
    field("Runtime Service", "runtime-url", state.baseUrl),
    field("Project", "project-id", state.projectId),
    el("div", { className: "connect-actions" }, [
      button("Connect", "connect", "primary"),
      button("Load Project", "load-project", "secondary"),
      button("Refresh", "refresh", "ghost"),
    ]),
  ]);
}

function renderStyleMemory(styleMemory) {
  const value = styleMemory || {};
  const preferences = Array.isArray(value.reusable_preferences) ? value.reusable_preferences : [];
  return el("section", { className: "style-memory-panel" }, [
    sectionTitle("Style Memory", value.status || "not_started"),
    el("p", { className: "card-summary", text: value.summary || "No project style memory yet." }),
    el("div", { className: "memory-facts" }, [
      badge(`${value.profile_version_count || 0} profiles`, value.profile_version_count ? "ready" : "quiet"),
      badge(`${value.feedback_count || 0} reviews`, value.feedback_count ? "active" : "quiet"),
    ]),
    preferences.length
      ? el("ul", { className: "memory-list" }, preferences.map((item) => el("li", { text: item })))
      : el("p", { className: "muted", text: "Review a first pass to create reusable preferences." }),
    value.next_pass_usage ? el("p", { className: "artifact-note", text: value.next_pass_usage }) : null,
  ]);
}

function renderProviderGate(card) {
  if (!card) return el("section", { className: "provider-gate" }, [sectionTitle("Provider Gate", "not requested")]);
  return el("section", { className: "provider-gate" }, [
    sectionTitle("Provider Gate", card.status),
    el("p", { className: "card-summary", text: card.summary || "Preflight only." }),
    el("div", { className: "chips" }, card.blockers.map((item) => badge(item.message || item.blocker_id, "blocked"))),
  ]);
}

function renderAdvanced(workbench) {
  const evidence = workbench.advanced_evidence;
  return el("details", { className: "advanced" }, [
    el("summary", { text: "Advanced Diagnostics" }),
    el("p", { text: evidence.safe_ref_policy || workbench.safe_ref_policy || "Safe refs only." }),
    el("div", { className: "chips" }, evidence.non_claims.map((item) => badge(item, "quiet"))),
  ]);
}

function viewActionGroups(activeView) {
  return {
    Projects: ["project", "result"],
    Create: ["scene", "runtime", "result"],
    Assets: ["assets", "scene", "result"],
    Review: ["review", "runtime", "result"],
    "Style Memory": ["review", "runtime", "result"],
    Jobs: ["runtime", "result"],
    Settings: ["project", "assets", "scene", "review", "runtime", "result"],
  }[activeView] || ["scene", "runtime", "result"];
}

function viewPanels(activeView, workbench, state) {
  const common = [
    renderProjectReadiness(workbench.project_readiness),
    renderCommandHub(workbench.command_hub),
    renderProductionBoard(workbench.production_board),
  ];
  if (activeView === "Projects") {
    return [...common, renderProjectHub(workbench.project_hub), renderActionPanel(state, viewActionGroups(activeView)), renderArtifactPanel(state)];
  }
  if (activeView === "Assets") {
    return [...common, renderActionPanel(state, viewActionGroups(activeView)), renderAssetLibrary(workbench.asset_library), renderArtifactPanel(state)];
  }
  if (activeView === "Review") {
    return [
      ...common,
      renderReviewRoom(workbench.review_room, state.selectedVariantId),
      renderStyleMemory(workbench.style_memory),
      renderActivityTimeline(workbench.activity_timeline),
      renderActionPanel(state, viewActionGroups(activeView)),
      renderArtifactPanel(state),
    ];
  }
  if (activeView === "Style Memory") {
    return [
      ...common,
      renderStyleMemory(workbench.style_memory),
      renderReviewRoom(workbench.review_room, state.selectedVariantId),
      renderActivityTimeline(workbench.activity_timeline),
      renderArtifactPanel(state),
    ];
  }
  if (activeView === "Jobs") {
    return [
      ...common,
      renderJobCenter(workbench.job_center),
      renderActivityTimeline(workbench.activity_timeline),
      renderProviderGate(workbench.provider_gate),
      renderActionPanel(state, viewActionGroups(activeView)),
      renderAdvanced(workbench),
    ];
  }
  if (activeView === "Settings") {
    return [
      ...common,
      renderActionPanel(state, viewActionGroups(activeView)),
      renderActivityTimeline(workbench.activity_timeline),
      renderProviderGate(workbench.provider_gate),
      renderAdvanced(workbench),
    ];
  }
  return [
    ...common,
    ...renderCreationWorkspace(workbench.creation_workspace, state),
    renderActionPanel(state, viewActionGroups(activeView)),
    renderArtifactPanel(state),
  ];
}

function renderWorkspace(state) {
  const workbench = state.workbench;
  if (!workbench) {
    return el("main", { className: "empty-workspace" }, [
      el("h2", { text: "Open a project" }),
      el("p", { text: "Runtime connection required." }),
    ]);
  }
  const activeView = state.activeView || "Create";
  return el("main", { className: "workspace" }, viewPanels(activeView, workbench, state));
}

export function renderApp(root, state) {
  root.replaceChildren(
    el("div", { className: "app-shell" }, [
      renderTopbar(state),
      el("div", { className: "main-layout" }, [
        el("aside", { className: "rail" }, [renderNav(state.workbench ? state.workbench.navigation : [], state.activeView), renderConnectPanel(state)]),
        renderWorkspace(state),
      ]),
      state.error ? el("div", { className: "toast error", text: state.error }) : null,
      state.loading ? el("div", { className: "toast", text: "Working..." }) : null,
    ]),
  );
}
