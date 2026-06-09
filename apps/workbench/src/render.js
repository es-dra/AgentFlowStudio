import { badge, button, el, field } from "./dom.js";
import { renderActionPanel } from "./render-actions.js";
import { renderArtifactPanel } from "./render-artifact.js?v=stage7-rc";
import { renderActivityTimeline } from "./render-activity.js";
import { renderAssetLibrary } from "./render-assets.js?v=stage7-rc";
import { renderCommandHub } from "./render-command-hub.js";
import { renderOperationsWorkspace } from "./render-operations-workspace.js";
import { renderProductionBoard } from "./render-production-board.js";
import { renderProjectHub } from "./render-project-hub.js";
import { renderProjectReadiness } from "./render-readiness.js";
import { renderReviewWorkspace } from "./render-review-workspace.js";
import { renderStyleMemoryWorkspace } from "./render-style-memory-workspace.js";
import { renderStudioWorkspace } from "./render-studio-workspace.js";
import { renderStoryboardWorkspace } from "./render-storyboard-workspace.js";
import { DEFAULT_WORKSPACE_ID, viewActionGroups, workspaceItems, workspaceMeta } from "./workspace-config.js";
import { displayStatus } from "./display-labels.js";

function renderNav(items, activeView) {
  const list = workspaceItems(items);
  return el(
    "nav",
    { className: "rail-nav" },
    list.map((item, index) =>
      el(
        "button",
        {
          className: `rail-item${item.id === activeView || (!activeView && index === 0) ? " active" : ""}`,
          attrs: { "data-view": item.id },
        },
        [
          el("span", { className: "rail-label", text: item.label }),
          el("small", { text: item.summary }),
        ],
      ),
    ),
  );
}

function renderRailHeader() {
  return el("div", { className: "rail-header" }, [
    el("span", { text: "工作区" }),
    el("strong", { text: "内容制作 / 记忆链路" }),
  ]);
}

function renderStatusPanel(state) {
  const health = state.health ? displayStatus(state.health.status || "ready") : "未连接";
  const capabilities = state.capabilities ? Object.keys(state.capabilities).length : 0;
  const projects = Array.isArray(state.projects) ? state.projects.length : 0;
  return el("div", { className: "status-panel" }, [
    badge(`运行服务 ${health}`, state.health ? "good" : "quiet"),
    badge(`${projects} 个项目`, projects ? "active" : "quiet"),
    badge(`${capabilities} 组能力`, capabilities ? "ready" : "quiet"),
  ]);
}

function renderTopbar(state) {
  const active = workspaceMeta(state.activeView || DEFAULT_WORKSPACE_ID);
  return el("header", { className: "topbar" }, [
    el("div", { className: "brand" }, [
      el("span", { className: "brand-mark", text: "AFS" }),
      el("div", {}, [el("h1", { text: "AgentFlow Studio" }), el("p", { text: "内容制作与项目记忆工作台" })]),
    ]),
    el("div", { className: "topbar-context" }, [
      el("span", { text: active.kicker }),
      el("strong", { text: active.label }),
    ]),
    renderStatusPanel(state),
  ]);
}

function renderDiagnosticPanel(state) {
  return el("details", { className: "diagnostic-panel" }, [
    el("summary", { text: "连接与诊断" }),
    field("运行服务地址", "runtime-url", state.baseUrl),
    field("项目 ID", "project-id", state.projectId),
    el("div", { className: "connect-actions" }, [
      button("连接", "connect", "primary"),
      button("加载项目", "load-project", "secondary"),
      button("刷新", "refresh", "ghost"),
    ]),
    el("p", { className: "diagnostic-note", text: "内部 id、产物引用和安全边界只在诊断视图或详情中展开。" }),
  ]);
}

function renderAdvanced(workbench) {
  const evidence = workbench.advanced_evidence;
  return el("details", { className: "advanced" }, [
    el("summary", { text: "高级诊断" }),
    el("p", { text: evidence.safe_ref_policy || workbench.safe_ref_policy || "仅使用安全引用。" }),
    el("div", { className: "chips" }, evidence.non_claims.map((item) => badge(item, "quiet"))),
  ]);
}

