import { currentLocale, message, setLocale } from "./i18n.js";

const DESKTOP_NAV = [
  ["overview", "workspace"],
  ["projects", "projects"],
  ["episodes", "episodes"],
  ["crew", "crew"],
  ["review", "review"],
  ["delivery", "delivery"],
];

const MOBILE_NAV = [
  ["overview", "overview"],
  ["todo", "todo"],
  ["review", "review"],
  ["delivery", "delivery"],
];

export function createProductShell(options = {}) {
  let locale = currentLocale();
  let section = "overview";
  let snapshot = { loading: true, workspace: null, project: null, error: "", authUser: null };

  function render(next = {}) {
    snapshot = { ...snapshot, ...next };
    const root = document.getElementById("product-shell-root");
    if (!root) return;
    root.replaceChildren();
    root.append(buildSidebar(), buildWorkspace());
    root.appendChild(buildMobileNav());
  }

  function buildSidebar() {
    const sidebar = node("aside", "product-sidebar");
    sidebar.setAttribute("aria-label", "产品导航");
    const brand = node("div", "product-brand");
    brand.innerHTML = '<span class="product-brand-mark" aria-hidden="true">A</span><strong>AgentFlow Studio</strong>';
    sidebar.appendChild(brand);
    const nav = node("nav", "product-nav");
    for (const [key, labelKey] of DESKTOP_NAV) {
      nav.appendChild(navButton(key, message(labelKey, locale), section === key));
    }
    sidebar.appendChild(nav);
    const workspace = node("div", "product-workspace-switcher");
    workspace.append(
      node("span", "product-label", locale === "zh-CN" ? "当前工作空间" : "Current workspace"),
      node("strong", "", snapshot.workspace?.workspace?.label || (locale === "zh-CN" ? "内容制作工作空间" : "Content production")),
    );
    sidebar.appendChild(workspace);
    return sidebar;
  }

  function buildWorkspace() {
    const wrap = node("section", "product-workspace");
    wrap.appendChild(buildHeader());
    const main = node("main", "product-main");
    main.id = "product-main";
    main.tabIndex = -1;
    if (snapshot.loading) main.appendChild(statePanel("loading"));
    else if (snapshot.error) main.appendChild(statePanel("error"));
    else if (!snapshot.project) main.appendChild(statePanel("empty"));
    else main.appendChild(sectionContent());
    wrap.appendChild(main);
    return wrap;
  }

  function buildHeader() {
    const header = node("header", "product-header");
    const identity = node("div", "product-breadcrumb");
    identity.append(
      node("span", "", message("workspace", locale)),
      node("span", "breadcrumb-separator", "/"),
      node("strong", "", snapshot.project?.name || message("projects", locale)),
      node("span", "breadcrumb-separator", "/"),
      node("span", "", snapshot.project?.episode || message("episodes", locale)),
    );
    const actions = node("div", "product-header-actions");
    const language = node("button", "product-quiet-button", locale === "zh-CN" ? "简体中文" : "English");
    language.type = "button";
    language.setAttribute("aria-label", `${message("language", locale)}：${language.textContent}`);
    language.addEventListener("click", () => {
      locale = setLocale(locale === "zh-CN" ? "en" : "zh-CN");
      render();
    });
    actions.appendChild(language);
    if (snapshot.authUser) {
      const account = node("button", "product-account-button", userLabel(snapshot.authUser));
      account.type = "button";
      account.setAttribute("aria-label", message("signOut", locale));
      account.addEventListener("click", () => options.onSignOut?.());
      actions.appendChild(account);
    }
    header.append(identity, actions);
    return header;
  }

  function sectionContent() {
    if (section === "projects") return projectsView();
    if (section === "crew") return crewView();
    if (section === "review" || section === "todo") return decisionsView();
    if (section === "delivery") return deliveryView();
    if (section === "episodes") return overviewView(true);
    return overviewView(false);
  }

  function overviewView(episodeFocus) {
    const project = snapshot.project;
    const fragment = document.createDocumentFragment();
    const head = node("div", "product-page-heading");
    const copy = node("div");
    copy.append(
      node("h1", "", episodeFocus ? project.episode : message("productionOverview", locale)),
      node("p", "", `${project.name} · ${project.current_stage || "待开始"} · ${project.progress_percent || 0}%`),
    );
    const canvas = node("button", "product-primary-button", message("enterCanvas", locale));
    canvas.type = "button";
    canvas.addEventListener("click", () => options.onOpenCanvas?.());
    head.append(copy, canvas);
    fragment.appendChild(head);
    fragment.appendChild(stageRail(project.stages || []));

    const grid = node("div", "product-overview-grid");
    grid.append(
      decisionPanel(project.decision_inbox),
      nextActionPanel(project),
      crewPanel(project.crew),
      deliveryPanel(project.delivery, project.canonical_state),
    );
    fragment.appendChild(grid);
    return fragment;
  }

  function stageRail(stages) {
    const rail = node("ol", "product-stage-rail");
    rail.setAttribute("aria-label", "单集制作阶段");
    for (const stage of stages) {
      const item = node("li", `product-stage ${stage.state || "not_started"}`);
      item.append(node("span", "stage-dot"), node("strong", "", stage.label || "制作阶段"), node("small", "", stageState(stage.state)));
      rail.appendChild(item);
    }
    return rail;
  }

  function decisionPanel(inbox = {}) {
    const panel = surface(message("decisions", locale), inbox.pending_count || 0, () => setSection("review"));
    const items = Array.isArray(inbox.items) ? inbox.items : [];
    if (!items.length) panel.body.appendChild(emptyLine(locale === "zh-CN" ? "当前没有待决策事项" : "No creator decisions pending"));
    for (const item of items.slice(0, 3)) {
      const row = node("article", "product-list-row decision-row");
      row.append(node("span", "decision-symbol", "◆"), textStack(item.title, item.priority === "high" ? "需要优先处理" : "等待主创确认"));
      const button = node("button", "product-link-button", item.action_label || message("impact", locale));
      button.type = "button";
      button.addEventListener("click", () => setSection("review"));
      row.appendChild(button);
      panel.body.appendChild(row);
    }
    return panel.wrap;
  }

  function nextActionPanel(project) {
    const panel = surface(locale === "zh-CN" ? "下一步行动" : "Next action");
    const action = node("div", "next-action-callout");
    action.append(node("span", "next-action-marker", "→"), textStack(project.next_action || "继续制作", project.current_stage || ""));
    panel.body.appendChild(action);
    const checks = [
      ["主创决策", project.decision_inbox?.pending_count || 0],
      ["制作阻塞", project.crew?.blocked_count || 0],
      ["待重新确认", project.decision_inbox?.reconfirmation_count || 0],
    ];
    for (const [label, count] of checks) {
      const row = node("div", "product-summary-row");
      row.append(node("span", "", label), node("strong", count ? "attention" : "", String(count)));
      panel.body.appendChild(row);
    }
    return panel.wrap;
  }

  function crewPanel(crew = {}) {
    const panel = surface(message("crewActivity", locale), crew.active_count || 0, () => setSection("crew"));
    const activities = Array.isArray(crew.activities) ? crew.activities : [];
    if (!activities.length) panel.body.appendChild(emptyLine(locale === "zh-CN" ? "剧组尚未领取制作任务" : "No active crew assignments"));
    for (const item of activities.slice(0, 5)) {
      const row = node("article", "product-list-row crew-row");
      row.append(node("span", "crew-avatar", String(item.role || "剧").slice(0, 1)), textStack(item.role, item.responsibility));
      row.appendChild(node("span", "product-status-text", item.state));
      panel.body.appendChild(row);
    }
    return panel.wrap;
  }

  function deliveryPanel(delivery = {}, canon = {}) {
    const panel = surface(message("deliveryReadiness", locale), delivery.delivered ? "完成" : "");
    const percent = delivery.delivered ? 100 : delivery.export_ready ? 80 : delivery.quality_reviewed ? 60 : delivery.candidate_selected ? 40 : 20;
    const readiness = node("div", "delivery-readiness");
    const meter = node("div", "delivery-meter");
    meter.appendChild(node("strong", "", `${percent}%`));
    meter.style.setProperty("--progress", `${percent * 3.6}deg`);
    const facts = node("div", "delivery-facts");
    for (const [label, value] of [
      ["候选版本", delivery.candidate_selected],
      ["质量审核", delivery.quality_reviewed],
      ["可导出", delivery.export_ready],
      ["下游已确认", canon.propagation_complete],
    ]) {
      const row = node("div", "product-summary-row");
      row.append(node("span", "", label), node("strong", value ? "ok" : "", value ? "已就绪" : "待完成"));
      facts.appendChild(row);
    }
    readiness.append(meter, facts);
    panel.body.append(readiness, node("p", "surface-footnote", delivery.message || ""));
    return panel.wrap;
  }

  function projectsView() {
    const wrap = node("section", "product-section-view");
    wrap.appendChild(viewHeading(message("projects", locale), snapshot.workspace?.projects?.length || 0));
    const list = node("div", "product-project-list");
    for (const project of snapshot.workspace?.projects || []) {
      const button = node("button", `project-row ${project.project_id === snapshot.project?.project_id ? "active" : ""}`);
      button.type = "button";
      button.append(textStack(project.name, `${project.episode} · ${project.current_stage}`), node("strong", "", `${project.progress_percent}%`));
      button.addEventListener("click", () => options.onSwitchProject?.(project.project_id));
      list.appendChild(button);
    }
    wrap.appendChild(list);
    return wrap;
  }

  function crewView() {
    const wrap = node("section", "product-section-view");
    wrap.append(viewHeading(message("crew", locale), snapshot.project.crew?.registered_role_count || 0), crewPanel(snapshot.project.crew));
    return wrap;
  }

  function decisionsView() {
    const wrap = node("section", "product-section-view");
    wrap.append(viewHeading(message(section === "todo" ? "todo" : "review", locale), snapshot.project.decision_inbox?.pending_count || 0), decisionPanel(snapshot.project.decision_inbox));
    return wrap;
  }

  function deliveryView() {
    const wrap = node("section", "product-section-view");
    wrap.append(viewHeading(message("delivery", locale), snapshot.project.delivery?.export_count || 0), deliveryPanel(snapshot.project.delivery, snapshot.project.canonical_state));
    return wrap;
  }

  function buildMobileNav() {
    const nav = node("nav", "product-mobile-nav");
    nav.setAttribute("aria-label", "移动端导航");
    for (const [key, labelKey] of MOBILE_NAV) nav.appendChild(navButton(key, message(labelKey, locale), section === key));
    return nav;
  }

  function navButton(key, label, active) {
    const button = node("button", active ? "active" : "", label);
    button.type = "button";
    button.dataset.section = key;
    button.setAttribute("aria-current", active ? "page" : "false");
    button.addEventListener("click", () => setSection(key));
    return button;
  }

  function setSection(next) {
    section = next;
    render();
    requestAnimationFrame(() => document.getElementById("product-main")?.focus());
  }

  async function refresh(runtime, authUser = null) {
    const requestRuntime = runtime;
    snapshot = { ...snapshot, loading: true, error: "", authUser };
    render();
    try {
      const workspace = await requestRuntime.workspaceOverview();
      if (options.isRuntimeCurrent && !options.isRuntimeCurrent(requestRuntime)) return;
      const activeProjectId = requestRuntime.projectId && requestRuntime.projectId !== "studio-empty"
        ? requestRuntime.projectId
        : workspace?.projects?.[0]?.project_id || "";
      let project = null;
      if (activeProjectId) {
        const projectRuntime = activeProjectId === requestRuntime.projectId
          ? requestRuntime
          : options.createRuntime?.(activeProjectId);
        const payload = await projectRuntime?.projectOverview?.();
        if (options.isRuntimeCurrent && !options.isRuntimeCurrent(requestRuntime)) return;
        project = payload?.project || null;
      }
      snapshot = { loading: false, workspace, project, error: "", authUser };
    } catch (error) {
      if (options.isRuntimeCurrent && !options.isRuntimeCurrent(requestRuntime)) return;
      snapshot = {
        ...snapshot,
        loading: false,
        project: null,
        error: options.formatError?.(error) || message("error", locale),
        authUser,
      };
    }
    render();
  }

  function showOverview() {
    const app = document.getElementById("app");
    app?.classList.remove("canvas-mode");
    app?.classList.add("product-mode");
    setSection("overview");
  }

  function showCanvas() {
    if (!document.getElementById("studio-editor-shell")) return false;
    const app = document.getElementById("app");
    app?.classList.remove("product-mode");
    app?.classList.add("canvas-mode");
    return true;
  }

  function statePanel(kind) {
    const wrap = node("section", `product-state product-state-${kind}`);
    wrap.setAttribute("role", kind === "error" ? "alert" : "status");
    if (kind === "loading") {
      wrap.append(node("div", "state-spinner"), node("h1", "", message("loading", locale)));
    } else if (kind === "error") {
      wrap.append(node("h1", "", message("error", locale)), node("p", "", snapshot.error), node("p", "", message("recovery", locale)));
      const retry = node("button", "product-primary-button", message("retry", locale));
      retry.addEventListener("click", () => options.onRetry?.());
      wrap.appendChild(retry);
    } else {
      wrap.append(node("h1", "", message("empty", locale)), node("p", "", message("emptyCopy", locale)));
    }
    return wrap;
  }

  return { render, refresh, showOverview, showCanvas, setSection, get section() { return section; } };
}

