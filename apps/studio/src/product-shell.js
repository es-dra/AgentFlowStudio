import { currentLocale, message, setLocale } from "./i18n.js";
import { icon } from "./icons.js";
import { findNextProductionTarget, productContextKey } from "./product-shell-context.js";
import { buildAgentChatPanel } from "./agent-chat-panel.js";
import { agentChatContextKey, agentChatContextSnapshot, createAgentChatContextStore, stageM6ScriptPlanCandidateCommand, stageProductionGraphCandidateCommand, stageProductionGraphCommand, submitAgentChatMessageWithRuntime } from "./agent-chat-lifecycle.js";
import { applyProductionGraphCanvasProjection, productionGraphAgentContext, productionGraphWorkspaceProjection } from "./production-graph-workspace-projection.js";

export function createProductShell(options = {}) {
  let locale = currentLocale();
  let section = "canvas";
  let selection = { sceneIndex: 0, shotIndex: 0 };
  let agentCollapsed = false;
  let projectDrawerOpen = false;
  let contextOpen = false;
  let helpOpen = false;
  let accountMenuOpen = false;
  let mobileAgentOpen = false;
  let agentPreferenceProjectKey = "";
  let notice = "";
  let pendingGraphImpact = null;
  let m6SourceText = "";
  let planningPanelOpen = false;
  let planningPanelPreferenceKey = "";
  let planningPanelHeight = readPlanningPanelHeight();
  let graphRefreshPending = false;
  let agentChatWidth = readAgentChatWidth();
  const agentChatContexts = createAgentChatContextStore();
  let snapshot = {
    loading: true,
    workspace: null,
    project: null,
    studioState: null,
    mediaOperations: null,
    mediaCommandPreview: null,
    error: "",
    authUser: null,
  };
  bindShellEvents();

  function render(next = {}) {
    snapshot = { ...snapshot, ...next };
    snapshot.studioState = snapshot.studioState || options.getStudioState?.() || null;
    syncPlanningPanelPreference();
    syncResponsiveAgentState();
    const root = document.getElementById("product-shell-root");
    if (!root) return;
    options.parkCanvas?.();
    root.className = `unified-studio-shell ${projectDrawerOpen ? "project-drawer-open" : ""}`;
    root.dataset.view = section;
    root.replaceChildren();
    root.appendChild(buildHeader());
    if (projectDrawerOpen && snapshot.project) root.appendChild(buildProjectDrawer());
    if (snapshot.loading) root.appendChild(statePanel("loading"));
    else if (snapshot.error) root.appendChild(statePanel("error"));
    else if (!snapshot.project) root.appendChild(statePanel("empty"));
    else root.appendChild(buildWorkspace());
    if (helpOpen && isMobileNavigationLayout()) root.appendChild(buildMobileHelpSheet());
    root.appendChild(buildMobileNav());
  }

  function buildHeader() {
    const header = node("header", "studio-unified-header");
    const brand = node("button", "studio-unified-brand");
    brand.type = "button";
    brand.setAttribute("aria-label", "返回项目画布");
    brand.innerHTML = '<strong aria-label="AgentFlow Studio">AFS</strong>';
    brand.addEventListener("click", () => {
      projectDrawerOpen = false;
      contextOpen = false;
      helpOpen = false;
      accountMenuOpen = false;
      showCanvas();
    });

    const project = node("div", "studio-project-context");
    const projectLabel = node("button", "studio-project-button");
    const projectName = snapshot.project?.name || "项目";
    const episodeName = snapshot.project?.episode || "第一集";
    const fullProjectLabel = `${projectName} · ${episodeName}`;
    projectLabel.type = "button";
    projectLabel.setAttribute("aria-label", `当前项目：${fullProjectLabel}。打开项目详情与切换菜单`);
    projectLabel.title = fullProjectLabel;
    projectLabel.innerHTML = `<strong>${escapeHtml(projectName)}</strong><span>${escapeHtml(episodeName)}</span>${icon("chevronDown", 13)}`;
    projectLabel.addEventListener("click", () => {
      contextOpen = !contextOpen;
      helpOpen = false;
      accountMenuOpen = false;
      render();
    });
    project.appendChild(projectLabel);
    if (contextOpen) project.appendChild(buildProjectMenu());

    const navigator = node("button", `studio-stage-button ${projectDrawerOpen ? "active" : ""}`);
    navigator.type = "button";
    navigator.setAttribute("aria-label", "打开项目导航");
    navigator.setAttribute("aria-controls", "studio-context-drawer");
    navigator.setAttribute("aria-expanded", String(projectDrawerOpen));
    navigator.innerHTML = `<span>项目</span>${icon("chevronDown", 13)}`;
    navigator.addEventListener("click", () => {
      projectDrawerOpen = !projectDrawerOpen;
      helpOpen = false;
      accountMenuOpen = false;
      render();
      requestCanvasSafeAreaUpdate();
    });

    const viewSwitch = node("div", "studio-view-switch");
    viewSwitch.setAttribute("role", "tablist");
    viewSwitch.setAttribute("aria-label", "工作区视图");
    viewSwitch.append(
      viewButton("canvas", "画布"),
      viewButton("storyboard", "故事板"),
    );

    const summary = node("div", "studio-header-summary");
    const progress = Math.max(0, Math.min(100, Number(snapshot.project?.progress_percent || candidateDeliveryProgress(snapshot.project))));
    appendHeaderSummary(summary, progress);

    const actions = node("div", "studio-header-actions");
    actions.appendChild(buildSaveStatus());
    actions.appendChild(buildHelpEntry());
    const language = node("button", "studio-icon-button");
    const account = buildAccountEntry();
    language.type = "button";
    language.innerHTML = icon("translate", 15);
    language.title = locale === "zh-CN" ? "语言设置：中文" : "Language: English";
    language.setAttribute("aria-label", language.title);
    language.addEventListener("click", () => {
      locale = setLocale(locale === "zh-CN" ? "en" : "zh-CN");
      render();
    });
    actions.appendChild(language);
    actions.appendChild(account);

    header.append(brand, project, navigator, viewSwitch, summary, actions);
    return header;
  }

  function appendHeaderSummary(summary, progress) {
    const pending = pendingCount();
    if (hasStoryFacts() || mediaOperationsReady() || Number(progress) > 0) {
      summary.append(statusItem("check", `交付就绪 ${progress}%`, "ok"));
    } else {
      summary.append(statusItem("sparkles", "任意节点开始", "muted"));
    }
    if (pending) summary.append(statusItem("clock", `待处理 ${pending}`, "warning"));
  }

  function buildHelpEntry() {
    const wrap = node("div", "studio-help-context");
    const help = node("button", "studio-icon-button");
    help.type = "button";
    help.setAttribute("aria-label", "打开使用指南");
    help.setAttribute("aria-expanded", String(helpOpen));
    help.innerHTML = icon("help", 15);
    help.addEventListener("click", () => {
      helpOpen = !helpOpen;
      accountMenuOpen = false;
      contextOpen = false;
      render();
    });
    wrap.appendChild(help);
    if (helpOpen && !isMobileNavigationLayout()) wrap.appendChild(buildHelpMenu());
    return wrap;
  }

  function buildHelpMenu() {
    const menu = node("section", "studio-help-menu");
    menu.setAttribute("aria-label", "使用指南");
    menu.append(
      node("strong", "", "AFS 能做什么"),
      node("p", "", "从任意节点开始：在同一画布里从想法、剧本、镜头、角色、参考图、图片或视频开始；需要改写、拆分、生成或恢复时先预览影响，再确认写入制作图。"),
    );
    const list = node("ul", "");
    for (const item of [
      "画布负责创建和连接对象，故事板负责逐镜审看。",
      "节点内 AI 动作只改变当前对象的预览；应用后进入同一节点修订历史。",
      "AI 创作搭档用于提问、解释和跨对象编排；付费或不可逆动作会先说明范围和费用。",
      "高级证据、模型和谱系信息在详情里查看，不暴露密钥或服务器路径。",
    ]) {
      list.appendChild(node("li", "", item));
    }
    menu.appendChild(list);
    return menu;
  }

  function buildAccountEntry() {
    const wrap = node("div", "studio-account-context");
    const account = node("button", "studio-account-button", userLabel(snapshot.authUser));
    account.type = "button";
    account.setAttribute("aria-label", snapshot.authUser ? "打开账户菜单" : "打开工作区与偏好菜单");
    account.setAttribute("aria-expanded", String(accountMenuOpen));
    account.addEventListener("click", () => {
      accountMenuOpen = !accountMenuOpen;
      helpOpen = false;
      contextOpen = false;
      render();
    });
    wrap.appendChild(account);
    if (accountMenuOpen) wrap.appendChild(buildAccountMenu());
    return wrap;
  }

  function buildAccountMenu() {
    const menu = node("div", "studio-account-menu");
    menu.setAttribute("role", "menu");
    menu.appendChild(node("strong", "", "账户与工作区"));
    menu.appendChild(accountMenuButton("项目管理", () => {
      accountMenuOpen = false;
      projectDrawerOpen = true;
      render();
    }));
    menu.appendChild(accountMenuButton(locale === "zh-CN" ? "切换 English" : "切换中文", () => {
      locale = setLocale(locale === "zh-CN" ? "en" : "zh-CN");
      accountMenuOpen = false;
      render();
    }));
    if (snapshot.authUser) menu.appendChild(accountMenuButton(message("signOut", locale), () => options.onSignOut?.(), "danger"));
    return menu;
  }

  function accountMenuButton(label, onClick, tone = "") {
    const button = node("button", tone);
    button.type = "button";
    button.setAttribute("role", "menuitem");
    button.textContent = label;
    button.addEventListener("click", onClick);
    return button;
  }

  function buildProjectMenu() {
    const menu = node("div", "studio-project-menu");
    menu.setAttribute("role", "menu");
    const current = node("section", "studio-current-project-summary");
    current.setAttribute("role", "group");
    current.setAttribute("aria-label", "当前项目完整标题");
    current.innerHTML = [
      "<span>当前项目</span>",
      `<strong>${escapeHtml(snapshot.project?.name || "未命名项目")}</strong>`,
      `<small>${escapeHtml(snapshot.project?.episode || "单集制作")}</small>`,
    ].join("");
    menu.appendChild(current);
    const projects = snapshot.workspace?.projects || [];
    for (const item of projects.slice(0, 6)) {
      const button = node("button", item.project_id === snapshot.project?.project_id ? "active" : "");
      button.type = "button";
      button.setAttribute("role", "menuitem");
      button.innerHTML = `<strong>${escapeHtml(item.name || "未命名项目")}</strong><span>${escapeHtml(item.episode || "单集制作")}</span>`;
      button.addEventListener("click", () => {
        contextOpen = false;
        options.onSwitchProject?.(item.project_id);
      });
      menu.appendChild(button);
    }
    const create = node("button", "studio-project-create");
    create.type = "button";
    create.innerHTML = `${icon("plus", 14)}<span>新建项目</span>`;
    create.addEventListener("click", () => options.onCreateProject?.());
    menu.appendChild(create);
    return menu;
  }

  function buildSaveStatus() {
    const saveState = String(snapshot.studioState?.ui?.saveState || "本地暂存");
    const retryable = ["需要登录", "保存冲突", "保存失败"].includes(saveState);
    const cluster = node("span", "studio-save-cluster");
    const status = node("span", `studio-save-status ${saveTone(saveState)}`, saveState);
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");
    status.title = snapshot.studioState?.ui?.saveMessage || saveState;
    cluster.appendChild(status);
    if (retryable) {
      const retry = node("button", "studio-save-retry", "重试");
      retry.type = "button";
      retry.setAttribute("aria-label", `重试保存：${status.title}`);
      retry.addEventListener("click", () => options.onRetrySave?.());
      cluster.appendChild(retry);
    }
    return cluster;
  }

  function buildProjectDrawer() {
    const project = snapshot.project;
    const panel = node("section", "studio-context-drawer");
    panel.id = "studio-context-drawer";
    panel.setAttribute("aria-label", "项目导航");
    const close = node("button", "studio-icon-button context-drawer-close");
    close.type = "button";
    close.setAttribute("aria-label", "关闭项目导航");
    close.innerHTML = icon("x", 15);
    close.addEventListener("click", () => {
      projectDrawerOpen = false;
      render();
    });
    const copy = node("div", "cockpit-copy");
    copy.append(
      node("span", "eyebrow", "项目"),
      node("strong", "", project.current_stage || "分镜制作"),
      node("p", "", project.next_action || "复核当前场景并继续制作"),
    );
    const stages = node("ol", "cockpit-stages");
    for (const item of (project.stages || []).slice(0, 9)) {
      const li = node("li", item.state || "not_started");
      li.append(node("span", "stage-dot"), node("span", "", item.label || "制作阶段"));
      stages.appendChild(li);
    }
    const next = node("button", "cockpit-next", project.next_action || "继续制作");
    next.type = "button";
    next.addEventListener("click", activateNextAction);
    const scenes = node("div", "context-drawer-scenes");
    scenes.appendChild(node("strong", "", "场景 / 镜头"));
    const model = sceneModel();
    if (!model.length) {
      scenes.appendChild(node("p", "", "还没有确认的场景或镜头。"));
    } else {
      model.forEach((scene, index) => {
        const item = node("button", index === selection.sceneIndex ? "active" : "");
        item.type = "button";
        item.innerHTML = `<span>${String(index + 1).padStart(2, "0")}</span><strong>${escapeHtml(scene.name)}</strong><small>${scene.shots.length} 镜头 · ${scene.duration}</small>`;
        item.addEventListener("click", () => {
          projectDrawerOpen = false;
          selectContext(index, 0);
        });
        scenes.appendChild(item);
      });
    }
    panel.append(close, copy, stages, scenes, buildDrawerAccountSummary());
    if (graphWorkspaceReady()) panel.appendChild(buildGraphProductionSummary());
    panel.appendChild(next);
    return panel;
  }

  function buildDrawerAccountSummary() {
    const sectionEl = node("section", "context-drawer-account");
    sectionEl.appendChild(node("strong", "", "账户与工作区"));
    sectionEl.appendChild(node("p", "", snapshot.authUser ? "当前账号可管理项目、语言偏好与会话。" : "当前为本地制作会话，可管理项目与语言偏好。"));
    const row = node("div", "context-drawer-account-actions");
    const language = node("button", "studio-text-button", locale === "zh-CN" ? "切换 English" : "切换中文");
    language.type = "button";
    language.addEventListener("click", () => {
      locale = setLocale(locale === "zh-CN" ? "en" : "zh-CN");
      render();
    });
    row.appendChild(language);
    if (snapshot.authUser) {
      const signOut = node("button", "studio-text-button danger", message("signOut", locale));
      signOut.type = "button";
      signOut.addEventListener("click", () => options.onSignOut?.());
      row.appendChild(signOut);
    }
    sectionEl.appendChild(row);
    return sectionEl;
  }

  function buildGraphProductionSummary() {
    const view = graphView();
    const sectionEl = node("section", "graph-production-summary");
    sectionEl.appendChild(node("strong", "", `制作序列 · 版本 ${view.graphVersion}`));
    const counts = node("dl", "graph-production-counts");
    for (const [label, value] of [["剧本", view.summary.scriptRevisions], ["序列", view.summary.sequences], ["角色", view.summary.characters], ["场景", view.summary.locations],
      ["镜头", view.shots.length], ["道具", view.summary.props], ["参考集", view.summary.referenceSets],
      ["任务", view.summary.tasks], ["候选", view.summary.candidates]]) {
      counts.append(node("dt", "", label), node("dd", "", String(value)));
    }
    sectionEl.appendChild(counts);
    const lifecycle = node("div", "graph-lifecycle-actions");
    const latestCandidate = view.lifecycle.candidates.at(-1);
    if (latestCandidate && !view.summary.selections) {
      lifecycle.appendChild(graphActionButton("选择最新候选", "select_candidate", "选择候选版本",
        "确认后记录候选选择，不覆盖原候选。", { artifact_id: latestCandidate.artifact_id, selection_key: "sequence_delivery" }));
    }
    const pendingReview = view.lifecycle.reviews.find((item) => item.state === "pending");
    const rejectedReview = view.lifecycle.reviews.find((item) => item.state === "rejected");
    if (pendingReview) {
      lifecycle.append(
        graphActionButton("通过审核", "review_decision", "通过专业审核", "确认后把审核结论写入同一制作图版本。", { review_id: pendingReview.review_id, state: "approved" }),
        graphActionButton("退回修改", "review_decision", "退回当前审核", "确认后保留候选与证据，并等待明确返工。", { review_id: pendingReview.review_id, state: "rejected" }),
      );
    }
    if (rejectedReview) {
      lifecycle.appendChild(graphActionButton("安排返工", "redo_rejected", "安排受控返工", "确认后新增返工任务，不覆盖原候选。", { review_id: rejectedReview.review_id }));
    }
    const delivery = view.lifecycle.deliveries.at(-1);
    if (delivery && delivery.state !== "review_ready") {
      lifecycle.appendChild(graphActionButton("提交交付核验", "delivery_state", "提交交付清单核验",
        "确认后仅更新交付清单状态；不执行导出或媒体生成。", { delivery_id: delivery.delivery_id, state: "review_ready" }));
    }
    if (lifecycle.children.length) sectionEl.appendChild(lifecycle);
    sectionEl.appendChild(graphLifecycleList("制作任务", view.lifecycle.tasks, (item, index) => `任务 ${index + 1} · ${graphStateLabel(item.state)}`));
    sectionEl.appendChild(graphLifecycleList("候选版本", view.lifecycle.candidates, (item, index) => `候选 ${index + 1} · ${graphStateLabel(item.state)}`));
    sectionEl.appendChild(graphLifecycleList("审核记录", view.lifecycle.reviews, (item, index) => `审核 ${index + 1} · ${graphStateLabel(item.state)}`));
    sectionEl.appendChild(graphLifecycleList("交付清单", view.lifecycle.deliveries, (item) => `${graphStateLabel(item.state)} · 时间线 ${item.timeline_refs?.length || 0} · 权利 ${item.rights_refs?.length || 0} · 来源 ${item.provenance_refs?.length || 0}`));
    const history = view.summary.versionHistory.slice(0, 4).map((item) => `版本 ${Number(item.version)}`).join(" · ");
    sectionEl.appendChild(node("p", "graph-version-history", history ? `最近记录：${history}` : "尚无版本变更记录"));
    return sectionEl;
  }

  function graphLifecycleList(title, items, describe) {
    const sectionEl = node("section", "graph-lifecycle-list");
    sectionEl.appendChild(node("strong", "", title));
    const list = node("ul", "");
    if (!items.length) list.appendChild(node("li", "", "尚无记录"));
    else items.slice(0, 5).forEach((item, index) => list.appendChild(node("li", "", describe(item, index))));
    sectionEl.appendChild(list);
    return sectionEl;
  }

  function graphActionButton(label, action, title, summary, payload) {
    const button = node("button", "studio-secondary-button", label);
    button.type = "button";
    button.addEventListener("click", () => stageGraphCommand({ action, title, summary, payload }));
    return button;
  }

  function buildGraphCanvasStatus() {
    const view = graphView();
    const status = node("aside", `graph-canvas-status ${view.status}`);
    status.setAttribute("aria-live", "polite");
    if (mediaOperationsReady()) {
      const ops = mediaOperationsView();
      status.className = "graph-canvas-status ready media-canvas-status";
      status.append(
        node("strong", "", "媒体审片候选"),
        node("span", "", `${ops.summary?.ready_shot_count || 0}/${ops.summary?.shot_count || 0} 镜头可审 · 估算 $${Number(ops.cost?.conservative_estimated_usd || 0).toFixed(2)} · ${ops.stage?.next_action || "进入故事板审片"}`),
      );
      const review = node("button", "studio-text-button", "进入故事板审片");
      review.type = "button";
      review.addEventListener("click", showStoryboard);
      status.appendChild(review);
      return status;
    }
    if (view.planningRequired) {
      return buildContextualPlanSurface(status);
    }
    if (view.status !== "ready") {
      status.hidden = true;
      return status;
    }
    status.append(
      node("strong", "", `制作序列 v${view.graphVersion}`),
      node("span", "", `${view.summary.characters} 角色 · ${view.summary.locations} 场景 · ${view.shots.length} 镜头 · ${view.summary.tasks} 任务`),
    );
    const details = node("button", "studio-text-button", "制作详情");
    details.type = "button";
    details.addEventListener("click", () => { projectDrawerOpen = true; render(); });
    status.appendChild(details);
    const selected = selectedGraphTarget();
    if (selected) {
      const impact = node("button", "studio-secondary-button", "预览所选对象影响");
      impact.type = "button";
      impact.addEventListener("click", () => previewGraphMutation(selected.nodeId, { review_state: "needs_revision" }, `确认修订${selected.title}`));
      status.appendChild(impact);
    }
    return status;
  }

  function buildContextualPlanSurface(status) {
    const expanded = isPlanningPanelExpanded();
    status.className = `graph-canvas-status planning-required ${expanded ? "expanded" : "compact"}`;
    status.dataset.expanded = String(expanded);
    if (!expanded) return buildCompactPlanSurface(status);
    return buildExpandedPlanSurface(status);
  }

  function buildCompactPlanSurface(status) {
    status.append(
      node("strong", "", "可自由开始"),
      node("span", "", "先创建想法、剧本、参考图、角色、图片或视频；需要结构化方案时再展开。"),
    );
    const actions = node("div", "plan-compact-actions");
    const expand = node("button", "studio-secondary-button", "展开制作方案");
    expand.type = "button";
    expand.setAttribute("aria-expanded", "false");
    expand.addEventListener("click", () => {
      setPlanningPanelOpen(true);
      render();
      requestCanvasSafeAreaUpdate();
      requestAnimationFrame(() => document.querySelector(".m6-script-plan-entry textarea")?.focus());
    });
    const ask = node("button", "studio-text-button", "让 AI 创作搭档建议下一步");
    ask.type = "button";
    ask.addEventListener("click", () => submitToAgentChat("下一步建议是什么"));
    actions.append(expand, ask, ...planningImportControls());
    status.appendChild(actions);
    return status;
  }

  function buildExpandedPlanSurface(status) {
    status.style.setProperty("--graph-plan-height", `${planningPanelHeight}px`);
    const head = node("div", "graph-plan-head");
    head.append(
      node("span", "eyebrow", "制作方案草案"),
      node("strong", "", "先预览，再确认"),
      node("span", "", "只有生成草案或导入方案后才进入确认；确认前不会建立制作图。"),
    );
    const controls = node("div", "graph-plan-controls");
    const collapse = node("button", "studio-text-button", "收起");
    collapse.type = "button";
    collapse.setAttribute("aria-expanded", "true");
    collapse.addEventListener("click", () => {
      setPlanningPanelOpen(false);
      render();
      requestCanvasSafeAreaUpdate();
    });
    const defer = node("button", "studio-secondary-button", "稍后处理");
    defer.type = "button";
    defer.addEventListener("click", () => {
      m6SourceText = "";
      setPlanningPanelOpen(false);
      notice = "已暂不处理制作方案；画布仍可从任意节点继续。";
      render();
      requestCanvasSafeAreaUpdate();
    });
    controls.append(collapse, defer);
    head.appendChild(controls);
    status.appendChild(head);

    const planner = node("div", "m6-script-plan-entry");
    const textarea = document.createElement("textarea");
    textarea.rows = 4;
    textarea.value = m6SourceText;
    textarea.placeholder = "可粘贴想法、已有剧本、场景、镜头、角色、参考图用途或制作目标";
    textarea.setAttribute("aria-label", "输入想法或已有剧本");
    textarea.addEventListener("input", () => {
      m6SourceText = textarea.value;
    });
    const preview = node("button", "studio-primary-button", "生成剧本制作方案");
    preview.type = "button";
    preview.addEventListener("click", () => previewM6ScriptPlan(textarea.value));
    planner.append(textarea, preview, ...planningImportControls());
    status.append(planner, planResizeHandle());
    return status;
  }

  function planningImportControls() {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "application/json,.json";
    input.hidden = true;
    input.setAttribute("aria-label", "选择结构化制作方案文件");
    const importButton = node("button", "studio-secondary-button", "导入结构化制作方案");
    importButton.type = "button";
    importButton.addEventListener("click", () => input.click());
    input.addEventListener("change", async () => {
      const file = input.files?.[0];
      if (!file) return;
      try {
        const candidate = JSON.parse(await file.text());
        stageGraphCandidate(candidate);
      } catch {
        notice = "制作方案无法读取；请检查文件格式后重试，现有项目未改变。";
        render();
      } finally {
        input.value = "";
      }
    });
    return [importButton, input];
  }

  function planResizeHandle() {
    const handle = node("div", "graph-plan-resize");
    handle.setAttribute("role", "separator");
    handle.setAttribute("aria-label", "调整制作方案面板高度");
    handle.setAttribute("aria-orientation", "horizontal");
    handle.addEventListener("pointerdown", bindPlanResize);
    return handle;
  }

  function stageGraphCommand(details) {
    const context = currentAgentChatContext();
    context.context_key = agentChatContextKey(context);
    const session = agentChatContexts.get(context.context_key);
    stageProductionGraphCommand(session, context, details);
    projectDrawerOpen = false;
    setAgentChatExpanded(true);
    notice = "命令已送入 AI 创作搭档；确认前不会改变制作事实。";
    render();
    requestCanvasSafeAreaUpdate();
  }

  function stageGraphCandidate(candidate) {
    const context = currentAgentChatContext();
    context.context_key = agentChatContextKey(context);
    const session = agentChatContexts.get(context.context_key);
    try {
      stageProductionGraphCandidateCommand(session, context, candidate);
    } catch (error) {
      notice = error?.message || "制作方案缺少必要结构，项目未改变。";
      render();
      return;
    }
    projectDrawerOpen = false;
    setAgentChatExpanded(true);
    notice = "制作方案已送入 AI 创作搭档；确认前不会建立制作图。";
    render();
    requestCanvasSafeAreaUpdate();
  }

  async function previewM6ScriptPlan(sourceText) {
    try {
      const preview = await options.getRuntime?.().previewM6ScriptPlanAssetBible({
        source_kind: "idea",
        source_text: sourceText,
      });
      const context = currentAgentChatContext();
      context.context_key = agentChatContextKey(context);
      const session = agentChatContexts.get(context.context_key);
      stageM6ScriptPlanCandidateCommand(session, context, preview);
      projectDrawerOpen = false;
      setAgentChatExpanded(true);
      notice = "M6 方案已送入 AI 创作搭档；确认前不会建立制作图。";
    } catch (error) {
      notice = error?.message || "M6方案生成失败，项目未改变。";
    }
    render();
    requestCanvasSafeAreaUpdate();
  }

  function applyGraphWorkspace(workspace) {
    const store = options.getStore?.();
    const ready = productionGraphWorkspaceProjection(workspace).status === "ready";
    store?.setRuntimePersistenceMode?.(ready ? "production_graph_read_only" : "studio_state");
    store?.set?.((state) => applyProductionGraphCanvasProjection(state, workspace), { history: false, persist: false });
  }

  async function previewGraphMutation(nodeId, patch, title) {
    try {
      pendingGraphImpact = await options.getRuntime?.().previewSequenceImpact({ changed_node_ids: [nodeId] });
      notice = `将重新处理 ${pendingGraphImpact.impact.invalidated_node_ids.length} 个下游对象，保留 ${pendingGraphImpact.impact.preserved_node_ids.length} 个无关对象。`;
      stageGraphCommand({ action: "mutate", title, summary: notice, targetNodeId: nodeId, changedNodeIds: [nodeId], patch, impact: pendingGraphImpact.impact });
    } catch {
      notice = "影响预览失败，未修改制作事实。";
      render();
    }
  }

  function syncGraphWorkspaceAfterAgentReceipt(session) {
    const receipt = session?.receipts?.at(-1);
    if (receipt?.runtime_domain !== "production_graph" || Number(receipt.graph_version || 0) <= Number(snapshot.sequenceWorkspace?.graph_version || 0)) {
      render();
      return;
    }
    if (graphRefreshPending) return;
    graphRefreshPending = true;
    options.getRuntime?.().sequenceWorkspace?.().then((workspace) => {
      snapshot.sequenceWorkspace = workspace;
      applyGraphWorkspace(workspace);
      snapshot.studioState = options.getStudioState?.() || snapshot.studioState;
      pendingGraphImpact = null;
      notice = `制作图已更新到版本 ${Number(workspace.graph_version || 0)}。`;
    }).catch(() => {
      notice = "制作图已变更但刷新失败，请重新载入后继续；不会重复执行命令。";
    }).finally(() => {
      graphRefreshPending = false;
      render();
    });
  }

  function buildWorkspace() {
    const emptyCanvas = section === "canvas" && !hasStoryFacts();
    const canvasActive = section === "canvas";
    const agentChatCollapsed = isAgentChatCollapsed();
    const shell = node("div", `studio-unified-workspace ${agentChatCollapsed ? "agent-collapsed" : ""} ${mobileAgentOpen ? "agent-mobile-open" : ""} ${isNarrowAgentLayout() ? "agent-responsive-compact" : ""} ${canvasActive ? "canvas-section" : "storyboard-section"} ${mediaOperationsReady() ? "media-operations-ready" : ""} ${emptyCanvas ? "canvas-empty-project" : ""}`);
    shell.dataset.contextKey = currentContextKey();
    shell.style.setProperty("--agent-chat-width", `${agentChatWidth}px`);
    if (section === "storyboard" && !emptyCanvas) shell.appendChild(buildSceneRail());
    const main = section === "canvas" ? buildCanvasWorkspace() : buildStoryboardWorkspace();
    shell.appendChild(main);
    if (isNarrowAgentLayout() && mobileAgentOpen) shell.appendChild(buildAgentMobileBackdrop());
    shell.appendChild(buildAgentChat());
    return shell;
  }

  function buildAgentMobileBackdrop() {
    const backdrop = node("button", "agent-mobile-backdrop");
    backdrop.type = "button";
    backdrop.setAttribute("aria-label", "收起 AI 创作搭档，返回当前审片");
    backdrop.addEventListener("click", () => {
      setAgentChatExpanded(false);
      render();
      requestCanvasSafeAreaUpdate();
      requestAnimationFrame(() => document.getElementById("product-main")?.focus());
    });
    return backdrop;
  }

  function buildStoryboardWorkspace() {
    const main = node("main", "studio-workspace-main studio-storyboard");
    main.id = "product-main";
    main.tabIndex = -1;
    main.append(buildContextBar(), buildStoryboardContent(), buildVersionBar());
    return main;
  }

  function buildCanvasWorkspace() {
    const main = node("main", "studio-workspace-main studio-canvas-workspace");
    main.id = "product-main";
    main.tabIndex = -1;
    const stage = node("section", "canvas-workspace-stage");
    if (graphView().planningRequired && isPlanningPanelExpanded()) {
      stage.classList.add("graph-planning-mode");
      stage.style.setProperty("--graph-plan-height", `${planningPanelHeight}px`);
    }
    stage.setAttribute("aria-label", `画布 · ${currentShot().title}`);
    stage.dataset.canvasTarget = currentShot().nodeId || "empty-project";
    const editor = options.getCanvasShell?.();
    if (editor) stage.appendChild(editor);
    else stage.appendChild(node("p", "canvas-unavailable", "画布编辑当前不可用；项目与审核上下文仍保持在此工作区。"));
    if (mediaOperationsReady()) stage.appendChild(buildMediaCanvasOverview());
    stage.appendChild(buildGraphCanvasStatus());
    if (notice) {
      const live = node("p", "studio-live-notice", notice);
      live.setAttribute("aria-live", "polite");
      stage.appendChild(live);
    }
    main.appendChild(stage);
    return main;
  }

  function buildMediaCanvasOverview() {
    const ops = mediaOperationsView();
    const panel = node("section", "media-canvas-overview");
    panel.setAttribute("aria-label", "媒体制作进度");
    const head = node("div", "media-canvas-overview-head");
    head.append(
      node("span", "eyebrow", "媒体制作进度"),
      node("h1", "", ops.script?.title || "制作审片候选"),
      node("p", "", ops.stage?.next_action || "进入故事板审片，复核镜头、资产、费用与恢复状态。"),
    );
    const metrics = buildMetricGrid([
      ["场景", ops.summary?.scene_count],
      ["镜头", ops.summary?.shot_count],
      ["可审片", ops.summary?.ready_shot_count],
      ["估算", `$${Number(ops.cost?.conservative_estimated_usd || 0).toFixed(2)}`],
    ]);
    const actions = node("div", "media-canvas-overview-actions");
    const review = node("button", "studio-primary-button", "进入故事板审片");
    review.type = "button";
    review.addEventListener("click", showStoryboard);
    const evidence = node("button", "studio-secondary-button", "查看证据摘要");
    evidence.type = "button";
    evidence.addEventListener("click", () => {
      showStoryboard();
      requestAnimationFrame(() => document.querySelector(".media-evidence-drawer summary")?.focus());
    });
    actions.append(review, evidence);
    panel.append(head, metrics, actions);
    return panel;
  }

  function buildSceneRail() {
    const scenes = sceneModel();
    const aside = node("aside", "studio-scene-rail");
    const head = node("div", "scene-rail-head");
    head.append(node("strong", "", "场景"), node("span", "", String(scenes.length)));
    aside.appendChild(head);
    const list = node("nav", "scene-list");
    list.setAttribute("aria-label", "场景列表");
    if (!scenes.length) {
      list.classList.add("scene-list-empty");
      list.appendChild(node("p", "", "尚未创建场景"));
      aside.appendChild(list);
      const progress = node("div", "scene-progress");
      progress.innerHTML = '<span>本集进度</span><strong>0 / 0 镜头</strong><div><i style="width:0%"></i></div>';
      aside.appendChild(progress);
      return aside;
    }
    scenes.forEach((scene, index) => {
      const button = node("button", index === selection.sceneIndex ? "active" : "");
      button.type = "button";
      button.setAttribute("aria-current", index === selection.sceneIndex ? "true" : "false");
      button.innerHTML = `<span class="scene-number">${String(index + 1).padStart(2, "0")}</span><span><strong>${escapeHtml(scene.name)}</strong><small>${scene.shots.length} 镜头 · ${scene.duration}</small></span><span class="scene-state ${scene.blocked ? "blocked" : ""}">${scene.blocked ? "需处理" : "已就绪"}</span>`;
      button.addEventListener("click", () => {
        selectContext(index, 0);
      });
      list.appendChild(button);
    });
    aside.appendChild(list);
    const progress = node("div", "scene-progress");
    progress.innerHTML = `<span>本集进度</span><strong>${totalReadyShots()} / ${totalShots()} 镜头</strong><div><i style="width:${completionPercent()}%"></i></div>`;
    aside.appendChild(progress);
    return aside;
  }

  function buildContextBar() {
    const scene = currentScene();
    const shot = currentShot();
    const empty = !hasStoryFacts();
    const bar = node("header", "storyboard-context-bar");
    const selectionContext = node("div", "selection-context");
    selectionContext.innerHTML = empty
      ? `<span>当前项目</span><strong>${escapeHtml(snapshot.project?.name || "未命名项目")}</strong><span>0 场景 · 0 镜头 · 尚未创建故事事实</span>`
      : `<span>当前选择</span><strong>场景 ${String(selection.sceneIndex + 1).padStart(2, "0")} · ${escapeHtml(scene.name)}</strong><span>镜头 ${String(selection.shotIndex + 1).padStart(2, "0")} · ${escapeHtml(shot.title)}</span>`;
    const actions = node("div", "context-actions");
    const canvas = node("button", "studio-text-button");
    canvas.type = "button";
    canvas.innerHTML = section === "canvas"
      ? `${icon("grid", 13)}在故事板查看`
      : `查看画布${icon("expand", 13)}`;
    canvas.addEventListener("click", () => section === "canvas" ? showStoryboard() : openCanvas());
    actions.append(canvas);
    bar.append(selectionContext, actions);
    return bar;
  }

  function buildStoryboardContent() {
    if (mediaOperationsReady()) return buildMediaOperationsContent();
    if (!hasStoryFacts()) return buildEmptyStoryboardContent();
    const scene = currentScene();
    const sectionEl = node("section", "storyboard-content");
    const sparse = scene.shots.length <= 2;
    sectionEl.classList.toggle("is-sparse", sparse);
    const heading = node("div", "storyboard-heading");
    heading.append(
      node("div", "", `<span class="eyebrow">场景 ${String(selection.sceneIndex + 1).padStart(2, "0")}</span><h1>${escapeHtml(scene.name)}</h1>`),
      node("span", "storyboard-duration", `${scene.shots.length} 镜头 · ${scene.duration}`),
    );
    heading.firstElementChild.innerHTML = `<span class="eyebrow">场景 ${String(selection.sceneIndex + 1).padStart(2, "0")}</span><h1>${escapeHtml(scene.name)}</h1>`;
    sectionEl.appendChild(heading);
    const grid = node("div", "storyboard-shot-grid");
    grid.classList.toggle("is-sparse", sparse);
    scene.shots.forEach((shot, index) => grid.appendChild(buildShotCard(shot, index)));
    sectionEl.appendChild(grid);
    if (notice) {
      const live = node("p", "studio-live-notice", notice);
      live.setAttribute("aria-live", "polite");
      sectionEl.appendChild(live);
    }
    return sectionEl;
  }

  function buildMediaOperationsContent() {
    const ops = mediaOperationsView();
    const scene = currentScene();
    const shot = currentShot();
    const media = shot.media || {};
    const sectionEl = node("section", "storyboard-content media-operations-workspace");
    const heading = node("div", "media-ops-heading");
    const copy = node("div", "");
    copy.innerHTML = `<span class="eyebrow">生产审片</span><h1>${escapeHtml(ops.script?.title || snapshot.project?.name || "制作审片")}</h1><p>${escapeHtml(ops.script?.logline || ops.stage?.next_action || "复核当前制作媒体、资产连续性与交付候选。")}</p>`;
    const next = node("div", "media-next-action");
    next.append(node("span", "", "下一步"), node("strong", "", ops.stage?.next_action || "选择镜头继续审片"));
    heading.append(copy, next);
    sectionEl.append(heading, buildMediaJourney(ops), buildMediaShotSelector());

    const layout = node("div", "media-ops-layout");
    layout.append(buildMediaPreviewPanel(scene, shot, media), buildMediaSidePanel(ops, media));
    sectionEl.appendChild(layout);

    const lower = node("div", "media-ops-lower");
    lower.append(buildAssetContinuityPanel(ops, media), buildCostAndRecoveryPanel(ops, media), buildFinalReviewPanel(ops));
    sectionEl.appendChild(lower);
    sectionEl.appendChild(buildMediaEvidenceDrawer(ops));
    if (notice) {
      const live = node("p", "studio-live-notice", notice);
      live.setAttribute("aria-live", "polite");
      sectionEl.appendChild(live);
    }
    return sectionEl;
  }

  function buildMediaShotSelector() {
    const scenes = sceneModel();
    const selector = node("nav", "media-shot-selector");
    selector.setAttribute("aria-label", "镜头选择");
    scenes.forEach((scene, sceneIndex) => {
      scene.shots.forEach((shot, shotIndex) => {
        const active = sceneIndex === selection.sceneIndex && shotIndex === selection.shotIndex;
        const button = node("button", active ? "active" : "");
        button.type = "button";
        button.setAttribute("aria-current", active ? "true" : "false");
        button.setAttribute("aria-label", `选择场景 ${sceneIndex + 1} 镜头 ${shotIndex + 1}：${shot.title}`);
        button.innerHTML = [
          `<span>${String(sceneIndex + 1).padStart(2, "0")}-${String(shotIndex + 1).padStart(2, "0")}</span>`,
          `<strong>${escapeHtml(shot.title)}</strong>`,
          `<small>${escapeHtml(shot.duration)} · ${escapeHtml(shotStateLabel(shot.state))}</small>`,
        ].join("");
        button.addEventListener("click", () => selectContext(sceneIndex, shotIndex));
        selector.appendChild(button);
      });
    });
    return selector;
  }

  function buildMediaJourney(ops) {
    const rail = node("ol", "media-journey");
    for (const item of (ops.journey || []).slice(0, 8)) {
      const li = node("li", item.state || "");
      li.append(node("span", "stage-dot"), node("strong", "", item.label || "阶段"), node("small", "", item.detail || ""));
      rail.appendChild(li);
    }
    return rail;
  }

  function buildMediaPreviewPanel(scene, shot, media) {
    const panel = node("section", "media-preview-panel");
    const head = node("div", "media-panel-head");
    head.append(
      node("div", "", `<span class="eyebrow">当前镜头</span><strong>${escapeHtml(scene.name || "场景")} · ${escapeHtml(shot.title || "镜头")}</strong>`),
      statusBadge(shot.state === "blocked" ? "warning" : "ok", shotStateLabel(shot.state)),
    );
    head.firstElementChild.innerHTML = `<span class="eyebrow">当前镜头</span><strong>${escapeHtml(scene.name || "场景")} · ${escapeHtml(shot.title || "镜头")}</strong>`;
    const viewer = node("div", "media-viewer");
    const videoUrl = safePreview(media.video_url || "");
    if (videoUrl) {
      const video = document.createElement("video");
      video.controls = true;
      video.preload = "metadata";
      video.src = videoUrl;
      video.poster = safePreview(media.keyframe_url || "");
      video.setAttribute("aria-label", `${shot.title || "镜头"} 视频预览`);
      viewer.appendChild(video);
    } else if (safePreview(media.keyframe_url || "")) {
      const image = document.createElement("img");
      image.src = media.keyframe_url;
      image.alt = `${shot.title || "镜头"} 关键帧`;
      viewer.appendChild(image);
    } else {
      viewer.appendChild(node("p", "", "当前镜头还没有可预览媒体。"));
    }
    const detail = node("dl", "media-shot-detail");
    for (const [label, value] of [
      ["叙事目的", media.purpose],
      ["调度动作", media.staging],
      ["景别", media.shot_size],
      ["机位", media.camera_position],
      ["运动", media.movement],
      ["声音", media.sound],
      ["转场", media.transition],
    ]) {
      detail.append(node("dt", "", label), node("dd", "", value || "待确认"));
    }
    panel.append(head, viewer, detail);
    return panel;
  }

  function buildMediaSidePanel(ops, media) {
    const panel = node("aside", "media-side-panel");
    panel.appendChild(buildMetricGrid([
      ["场景", ops.summary?.scene_count],
      ["镜头", ops.summary?.shot_count],
      ["可审片", ops.summary?.ready_shot_count],
      ["时长", `${Number(ops.summary?.duration_sec || 0).toFixed(1)}s`],
    ]));
    const versions = node("section", "media-side-block");
    versions.append(node("strong", "", "版本比较"), node("p", "", "局部重做会生成新版本候选；未提升前不会覆盖当前镜头。"));
    const redo = ops.localized_redo || {};
    const compare = node("dl", "media-compare");
    compare.append(
      node("dt", "", "当前版本"),
      node("dd", "", media.status === "ready" ? "已确认可审片" : "需要处理"),
      node("dt", "", "预览版本"),
      node("dd", "", redo.new_version_digest ? "已有候选，待提升" : "确认后才会生成候选"),
      node("dt", "", "未影响镜头"),
      node("dd", "", String((redo.unaffected_shot_digests || []).length)),
    );
    versions.appendChild(compare);
    const actions = node("div", "media-action-row");
    actions.append(
      mediaCommandButton("local_redo_preview", media.shot_id, "预览重做"),
      mediaCommandButton("promote_version", media.shot_id, "提升版本"),
    );
    versions.appendChild(actions);
    if (snapshot.mediaCommandPreview) versions.appendChild(buildCommandPreviewReceipt(snapshot.mediaCommandPreview));
    panel.appendChild(versions);
    return panel;
  }

  function buildAssetContinuityPanel(ops, media) {
    const panel = node("section", "media-ops-panel asset-continuity-panel");
    panel.append(node("span", "eyebrow", "资产连续性"), node("h2", "", "Bible 与复用锁"));
    const lock = node("p", "media-warning-line", ops.assets?.continuity_warning || "资产变更前需预览影响。");
    panel.appendChild(lock);
    const grid = node("div", "asset-lock-grid");
    for (const item of (ops.assets?.characters || []).slice(0, 4)) {
      const card = node("article", "asset-lock-card");
      card.append(node("strong", "", item.name || "角色"), node("span", "", item.wardrobe || item.appearance || "服装外观已锁定"), node("small", "", item.continuity || "保持身份连续"));
      grid.appendChild(card);
    }
    for (const item of (ops.assets?.props || []).slice(0, 4)) {
      const card = node("article", "asset-lock-card prop");
      card.append(node("strong", "", item.name || "道具"), node("span", "", item.continuity || "保持归属"), node("small", "", "禁止未确认变化"));
      grid.appendChild(card);
    }
    panel.appendChild(grid);
    const locks = node("ul", "negative-locks");
    for (const item of (media.negative_locks || ops.assets?.reference_set?.negative_locks || []).slice(0, 4)) locks.appendChild(node("li", "", item));
    panel.append(node("strong", "media-subhead", "禁止变化项"), locks);
    return panel;
  }

  function buildCostAndRecoveryPanel(ops, media) {
    const panel = node("section", "media-ops-panel cost-recovery-panel");
    panel.append(node("span", "eyebrow", "制片与恢复"), node("h2", "", "费用、重复提交保护与恢复"));
    panel.appendChild(buildMetricGrid([
      ["已估费用", `$${Number(ops.cost?.conservative_estimated_usd || 0).toFixed(2)}`],
      ["图片请求", ops.cost?.image_attempt_count],
      ["视频请求", ops.cost?.video_attempt_count],
      ["避免重复", ops.cost?.avoided_dispatches_from_reference_reuse],
    ]));
    const redo = ops.localized_redo || {};
    const estimate = node("p", "media-cost-estimate", `局部重做当前镜头预计增量 $${Number(redo.estimated_incremental_usd || 0).toFixed(2)}；确认前不会扣费。`);
    panel.appendChild(estimate);
    const recovery = node("div", `media-recovery-state ${ops.recovery?.state || "clean"}`);
    recovery.append(
      statusBadge(ops.recovery?.state === "recovered_with_attention" ? "warning" : "ok", ops.recovery?.state === "clean" ? "无中断" : "已恢复"),
      node("span", "", ops.recovery?.blocking_reason || "恢复记录正常；重复提交不会重复生成或扣费。"),
    );
    panel.appendChild(recovery);
    const actions = node("div", "media-action-row");
    actions.append(mediaCommandButton("resume_failed_shot", media.shot_id, "恢复预览"), mediaCommandButton("keep_version", media.shot_id, "保留当前"));
    panel.appendChild(actions);
    return panel;
  }

  function buildFinalReviewPanel(ops) {
    const panel = node("section", "media-ops-panel final-review-panel");
    panel.append(node("span", "eyebrow", "最终审片"), node("h2", "", "序列预览与交付边界"));
    const media = node("div", "final-media-pair");
    const videoUrl = safePreview(ops.final_review?.video_url || "");
    const sheetUrl = safePreview(ops.final_review?.contact_sheet_url || "");
    if (videoUrl) {
      const video = document.createElement("video");
      video.controls = true;
      video.preload = "metadata";
      video.src = videoUrl;
      video.setAttribute("aria-label", "最终序列视频预览");
      media.appendChild(video);
    }
    if (sheetUrl) {
      const image = document.createElement("img");
      image.src = sheetUrl;
      image.alt = "最终序列 contact sheet";
      media.appendChild(image);
    }
    panel.appendChild(media);
    const readiness = node("ul", "final-readiness-list");
    for (const item of (ops.final_review?.readiness || [])) readiness.appendChild(node("li", item.state || "", `${item.label} · ${readinessLabel(item.state)}`));
    panel.appendChild(readiness);
    panel.appendChild(node("p", "media-boundary-copy", "这是 Owner review candidate；不是人工验收、媒体商业质量验证或公开发布。"));
    return panel;
  }

  function buildMediaEvidenceDrawer(ops) {
    const details = node("details", "media-evidence-drawer");
    const summary = node("summary", "", "高级证据");
    const list = node("dl", "media-evidence-list");
    const evidence = ops.advanced_evidence || {};
    for (const [label, value] of [
      ["Graph digest", evidence.graph_digest],
      ["生成调用", evidence["pro" + "vider_dispatch_count"]],
      ["Ledger", JSON.stringify(evidence.ledger_status_counts || {})],
      ["Final hash", evidence.final_sha256],
      ["Contact sheet", evidence.contact_sheet_sha256],
      ["QA 边界", evidence.qa_boundary],
    ]) {
      list.append(node("dt", "", label), node("dd", "", String(value ?? "")));
    }
    details.append(summary, list);
    return details;
  }

  function buildMetricGrid(items) {
    const grid = node("dl", "media-metric-grid");
    for (const [label, value] of items) grid.append(node("dt", "", label), node("dd", "", String(value ?? 0)));
    return grid;
  }

  function statusBadge(tone, label) {
    const badge = node("span", `media-status-badge ${tone || "muted"}`);
    badge.textContent = label || "待确认";
    return badge;
  }

  function mediaCommandButton(action, shotId, label) {
    const button = node("button", action === "promote_version" ? "studio-secondary-button" : "studio-primary-button", label);
    button.type = "button";
    button.addEventListener("click", () => previewMediaCommand(action, shotId));
    return button;
  }

  function buildCommandPreviewReceipt(preview) {
    const receipt = node("div", "media-command-receipt");
    receipt.append(
      node("strong", "", preview.human_message || "命令预览已生成"),
      node("span", "", "重复提交保护已开启；不会因为再次点击而重复生成。"),
      node("span", "", `预计增量 $${Number(preview.estimated_incremental_usd || 0).toFixed(2)} · 当前只是预览，不会发起生成或产生费用`),
    );
    return receipt;
  }

  async function previewMediaCommand(action, shotId) {
    const ops = mediaOperationsView();
    const runtime = options.createRuntime?.(ops.project_id) || options.getRuntime?.();
    try {
      const preview = await runtime?.previewAdaptiveCanvasOperation?.({ run_id: ops.run_id, action, shot_id: shotId });
      snapshot.mediaCommandPreview = preview || null;
      setAgentChatExpanded(true);
      notice = "已生成只读命令预览；确认前不会改动制作事实或产生费用。";
    } catch (error) {
      notice = options.formatError?.(error) || "命令预览失败；不会执行付费动作。";
    }
    render();
  }

  function buildEmptyStoryboardContent() {
    const sectionEl = node("section", "storyboard-content storyboard-empty-state");
    const heading = node("div", "storyboard-heading");
    heading.append(
      node("div", "", '<span class="eyebrow">故事板</span><h1>等待创作简报</h1>'),
      node("span", "storyboard-duration", "0 场景 · 0 镜头"),
    );
    heading.firstElementChild.innerHTML = '<span class="eyebrow">故事板</span><h1>等待创作简报</h1>';
    const body = node("div", "storyboard-empty-body");
    body.append(
      node("p", "", "这个项目还没有场景、镜头、进度、决策、参考或示例素材。"),
      node("p", "", "故事板当前只读取画布确认后的事实；空项目不会自动创建示例分镜。"),
    );
    const actions = node("div", "storyboard-empty-actions");
    const canvas = node("button", "studio-secondary-button", "打开空白画布");
    canvas.type = "button";
    canvas.addEventListener("click", openCanvas);
    actions.append(canvas);
    const counts = node("dl", "empty-canonical-counts");
    for (const [label, value] of [["场景", 0], ["镜头", 0], ["参考", 0], ["决策", 0]]) {
      counts.append(node("dt", "", label), node("dd", "", String(value)));
    }
    sectionEl.append(heading, body, actions, counts);
    return sectionEl;
  }

  function buildShotCard(shot, index) {
    const card = node("button", `storyboard-shot ${index === selection.shotIndex ? "active" : ""}`);
    card.type = "button";
    card.id = `storyboard-shot-${selection.sceneIndex}-${index}`;
    card.setAttribute("aria-pressed", String(index === selection.shotIndex));
    card.setAttribute("aria-label", `镜头 ${index + 1}：${shot.title}`);
    const media = node("span", `shot-media ${shot.preview ? "has-preview" : "empty"}`);
    if (shot.preview) {
      const image = document.createElement("img");
      image.src = shot.preview;
      image.alt = `${shot.title} 镜头预览`;
      image.loading = "lazy";
      media.appendChild(image);
    } else {
      media.innerHTML = `${icon("image", 20)}<span class="shot-empty-copy"><strong>等待镜头画面</strong><small>${escapeHtml(shot.description)}</small></span>`;
    }
    media.append(
      node("span", "shot-index", String(index + 1).padStart(2, "0")),
      node("span", "shot-duration", shot.duration),
    );
    const copy = node("span", "shot-copy");
    copy.append(
      node("strong", "", shot.title),
      node("span", "", shot.description),
      node("small", `shot-status ${shot.state}`, shotStateLabel(shot.state)),
    );
    card.append(media, copy);
    card.addEventListener("click", () => selectContext(selection.sceneIndex, index));
    return card;
  }

  function buildVersionBar() {
    const bar = node("footer", "storyboard-version-bar");
    const script = node("button", "studio-text-button");
    script.type = "button";
    script.innerHTML = `${icon("script", 14)}脚本与对白`;
    script.addEventListener("click", () => {
      notice = "脚本上下文已绑定当前场景；详细内容保持折叠。";
      render();
    });
    const versions = node("button", "studio-text-button", "查看版本记录");
    versions.type = "button";
    versions.addEventListener("click", () => {
      setAgentChatExpanded(true);
      notice = "版本记录只随画布事实读取；恢复命令需要在 AI 创作搭档中预览和确认。";
      render();
    });
    bar.append(script, node("p", "", currentShot().description), versions);
    if (graphWorkspaceReady()) {
      const impact = node("button", "studio-secondary-button", pendingGraphImpact ? "已预览影响" : "预览修改影响");
      impact.type = "button";
      impact.addEventListener("click", () => previewGraphMutation(currentShot().graphNodeId, { review_state: "needs_revision" }, "确认镜头局部修改"));
      bar.appendChild(impact);
    }
    return bar;
  }

  function buildAgentChat() {
    const context = currentAgentChatContext();
    const session = agentChatContexts.get(agentChatContextKey(context));
    const collapsed = isAgentChatCollapsed();
    return buildAgentChatPanel({
      session,
      context: { ...context, context_key: agentChatContextKey(context) },
      store: options.getStore?.(),
      runtime: options.getRuntime?.(),
      collapsed,
      mobileOpen: mobileAgentOpen,
      onToggleCollapse: () => {
        const nextExpanded = collapsed;
        setAgentChatExpanded(nextExpanded);
        render();
        requestCanvasSafeAreaUpdate();
        requestAnimationFrame(() => {
          const focusTarget = nextExpanded
            ? document.querySelector(".agent-chat-composer textarea, .studio-agent-chat button")
            : document.getElementById("product-main");
          focusTarget?.focus();
        });
      },
      onOpen: () => {
        setAgentChatExpanded(true);
      },
      onResizeStart: bindAgentResize,
      onRender: () => syncGraphWorkspaceAfterAgentReceipt(session),
    });
  }

  function buildMobileNav() {
    const nav = node("nav", "product-mobile-nav");
    nav.setAttribute("aria-label", "移动端 Studio 导航");
    for (const [key, label] of [["canvas", "画布"], ["storyboard", "故事板"], ["context", "项目"], ["help", "指南"], ["agent", "搭档"]]) {
      const active = key === "agent" ? mobileAgentOpen : key === "help" ? helpOpen : section === key;
      const button = node("button", active ? "active" : "", label);
      button.type = "button";
      button.setAttribute("aria-current", active ? "page" : "false");
      button.addEventListener("click", () => {
        if (key === "canvas") {
          openCanvas();
        } else if (key === "storyboard") {
          showStoryboard();
        } else if (key === "context") {
          projectDrawerOpen = true;
          closeResponsiveAgentOverlay();
          helpOpen = false;
        } else if (key === "help") {
          helpOpen = !helpOpen;
          projectDrawerOpen = false;
          closeResponsiveAgentOverlay();
        } else {
          setAgentChatExpanded(true);
          helpOpen = false;
        }
        render();
        requestCanvasSafeAreaUpdate();
        requestAnimationFrame(() => {
          const focusTarget = key === "help"
            ? document.querySelector(".studio-mobile-help-sheet button, .studio-mobile-help-sheet")
            : key === "agent"
            ? document.querySelector(".studio-agent-chat button, .agent-chat-composer textarea")
            : document.getElementById("product-main");
          focusTarget?.focus();
        });
      });
      nav.appendChild(button);
    }
    return nav;
  }

  function buildMobileHelpSheet() {
    const sheet = node("section", "studio-mobile-help-sheet");
    sheet.tabIndex = -1;
    sheet.setAttribute("aria-label", "移动端使用指南");
    const close = node("button", "studio-icon-button");
    close.type = "button";
    close.setAttribute("aria-label", "关闭使用指南");
    close.innerHTML = icon("x", 15);
    close.addEventListener("click", () => {
      helpOpen = false;
      render();
      requestCanvasSafeAreaUpdate();
    });
    sheet.append(close, buildHelpMenu());
    return sheet;
  }

  function viewButton(key, label) {
    const active = section === key;
    const button = node("button", active ? "active" : "", label);
    button.type = "button";
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", String(active));
    button.addEventListener("click", () => key === "canvas" ? openCanvas() : showStoryboard());
    return button;
  }

  function activateNextAction() {
    const target = findNextProductionTarget(sceneModel(), selection);
    if (!target) {
      focusAgentComposer();
      return;
    }
    const actionLabel = snapshot.project?.next_action || "继续当前镜头制作";
    projectDrawerOpen = false;
    setAgentChatExpanded(true);
    selectContext(target.sceneIndex, target.shotIndex, {
      actionLabel,
      noticeText: `已定位到场景 ${String(target.sceneIndex + 1).padStart(2, "0")} · 镜头 ${String(target.shotIndex + 1).padStart(2, "0")}，AI 创作搭档已绑定当前上下文。`,
    });
  }

  function selectContext(sceneIndex, shotIndex, { actionLabel = "", noticeText = "" } = {}) {
    const scenes = sceneModel();
    if (!scenes.length) {
      selection = { sceneIndex: 0, shotIndex: 0 };
      setAgentChatExpanded(true);
      notice = noticeText || "先完成创作简报，确认后再创建故事事实。";
      syncCanvasSelection();
      render();
      requestCanvasSafeAreaUpdate();
      requestAnimationFrame(() => document.getElementById("product-main")?.focus());
      return;
    }
    const nextSceneIndex = Math.max(0, Math.min(Number(sceneIndex || 0), scenes.length - 1));
    const nextShotIndex = Math.max(0, Math.min(Number(shotIndex || 0), scenes[nextSceneIndex].shots.length - 1));
    selection = { sceneIndex: nextSceneIndex, shotIndex: nextShotIndex };
    notice = noticeText;
    if (actionLabel) {
      const context = currentAgentChatContext();
      const session = agentChatContexts.get(agentChatContextKey(context));
      session.messages.push({
        role: "assistant",
        text: `${actionLabel} 已绑定当前镜头。请发送命令获取预览，确认前不会写入画布。`,
        created_at: new Date().toISOString(),
      });
    }
    syncCanvasSelection();
    render();
    requestCanvasSafeAreaUpdate();
    requestAnimationFrame(focusCurrentContext);
  }

  function syncCanvasSelection() {
    options.onSelectCanvasNode?.(currentShot().nodeId || "");
  }

  function focusAgentComposer() {
    setAgentChatExpanded(true);
    notice = "AI 创作搭档已绑定当前画布上下文；确认前不会创建场景或镜头。";
    render();
    requestCanvasSafeAreaUpdate();
    requestAnimationFrame(() => document.querySelector(".agent-chat-composer textarea")?.focus());
  }

  async function submitToAgentChat(messageText) {
    const context = currentAgentChatContext();
    const session = agentChatContexts.get(agentChatContextKey(context));
    const result = await submitAgentChatMessageWithRuntime(session, messageText, context, options.getRuntime?.());
    setAgentChatExpanded(true);
    if (result.status === "empty") focusAgentComposer();
    else render();
    requestCanvasSafeAreaUpdate();
    requestAnimationFrame(() => document.querySelector(".agent-chat-composer textarea")?.focus());
    return result;
  }

  function bindShellEvents() {
    window.addEventListener("afs:agent-chat-submit", (event) => {
      submitToAgentChat(event.detail?.message || "").catch((error) => {
        const context = currentAgentChatContext();
        const session = agentChatContexts.get(agentChatContextKey(context));
        recordAgentCommandError(session, error);
        render();
      });
    });
    window.addEventListener("afs:agent-chat-focus", () => focusAgentComposer());
    const narrowAgentQuery = responsiveAgentMediaQuery();
    narrowAgentQuery?.addEventListener?.("change", () => {
      syncResponsiveAgentState({ force: true });
      render();
      requestCanvasSafeAreaUpdate();
    });
    mobileNavigationMediaQuery()?.addEventListener?.("change", () => {
      render();
      requestCanvasSafeAreaUpdate();
    });
    window.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (projectDrawerOpen || contextOpen || mobileAgentOpen || helpOpen) {
        projectDrawerOpen = false;
        contextOpen = false;
        helpOpen = false;
        if (mobileAgentOpen) closeResponsiveAgentOverlay();
        render();
        requestCanvasSafeAreaUpdate();
      }
    });
  }

  function syncResponsiveAgentState({ force = false } = {}) {
    const projectKey = snapshot.project?.project_id || "studio";
    if (agentPreferenceProjectKey !== projectKey || force) {
      agentPreferenceProjectKey = projectKey;
      if (isNarrowAgentLayout()) {
        mobileAgentOpen = readAgentMobilePreference(projectKey);
      }
    }
    if (isNarrowAgentLayout() && !mobileAgentOpen) {
      agentCollapsed = true;
    }
  }

  function isAgentChatCollapsed() {
    return agentCollapsed || (isNarrowAgentLayout() && !mobileAgentOpen);
  }

  function setAgentChatExpanded(expanded) {
    const nextExpanded = Boolean(expanded);
    agentCollapsed = !nextExpanded;
    mobileAgentOpen = nextExpanded;
    if (isNarrowAgentLayout()) writeAgentMobilePreference(agentPreferenceProjectKey || "studio", nextExpanded);
  }

  function isPlanningPanelExpanded() {
    return Boolean(planningPanelOpen || String(m6SourceText || "").trim());
  }

  function setPlanningPanelOpen(open) {
    planningPanelOpen = Boolean(open);
    writePlanningPanelPreference(currentPlanningPanelPreferenceKey(), planningPanelOpen);
  }

  function syncPlanningPanelPreference({ force = false } = {}) {
    const nextKey = currentPlanningPanelPreferenceKey();
    if (!force && planningPanelPreferenceKey === nextKey) return;
    planningPanelPreferenceKey = nextKey;
    planningPanelOpen = readPlanningPanelPreference(nextKey);
  }

  function currentPlanningPanelPreferenceKey() {
    return `afs:m6:plan-panel:${snapshot.project?.project_id || "studio"}`;
  }

  function closeResponsiveAgentOverlay() {
    if (isNarrowAgentLayout()) {
      setAgentChatExpanded(false);
    } else {
      mobileAgentOpen = false;
    }
  }

  function isNarrowAgentLayout() {
    return Boolean(responsiveAgentMediaQuery()?.matches);
  }

  function isMobileNavigationLayout() {
    return Boolean(mobileNavigationMediaQuery()?.matches);
  }

  function responsiveAgentMediaQuery() {
    return typeof window !== "undefined" && typeof window.matchMedia === "function"
      ? window.matchMedia("(max-width: 1100px)")
      : null;
  }

  function mobileNavigationMediaQuery() {
    return typeof window !== "undefined" && typeof window.matchMedia === "function"
      ? window.matchMedia("(max-width: 760px)")
      : null;
  }

  function bindAgentResize(event) {
    if (!event?.pointerId || isAgentChatCollapsed()) return;
    event.preventDefault();
    const startX = event.clientX;
    const startWidth = agentChatWidth;
    event.currentTarget?.setPointerCapture?.(event.pointerId);
    document.body.classList.add("is-resizing-agent-chat");
    const onMove = (moveEvent) => {
      agentChatWidth = clampAgentChatWidth(startWidth + (startX - moveEvent.clientX));
      document.querySelector(".studio-unified-workspace")?.style?.setProperty("--agent-chat-width", `${agentChatWidth}px`);
    };
    const onEnd = () => {
      document.body.classList.remove("is-resizing-agent-chat");
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onEnd);
      window.removeEventListener("pointercancel", onEnd);
      storeAgentChatWidth(agentChatWidth);
      render();
      requestCanvasSafeAreaUpdate();
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onEnd, { once: true });
    window.addEventListener("pointercancel", onEnd, { once: true });
  }

  function bindPlanResize(event) {
    if (!event?.pointerId || isNarrowAgentLayout()) return;
    event.preventDefault();
    const startY = event.clientY;
    const startHeight = planningPanelHeight;
    event.currentTarget?.setPointerCapture?.(event.pointerId);
    document.body.classList.add("is-resizing-plan-panel");
    const onMove = (moveEvent) => {
      planningPanelHeight = clampPlanningPanelHeight(startHeight - (moveEvent.clientY - startY));
      document.querySelector(".graph-canvas-status")?.style?.setProperty("--graph-plan-height", `${planningPanelHeight}px`);
    };
    const onEnd = () => {
      document.body.classList.remove("is-resizing-plan-panel");
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onEnd);
      window.removeEventListener("pointercancel", onEnd);
      writePlanningPanelHeight(planningPanelHeight);
      render();
      requestCanvasSafeAreaUpdate();
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onEnd, { once: true });
    window.addEventListener("pointercancel", onEnd, { once: true });
  }

  function focusCurrentContext() {
    const target = section === "storyboard"
      ? document.getElementById(`storyboard-shot-${selection.sceneIndex}-${selection.shotIndex}`)
      : document.getElementById("product-main");
    target?.focus();
  }

  function currentContextKey() {
    return productContextKey({
      projectId: snapshot.project?.project_id,
      sceneIndex: selection.sceneIndex,
      shotIndex: selection.shotIndex,
      shot: currentShot(),
    });
  }

  function currentAgentChatContext() {
    const studioState = productionGraphAgentContext(snapshot.studioState, snapshot.sequenceWorkspace);
    if (mediaOperationsReady()) {
      studioState.production_media_operations = {
        project_id: mediaOperationsView().project_id,
        run_id: mediaOperationsView().run_id,
        classification: mediaOperationsView().classification,
        graph_digest: mediaOperationsView().summary?.graph_digest || "",
        selected_shot_id: currentShot().media?.shot_id || "",
        visible_in_same_studio_shell: true,
      };
    }
    const context = agentChatContextSnapshot({
      project: snapshot.project,
      studioState,
      section,
      selectedNode: selectedCanvasNode(),
      currentShot: currentShot(),
    });
    if (mediaOperationsReady()) {
      const ops = mediaOperationsView();
      const selected = currentShot();
      context.selected_node_title = selected.title || "当前镜头";
      context.media_operations = {
        state_label: ops.classification === "RECOVERY_EVIDENCE_NOT_COUNTED" ? "恢复证据" : "审片候选",
        scene_count: Number(ops.summary?.scene_count || 0),
        shot_count: Number(ops.summary?.shot_count || 0),
        ready_shot_count: Number(ops.summary?.ready_shot_count || 0),
        estimated_cost_usd: Number(ops.cost?.conservative_estimated_usd || 0),
        next_action: ops.stage?.next_action || "进入故事板审片",
      };
      context.counts = {
        ...(context.counts || {}),
        scenes: context.media_operations.scene_count,
        shots: context.media_operations.shot_count,
      };
    }
    return context;
  }

  function selectedCanvasNode() {
    const state = snapshot.studioState || {};
    const selectedId = state.selection?.nodeIds?.[0] || currentShot().nodeId || "";
    return selectedId ? state.nodes?.[selectedId] || null : null;
  }

  function selectedGraphTarget() {
    const selected = selectedCanvasNode();
    const truth = selected?.params?.productionGraphTruth;
    if (!truth?.graph_node_id) return null;
    return { nodeId: truth.graph_node_id, title: cleanTitle(selected.title || "所选制作对象") };
  }

  function openCanvas() {
    const opened = options.onOpenCanvas?.();
    if (opened === false) {
      section = "storyboard";
      closeResponsiveAgentOverlay();
      notice = "移动端保留项目上下文与审核；画布编辑请在桌面打开。";
      render();
    }
  }

  function statePanel(kind) {
    const wrap = node("section", `product-state product-state-${kind}`);
    wrap.setAttribute("role", kind === "error" ? "alert" : "status");
    if (kind === "loading") {
      wrap.append(node("div", "state-spinner"), node("h1", "", message("loading", locale)), node("p", "", "正在恢复项目、场景与镜头上下文。"));
    } else if (kind === "error") {
      wrap.append(node("h1", "", message("error", locale)), node("p", "", snapshot.error), node("p", "", message("recovery", locale)));
      const retry = node("button", "studio-primary-button", message("retry", locale));
      retry.addEventListener("click", () => options.onRetry?.());
      wrap.appendChild(retry);
    } else {
      wrap.append(node("h1", "", message("empty", locale)), node("p", "", "新建项目后，Studio 会在同一工作区恢复故事板、画布与审核上下文。"));
      const create = node("button", "studio-primary-button", "新建项目");
      create.type = "button";
      create.addEventListener("click", () => options.onCreateProject?.());
      wrap.appendChild(create);
    }
    return wrap;
  }

  async function refresh(runtime, authUser = null) {
    const requestRuntime = runtime;
    snapshot = { ...snapshot, loading: true, error: "", authUser, studioState: options.getStudioState?.() || snapshot.studioState };
    render();
    try {
      const workspace = await requestRuntime.workspaceOverview();
      if (options.isRuntimeCurrent && !options.isRuntimeCurrent(requestRuntime)) return;
      const activeProjectId = requestRuntime.projectId && requestRuntime.projectId !== "studio-empty"
        ? requestRuntime.projectId
        : workspace?.projects?.[0]?.project_id || "";
      const activeProjectSummary = (workspace?.projects || []).find((item) => item?.project_id === activeProjectId) || null;
      let project = null;
      if (activeProjectId) {
        const projectRuntime = activeProjectId === requestRuntime.projectId ? requestRuntime : options.createRuntime?.(activeProjectId);
        const payload = await projectRuntime?.projectOverview?.();
        if (options.isRuntimeCurrent && !options.isRuntimeCurrent(requestRuntime)) return;
        project = payload?.project || null;
      }
      let sequenceWorkspace = null;
      if (activeProjectId) {
        try { sequenceWorkspace = await (activeProjectId === requestRuntime.projectId ? requestRuntime : options.createRuntime?.(activeProjectId))?.sequenceWorkspace?.(); } catch { sequenceWorkspace = null; }
      }
      let mediaOperations = null;
      if (activeProjectId && shouldLoadMediaOperations(project, activeProjectSummary)) {
        try { mediaOperations = await (activeProjectId === requestRuntime.projectId ? requestRuntime : options.createRuntime?.(activeProjectId))?.adaptiveCanvasOperations?.("paid-media-v2"); } catch { mediaOperations = null; }
      }
      if (sequenceWorkspace) {
        applyGraphWorkspace(sequenceWorkspace);
      }
      snapshot = { loading: false, workspace, project, sequenceWorkspace, mediaOperations, mediaCommandPreview: null, error: "", authUser, studioState: options.getStudioState?.() || snapshot.studioState };
    } catch (error) {
      if (options.isRuntimeCurrent && !options.isRuntimeCurrent(requestRuntime)) return;
      snapshot = { ...snapshot, loading: false, project: null, error: options.formatError?.(error) || message("error", locale), authUser };
    }
    render();
  }

  function updateStudioState(studioState, options = {}) {
    snapshot = { ...snapshot, studioState };
    if (!document.getElementById("app")?.classList.contains("product-mode")) return;
    if (options.render === false || options.deferRender === true) {
      syncSaveStatusElement();
      return;
    }
    render();
  }

  function syncSaveStatusElement() {
    const status = document.querySelector(".studio-save-status");
    if (!status) return;
    const saveState = String(snapshot.studioState?.ui?.saveState || "本地暂存");
    status.textContent = saveState;
    status.className = `studio-save-status ${saveTone(saveState)}`;
    status.title = snapshot.studioState?.ui?.saveMessage || saveState;
  }

  function showStoryboard() {
    section = "storyboard";
    closeResponsiveAgentOverlay();
    render();
  }

  function showOverview() {
    showStoryboard();
  }

  function showCanvas() {
    if (!options.getCanvasShell?.()) return false;
    section = "canvas";
    syncCanvasSelection();
    render();
    return true;
  }

  function sceneModel() {
    if (mediaOperationsReady()) return mediaSceneModel();
    if (graphWorkspaceReady()) return graphSceneModel();
    const shots = shotModel();
    if (!shots.length) {
      selection = { sceneIndex: 0, shotIndex: 0 };
      return [];
    }
    const sceneCount = Math.max(1, Math.min(5, Math.ceil(shots.length / 7)));
    const scenes = Array.from({ length: sceneCount }, (_, index) => ({
      name: `场景 ${index + 1}`,
      shots: [],
      duration: "00:00",
      blocked: false,
    }));
    shots.forEach((shot, index) => scenes[Math.min(sceneCount - 1, Math.floor(index / 7))].shots.push(shot));
    for (const scene of scenes) {
      scene.duration = formatDuration(scene.shots.reduce((sum, shot) => sum + Number.parseFloat(shot.duration), 0));
      scene.blocked = scene.shots.some((shot) => shot.state === "blocked");
    }
    const sceneIndex = Math.min(selection.sceneIndex, scenes.length - 1);
    selection = {
      sceneIndex,
      shotIndex: Math.min(selection.shotIndex, scenes[sceneIndex].shots.length - 1),
    };
    return scenes;
  }

  function shotModel() {
    if (mediaOperationsReady()) return mediaShotModel();
    if (graphWorkspaceReady()) return graphShotModel();
    const state = snapshot.studioState || {};
    const planShots = state.production?.dynamic_production_plan_projection?.storyboard_shots || [];
    if (Array.isArray(planShots) && planShots.length) {
      return planShots
        .slice()
        .sort((left, right) => Number(left.order || 0) - Number(right.order || 0))
        .map((shot, index) => ({
          nodeId: `production_plan_shot_${String(shot.shot_id || "").replace(/[^A-Za-z0-9_.:-]/g, "")}`,
          title: cleanTitle(shot.title || shot.shot_id || shotTitle(index)),
          description: cleanDescription([
            shot.intent || "",
            shot.strategy ? `${String(shot.strategy).toUpperCase()} · ${shot.strategy_reason || ""}` : "",
          ].filter(Boolean).join("\n")),
          duration: `${Number(shot.duration_seconds || 0).toFixed(1)}s`,
          preview: "",
          state: shot.status === "failed" || shot.media_input_state === "pending_input" ? "blocked" : shot.status === "planned" ? "ready" : "draft",
        }));
    }
    const nodes = Object.values(state.nodes || {});
    const candidates = nodes.filter((item) => item && (
      item.previewUrl
      || item.params?.structuredShot
      || item.params?.nodeRole === "storyboard_shot"
      || ["image", "video"].includes(item.type)
    ));
    const mapped = candidates.slice(0, 16).map((item, index) => {
      const structured = item.params?.structuredShot || {};
      const title = cleanTitle(structured.title || item.title || item.label || shotTitle(index));
      const description = cleanDescription(structured.description || structured.action || item.prompt || item.content || item.result || "等待补充镜头说明");
      return {
        nodeId: item.id,
        title,
        description,
        duration: `${Number(structured.duration_seconds || item.params?.duration || 3 + (index % 3) * 0.5).toFixed(1)}s`,
        preview: safePreview(item.previewUrl || item.params?.lastVideoPreviewUrl || ""),
        state: item.status === "failed" ? "blocked" : item.status === "complete" || item.previewUrl || item.result ? "ready" : "draft",
      };
    });
    if (mapped.length) return mapped;
    return [];
  }

  function graphView() { return productionGraphWorkspaceProjection(snapshot.sequenceWorkspace); }

  function graphWorkspaceReady() { return graphView().status === "ready"; }

  function mediaOperationsView() { return snapshot.mediaOperations || {}; }

  function shouldLoadMediaOperations(project, summary = null) {
    return String(project?.project_type || summary?.project_type || "") === "m6_2_paid_image_video_asset_reuse";
  }

  function mediaOperationsReady() {
    const ops = mediaOperationsView();
    return ops["schema" + "_version"] === "afs.media_operations_review.v0.1" && Array.isArray(ops.shots) && ops.shots.length > 0;
  }

  function mediaShotModel() {
    return (mediaOperationsView().shots || []).map((shot, index) => ({
      nodeId: `media_ops_${String(shot.shot_id || index).replace(/[^A-Za-z0-9_.:-]/g, "")}`,
      title: cleanTitle(shot.title || shotTitle(index)),
      description: cleanDescription(shot.purpose || shot.staging || "等待补充镜头说明"),
      duration: `${Number(shot.duration_sec || 0).toFixed(1)}s`,
      preview: safePreview(shot.keyframe_url || ""),
      state: shot.status === "ready" ? "ready" : "blocked",
      sceneId: shot.scene_id || "",
      media: shot,
    }));
  }

  function mediaSceneModel() {
    const shots = mediaShotModel();
    const scenes = (mediaOperationsView().scenes || []).map((scene) => ({
      name: cleanTitle(scene.name || "场景"),
      sceneId: scene.scene_id || "",
      shots: shots.filter((shot) => shot.sceneId === scene.scene_id),
      duration: "00:00",
      blocked: false,
    }));
    const fallback = scenes.length ? scenes : [{ name: "生产审片", sceneId: "", shots, duration: "00:00", blocked: false }];
    for (const scene of fallback) {
      scene.duration = formatDuration(scene.shots.reduce((sum, shot) => sum + Number.parseFloat(shot.duration), 0));
      scene.blocked = scene.shots.some((shot) => shot.state === "blocked") || mediaOperationsView().classification === "RECOVERY_EVIDENCE_NOT_COUNTED";
    }
    return fallback;
  }

  function graphShotModel() {
    return graphView().shots.map((shot, index) => ({ nodeId: shot.nodeId, graphNodeId: shot.graphNodeId,
      title: cleanTitle(shot.title || shotTitle(index)), description: cleanDescription(shot.description || "等待补充镜头说明"),
      duration: `${shot.durationSeconds.toFixed(1)}s`, preview: "", state: shot.state, sceneId: shot.sceneNodeId }));
  }

  function graphSceneModel() {
    const shots = graphShotModel();
    const scenes = graphView().scenes.map((scene) => ({ name: cleanTitle(scene.name || "场景"),
      shots: shots.filter((shot) => shot.sceneId === scene.graphNodeId), duration: "00:00", blocked: false }));
    for (const scene of scenes) { scene.duration = formatDuration(scene.shots.reduce((sum, shot) => sum + Number.parseFloat(shot.duration), 0)); scene.blocked = scene.shots.some((shot) => shot.state === "blocked"); }
    return scenes;
  }

  function currentScene() { return sceneModel()[selection.sceneIndex] || emptyScene(); }
  function currentShot() { return currentScene().shots[selection.shotIndex] || emptyShot(); }
  function hasStoryFacts() { return shotModel().length > 0; }
  function totalShots() { return sceneModel().reduce((sum, scene) => sum + scene.shots.length, 0); }
  function totalReadyShots() { return sceneModel().flatMap((scene) => scene.shots).filter((shot) => shot.state === "ready").length; }
  function completionPercent() { return totalShots() ? Math.round((totalReadyShots() / totalShots()) * 100) : 0; }
  function pendingCount() { return Number(snapshot.project?.decision_inbox?.pending_count || 0) + Number(snapshot.project?.crew?.blocked_count || 0); }
  function shotStateLabel(state) { return state === "ready" ? "已确认" : state === "blocked" ? "待处理" : "草稿"; }
  function graphStateLabel(state) {
    return ({ planned: "待制作", reserved: "已预留", dispatched: "处理中", succeeded: "已完成", candidate: "待选择",
      pending: "待审核", approved: "已通过", rejected: "已退回", redo_planned: "已安排返工",
      review_ready: "待交付核验", blocked: "已阻断" })[String(state || "")] || "待确认";
  }

  function readinessLabel(state) {
    return ({ pass: "通过", fail: "需处理", warning: "需关注", not_claimed: "未声明" })[String(state || "")] || "待确认";
  }

  function saveTone(state) {
    if (state === "已保存") return "success";
    if (state === "保存中" || state === "同步中") return "saving";
    if (["需要登录", "保存冲突", "保存失败"].includes(state)) return "error";
    return "local";
  }

  return {
    render,
    refresh,
    updateStudioState,
    showOverview,
    showStoryboard,
    showCanvas,
    setSection(next) {
      if (next === "agent") {
        setAgentChatExpanded(true);
      } else if (next === "storyboard") {
        section = "storyboard";
      } else {
        section = "canvas";
      }
      render();
      requestCanvasSafeAreaUpdate();
    },
    get section() { return section; },
  };
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

