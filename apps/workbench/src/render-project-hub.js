import { badge, button, el, field } from "./dom.js";
import { displayStatus, displayText } from "./display-labels.js";
import { PROJECT_SHOWCASES } from "./project-showcase-data.js";
import { renderShowcaseDetail } from "./render-project-showcase.js";
import { PROJECT_TEMPLATES } from "./presets.js";
import { statusTone } from "./workbench-state.js";

export function renderProjectHub(projectHub, state = {}) {
  const value = projectHub || {};
  const project = value.active_project || {};
  const counts = value.counts || {};
  const projects = Array.isArray(state.projects) ? state.projects : [];
  if (state.projectPortalMode === "all-projects") {
    return renderProjectDirectory(projects, state.projectId, project, state);
  }
  if (state.projectPortalMode === "showcase-detail") {
    return renderShowcaseDetail(state);
  }
  return el("section", { className: "project-portal" }, [
    renderPortalTopbar(state, projects.length),
    renderHeroStrip(counts),
    renderRecentProjects(projects, state.projectId, project),
    renderShowcase(state),
    state.portalMenuOpen ? renderPortalDrawer() : null,
  ]);
}

function renderPortalTopbar(state, projectCount) {
  return el("header", { className: "portal-topbar" }, [
    el("div", { className: "portal-brand" }, [
      el("button", {
        className: "portal-menu",
        text: "☰",
        dataset: { portalMenu: "open" },
        attrs: { type: "button", "aria-label": "菜单" },
      }),
      el("span", { className: "portal-logo", text: "AFS" }),
      el("strong", { text: "AgentFlow Studio" }),
    ]),
    el("div", { className: "portal-status" }, [
      badge(`运行服务 ${state.health ? displayStatus(state.health.status || "ready") : "未连接"}`, state.health ? "good" : "quiet"),
      badge(`${projectCount} 个项目`, projectCount ? "active" : "quiet"),
      badge("生成能力默认关闭", "blocked"),
    ]),
  ]);
}

function renderHeroStrip(counts) {
  const blockers = Number(counts.provider_blockers || 0);
  const cards = [
    ["内容制作链路", "从素材摘要到分镜、审片和项目记忆复用。", "进入画布", "Create"],
    ["项目记忆工作台", "复用已确认偏好，但不声明长期记忆。", "查看记忆", "Style Memory"],
    ["生成能力门", blockers ? `${blockers} 个阻塞项等待处理。` : "真实模型调用前先完成安全预检。", "看预检", "Jobs"],
  ];
  return el("div", { className: "portal-hero-strip" }, cards.map(([title, summary, action, view], index) =>
    el("button", {
      className: `portal-hero-card portal-hero-${index + 1}`,
      dataset: { view },
      attrs: { type: "button" },
    }, [
      el("span", { text: title }),
      el("strong", { text: summary }),
      el("small", { text: action }),
    ]),
  ));
}

function renderRecentProjects(projects, currentProjectId, activeProject) {
  const recent = projects.slice(0, 5);
  return el("section", { className: "portal-section" }, [
    renderSectionHead("最近项目", "全部项目", "all-projects"),
    el("div", { className: "portal-project-grid" }, [
      renderStartCard(activeProject),
      ...recent.map((project) => renderProjectCard(project, currentProjectId)),
    ]),
  ]);
}

function renderStartCard(activeProject) {
  return el("article", { className: "portal-start-card" }, [
    el("div", { className: "portal-start-plus", text: "+" }),
    el("strong", { text: "开始创作" }),
    el("small", { text: "选择模板，创建项目并进入画布。" }),
    el("div", { className: "portal-template-row" }, PROJECT_TEMPLATES.slice(0, 3).map((item) =>
      button(item.label, "apply-project-template", "ghost", { templateId: item.id }),
    )),
    field("本轮目标", "project-goal", displayText(activeProject.goal || "构建一个受生成能力门保护的内容制作与项目记忆工作台。")),
    el("details", { className: "portal-advanced-id" }, [
      el("summary", { text: "高级项目代号" }),
      field("项目代号", "project-id-action", activeProject.project_id || "proj_runtime_demo"),
      field("项目类型", "project-type", activeProject.project_type || "short_video_campaign"),
    ]),
    el("div", { className: "portal-card-actions" }, [
      el("button", {
        className: "btn primary",
        text: "开始创作",
        dataset: { view: "Create", studioStarter: "open" },
        attrs: { type: "button" },
      }),
      button("创建项目", "create-project", "primary"),
      button("打开项目", "load-project", "secondary"),
    ]),
  ]);
}

