import { badge, button, el, field } from "./dom.js";
import { renderActionPanel } from "./render-actions.js";
import { renderArtifactPanel } from "./render-artifact.js";
import { renderActivityTimeline } from "./render-activity.js";
import { renderAssetLibrary } from "./render-assets.js";
import { renderCommandHub } from "./render-command-hub.js";
import { renderMemoryWorkspace } from "./render-memory-workspace.js";
import { renderOperationsWorkspace } from "./render-operations-workspace.js";
import { renderProductionBoard } from "./render-production-board.js";
import { renderProjectHub } from "./render-project-hub.js";
import { renderProjectReadiness } from "./render-readiness.js";
import { renderStudioWorkspace } from "./render-studio-workspace.js";

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
      renderMemoryWorkspace(workbench.memory_workspace, state),
      renderActivityTimeline(workbench.activity_timeline),
      renderActionPanel(state, viewActionGroups(activeView)),
      renderArtifactPanel(state),
    ];
  }
  if (activeView === "Style Memory") {
    return [
      ...common,
      renderMemoryWorkspace(workbench.memory_workspace, state),
      renderActivityTimeline(workbench.activity_timeline),
      renderArtifactPanel(state),
    ];
  }
  if (activeView === "Jobs") {
    return [
      ...common,
      renderOperationsWorkspace(workbench.operations_workspace),
      renderActionPanel(state, viewActionGroups(activeView)),
      renderAdvanced(workbench),
    ];
  }
  if (activeView === "Settings") {
    return [
      ...common,
      renderActionPanel(state, viewActionGroups(activeView)),
      renderActivityTimeline(workbench.activity_timeline),
      renderAdvanced(workbench),
    ];
  }
  return [
    renderStudioWorkspace(workbench.studio_workspace, state),
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
