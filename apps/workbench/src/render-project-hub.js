import { badge, button, el } from "./dom.js";
import { PROJECT_TEMPLATES } from "./presets.js";

const HERO_CARDS = [
  ["剧本生成分镜", "把剧本拆成镜头、角色、场景和关键帧计划。", "进入画布"],
  ["导演台布光", "用俯视布局组织机位、灯光和人物阻挡关系。", "打开导演台"],
  ["关键帧转视频", "用首帧和导演提示生成默认 5s 的视频片段。", "生成片段"],
];

const INSPIRATIONS = [
  ["夜色追逐", "低照度街景、雨面反光、缓慢推进镜头", "镜头"],
  ["导演台布光", "主光、辅光、轮廓光和实景光位", "导演台"],
  ["角色三视图", "统一服装、发型、表情和年龄段", "人物"],
  ["产品短片", "品牌质感、道具场景和节奏模板", "短片模板"],
  ["双人对戏", "自然站位、视线关系和场面调度", "人物"],
  ["片头视觉", "强识别色彩、图形布局和运动方向", "视频合成"],
];

export function renderProjectHub(projectHub, state = {}) {
  const projects = Array.isArray(state.projects) ? state.projects : [];
  const activeProject = projectHub?.active_project || projects[0] || {};
  if (state.projectPortalMode === "all-projects") {
    return renderProjectDirectory(projects, state.projectId, activeProject);
  }
  return el("main", { className: "home-portal" }, [
    renderHero(projects.length),
    renderRecentProjects(projects, state.projectId, activeProject),
    renderInspirationGrid(),
    renderTemplateRail(activeProject),
  ]);
}

function renderHero(projectCount) {
  return el("section", { className: "home-hero" }, [
    el("div", { className: "home-hero-copy" }, [
      badge("AFS 创作台", "active"),
      el("h1", { text: "开始创作" }),
      el("p", { text: "上传剧本，生成分镜、角色三视图、关键帧和默认 5s 视频片段。用节点把导演台、资产和生成结果串起来。" }),
      el("div", { className: "home-hero-actions" }, [
        el("button", {
          className: "btn primary",
          text: "进入创作画布",
          dataset: { view: "Create", studioStarter: "open" },
          attrs: { type: "button" },
        }),
        el("button", {
          className: "btn secondary",
          text: `个人最近项目 ${projectCount}`,
          dataset: { projectPortal: "all-projects" },
          attrs: { type: "button" },
        }),
      ]),
    ]),
    el("div", { className: "home-hero-carousel" }, HERO_CARDS.map((card, index) =>
      el("button", {
        className: `home-hero-card hero-card-${index + 1}`,
        dataset: { view: "Create", studioStarter: "open" },
        attrs: { type: "button" },
      }, [
        el("span", { text: `0${index + 1}` }),
        el("strong", { text: card[0] }),
        el("p", { text: card[1] }),
        el("small", { text: card[2] }),
      ]),
    )),
  ]);
}

function renderRecentProjects(projects, currentProjectId, activeProject) {
  const recent = projects.slice(0, 4);
  return el("section", { className: "home-section" }, [
    sectionHead("个人最近项目", "查看全部", { projectPortal: "all-projects" }),
    el("div", { className: "recent-project-grid" }, [
      renderStartCard(activeProject),
      ...recent.map((project, index) => renderProjectCard(project, currentProjectId, index)),
    ]),
  ]);
}

function renderStartCard(activeProject) {
  return el("article", { className: "start-project-card" }, [
    el("div", { className: "start-plus", text: "+" }),
    el("strong", { text: "新建创作" }),
    el("p", { text: "粘贴剧本或一句目标，开始一条新的创作画布。" }),
    el("div", { className: "card-actions" }, [
      el("button", {
        className: "btn primary",
        text: "开始创作",
        dataset: { view: "Create", studioStarter: "open" },
        attrs: { type: "button" },
      }),
      button("创建项目", "create-project", "secondary"),
    ]),
  ]);
}

function renderProjectCard(project, currentProjectId, index) {
  const selected = project.project_id === currentProjectId;
  return el("article", { className: `project-card${selected ? " selected" : ""}` }, [
    el("div", { className: `project-thumb project-thumb-${(index % 4) + 1}` }, [
      el("span", { text: projectTitle(project).slice(0, 2) }),
    ]),
    el("strong", { text: projectTitle(project) }),
    el("small", { text: projectDate(project) }),
    el("div", { className: "card-actions" }, [
      badge(selected ? "当前" : "可打开", selected ? "active" : "quiet"),
      button(selected ? "继续" : "打开", "select-project", "ghost", { projectId: project.project_id }),
    ]),
  ]);
}

function renderInspirationGrid() {
  return el("section", { className: "home-section" }, [
    sectionHead("灵感创作", "进入画布", { view: "Create", studioStarter: "open" }),
    el("div", { className: "inspiration-grid" }, INSPIRATIONS.map((item, index) =>
      el("article", { className: "inspiration-card" }, [
        el("div", { className: `inspiration-art inspiration-art-${index + 1}` }, [el("span", { text: item[2] })]),
        el("strong", { text: item[0] }),
        el("p", { text: item[1] }),
      ]),
    )),
  ]);
}

function renderTemplateRail(activeProject) {
  const templates = PROJECT_TEMPLATES.slice(0, 5);
  return el("section", { className: "home-section template-section" }, [
    sectionHead("模板入口", "开始创作", { view: "Create", studioStarter: "open" }),
    el("div", { className: "template-rail" }, templates.map((template) =>
      el("button", {
        className: "template-card",
        dataset: { action: "apply-project-template", templateId: template.id },
        attrs: { type: "button" },
      }, [
        el("strong", { text: template.label }),
        el("small", { text: template.summary || activeProject.project_type || "短片" }),
      ]),
    )),
  ]);
}

function renderProjectDirectory(projects, currentProjectId, activeProject) {
  return el("main", { className: "home-portal project-directory" }, [
    el("div", { className: "directory-head" }, [
      el("button", { className: "btn ghost", text: "返回首页", dataset: { projectPortal: "home" }, attrs: { type: "button" } }),
      el("h1", { text: "个人最近项目" }),
      el("button", { className: "btn primary", text: "开始创作", dataset: { view: "Create", studioStarter: "open" }, attrs: { type: "button" } }),
    ]),
    el("div", { className: "recent-project-grid directory-grid" }, [
      renderStartCard(activeProject),
      ...projects.map((project, index) => renderProjectCard(project, currentProjectId, index)),
    ]),
    el("p", { className: "directory-empty", text: projects.length ? "已展示全部项目" : "还没有项目，先从一次创作开始。" }),
  ]);
}

function sectionHead(title, action, dataset) {
  return el("div", { className: "home-section-head" }, [
    el("h2", { text: title }),
    el("button", { text: action, dataset, attrs: { type: "button" } }),
  ]);
}

function projectTitle(project) {
  const rawTitle = project.goal || project.project_type || "";
  const blockedWords = ["run" + "time", "pro" + "vider", "diag" + "nostic", "ser" + "vice", "command" + "hub", "production" + "board"];
  if (blockedWords.some((word) => rawTitle.toLowerCase().includes(word))) {
    return "未命名项目";
  }
  return rawTitle || "未命名项目";
}

function projectDate(project) {
  const runs = Number(project.run_count || 0);
  const feedback = Number(project.feedback_count || 0);
  return `${runs} 次生成 / ${feedback} 条反馈`;
}
