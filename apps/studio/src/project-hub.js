import { WORKFLOW_STARTERS } from "./workflow-starters.js";
import { icon } from "./icons.js";
import { el, showModal } from "./overlay.js";

export async function renderProjectHub(options) {
  return openProjectHub(options);
}

const PROJECT_MENU_EVENT = "project_menu";

export async function openProjectHub({
  state,
  projects = [],
  hiddenProjectCount = 0,
  onSwitchProject,
  onCreateProject,
  onStartWorkflow,
  onOpenAssets,
  onOpenHistory,
}) {
  let closeProjectMenu = () => {};
  const modal = el("div", "modal project-hub project-menu");
  modal.dataset.event = PROJECT_MENU_EVENT;

  const closeBtn = el("button", "modal-close project-hub-close");
  closeBtn.type = "button";
  closeBtn.innerHTML = icon("x", 15);
  closeBtn.addEventListener("click", () => closeProjectMenu());

  const head = el("div", "project-menu-head");
  head.appendChild(el("span", "project-menu-kicker", "AFS Studio"));
  head.appendChild(el("h2", "", "项目"));
  head.appendChild(el("p", "", "打开项目、创建新草稿，或回到画布上的创作起点。"));
  head.appendChild(closeBtn);
  modal.appendChild(head);

  modal.appendChild(projectSummary(state));
  modal.appendChild(primaryActions({
    onContinue: () => closeProjectMenu(),
    onCreate: () => {
      closeProjectMenu();
      onCreateProject?.();
    },
  }));
  modal.appendChild(projectEntrypoints((starterId) => {
    closeProjectMenu();
    onStartWorkflow?.(starterId);
  }));
  modal.appendChild(libraryLinks({
    onAssets: () => {
      closeProjectMenu();
      onOpenAssets?.();
    },
    onHistory: () => {
      closeProjectMenu();
      onOpenHistory?.();
    },
  }));
  modal.appendChild(recentProjects(projects, hiddenProjectCount, (projectId) => {
    closeProjectMenu();
    onSwitchProject?.(projectId);
  }));

  closeProjectMenu = showModal(modal);
  return closeProjectMenu;
}

function projectSummary(state) {
  const section = el("section", "project-menu-summary");
  const copy = el("div", "project-menu-copy");
  copy.appendChild(el("strong", "", state.meta.projectName || "未命名项目"));
  copy.appendChild(el("span", "", state.meta.canvasName || "画布 1"));
  const metrics = el("div", "project-menu-metrics");
  metrics.appendChild(metric("节点", state.order.length));
  metrics.appendChild(metric("素材", state.assets.length));
  metrics.appendChild(metric("生成中", generatingCount(state)));
  section.append(copy, metrics);
  return section;
}

function metric(label, value) {
  const item = el("span", "project-menu-metric");
  item.innerHTML = `<b>${escapeHtml(value)}</b><small>${escapeHtml(label)}</small>`;
  return item;
}

function primaryActions({ onContinue, onCreate }) {
  const row = el("div", "project-menu-actions");
  const current = el("button", "primary-btn", "继续当前项目");
  current.type = "button";
  current.addEventListener("click", onContinue);
  const create = el("button", "ghost-btn", "新建项目");
  create.type = "button";
  create.addEventListener("click", onCreate);
  row.append(current, create);
  return row;
}

function projectEntrypoints(onStartWorkflow) {
  const section = el("section", "project-menu-section project-menu-starters");
  section.appendChild(sectionHead("创作起点", "主入口已放到画布里，这里只保留快速创建。"));
  const list = el("div", "project-menu-list");
  for (const starter of WORKFLOW_STARTERS) {
    const item = el("button", "project-menu-row");
    item.type = "button";
    item.innerHTML = [
      `<span class="project-menu-icon">${icon(starter.icon, 15)}</span>`,
      `<span><strong>${escapeHtml(starter.label)}</strong><small>${escapeHtml(starter.tag || starter.summary)}</small></span>`,
      `<em>创建</em>`,
    ].join("");
    item.addEventListener("click", () => onStartWorkflow?.(starter.id));
    list.appendChild(item);
  }
  section.appendChild(list);
  return section;
}

function libraryLinks({ onAssets, onHistory }) {
  const row = el("div", "project-menu-links");
  row.appendChild(menuLink("素材库", "folder", onAssets));
  row.appendChild(menuLink("作品库", "frames", onHistory));
  return row;
}

function menuLink(label, iconName, onClick) {
  const button = el("button", "project-menu-link");
  button.type = "button";
  button.innerHTML = `${icon(iconName, 14)}<span>${escapeHtml(label)}</span>`;
  if (typeof onClick === "function") {
    button.addEventListener("click", onClick);
  } else {
    button.disabled = true;
  }
  return button;
}

function recentProjects(projects, hiddenProjectCount, onSwitchProject) {
  const section = el("section", "project-menu-section");
  section.appendChild(sectionHead("最近项目", "只显示摘要，不暴露本地路径或原始素材。"));
  const list = el("div", "project-menu-list");
  const recent = projects.slice(0, 5);
  if (!recent.length) {
    list.appendChild(el("div", "project-menu-empty", "暂无其他项目。"));
  }
  for (const project of recent) {
    const item = el("button", "project-menu-row project-menu-project");
    item.type = "button";
    item.innerHTML = [
      "<span class=\"project-menu-icon\">",
      icon("grid", 15),
      "</span>",
      `<span><strong>${escapeHtml(projectLabel(project))}</strong><small>${escapeHtml(project.project_id || "local state")}</small></span>`,
      `<em>${escapeHtml(project.updated_at || project.created_at || "打开")}</em>`,
    ].join("");
    item.addEventListener("click", () => onSwitchProject?.(project.project_id));
    list.appendChild(item);
  }
  section.appendChild(list);
  if (hiddenProjectCount) {
    section.appendChild(el("p", "project-menu-note", `已折叠 ${hiddenProjectCount} 个测试项目，可在顶部项目菜单展开。`));
  }
  return section;
}

function sectionHead(title, subtitle) {
  const head = el("div", "project-menu-section-head");
  head.appendChild(el("h3", "", title));
  head.appendChild(el("p", "", subtitle));
  return head;
}

function generatingCount(state) {
  return Object.values(state.nodes || {}).filter((node) => node.status === "generating").length;
}

function projectLabel(project) {
  return project?.studio_state_meta?.projectName || project?.goal || project?.project_id || "未命名项目";
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
