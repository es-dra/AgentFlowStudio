import { icon } from "./icons.js";
import { el } from "./overlay.js";

export function renderTopbar(options) {
  const {
    state,
    store,
    runtime,
    projectSummaries,
    projectOptions,
    hiddenProjectCount,
    showAllProjects,
    onToggleProjectFilter,
    onSwitchProject,
    onCreateProject,
    onOpenHome,
  } = options;
  const topbar = document.getElementById("topbar");
  const signature = [
    state.meta.projectId,
    state.ui.drawerOpen,
    state.meta.projectName,
    state.meta.canvasName,
    state.ui.saveState,
    state.ui.saveMessage,
    showAllProjects ? "all-projects" : "studio-projects",
    projectSummaries.map((item) => item.project_id).join(","),
  ].join("|");
  if (topbar.dataset.signature === signature) return;
  topbar.dataset.signature = signature;
  topbar.classList.toggle("drawer-open", state.ui.drawerOpen);
  topbar.replaceChildren();

  if (!state.ui.drawerOpen) {
    renderCompactTopbar(topbar, { state, store, runtime, projectOptions, hiddenProjectCount, showAllProjects, onToggleProjectFilter, onSwitchProject, onCreateProject, onOpenHome });
  } else {
    topbar.appendChild(studioHomeButton(onOpenHome));
    appendProjectControls(topbar, { runtime, projectOptions, hiddenProjectCount, showAllProjects, onToggleProjectFilter, onSwitchProject, onCreateProject });
  }

  topbar.appendChild(el("div", "topbar-spacer"));
  const right = el("div", "topbar-right");
  const save = el("span", `save-pill ${saveClass(state.ui.saveState)}`, state.ui.saveState || "本地暂存");
  if (state.ui.saveMessage) save.title = state.ui.saveMessage;
  right.appendChild(save);
  topbar.appendChild(right);
}

function renderCompactTopbar(topbar, options) {
  const { state, store, projectOptions, onOpenHome } = options;
  const openDrawer = el("button", "icon-btn drawer-restore");
  openDrawer.innerHTML = icon("panel", 15);
  openDrawer.title = "展开侧栏";
  openDrawer.addEventListener("click", () => store.set((s) => { s.ui.drawerOpen = true; }, { history: false, persist: false }));
  topbar.appendChild(openDrawer);

  topbar.appendChild(el("div", "topbar-logo", "AFS"));
  topbar.appendChild(studioHomeButton(onOpenHome));

  const title = el("div", "topbar-title compact-project");
  title.appendChild(el("span", "proj-name", state.meta.projectName));
  title.appendChild(el("span", "divider"));
  title.appendChild(el("span", "canvas-name", `${state.meta.canvasName} ▾`));
  topbar.appendChild(title);

  appendProjectControls(topbar, { ...options, projectOptions });
}

function studioHomeButton(onOpenHome) {
  const home = el("button", "icon-btn studio-home-btn");
  home.innerHTML = `${icon("grid", 14)}<span>工作台</span>`;
  home.title = "打开创作工作台";
  home.addEventListener("click", onOpenHome);
  return home;
}

function appendProjectControls(topbar, options) {
  const { runtime, projectOptions, hiddenProjectCount, showAllProjects, onToggleProjectFilter, onSwitchProject, onCreateProject } = options;
  const projectSelect = el("select", "project-select");
  projectSelect.title = "切换项目";
  for (const item of projectOptions) {
    const option = document.createElement("option");
    option.value = item.project_id;
    option.textContent = projectLabel(item);
    option.selected = item.project_id === runtime.projectId;
    projectSelect.appendChild(option);
  }
  projectSelect.addEventListener("change", () => onSwitchProject(projectSelect.value));
  topbar.appendChild(projectSelect);

  const newProject = el("button", "icon-btn");
  newProject.innerHTML = icon("plus", 14);
  newProject.title = "新建项目";
  newProject.addEventListener("click", onCreateProject);
  topbar.appendChild(newProject);
  appendProjectFilterToggle(topbar, { hiddenProjectCount, showAllProjects, onToggleProjectFilter });
}

function appendProjectFilterToggle(topbar, { hiddenProjectCount, showAllProjects, onToggleProjectFilter }) {
  if (!hiddenProjectCount && !showAllProjects) return;
  const toggle = el("button", "icon-btn project-noise-toggle");
  toggle.innerHTML = icon("more", 14);
  toggle.title = showAllProjects ? "收起测试项目" : `显示全部项目（隐藏 ${hiddenProjectCount} 个测试项目）`;
  toggle.addEventListener("click", onToggleProjectFilter);
  topbar.appendChild(toggle);
}

function projectLabel(item) {
  return item.studio_state_meta?.projectName || item.goal || item.project_id;
}

function saveClass(state) {
  if (state === "已保存") return "saved";
  if (state === "保存中" || state === "同步中") return "saving";
  return "local";
}