function renderProjectCard(project, currentProjectId) {
  const selected = project.project_id === currentProjectId;
  return el("article", { className: `portal-project-card${selected ? " selected" : ""}` }, [
    el("div", { className: "portal-thumb", attrs: { "aria-hidden": "true" } }),
    el("div", { className: "portal-card-copy" }, [
      el("strong", { text: projectTitle(project) }),
      el("small", { text: projectMeta(project) }),
    ]),
    el("div", { className: "portal-card-actions" }, [
      badge(displayStatus(project.status || "in_progress"), statusTone(project.status)),
      button(selected ? "已选中" : "打开", "select-project", "ghost", { projectId: project.project_id }),
    ]),
  ]);
}

function renderShowcase(state) {
  const filter = state.showcaseFilter || "全部";
  const query = String(state.showcaseQuery || "").trim().toLowerCase();
  const filters = ["全部", "短视频", "分镜工作流", "项目记忆", "生成门"];
  const items = PROJECT_SHOWCASES.filter((item) => {
    const filterMatch = filter === "全部" || item.category === filter;
    const queryText = `${item.title} ${item.summary} ${item.tag} ${item.category}`.toLowerCase();
    return filterMatch && (!query || queryText.includes(query));
  });
  return el("section", { className: "portal-section portal-showcase" }, [
    renderSectionHead("精选画布", "查看创作过程", "", "Create"),
    el("div", { className: "portal-filter-row" }, [
      ...filters.map((item) => el("button", {
        className: item === filter ? "selected" : "",
        text: item,
        dataset: { showcaseFilter: item },
        attrs: { type: "button" },
      })),
      el("input", {
        className: "portal-search",
        dataset: { showcaseSearch: "true" },
        attrs: { type: "search", placeholder: "请输入搜索内容", value: state.showcaseQuery || "" },
      }),
    ]),
    el("div", { className: "portal-showcase-grid" }, items.length ? items.map((item) =>
      el("article", { className: "portal-showcase-card" }, [
        el("button", {
          className: `portal-showcase-art portal-showcase-art-${item.palette}`,
          text: item.tag,
          dataset: { showcaseId: item.id, projectPortal: "showcase-detail" },
          attrs: { type: "button" },
        }),
        el("strong", { text: item.title }),
        el("p", { text: item.summary }),
        el("button", {
          text: "查看流程",
          dataset: { showcaseId: item.id, projectPortal: "showcase-detail" },
          attrs: { type: "button" },
        }),
      ]),
    ) : [el("p", { className: "portal-showcase-empty", text: "没有匹配的画布" })]),
  ]);
}

function renderProjectDirectory(projects, currentProjectId, activeProject, state) {
  return el("section", { className: "project-portal portal-directory" }, [
    renderPortalTopbar(state, projects.length),
    el("div", { className: "portal-directory-head" }, [
      el("button", { className: "portal-back", text: "‹ 返回", dataset: { projectPortal: "home" }, attrs: { type: "button" } }),
      el("h2", { text: "全部项目" }),
      el("button", { className: "portal-folder-button", text: "新建文件夹", attrs: { type: "button" } }),
    ]),
    el("div", { className: "portal-directory-grid" }, [
      renderDirectoryStartCard(activeProject),
      ...projects.map((project) => renderProjectCard(project, currentProjectId)),
    ]),
    el("p", { className: "portal-end-note", text: "没有更多了" }),
    state.portalMenuOpen ? renderPortalDrawer() : null,
  ]);
}

