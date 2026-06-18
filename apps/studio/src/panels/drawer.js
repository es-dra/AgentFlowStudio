import { el } from "../overlay.js";
import { renderAssetDrawer } from "./drawer-assets.js";
import { renderJobCenter } from "./job-center.js";
import { renderProjectNavigator } from "./project-navigator.js";

const DRAWER_TABS = [
  ["canvas", "画布"],
  ["assets", "素材"],
  ["jobs", "进度"],
  ["history", "作品"],
];

export function renderDrawer(state, store, runtime) {
  const drawer = document.getElementById("drawer");
  drawer.classList.toggle("collapsed", !state.ui.drawerOpen);
  const signature = drawerSignature(state);
  if (drawer.dataset.signature === signature) return;
  drawer.dataset.signature = signature;
  drawer.replaceChildren();

  drawer.appendChild(drawerHeader());
  drawer.appendChild(projectLabel(state));
  drawer.appendChild(tabBar(state, store));

  const body = el("div", "drawer-body");
  if (state.ui.drawerTab === "canvas") renderProjectNavigator(state, store, body);
  else if (state.ui.drawerTab === "assets") renderAssetDrawer(state, store, runtime, drawer, body);
  else if (state.ui.drawerTab === "jobs") renderJobCenter(state, store, body, "jobs");
  else renderJobCenter(state, store, body, "history");
  drawer.appendChild(body);
  drawer.appendChild(drawerFooter(state, store));
}

function drawerHeader() {
  const head = el("div", "drawer-head");
  head.appendChild(el("div", "topbar-logo", "▣"));
  return head;
}

function projectLabel(state) {
  const proj = el("div", "drawer-project");
  proj.appendChild(el("span", "proj-name", state.meta.projectName));
  proj.appendChild(el("span", "", "|"));
  proj.appendChild(el("span", "", `${state.meta.canvasName} ▾`));
  return proj;
}

function tabBar(state, store) {
  const tabs = el("div", "drawer-tabs");
  for (const [id, label] of DRAWER_TABS) {
    const tab = el("button", `drawer-tab${state.ui.drawerTab === id ? " active" : ""}`, label);
    tab.addEventListener("click", () => store.set((s) => { s.ui.drawerTab = id; }));
    tabs.appendChild(tab);
  }
  return tabs;
}

function drawerFooter(state, store) {
  const foot = el("div", "drawer-foot");
  const collapse = el("button", "icon-btn", "↤");
  collapse.title = "收起节点侧栏";
  collapse.addEventListener("click", () => store.set((s) => { s.ui.drawerOpen = false; }));
  foot.appendChild(collapse);
  foot.appendChild(el("span", "", `共 ${state.order.length} 节点`));
  return foot;
}

function drawerSignature(state) {
  return [
    state.meta.projectId, state.meta.projectName, state.meta.canvasName,
    state.ui.drawerOpen, state.ui.drawerTab,
    state.ui.drawerSearch, state.ui.assetLifecycleFilter, state.ui.navigatorSearch,
    state.order.join(","),
    state.selection.nodeIds.join(","),
    Object.keys(state.groups).join(","),
    state.assets.length,
    ...Object.values(state.nodes).map((n) => n.title),
    ...state.assets.map((asset) => `${asset.title}:${asset.safe_summary}:${asset.source_node_id}:${asset.asset_id || asset.visual_asset_id || asset.id}:${asset.status || asset.asset_status || ""}:${asset.runtime_status || ""}`),
    ...Object.values(state.nodes).flatMap((node) => (node.params?.visualAssets || []).map((asset) => `${node.id}:${asset.asset_id}:${asset.status || ""}:${asset.runtime_status || ""}:${asset.disabled_reason || ""}`)),
  ].join("|");
}