function renderWindowHeader(activeView) {
  const meta = workspaceMeta(activeView);
  return el("header", { className: "workspace-header" }, [
    el("div", {}, [
      el("span", { text: meta.kicker }),
      el("h2", { text: meta.label }),
      el("p", { text: meta.summary }),
    ]),
  ]);
}

function withWindow(activeView, panels) {
  return [renderWindowHeader(activeView), ...panels];
}

function viewPanels(activeView, workbench, state) {
  const common = [
    renderProjectReadiness(workbench.project_readiness),
    renderCommandHub(workbench.command_hub),
    renderProductionBoard(workbench.production_board),
  ];
  if (activeView === "Projects") {
    return withWindow(activeView, [
      renderProjectHub(workbench.project_hub),
      renderActionPanel(state, viewActionGroups(activeView)),
      ...common,
      renderArtifactPanel(state),
    ]);
  }
  if (activeView === "Assets") {
    return withWindow(activeView, [
      renderAssetLibrary(workbench.asset_library),
      renderActionPanel(state, viewActionGroups(activeView)),
      ...common,
      renderArtifactPanel(state),
    ]);
  }
  if (activeView === "Storyboard") {
    return withWindow(activeView, [renderStoryboardWorkspace(workbench.studio_workspace, workbench.creation_workspace, state), renderArtifactPanel(state)]);
  }
  if (activeView === "Review") {
    return withWindow(activeView, [
      renderReviewWorkspace(workbench.review_room, workbench.memory_workspace, state),
      renderActionPanel(state, viewActionGroups(activeView)),
      renderArtifactPanel(state),
    ]);
  }
  if (activeView === "Style Memory") {
    return withWindow(activeView, [
      renderStyleMemoryWorkspace(workbench.style_memory, workbench.memory_workspace),
      renderArtifactPanel(state),
    ]);
  }
  if (activeView === "Jobs") {
    return withWindow(activeView, [
      renderOperationsWorkspace(workbench.operations_workspace),
      renderActionPanel(state, viewActionGroups(activeView)),
      renderAdvanced(workbench),
    ]);
  }
  if (activeView === "Settings") {
    return withWindow(activeView, [
      renderAdvanced(workbench),
      renderActivityTimeline(workbench.activity_timeline),
      renderActionPanel(state, viewActionGroups(activeView)),
    ]);
  }
  return withWindow("Create", [
    renderStudioWorkspace(workbench.studio_workspace, state),
    renderArtifactPanel(state),
  ]);
}

function renderWorkspace(state) {
  const workbench = state.workbench;
  if (!workbench) {
    return el("main", { className: "empty-workspace" }, [
      el("span", { className: "empty-kicker", text: "项目入口" }),
      el("h2", { text: "从一个内容项目开始" }),
      el("p", { text: "创建或打开项目后，工作台会进入创作画布、素材库、审片室、项目记忆和任务中心。" }),
      renderActionPanel(state, ["project", "result"]),
    ]);
  }
  const activeView = state.activeView || DEFAULT_WORKSPACE_ID;
  const workspaceClass = activeView === "Create" ? "workspace workspace-canvas-v2" : "workspace";
  return el("main", { className: workspaceClass }, viewPanels(activeView, workbench, state));
}

export function renderApp(root, state) {
  root.replaceChildren(
    el("div", { className: "app-shell" }, [
      renderTopbar(state),
      el("div", { className: "main-layout" }, [
        el("aside", { className: "rail" }, [
          renderRailHeader(),
          renderNav(state.workbench ? state.workbench.navigation : [], state.activeView),
          renderDiagnosticPanel(state),
        ]),
        renderWorkspace(state),
      ]),
      state.error ? el("div", { className: "toast error", text: state.error }) : null,
      state.loading ? el("div", { className: "toast", text: "处理中..." }) : null,
    ]),
  );
}
