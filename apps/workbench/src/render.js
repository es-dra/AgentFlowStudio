import { badge, el } from "./dom.js";
import { renderProjectHub } from "./render-project-hub.js";
import { renderStudioWorkspace } from "./render-studio-workspace.js";
import { renderVisibleAssetsLibrary } from "./render-visible-assets.js";
import { DEFAULT_WORKSPACE_ID, workspaceItems, workspaceMeta } from "./workspace-config.js";

function productNav(activeView) {
  return el("nav", { className: "product-nav" }, workspaceItems().map((item) =>
    el("button", {
      className: item.id === activeView ? "active" : "",
      text: item.label,
      dataset: { view: item.id },
      attrs: { type: "button" },
    }),
  ));
}

function renderDebugPanel(state) {
  if (!state.debugMode) return null;
  const workbench = state.workbench || {};
  return el("aside", { className: "debug-panel" }, [
    el("header", {}, [
      el("strong", { text: "内部调试" }),
      el("small", { text: "Alt+D 可隐藏" }),
    ]),
    el("dl", {}, [
      el("dt", { text: "当前视图" }),
      el("dd", { text: state.activeView || DEFAULT_WORKSPACE_ID }),
      el("dt", { text: "项目" }),
      el("dd", { text: state.projectId || "未选择" }),
      el("dt", { text: "状态" }),
      el("dd", { text: state.health?.status || "未连接" }),
      el("dt", { text: "画布卡片" }),
      el("dd", { text: String(workbench.canvas_cards?.length || 0) }),
    ]),
  ]);
}

function renderView(activeView, state) {
  const workbench = state.workbench || {};
  if (activeView === "Create") return renderStudioWorkspace(workbench.studio_workspace, state);
  if (activeView === "Assets") return renderVisibleAssetsLibrary(state, workbench.studio_workspace);
  return renderProjectHub(workbench.project_hub, state);
}

function renderToast(state) {
  if (state.error) return el("div", { className: "toast error", text: state.error });
  if (state.loading) return el("div", { className: "toast", text: "处理中..." });
  return null;
}

function renderShellHeader(activeView, state) {
  const meta = workspaceMeta(activeView);
  return el("header", { className: "shell-header" }, [
    el("button", {
      className: "shell-brand",
      dataset: { view: "Projects" },
      attrs: { type: "button", "aria-label": "回到首页" },
    }, [
      el("span", { text: "AFS" }),
      el("strong", { text: "AgentFlow Studio" }),
    ]),
    productNav(activeView),
    el("div", { className: "shell-actions" }, [
      badge(meta.kicker, "quiet"),
      el("button", {
        className: "btn primary",
        text: "开始创作",
        dataset: { view: "Create", studioStarter: "open" },
        attrs: { type: "button" },
      }),
    ]),
  ]);
}

export function renderApp(root, state) {
  const activeView = state.activeView || DEFAULT_WORKSPACE_ID;
  const header = activeView === "Create" ? null : renderShellHeader(activeView, state);
  root.replaceChildren(
    el("div", { className: `app-shell libtv-shell app-view-${activeView.toLowerCase()}` }, [
      header,
      renderView(activeView, state),
      renderDebugPanel(state),
      renderToast(state),
    ]),
  );
}