export function showSecureEntry(messageText, { error = false } = {}) {
  const app = document.getElementById("app");
  app.className = "identity-pending";
  app.replaceChildren();
  const secure = document.createElement("section");
  secure.id = "secure-entry";
  secure.setAttribute("aria-live", "polite");
  secure.innerHTML = '<span class="secure-brand">AgentFlow Studio</span><p></p>';
  secure.querySelector("p").textContent = messageText;
  secure.classList.toggle("error", error);
  const overlay = document.createElement("div");
  overlay.id = "overlay-root";
  app.append(secure, overlay);
}

function surface(title, count = "", onMore = null) {
  const wrap = node("section", "product-surface");
  const head = node("header", "product-surface-head");
  const titleWrap = node("div");
  titleWrap.append(node("h2", "", title));
  if (count !== "") titleWrap.appendChild(node("span", "surface-count", String(count)));
  head.appendChild(titleWrap);
  if (onMore) {
    const more = node("button", "product-link-button", "查看全部");
    more.type = "button";
    more.addEventListener("click", onMore);
    head.appendChild(more);
  }
  const body = node("div", "product-surface-body");
  wrap.append(head, body);
  return { wrap, body };
}

function viewHeading(title, count) {
  const head = node("div", "product-page-heading");
  const copy = node("div");
  copy.append(node("h1", "", title), node("p", "", `共 ${count} 项`));
  head.appendChild(copy);
  return head;
}

function textStack(title, copy) {
  const stack = node("span", "product-text-stack");
  stack.append(node("strong", "", title || "—"), node("small", "", copy || ""));
  return stack;
}

function emptyLine(text) {
  return node("p", "product-empty-line", text);
}

function stageState(value) {
  return value === "completed" ? "已完成" : value === "in_progress" ? "进行中" : "未开始";
}

function userLabel(user) {
  return String(user?.display_name || user?.email || "账户").slice(0, 32);
}

function node(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== "") element.textContent = String(text);
  return element;
}