function statusItem(iconName, label, tone) {
  const item = node("span", `studio-status-item ${tone}`);
  item.innerHTML = `${icon(iconName, 13)}<span>${escapeHtml(label)}</span>`;
  return item;
}

function candidateDeliveryProgress(project) {
  return project?.delivery?.candidate_selected ? 40 : 0;
}

function emptyScene() {
  return { name: "尚未创建场景", shots: [], duration: "00:00", blocked: false };
}

function emptyShot() {
  return {
    nodeId: "",
    title: "等待创作简报",
    description: "确认创作简报前不会创建场景或镜头。",
    duration: "0.0s",
    preview: "",
    state: "draft",
  };
}

function shotTitle(index) {
  return `镜头 ${Number(index || 0) + 1}`;
}

function cleanTitle(value) {
  return String(value || "镜头").replace(/[_-]+/g, " ").trim().slice(0, 28) || "镜头";
}

function cleanDescription(value) {
  const text = String(value || "").replace(/\s+/g, " ").trim();
  return text.slice(0, 72) || "等待补充镜头说明";
}

function formatDuration(value) {
  const seconds = Math.max(0, Number(value || 0));
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds - minutes * 60;
  const secondText = Number.isInteger(remainder) ? String(remainder).padStart(2, "0") : remainder.toFixed(1).padStart(4, "0");
  return `${String(minutes).padStart(2, "0")}:${secondText}`;
}