function renderPortalDrawer() {
  return el("div", { className: "portal-drawer-layer" }, [
    el("aside", { className: "portal-drawer", attrs: { role: "dialog", "aria-label": "工作台菜单" } }, [
      el("button", {
        className: "portal-drawer-close",
        text: "×",
        dataset: { portalMenu: "close" },
        attrs: { type: "button", "aria-label": "关闭菜单" },
      }),
      el("div", { className: "portal-drawer-account" }, [
        el("span", { className: "portal-drawer-avatar", text: "AF" }),
        el("strong", { text: "AFS 内容制作席位" }),
      ]),
      el("div", { className: "portal-drawer-membership", text: "执行投影已连接" }),
      el("nav", { className: "portal-drawer-nav" }, [
        drawerRow("⌂", "首页", "回到项目创作门户", { projectPortal: "home" }),
        drawerRow("◐", "模式切换", "暗色生产界面 / 诊断信息按需查看", { portalMenu: "close" }),
        drawerRow("◇", "生成能力门", "真实模型调用前必须完成 gate 预检", { view: "Jobs" }),
        drawerRow("↩", "退出登录", "当前版本仅保留占位，不处理账号凭据", { portalMenu: "close" }),
      ]),
      el("footer", { className: "portal-drawer-social" }, [
        el("span", { text: "规则边界" }),
        el("small", { text: "不写入密钥、临时访问地址、模型原始响应或私有素材字节" }),
      ]),
    ]),
    el("button", {
      className: "portal-drawer-scrim",
      text: "",
      dataset: { portalMenu: "close" },
      attrs: { type: "button", "aria-label": "关闭菜单遮罩" },
    }),
  ]);
}

function drawerRow(icon, title, summary, dataset = {}) {
  return el("button", { className: "portal-drawer-row", dataset, attrs: { type: "button" } }, [
    el("span", { text: icon }),
    el("strong", { text: title }),
    el("small", { text: summary }),
  ]);
}

function renderDirectoryStartCard(activeProject) {
  return el("article", { className: "portal-directory-start" }, [
    el("div", { className: "portal-start-plus", text: "+" }),
    el("strong", { text: "开始创作" }),
    el("small", { text: "创建新的视频项目" }),
    field("本轮目标", "project-goal", displayText(activeProject.goal || "构建一个受生成能力门保护的内容制作与项目记忆工作台。")),
    el("details", { className: "portal-advanced-id" }, [
      el("summary", { text: "高级项目代号" }),
      field("项目代号", "project-id-action", activeProject.project_id || "proj_runtime_demo"),
      field("项目类型", "project-type", activeProject.project_type || "short_video_campaign"),
    ]),
    el("button", {
      className: "btn primary",
      text: "开始创作",
      dataset: { view: "Create", studioStarter: "open" },
      attrs: { type: "button" },
    }),
    button("创建项目", "create-project", "secondary"),
  ]);
}

function renderSectionHead(title, action, portalMode = "", view = "") {
  return el("div", { className: "portal-section-head" }, [
    el("h2", { text: title }),
    el("button", {
      text: `${action} ›`,
      dataset: portalMode ? { projectPortal: portalMode } : view ? { view } : {},
      attrs: { type: "button" },
    }),
  ]);
}

function projectTitle(project) {
  const title = displayText(project.goal || project.project_type || "内容项目");
  const questionMarks = (title.match(/\?/g) || []).length;
  if (questionMarks >= 6) return "历史演练项目";
  return title.includes("Stage 7 RC") ? "验收演练项目" : title;
}

function projectMeta(project) {
  const type = displayText(project.project_type || "short_video_campaign");
  const runs = Number(project.run_count || 0);
  const feedback = Number(project.feedback_count || 0);
  const memory = Number(project.profile_version_count || 0);
  return `${type} · ${runs} 次运行 · ${feedback} 条审片 · ${memory} 个记忆版本`;
}