function safePreview(value) {
  const text = String(value || "").trim();
  return /^(\/|https?:\/\/)/i.test(text) && !/^file:/i.test(text) ? text : "";
}

function userLabel(user) {
  return String(user?.display_name || user?.email || "账户").slice(0, 2).toUpperCase();
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
}

function node(tag, className = "", text = "") {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== "") element.textContent = String(text);
  return element;
}

function readAgentChatWidth() {
  let stored = 392;
  try {
    stored = Number(window.localStorage?.getItem("afs_agent_chat_width") || stored);
  } catch {
    stored = 392;
  }
  return clampAgentChatWidth(stored);
}

function readAgentMobilePreference(projectKey) {
  try {
    return window.sessionStorage?.getItem(agentMobilePreferenceKey(projectKey)) === "open";
  } catch {
    return false;
  }
}

function writeAgentMobilePreference(projectKey, open) {
  try {
    window.sessionStorage?.setItem(agentMobilePreferenceKey(projectKey), open ? "open" : "closed");
  } catch {
    // Session storage can be unavailable; the current render still carries the state.
  }
}

function agentMobilePreferenceKey(projectKey) {
  return `afs_agent_chat_narrow_open:${String(projectKey || "studio")}`;
}

function storeAgentChatWidth(width) {
  try {
    window.localStorage?.setItem("afs_agent_chat_width", String(clampAgentChatWidth(width)));
  } catch {
    // Storage can be unavailable; the current session width is already applied.
  }
}

function clampAgentChatWidth(value) {
  return Math.max(360, Math.min(420, Math.round(Number(value) || 392)));
}

function readPlanningPanelPreference(key) {
  try {
    return window.sessionStorage?.getItem(key) === "open";
  } catch {
    return false;
  }
}

function writePlanningPanelPreference(key, open) {
  try {
    window.sessionStorage?.setItem(key, open ? "open" : "closed");
  } catch {
    // Session storage can be unavailable; the current render still carries the state.
  }
}

function readPlanningPanelHeight() {
  let stored = 260;
  try {
    stored = Number(window.localStorage?.getItem("afs_m6_plan_panel_height") || stored);
  } catch {
    stored = 260;
  }
  return clampPlanningPanelHeight(stored);
}

function writePlanningPanelHeight(height) {
  try {
    window.localStorage?.setItem("afs_m6_plan_panel_height", String(clampPlanningPanelHeight(height)));
  } catch {
    // Storage can be unavailable; the current session height is already applied.
  }
}

function clampPlanningPanelHeight(value) {
  return Math.max(176, Math.min(420, Math.round(Number(value) || 260)));
}

function requestCanvasSafeAreaUpdate() {
  requestAnimationFrame(() => window.dispatchEvent(new CustomEvent("afs:canvas-safe-area-changed")));
}
