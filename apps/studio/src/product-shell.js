import { currentLocale, message, setLocale } from "./i18n.js";
import { icon } from "./icons.js";
import { findNextProductionTarget, productContextKey } from "./product-shell-context.js";
import { buildAgentChatPanel } from "./agent-chat-panel.js";
import { agentChatContextFingerprint, agentChatContextKey, agentChatContextSnapshot, createAgentChatContextStore, stageM6ScriptPlanCandidateCommand, stageProductionGraphCandidateCommand, stageProductionGraphCommand, submitAgentChatMessageWithRuntime, syncM6PreviewRunSession } from "./agent-chat-lifecycle.js";
import { applyProductionGraphCanvasProjection, productionGraphAgentContext, productionGraphWorkspaceProjection } from "./production-graph-workspace-projection.js";
import { fitVisibleCanvasViewport } from "./canvas-safe-area.js";
import { legacyAppliedStoryboardProjection } from "./shot-truth-projection.js";
import {
  assetBibleProjection,
  assetBibleSourceContext,
  assetVisualBlockers,
  assetOccurrenceLabel,
  assetReviewLabel,
  assetTypeLabel,
  deriveProductionCopilotState,
  localizedNegativeLock,
  pendingFieldLabel,
} from "./asset-bible-workspace.js";
import {
  imageAdmissionCommand,
  imageAdmissionGenerationRequest,
  imageAdmissionGenerationResult,
  imageAdmissionItemTypeLabel,
  imageAdmissionItemJobId,
  imageAdmissionJobCommand,
  imageAdmissionMediaKey,
  imageAdmissionProjection,
  imageAdmissionStateLabel,
} from "./image-admission-workspace.js";
import {
  assetBibleConfirmRecovery,
  assetBibleConfirmRequest,
  syncAssetBibleCommandAssistantReceipt,
} from "./asset-bible-command-recovery.js";

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
  let m6PreviewRun = null;
  let m6PreviewRecovering = false;
  let m6PreviewPollGeneration = 0;
  let planningPanelOpen = false;
  let planningPanelPreferenceKey = "";
  let planningPanelHeight = readPlanningPanelHeight();
  let graphRefreshPending = false;
  let agentChatWidth = readAgentChatWidth();
  let selectedAssetId = "";
  let assetCommandPreview = null;
  let assetCommandError = "";
  let assetCommandRecovery = null;
  let assetCommandConfirmPending = false;
  let lastAssetCommand = null;
  let assetDraft = null;
  let artDirectionDraft = null;
  let assetCreateOpen = false;
  let assetCreateDraft = { asset_type: "prop", display_name: "", aliases: "", scene_ids: [], shot_ids: [], evidence: "" };
  let resolutionReason = "";
  let mergeAssetIds = new Set();
  let imageAdmissionOpen = false;
  let imageAdmissionPreview = null;
  let imageAdmissionError = "";
  const imageAdmissionMediaStates = new Map();
  let imageAdmissionViewer = null;
  let imageAdmissionViewerReturnKey = "";
  const agentChatContexts = createAgentChatContextStore();
  let snapshot = {
    loading: true,
    workspace: null,
    project: null,
    studioState: null,
    mediaOperations: null,
    runtimeAssetBible: null,
    imageAdmission: null,
    mediaGates: {},
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
    if (projectIdentityStatus() === "blocked") root.appendChild(statePanel("identity"));
    else if (projectIdentityStatus() === "loading") root.appendChild(statePanel("loading"));
    else if (snapshot.loading) root.appendChild(statePanel("loading"));
    else if (snapshot.error) root.appendChild(statePanel("error"));
    else if (!snapshot.project) root.appendChild(statePanel("empty"));
    else {
      const workspace = buildWorkspace();
      if (projectIdentityStatus() === "cache_read_only") {
        workspace.classList.add("identity-cache-read-only");
        workspace.querySelectorAll("button, input, textarea, select").forEach((control) => {
          control.disabled = true;
        });
        workspace.prepend(node("div", "identity-cache-banner", "只读缓存 · 重新验证当前项目后才能继续修改或调用 AI"));
      }
      root.appendChild(workspace);
    }
    if (helpOpen && isMobileNavigationLayout()) root.appendChild(buildMobileHelpSheet());
    root.appendChild(buildMobileNav());
    if (imageAdmissionViewer) root.appendChild(buildImageAdmissionViewer());
  }

  function buildHeader() {
    const header = node("header", "studio-unified-header");
    const brand = node("button", "studio-unified-brand");
    brand.type = "button";
    brand.setAttribute("aria-label", "返回项目画布");
    brand.innerHTML = '<img class="studio-brand-logo" src="./favicon.svg" alt="" aria-hidden="true"><strong aria-label="AgentFlow Studio">AFS</strong>';
    brand.addEventListener("click", () => {
      projectDrawerOpen = false;
      contextOpen = false;
      helpOpen = false;
      accountMenuOpen = false;
      showCanvas();
    });

    const project = node("div", "studio-project-context");
    const projectLabel = node("button", "studio-project-button");
    const projectName = projectDisplayName();
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

    const viewSwitch = node("div", "studio-view-switch");
    viewSwitch.setAttribute("role", "tablist");
    viewSwitch.setAttribute("aria-label", "工作区视图");
    viewSwitch.append(
      viewButton("canvas", "画布"),
      viewButton("storyboard", "故事板"),
      viewButton("asset_bible", "资产 Bible"),
    );

    const summary = node("div", "studio-header-summary");
    const progress = Math.max(0, Math.min(100, Number(snapshot.project?.progress_percent || candidateDeliveryProgress(snapshot.project))));
    appendHeaderSummary(summary, progress);

    const actions = node("div", "studio-header-actions");
    actions.appendChild(buildSaveStatus());
    if (notice) actions.appendChild(buildHeaderNotice());
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

    header.append(brand, project, viewSwitch, summary, actions);
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
      node("p", "", "从想法、剧本、镜头、角色、参考图、图片或视频开始；需要改写、拆分或生成时，先查看完整影响，再决定是否保存。"),
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
    const identity = node("p", "studio-account-identity", snapshot.authUser
      ? `${snapshot.authUser.display_name || snapshot.authUser.email || "当前账号"}`
      : "本地创作会话");
    menu.appendChild(identity);
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
      `<strong>${escapeHtml(projectDisplayName())}</strong>`,
      `<small>${escapeHtml(snapshot.project?.episode || "单集制作")}</small>`,
    ].join("");
    menu.appendChild(current);
    const projects = snapshot.workspace?.projects || [];
    if (projects.length > 4) {
      const search = node("input", "studio-project-search");
      search.type = "search";
      search.placeholder = "搜索最近项目";
      search.setAttribute("aria-label", "搜索项目");
      search.addEventListener("input", () => filterProjectMenu(menu, search.value));
      menu.appendChild(search);
    }
    const list = node("section", "studio-project-switch-list");
    list.setAttribute("aria-label", "切换项目");
    for (const item of projects.slice(0, 8)) {
      const button = node("button", item.project_id === snapshot.project?.project_id ? "active" : "");
      button.type = "button";
      button.setAttribute("role", "menuitem");
      button.dataset.projectOption = "true";
      button.dataset.projectSearch = `${item.name || ""} ${item.episode || ""} ${item.project_id || ""}`.toLowerCase();
      button.innerHTML = `<strong>${escapeHtml(item.name || "未命名项目")}</strong><span>${escapeHtml(item.episode || "单集制作")}</span>`;
      button.addEventListener("click", () => {
        contextOpen = false;
        options.onSwitchProject?.(item.project_id);
      });
      list.appendChild(button);
    }
    menu.appendChild(list);
    const projectActions = node("section", "studio-project-management");
    projectActions.setAttribute("aria-label", "当前项目管理");
    const create = node("button", "studio-project-create");
    create.type = "button";
    create.innerHTML = `${icon("plus", 14)}<span>新建项目</span>`;
    create.addEventListener("click", () => {
      contextOpen = false;
      options.onCreateProject?.();
    });
    create.disabled = ["blocked", "cache_read_only", "loading"].includes(projectIdentityStatus());
    const settings = node("button", "studio-project-settings");
    settings.type = "button";
    settings.innerHTML = `${icon("settings", 14)}<span>项目设置</span>`;
    settings.addEventListener("click", () => {
      contextOpen = false;
      projectDrawerOpen = true;
      render();
    });
    const remove = node("button", "studio-project-delete");
    remove.type = "button";
    remove.innerHTML = `${icon("trash", 14)}<span>删除项目</span>`;
    remove.addEventListener("click", () => {
      contextOpen = false;
      options.onDeleteProject?.(snapshot.project);
      render();
    });
    remove.disabled = projectIdentityStatus() !== "ready";
    projectActions.append(create, settings, remove);
    menu.appendChild(projectActions);
    return menu;
  }

  function filterProjectMenu(menu, query) {
    const normalized = String(query || "").trim().toLowerCase();
    menu.querySelectorAll("[data-project-option='true']").forEach((button) => {
      button.hidden = Boolean(normalized) && !String(button.dataset.projectSearch || "").includes(normalized);
    });
  }

  function buildHeaderNotice() {
    const item = node("span", "studio-header-notice", notice);
    item.setAttribute("role", "status");
    item.setAttribute("aria-live", "polite");
    item.title = notice;
    return item;
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
        node("strong", "", "镜头已可审看"),
        node("span", "", `${ops.summary?.ready_shot_count || 0}/${ops.summary?.shot_count || 0} 镜头可审看 · ${ops.stage?.next_action || "进入故事板审片"}`),
      );
      const review = node("button", "studio-text-button", "查看故事板");
      review.type = "button";
      review.addEventListener("click", showStoryboard);
      status.appendChild(review);
      return status;
    }
    if (view.planningRequired) {
      return buildContextualPlanSurface(status, { existingCanvas: hasCanvasContent() });
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

  function buildContextualPlanSurface(status, options = {}) {
    const existingCanvas = Boolean(options.existingCanvas);
    if (existingCanvas && !planningPanelOpen) return buildInlinePlanAction(status);
    const expanded = isPlanningPanelExpanded();
    status.className = `graph-canvas-status planning-required ${existingCanvas ? "contextual" : "empty-entry"} ${expanded ? "expanded" : "compact"}`;
    status.dataset.expanded = String(expanded);
    if (!expanded) return buildCompactPlanSurface(status);
    return buildExpandedPlanSurface(status);
  }

  function buildInlinePlanAction(status) {
    status.className = "graph-canvas-status planning-required contextual-inline compact";
    status.dataset.expanded = "false";
    const action = node("button", "studio-text-button plan-inline-action", "制作方案");
    action.type = "button";
    action.title = "展开制作方案输入区";
    action.addEventListener("click", () => {
      setPlanningPanelOpen(true);
      render();
      requestCanvasSafeAreaUpdate();
      requestAnimationFrame(() => document.querySelector(".m6-script-plan-entry textarea")?.focus());
    });
    status.appendChild(action);
    return status;
  }

  function buildCompactPlanSurface(status) {
    status.append(
      node("strong", "", "从一个想法开始"),
      node("span", "", "描述故事、角色或一个画面，画布与 AI 创作搭档会一起继续。"),
    );
    const actions = node("div", "plan-compact-actions");
    const start = node("button", "studio-secondary-button", "输入创作想法");
    start.type = "button";
    start.addEventListener("click", () => {
      requestAnimationFrame(() => document.querySelector(".canvas-empty-onboarding textarea")?.focus());
    });
    actions.appendChild(start);
    status.appendChild(actions);
    return status;
  }

  function buildExpandedPlanSurface(status) {
    status.style.setProperty("--graph-plan-height", `${planningPanelHeight}px`);
    const head = node("div", "graph-plan-head");
    head.append(
      node("span", "eyebrow", "制作方案草案"),
      node("strong", "", "先预览，再确认"),
      node("span", "", "生成草案或导入方案后会先显示完整内容；确认前不会保存到项目。"),
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
    const previewBusy = ["queued", "running"].includes(String(m6PreviewRun?.phase || ""));
    preview.disabled = previewBusy;
    preview.textContent = previewBusy ? "制作方案处理中" : "生成剧本制作方案";
    preview.addEventListener("click", () => previewM6ScriptPlan(textarea.value));
    planner.append(textarea, preview, ...planningImportControls());
    if (m6PreviewRun?.run_id) planner.appendChild(buildM6PreviewRunStatus());
    status.append(planner, planResizeHandle());
    return status;
  }

  function buildM6PreviewRunStatus() {
    const phase = String(m6PreviewRun?.phase || "queued");
    const panel = node("section", `m6-preview-run-status phase-${phase}`);
    panel.setAttribute("role", "status");
    panel.setAttribute("aria-live", "polite");
    const copy = m6PreviewRecovering
      ? "正在恢复同一制作方案预览，不会再次提交文本任务。"
      : {
          queued: "已提交制作方案；确认前项目内容不会改变。",
          running: "制作方案处理中。连接中断后仍可恢复同一任务。",
          running_cancel_requested: "已请求停止后续处理；当前同步任务可能仍会完成。",
          succeeded: "预览已恢复并可审阅；确认前项目内容不会改变。",
          failed: m6PreviewRun?.error?.message || "制作方案需要处理；原项目内容已保留。",
          unknown: m6PreviewRun?.error?.message || "文本任务状态需要人工核对；系统不会自动再次提交。",
          cancelled: "预览已取消；项目内容没有改变。",
          confirmed: "制作方案已确认并保存。",
        }[phase] || "正在读取同一制作方案任务状态。";
    panel.appendChild(node("strong", "", m6PreviewRecovering ? "正在恢复" : m6PreviewPhaseLabel(phase)));
    panel.appendChild(node("p", "", copy));
    const actions = node("div", "m6-preview-run-actions");
    if (["queued", "running", "running_cancel_requested"].includes(phase)) {
      const cancel = node("button", "studio-secondary-button", "停止后续处理");
      cancel.type = "button";
      cancel.disabled = phase === "running_cancel_requested";
      cancel.addEventListener("click", () => cancelM6PreviewRun());
      actions.appendChild(cancel);
    }
    if (["failed", "unknown", "running", "running_cancel_requested"].includes(phase)) {
      const recover = node("button", "studio-secondary-button", "恢复同一预览");
      recover.type = "button";
      recover.addEventListener("click", () => recoverM6PreviewRun());
      actions.appendChild(recover);
    }
    if (actions.childElementCount) panel.appendChild(actions);
    return panel;
  }

  function m6PreviewPhaseLabel(phase) {
    return {
      queued: "已提交",
      running: "处理中",
      running_cancel_requested: "停止请求已记录",
      succeeded: "预览已恢复",
      failed: "任务失败",
      unknown: "需要核对",
      cancelled: "已取消",
      confirmed: "已确认",
    }[phase] || "状态恢复";
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
    const runtime = options.getRuntime?.();
    if (!runtime) return;
    const expectedProjectId = currentM6ProjectId();
    if (!isM6RuntimeCurrent(runtime, expectedProjectId)) return;
    const clientRequestId = runtime.newM6PreviewClientRequestId?.() || `m6_${Date.now()}`;
    m6PreviewRun = {
      run_id: "",
      project_id: expectedProjectId,
      client_request_id: clientRequestId,
      phase: "queued",
      status: "queued",
    };
    m6PreviewRecovering = false;
    notice = "制作方案已提交；确认前不会改变制作事实。";
    syncM6RunToAgent(m6PreviewRun);
    render();
    try {
      const run = await runtime.previewM6ScriptPlanAssetBible({
        source_kind: "idea",
        source_text: sourceText,
      }, clientRequestId);
      if (!isM6RuntimeCurrent(runtime, expectedProjectId)) return;
      await observeM6PreviewRun(run, runtime, expectedProjectId);
    } catch (error) {
      if (!isM6RuntimeCurrent(runtime, expectedProjectId)) return;
      if (error?.status === 0 && error?.clientRequestId) {
        m6PreviewRecovering = true;
        notice = "连接已中断，正在恢复同一制作方案预览；不会重复提交。";
        render();
        try {
          const recovered = await runtime.recoverM6ScriptPlanPreviewByClient(error.clientRequestId);
          if (!isM6RuntimeCurrent(runtime, expectedProjectId)) return;
          await observeM6PreviewRun(recovered, runtime, expectedProjectId);
        } catch (recoveryError) {
          notice = recoveryError?.message || "同一制作方案状态暂时无法读取；项目事实未改变。";
        }
      } else {
        notice = error?.message || "制作方案生成失败，项目内容没有改变。";
      }
    }
    render();
    requestCanvasSafeAreaUpdate();
  }

  async function observeM6PreviewRun(initialRun, runtime = options.getRuntime?.(), expectedProjectId = currentM6ProjectId()) {
    if (!runtime || !initialRun?.run_id || !isM6RunCurrent(initialRun, runtime, expectedProjectId)) return;
    const generation = ++m6PreviewPollGeneration;
    let run = initialRun;
    while (generation === m6PreviewPollGeneration) {
      if (!isM6RunCurrent(run, runtime, expectedProjectId)) return;
      m6PreviewRun = run;
      m6PreviewRecovering = false;
      syncM6RunToAgent(run);
      render();
      requestCanvasSafeAreaUpdate();
      if (!["queued", "running", "running_cancel_requested"].includes(String(run.phase || ""))) break;
      await delay(700);
      try {
        run = await runtime.loadM6ScriptPlanPreviewRun(run.run_id);
        if (!isM6RunCurrent(run, runtime, expectedProjectId)) return;
      } catch (error) {
        if (!isM6RuntimeCurrent(runtime, expectedProjectId)) return;
        m6PreviewRecovering = true;
        notice = error?.status === 0
          ? "连接已中断，仍在恢复同一制作方案预览。"
          : (error?.message || "制作方案状态暂时无法读取。");
        if (error?.status && error.status !== 0) {
          m6PreviewRecovering = false;
          render();
          return;
        }
        render();
        await delay(1200);
      }
    }
    if (generation !== m6PreviewPollGeneration || !isM6RunCurrent(run, runtime, expectedProjectId)) return;
    m6PreviewRun = run;
    m6PreviewRecovering = false;
    syncM6RunToAgent(run);
    if (run.phase === "succeeded") {
      stageRecoveredM6Candidate(run);
      notice = "制作方案预览已恢复；确认前不会保存到项目。";
    } else if (run.phase === "failed") {
      notice = run?.error?.message || "制作方案任务失败；项目事实未改变。";
    } else if (run.phase === "cancelled") {
      notice = "制作方案预览已取消；项目事实未改变。";
    }
  }

  function stageRecoveredM6Candidate(run) {
    if (!isM6RunCurrent(run)) return;
    const context = currentAgentChatContext();
    context.context_key = agentChatContextKey(context);
    const session = agentChatContexts.get(context.context_key);
    if (session.pendingCommand?.run_id !== run.run_id) {
      stageM6ScriptPlanCandidateCommand(session, context, run);
    }
    projectDrawerOpen = false;
    setPlanningPanelOpen(false);
    setAgentChatExpanded(true);
  }

  function syncM6RunToAgent(run) {
    if (!run?.run_id || !isM6RunCurrent(run)) return;
    const context = currentAgentChatContext();
    context.context_key = agentChatContextKey(context);
    const session = agentChatContexts.get(context.context_key);
    syncM6PreviewRunSession(session, context, run);
  }

  async function recoverM6PreviewRun() {
    if (!m6PreviewRun?.run_id) return;
    const runtime = options.getRuntime?.();
    const expectedProjectId = currentM6ProjectId();
    if (!isM6RunCurrent(m6PreviewRun, runtime, expectedProjectId)) return;
    m6PreviewRecovering = true;
    render();
    try {
      const run = await runtime.loadM6ScriptPlanPreviewRun(m6PreviewRun.run_id);
      if (!isM6RunCurrent(run, runtime, expectedProjectId)) return;
      await observeM6PreviewRun(run, runtime, expectedProjectId);
    } catch (error) {
      notice = error?.message || "同一制作方案状态暂时无法读取。";
    } finally {
      m6PreviewRecovering = false;
      render();
    }
  }

  async function cancelM6PreviewRun() {
    if (!m6PreviewRun?.run_id) return;
    const runtime = options.getRuntime?.();
    const expectedProjectId = currentM6ProjectId();
    if (!isM6RunCurrent(m6PreviewRun, runtime, expectedProjectId)) return;
    try {
      const run = await runtime.cancelM6ScriptPlanPreviewRun(m6PreviewRun.run_id);
      if (!isM6RunCurrent(run, runtime, expectedProjectId)) return;
      m6PreviewRun = run;
      syncM6RunToAgent(run);
      notice = run.phase === "cancelled"
        ? "制作方案预览已取消；项目事实未改变。"
        : "已记录停止后续处理；当前同步任务可能仍会完成。";
    } catch (error) {
      notice = error?.message || "无法更新同一制作方案的停止状态。";
    }
    render();
  }

  function applyGraphWorkspace(workspace) {
    const store = options.getStore?.();
    const ready = productionGraphWorkspaceProjection(workspace).status === "ready";
    store?.setRuntimePersistenceMode?.(ready ? "production_graph_read_only" : "studio_state");
    store?.set?.((state) => {
      applyProductionGraphCanvasProjection(state, workspace);
      if (ready) {
        const viewport = fitVisibleCanvasViewport(state.nodes, 110);
        if (viewport) state.viewport = viewport;
      }
    }, { history: false, persist: false });
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
    const emptyCanvas = section === "canvas" && !hasCanvasContent();
    const canvasActive = section === "canvas";
    const agentChatCollapsed = isAgentChatCollapsed();
    const legacyWorkspaceClass = canvasActive ? "canvas-section" : "storyboard-section";
    const workspaceClass = section === "asset_bible" ? "asset-bible-section" : legacyWorkspaceClass;
    const shell = node("div", `studio-unified-workspace ${agentChatCollapsed ? "agent-collapsed" : ""} ${mobileAgentOpen ? "agent-mobile-open" : ""} ${isNarrowAgentLayout() ? "agent-responsive-compact" : ""} ${workspaceClass} ${mediaOperationsReady() ? "media-operations-ready" : ""} ${emptyCanvas ? "canvas-empty-project" : ""}`);
    shell.dataset.contextKey = currentContextKey();
    shell.style.setProperty("--agent-chat-width", `${agentChatWidth}px`);
    if (section === "storyboard" && !emptyCanvas) shell.appendChild(buildSceneRail());
    const main = section === "canvas"
      ? buildCanvasWorkspace()
      : section === "asset_bible"
        ? buildAssetBibleWorkspace()
        : buildStoryboardWorkspace();
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
    main.appendChild(stage);
    return main;
  }

  function buildAssetBibleWorkspace() {
    const main = node("main", "studio-workspace-main studio-asset-bible");
    main.id = "product-main";
    main.tabIndex = -1;
    const view = assetBibleView();
    const source = assetBibleSourceContext(snapshot.studioState || {});
    const header = node("header", "asset-bible-header");
    const title = node("div", "");
    title.append(
      node("span", "eyebrow", "角色 · 场景 · 道具 · 制作参考"),
      node("h1", "", "Asset Bible"),
      node(
        "p",
        "",
        view.status === "locked"
          ? `版本 ${view.version} 已锁定 · ${view.counts.approved} 已批准 · ${view.counts.rejected} 已拒绝 · ${view.counts.superseded} 已取代`
          : view.counts.total
            ? `版本 ${view.version} · ${view.counts.approved}/${view.counts.total} 已批准 · ${view.counts.candidate} 待确认`
            : "从当前剧本和已应用分镜建立本地确定性资产候选。",
      ),
    );
    const headerActions = node("div", "asset-bible-header-actions");
    if (!view.counts.total) {
      const identify = node("button", "studio-primary-button", "识别资产候选");
      identify.type = "button";
      identify.disabled = !source || Boolean(assetCommandPreview);
      identify.title = source ? "基于当前剧本与已应用分镜执行本地确定性识别" : "请先应用分镜";
      identify.addEventListener("click", () => void stageAssetBibleCommand({ type: "generate_candidates" }));
      headerActions.appendChild(identify);
    } else {
      const recognize = node("button", "studio-secondary-button", "重新识别");
      recognize.type = "button";
      recognize.disabled = view.status === "locked" || Boolean(assetCommandPreview);
      recognize.title = "预览新增、聚类、保留与历史变化；确认前不改变事实";
      recognize.addEventListener("click", () => void stageAssetBibleCommand({ type: "regenerate_candidates" }));
      const add = node("button", "studio-secondary-button", "补充资产");
      add.type = "button";
      add.disabled = view.status === "locked" || Boolean(assetCommandPreview);
      add.addEventListener("click", () => {
        assetCreateOpen = !assetCreateOpen;
        render();
      });
      const merge = node("button", "studio-secondary-button", `合并已选 ${mergeAssetIds.size}`);
      merge.type = "button";
      merge.disabled = mergeAssetIds.size < 2 || view.status === "locked" || Boolean(assetCommandPreview);
      merge.addEventListener("click", () => {
        const names = view.assets.filter((item) => mergeAssetIds.has(item.stable_id)).map((item) => item.display_name);
        void stageAssetBibleCommand({
          type: "merge",
          target_ids: [...mergeAssetIds],
          display_name: names[0] || "合并资产",
        });
      });
      const lock = node("button", "studio-primary-button", view.status === "locked" ? "当前版本已锁定" : "锁定当前版本");
      lock.type = "button";
      lock.disabled = view.status === "locked"
        || view.counts.candidate > 0
        || !view.counts.approved
        || view.active_assets.some((asset) => assetVisualBlockers(asset).length)
        || view.art_direction.status !== "confirmed"
        || view.recognition_quality.status !== "pass"
        || !view.coverage.coverage_pass
        || Boolean(assetCommandPreview);
      lock.title = view.counts.candidate
        ? `仍有 ${view.counts.candidate} 个候选待确认`
        : view.active_assets.some((asset) => assetVisualBlockers(asset).length)
          ? "仍有资产缺少视觉身份、正向特征或连续性状态"
          : view.art_direction.status !== "confirmed"
            ? "请先审核并确认统一美术方向"
        : view.recognition_quality.status !== "pass"
          ? `识别质量门有 ${view.recognition_quality.issues.length} 项阻塞`
        : view.coverage.unresolved_required
          ? `${view.coverage.unresolved_required} 个必要出现范围尚未解决`
          : !view.coverage.coverage_pass
            ? `${view.coverage.shot_covered}/${view.coverage.shot_total} 镜头覆盖未完成`
            : "锁定后才满足图片生产结构准入";
      lock.addEventListener("click", () => void stageAssetBibleCommand({ type: "lock" }));
      if (view.status === "locked") headerActions.append(lock);
      else headerActions.append(recognize, add, merge, lock);
      if (view.status === "locked") {
        const admission = node("button", "studio-secondary-button", "图片准入");
        admission.type = "button";
        admission.addEventListener("click", () => {
          imageAdmissionOpen = true;
          render();
        });
        headerActions.appendChild(admission);
      }
    }
    header.append(title, headerActions);
    main.appendChild(header);
    main.appendChild(assetBibleStatusBar(view, source));
    if (view.counts.total) main.appendChild(assetBibleQualityGate(view));
    if (view.counts.total) main.appendChild(assetBibleArtDirection(view));
    if (imageAdmissionOpen || imageAdmissionView().status !== "empty") {
      main.appendChild(buildImageAdmissionPanel());
    }
    if (assetCommandError && !assetCommandPreview) main.appendChild(assetBibleFailure());
    if (assetCommandPreview) main.appendChild(assetBibleCommandReview());
    if (assetCreateOpen && view.status !== "locked") main.appendChild(assetBibleCreateForm(view));
    if (!view.counts.total) {
      main.appendChild(assetBibleEmpty(source));
      return main;
    }
    const workspace = node("div", "asset-bible-workspace");
    workspace.append(assetBibleList(view), assetBibleDetail(view));
    main.appendChild(workspace);
    return main;
  }

  function assetBibleStatusBar(view, source) {
    const bar = node("section", "asset-bible-status-bar");
    bar.setAttribute("aria-live", "polite");
    const items = [
      ["剧本", source?.script_revision_id ? "已选择" : "待选择"],
      ["镜头", source ? `${source.scene_count} 场 · ${source.shot_count} 镜头` : "待安排"],
      ["创作资产", view.counts.total ? `${view.counts.approved}/${view.counts.total} 已确认` : "待整理"],
      ["美术方向", view.art_direction.status === "confirmed" ? "已确认" : "待确认"],
      ["图片", imageAdmissionView().counts.approved
        ? `${imageAdmissionView().counts.approved} 张已确认`
        : imageAdmissionView().counts.candidate
          ? `${imageAdmissionView().counts.candidate} 张待审看`
          : "尚未生成"],
    ];
    for (const [label, value] of items) {
      const item = node("div", "");
      item.append(node("span", "", label), node("strong", "", value));
      bar.appendChild(item);
    }
    return bar;
  }

  function assetBibleQualityGate(view) {
    const sectionEl = node(
      "section",
      `asset-bible-quality-gate ${view.recognition_quality.status === "pass" ? "pass" : "blocked"}`,
    );
    sectionEl.setAttribute("aria-live", "polite");
    const head = node("div", "");
    head.append(
      node("strong", "", view.recognition_quality.status === "pass" ? "识别质量门已通过" : "识别质量门阻止锁定"),
      node(
        "span",
        "",
        `${view.coverage.asset_shot_covered}/${view.coverage.shot_total} 镜头有可追溯资产范围`,
      ),
    );
    sectionEl.appendChild(head);
    if (view.recognition_quality.status === "pass") {
      sectionEl.appendChild(node("p", "", "具名资产、别名唯一性与场景下属镜头覆盖均已通过结构检查。"));
      return sectionEl;
    }
    const list = node("ul", "");
    for (const issue of view.recognition_quality.issues.slice(0, 8)) {
      list.appendChild(node("li", "", `${issue.message} 下一步：${issue.action}。`));
    }
    sectionEl.appendChild(list);
    if (view.status !== "locked") {
      const retry = node("button", "studio-primary-button", "预览重新识别");
      retry.type = "button";
      retry.disabled = Boolean(assetCommandPreview);
      retry.addEventListener("click", () => void stageAssetBibleCommand({ type: "regenerate_candidates" }));
      sectionEl.appendChild(retry);
    }
    return sectionEl;
  }

  function assetBibleArtDirection(view) {
    const sectionEl = node(
      "section",
      `asset-bible-art-direction ${view.art_direction.status === "confirmed" ? "confirmed" : "pending"}`,
    );
    sectionEl.setAttribute("aria-live", "polite");
    sectionEl.append(
      node("strong", "", view.art_direction.status === "confirmed" ? "统一美术方向已确认" : "统一美术方向待确认"),
      node("p", "", "该版本会冻结到图片准入清单，并用于界面预览与实际请求的同一提示合同。"),
    );
    if (view.status === "locked") {
      const summary = node("dl", "asset-bible-art-direction-summary");
      for (const [label, key] of [
        ["视觉风格", "visual_style"],
        ["媒介与质感", "medium"],
        ["色彩方案", "palette"],
        ["光线规则", "lighting"],
      ]) summary.append(node("dt", "", label), node("dd", "", view.art_direction[key] || "未确认"));
      sectionEl.appendChild(summary);
      return sectionEl;
    }
    if (!artDirectionDraft) artDirectionDraft = { ...view.art_direction };
    const form = node("form", "asset-bible-art-direction-form");
    for (const [label, key, placeholder] of [
      ["视觉风格", "visual_style", "例如：写实古装动作片"],
      ["媒介与质感", "medium", "例如：电影摄影，真实皮肤与织物"],
      ["色彩方案", "palette", "例如：低饱和青绿与暖金点缀"],
      ["光线规则", "lighting", "例如：黄昏侧逆光，人物面部可辨"],
    ]) {
      const wrap = node("label", "");
      wrap.appendChild(node("span", "", label));
      const input = document.createElement("input");
      input.value = artDirectionDraft[key] || "";
      input.placeholder = placeholder;
      input.required = true;
      input.addEventListener("input", () => { artDirectionDraft[key] = input.value; });
      wrap.appendChild(input);
      form.appendChild(wrap);
    }
    const submit = node("button", "studio-secondary-button", "预览美术方向");
    submit.type = "submit";
    submit.disabled = Boolean(assetCommandPreview);
    form.appendChild(submit);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void stageAssetBibleCommand({
        type: "set_art_direction",
        art_direction: {
          visual_style: artDirectionDraft.visual_style,
          medium: artDirectionDraft.medium,
          palette: artDirectionDraft.palette,
          lighting: artDirectionDraft.lighting,
        },
      });
    });
    sectionEl.appendChild(form);
    return sectionEl;
  }

  function assetBibleEmpty(source) {
    const wrap = node("section", "asset-bible-empty");
    wrap.appendChild(node("strong", "", source ? "可以建立资产候选" : "等待已应用分镜"));
    wrap.appendChild(node(
      "p",
      "",
      source
        ? `将读取当前剧本版本和 ${source.scene_count} 场 / ${source.shot_count} 镜头，仅识别角色、场景、道具及连续性待确认项。`
        : "先在 Canvas 完成剧本并应用拆镜；预览、失败或已取消的分镜不会进入 Asset Bible。",
    ));
    const facts = node("ul", "");
    for (const text of ["不会调用外部文本、图片或视频能力", "候选不是最终审美结论", "确认前不会写入项目事实"]) {
      facts.appendChild(node("li", "", text));
    }
    wrap.appendChild(facts);
    return wrap;
  }

  function assetBibleList(view) {
    const list = node("section", "asset-bible-list");
    list.setAttribute("aria-label", "资产候选列表");
    const summary = node("div", "asset-bible-list-summary");
    summary.append(
      node("strong", "", `${view.counts.total} 个当前资产`),
      node("span", "", `${view.counts.character} 角色 · ${view.counts.scene} 场景 · ${view.counts.prop} 道具`),
    );
    list.appendChild(summary);
    for (const asset of view.active_assets) {
      list.appendChild(assetBibleListRow(asset, view, false));
    }
    if (view.history_assets.length) {
      const history = node("details", "asset-bible-history");
      history.appendChild(node(
        "summary",
        "",
        `审核与版本历史 · ${view.counts.rejected} 已拒绝 · ${view.counts.superseded} 已取代`,
      ));
      for (const asset of view.history_assets) history.appendChild(assetBibleListRow(asset, view, true));
      list.appendChild(history);
    }
    return list;
  }

  function assetBibleListRow(asset, view, historical) {
      const row = node("article", `asset-bible-row ${asset.stable_id === selectedAsset()?.stable_id ? "selected" : ""}`);
      const select = node("button", "asset-bible-row-main");
      select.type = "button";
      select.setAttribute("aria-pressed", String(asset.stable_id === selectedAsset()?.stable_id));
      select.addEventListener("click", () => {
        selectedAssetId = asset.stable_id;
        assetDraft = null;
        render();
      });
      const labels = node("div", "");
      labels.append(
        node("span", "eyebrow", assetTypeLabel(asset.asset_type)),
        node("strong", "", asset.display_name),
        node("small", "", `${asset.occurrences.scene_ids.length} 场 · ${asset.occurrences.shot_ids.length} 镜头`),
      );
      select.append(labels, node("span", `asset-review-state ${asset.review_state}`, assetReviewLabel(asset.review_state)));
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = mergeAssetIds.has(asset.stable_id);
      checkbox.disabled = view.status === "locked" || historical;
      checkbox.setAttribute("aria-label", `选择 ${asset.display_name} 用于合并`);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked) mergeAssetIds.add(asset.stable_id);
        else mergeAssetIds.delete(asset.stable_id);
        render();
      });
      row.append(select, checkbox);
      return row;
  }

  function assetBibleDetail(view) {
    const asset = selectedAsset();
    const detail = node("section", "asset-bible-detail");
    detail.setAttribute("aria-label", "资产详情与审核");
    if (!asset) {
      detail.appendChild(node("p", "", "选择一个资产查看来源、出现范围和连续性约束。"));
      return detail;
    }
    const head = node("header", "");
    const title = node("div", "");
    title.append(
      node("span", "eyebrow", `${assetTypeLabel(asset.asset_type)} · ${assetReviewLabel(asset.review_state)}`),
      node("h2", "", asset.display_name),
    );
    const actions = node("div", "asset-bible-detail-actions");
    if (view.status !== "locked" && asset.review_state !== "superseded") {
      for (const [type, label, className] of [
        ["approve", "批准", "studio-primary-button"],
        ["reject", "拒绝", "studio-secondary-button"],
      ]) {
        const button = node("button", className, label);
        button.type = "button";
        const visualBlockers = type === "approve" ? assetVisualBlockers(asset) : [];
        button.disabled = Boolean(assetCommandPreview) || visualBlockers.length > 0;
        button.title = visualBlockers.length
          ? `请先补全${visualBlockers.join("、")}；不能把缺字段候选标为已批准`
          : `${label}当前资产`;
        button.addEventListener("click", () => void stageAssetBibleCommand({ type, target_id: asset.stable_id }));
        actions.appendChild(button);
      }
    }
    head.appendChild(title);
    if (actions.childElementCount) head.appendChild(actions);
    detail.appendChild(head);
    const metrics = node("dl", "asset-bible-metrics");
    const confidenceReview = asset.review_state === "approved" ? "已人工确认" : "仍需人工确认";
    for (const [label, value] of [
      ["可信度", `${Math.round(Number(asset.confidence || 0) * 100)}% · ${confidenceReview}`],
      ["出现", `${asset.occurrences.scene_ids.length} 场 · ${asset.occurrences.shot_ids.length} 镜头`],
      ["别名", asset.aliases.join("、") || "无"],
      ["待确认", asset.pending_fields.map(pendingFieldLabel).join("、") || "无"],
    ]) metrics.append(node("dt", "", label), node("dd", "", value));
    detail.appendChild(metrics);
    detail.appendChild(assetTagSection("视觉身份", asset.visual_identity ? [asset.visual_identity] : [], "尚未确认视觉身份"));
    detail.appendChild(assetTagSection("正向特征", asset.positive_traits, "尚未确认正向视觉特征"));
    detail.appendChild(assetTagSection(
      "连续性状态",
      asset.continuity_states.filter((item) => item?.status === "confirmed").map((item) => item.label),
      "尚未确认连续性状态",
    ));
    detail.appendChild(assetTagSection("禁改项", asset.negative_locks.map(localizedNegativeLock), "尚未设置禁改项"));
    detail.appendChild(assetOccurrenceSection(asset, view));
    if (view.status !== "locked") detail.appendChild(assetResolutionSection(asset, view));
    detail.appendChild(assetEvidenceSection(asset));
    if (view.status !== "locked" && asset.review_state !== "superseded") detail.appendChild(assetEditForm(asset));
    return detail;
  }

  function assetTagSection(title, values, emptyText) {
    const sectionEl = node("section", "asset-bible-tag-section");
    sectionEl.appendChild(node("strong", "", title));
    const tags = node("div", "");
    if (values.length) {
      for (const value of values) tags.appendChild(node("span", "", value));
    } else {
      tags.appendChild(node("small", "", emptyText));
    }
    sectionEl.appendChild(tags);
    return sectionEl;
  }

  function assetOccurrenceSection(asset, view) {
    const sectionEl = node("section", "asset-bible-occurrences");
    sectionEl.appendChild(node("strong", "", "双向出现范围"));
    const scenes = node(
      "p",
      "",
      `场景：${asset.occurrences.scene_ids.map((id) => assetOccurrenceLabel(view.candidate_set, "scene", id)).join("、") || "未绑定"}`,
    );
    const shots = node(
      "p",
      "",
      `镜头：${asset.occurrences.shot_ids.map((id) => assetOccurrenceLabel(view.candidate_set, "shot", id)).join("、") || "未绑定"}`,
    );
    sectionEl.append(scenes, shots);
    return sectionEl;
  }

  function assetEvidenceSection(asset) {
    const details = node("details", "asset-bible-evidence");
    details.appendChild(node("summary", "", "来源与追溯"));
    details.appendChild(node("p", "", `追溯标识：${asset.stable_id}`));
    if (!asset.source_evidence.length) {
      details.appendChild(node("p", "", "无可验证文本证据，保持待确认。"));
    } else {
      for (const evidence of asset.source_evidence) {
        details.appendChild(node("p", "", evidence.excerpt || "结构引用"));
      }
    }
    return details;
  }

  function assetResolutionSection(asset, view) {
    const sectionEl = node("section", "asset-bible-resolution");
    sectionEl.appendChild(node("strong", "", "必要出现范围"));
    const requirements = view.resolution_ledger.filter(
      (item) => item.source_asset_id === asset.stable_id || item.assigned_asset_id === asset.stable_id,
    );
    if (!requirements.length) {
      sectionEl.appendChild(node("p", "", "当前资产没有必须解决的场景或镜头引用。"));
      return sectionEl;
    }
    const unresolved = requirements.filter((item) => !item.resolved);
    sectionEl.appendChild(node(
      "p",
      "",
      unresolved.length
        ? `${requirements.length - unresolved.length}/${requirements.length} 已解决；${unresolved.length} 项仍会阻止锁定。`
        : `${requirements.length}/${requirements.length} 已解决。`,
    ));
    const list = node("ul", "asset-resolution-list");
    for (const item of requirements.slice(0, 24)) {
      list.appendChild(node(
        "li",
        item.resolved ? "resolved" : "blocked",
        `${assetOccurrenceLabel(view.candidate_set, item.occurrence_kind, item.occurrence_id)} · ${resolutionStatusLabel(item.status)}`,
      ));
    }
    sectionEl.appendChild(list);
    if (!unresolved.length || asset.review_state === "superseded") return sectionEl;
    const form = node("form", "asset-resolution-form");
    const destinationLabel = node("label", "");
    destinationLabel.appendChild(node("span", "", "重分配到已批准资产"));
    const destination = document.createElement("select");
    for (const candidate of view.active_assets.filter(
      (item) => item.review_state === "approved"
        && item.asset_type === asset.asset_type
        && item.stable_id !== asset.stable_id,
    )) {
      const option = document.createElement("option");
      option.value = candidate.stable_id;
      option.textContent = `${assetTypeLabel(candidate.asset_type)} · ${candidate.display_name}`;
      destination.appendChild(option);
    }
    destinationLabel.appendChild(destination);
    const reassign = node("button", "studio-secondary-button", "预览重分配影响");
    reassign.type = "button";
    reassign.disabled = !destination.options.length;
    reassign.addEventListener("click", () => void stageAssetBibleCommand({
      type: "reassign_occurrences",
      target_id: destination.value,
      requirement_ids: unresolved.map((item) => item.requirement_id),
      reason: `人工审核将 ${asset.display_name} 的必要出现范围重分配`,
    }));
    const reasonLabel = node("label", "");
    reasonLabel.appendChild(node("span", "", "明确无需的审核理由"));
    const reason = document.createElement("input");
    reason.value = resolutionReason;
    reason.placeholder = "说明为何这些场景/镜头不需要该资产";
    reason.addEventListener("input", () => { resolutionReason = reason.value; });
    reasonLabel.appendChild(reason);
    const notNeeded = node("button", "studio-text-button", "预览标记为无需");
    notNeeded.type = "button";
    notNeeded.addEventListener("click", () => void stageAssetBibleCommand({
      type: "mark_not_needed",
      requirement_ids: unresolved.map((item) => item.requirement_id),
      reason: resolutionReason,
    }));
    form.append(destinationLabel, reassign, reasonLabel, notNeeded);
    sectionEl.appendChild(form);
    return sectionEl;
  }

  function assetBibleCreateForm(view) {
    const form = node("form", "asset-bible-create-form");
    form.setAttribute("aria-label", "人工补充资产候选");
    form.append(node("strong", "", "补充遗漏资产"), node("p", "", "仅添加有剧本或分镜依据的资产；出现范围将进入同一覆盖账本。"));
    const typeLabel = node("label", "");
    typeLabel.appendChild(node("span", "", "类型"));
    const type = document.createElement("select");
    for (const [value, label] of [["character", "角色"], ["scene", "场景"], ["prop", "道具"]]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      option.selected = assetCreateDraft.asset_type === value;
      type.appendChild(option);
    }
    type.addEventListener("change", () => { assetCreateDraft.asset_type = type.value; });
    typeLabel.appendChild(type);
    const nameLabel = createAssetTextField("名称", "display_name", "例如：九齿钉耙");
    const aliasesLabel = createAssetTextField("别名", "aliases", "顿号分隔");
    const evidenceLabel = createAssetTextField("审核依据", "evidence", "说明来自哪段剧本或哪些镜头");
    form.append(typeLabel, nameLabel, aliasesLabel, evidenceLabel);
    form.appendChild(assetOccurrencePicker(view, "scene", "出现的场景"));
    form.appendChild(assetOccurrencePicker(view, "shot", "出现的镜头"));
    const actions = node("div", "asset-bible-edit-actions");
    const preview = node("button", "studio-primary-button", "预览补充影响");
    preview.type = "submit";
    const cancel = node("button", "studio-secondary-button", "取消");
    cancel.type = "button";
    cancel.addEventListener("click", () => {
      assetCreateOpen = false;
      render();
    });
    actions.append(preview, cancel);
    form.appendChild(actions);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void stageAssetBibleCommand({
        type: "create_asset",
        asset_type: assetCreateDraft.asset_type,
        display_name: assetCreateDraft.display_name,
        aliases: splitList(assetCreateDraft.aliases),
        scene_ids: assetCreateDraft.scene_ids,
        shot_ids: assetCreateDraft.shot_ids,
        evidence: assetCreateDraft.evidence,
      });
    });
    return form;
  }

  function createAssetTextField(label, key, placeholder) {
    const wrap = node("label", "");
    wrap.appendChild(node("span", "", label));
    const input = document.createElement("input");
    input.value = assetCreateDraft[key] || "";
    input.placeholder = placeholder;
    input.addEventListener("input", () => { assetCreateDraft[key] = input.value; });
    wrap.appendChild(input);
    return wrap;
  }

  function assetOccurrencePicker(view, kind, title) {
    const fieldset = document.createElement("fieldset");
    fieldset.className = "asset-occurrence-picker";
    fieldset.appendChild(node("legend", "", title));
    const source = kind === "scene" ? view.candidate_set.scene_index || [] : view.candidate_set.shot_index || [];
    const key = kind === "scene" ? "scene_ids" : "shot_ids";
    for (const item of source) {
      const id = kind === "scene" ? item.scene_id : item.shot_id;
      const label = node("label", "");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = assetCreateDraft[key].includes(id);
      input.addEventListener("change", () => {
        const values = new Set(assetCreateDraft[key]);
        if (input.checked) values.add(id);
        else values.delete(id);
        assetCreateDraft[key] = [...values];
      });
      label.append(input, node("span", "", assetOccurrenceLabel(view.candidate_set, kind, id)));
      fieldset.appendChild(label);
    }
    return fieldset;
  }

  function assetEditForm(asset) {
    if (!assetDraft || assetDraft.stable_id !== asset.stable_id) {
      assetDraft = {
        stable_id: asset.stable_id,
        display_name: asset.display_name,
        aliases: asset.aliases.join("、"),
        positive_traits: asset.positive_traits.join("、"),
        visual_identity: asset.visual_identity,
        continuity_states: asset.continuity_states.map((item) => item?.label).filter(Boolean).join("、"),
        negative_locks: asset.negative_locks.join("、"),
        split_name_a: `${asset.display_name} A`,
        split_name_b: `${asset.display_name} B`,
      };
    }
    const form = node("form", "asset-bible-edit-form");
    form.appendChild(node("strong", "", "编辑当前候选"));
    const fields = [
      ["display_name", "名称", "text"],
      ["aliases", "别名（顿号分隔）", "text"],
      ["visual_identity", "视觉身份", "text"],
      ["positive_traits", "正向特征（顿号分隔）", "text"],
      ["continuity_states", "连续性状态（顿号分隔）", "text"],
      ["negative_locks", "禁改项（顿号分隔）", "text"],
    ];
    for (const [key, label, type] of fields) {
      const wrap = node("label", "");
      wrap.appendChild(node("span", "", label));
      const input = document.createElement("input");
      input.type = type;
      input.value = assetDraft[key] || "";
      input.addEventListener("input", () => { assetDraft[key] = input.value; });
      wrap.appendChild(input);
      form.appendChild(wrap);
    }
    const actions = node("div", "asset-bible-edit-actions");
    const save = node("button", "studio-secondary-button", "预览编辑影响");
    save.type = "submit";
    const split = node("button", "studio-text-button", "拆分资产");
    split.type = "button";
    split.addEventListener("click", () => {
      const sceneRefs = asset.occurrences.scene_ids;
      const shotRefs = asset.occurrences.shot_ids;
      void stageAssetBibleCommand({
        type: "split",
        target_id: asset.stable_id,
        names: [assetDraft.split_name_a, assetDraft.split_name_b],
        occurrence_assignments: {
          "0": {
            scene_ids: sceneRefs.slice(0, Math.ceil(sceneRefs.length / 2)),
            shot_ids: shotRefs.slice(0, Math.ceil(shotRefs.length / 2)),
          },
          "1": {
            scene_ids: sceneRefs.slice(Math.ceil(sceneRefs.length / 2)),
            shot_ids: shotRefs.slice(Math.ceil(shotRefs.length / 2)),
          },
        },
      });
    });
    actions.append(save, split);
    form.appendChild(actions);
    const splitNames = node("div", "asset-bible-split-fields");
    for (const [key, label] of [["split_name_a", "拆分名称 A"], ["split_name_b", "拆分名称 B"]]) {
      const wrap = node("label", "");
      wrap.appendChild(node("span", "", label));
      const input = document.createElement("input");
      input.value = assetDraft[key];
      input.addEventListener("input", () => { assetDraft[key] = input.value; });
      wrap.appendChild(input);
      splitNames.appendChild(wrap);
    }
    form.appendChild(splitNames);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void stageAssetBibleCommand({
        type: "edit",
        target_id: asset.stable_id,
        patch: {
          display_name: assetDraft.display_name,
          aliases: splitList(assetDraft.aliases),
          visual_identity: assetDraft.visual_identity,
          positive_traits: splitList(assetDraft.positive_traits),
          continuity_states: splitList(assetDraft.continuity_states),
          negative_locks: splitList(assetDraft.negative_locks),
        },
      });
    });
    return form;
  }

  function assetBibleCommandReview() {
    const preview = assetCommandPreview;
    const command = preview.command || {};
    const impact = preview.impact || {};
    const sectionEl = node("section", "asset-bible-command-review");
    sectionEl.setAttribute("role", "status");
    sectionEl.setAttribute("aria-live", "polite");
    sectionEl.append(
      node("span", "eyebrow", "保存前预览"),
      node("strong", "", assetCommandLabel(command.type)),
      node("p", "", `影响 ${impact.asset_ids?.length || preview.result?.asset_bible?.assets?.length || 0} 个资产 · ${impact.scene_count || 0} 场 · ${impact.shot_count || 0} 镜头；取消不会改变事实。`),
    );
    if (assetCommandRecovery) {
      const recovery = node("div", "asset-bible-failure");
      recovery.setAttribute("role", "alert");
      recovery.append(
        node("strong", "", assetCommandRecovery.category),
        node("p", "", assetCommandRecovery.message),
        node("small", "", "当前页面事实保持不变；同一命令号用于恢复，成功结果不会重复应用。"),
      );
      sectionEl.appendChild(recovery);
    }
    if (Number.isFinite(Number(impact.unresolved_required_after))) {
      sectionEl.appendChild(node(
        "p",
        "",
        `必要出现范围：${impact.unresolved_required_before || 0} 未解决 → ${impact.unresolved_required_after || 0} 未解决。`,
      ));
    }
    if (impact.recognition_delta) {
      const delta = impact.recognition_delta;
      sectionEl.appendChild(node(
        "p",
        "",
        `重新识别变化：新增 ${delta.added_asset_ids?.length || 0} · 聚类 ${delta.merged_asset_ids?.length || 0} · 保留已审核 ${delta.retained_asset_ids?.length || 0} · 转入历史 ${delta.history_asset_ids?.length || 0}；质量阻塞 ${impact.quality_issue_count_before || 0} → ${impact.quality_issue_count_after || 0}。`,
      ));
    }
    for (const item of impact.occurrence_resolution_changes || []) {
      const destination = preview.result?.asset_bible?.assets?.find(
        (asset) => asset.stable_id === item.assigned_asset_id,
      );
      sectionEl.appendChild(node(
        "small",
        "",
        `${assetOccurrenceLabel(preview.result?.asset_bible?.candidate_set || {}, item.occurrence_kind, item.occurrence_id)} → ${destination?.display_name || "无需资产"}（${resolutionStatusLabel(item.status)}）`,
      ));
    }
    const actions = node("div", "");
    const confirm = node(
      "button",
      "studio-primary-button",
      assetCommandConfirmPending
        ? "确认中"
        : assetCommandRecovery
          ? "重试同一确认"
          : "确认应用",
    );
    confirm.type = "button";
    confirm.disabled = assetCommandConfirmPending;
    confirm.addEventListener("click", () => void confirmAssetBibleCommand());
    const cancel = node("button", "studio-secondary-button", "取消");
    cancel.type = "button";
    cancel.disabled = assetCommandConfirmPending;
    cancel.addEventListener("click", cancelAssetBibleCommand);
    actions.append(confirm, cancel);
    sectionEl.appendChild(actions);
    return sectionEl;
  }

  function assetBibleFailure() {
    const sectionEl = node("section", "asset-bible-failure");
    sectionEl.setAttribute("role", "alert");
    sectionEl.append(
      node("strong", "", "这一步需要处理"),
      node("p", "", `${assetCommandError} 当前资产内容已保留。`),
    );
    if (lastAssetCommand) {
      const retry = node("button", "studio-primary-button", "重新预览同一命令");
      retry.type = "button";
      retry.addEventListener("click", () => void stageAssetBibleCommand(lastAssetCommand));
      sectionEl.appendChild(retry);
    }
    return sectionEl;
  }

  async function stageAssetBibleCommand(command) {
    if (assetCommandPreview) return;
    const source = assetBibleSourceContext(snapshot.studioState || {});
    if (["generate_candidates", "regenerate_candidates"].includes(command.type) && !source) {
      assetCommandError = "缺少已应用的剧本和分镜上下文。";
      render();
      return;
    }
    lastAssetCommand = JSON.parse(JSON.stringify(command));
    assetCommandError = "";
    assetCommandRecovery = null;
    try {
      section = "asset_bible";
      const view = assetBibleView();
      const context = currentAgentChatContext();
      const request = {
        asset_bible: view.authority_mode === "legacy_studio_adapter" ? snapshot.studioState?.assetBible || {} : view.raw || {},
        authority_mode: view.authority_mode,
        context_fingerprint: agentChatContextFingerprint(context),
        expected_asset_bible_revision_id: view.current_revision_id || "",
        command,
        requested_at: new Date().toISOString(),
        ...(["generate_candidates", "regenerate_candidates"].includes(command.type) ? source : {}),
      };
      const preview = await options.getRuntime?.().previewAssetBibleCommand(request);
      assetCommandPreview = { ...preview, request };
    } catch (error) {
      assetCommandError = options.formatError?.(error) || String(error?.message || error || "资产命令预览失败");
    }
    render();
  }

  function imageAdmissionSource() {
    const view = assetBibleView();
    const source = assetBibleSourceContext(snapshot.studioState || {});
    const scenes = [];
    const shots = [];
    for (const [sceneIndex, scene] of (source?.shot_plan?.scenes || []).entries()) {
      const sceneId = String(scene.scene_id || "");
      scenes.push({
        scene_id: sceneId,
        name: String(scene.name || scene.title || ""),
        number: Number(scene.number || sceneIndex + 1),
        description: String(scene.description || ""),
      });
      for (const [shotIndex, shot] of (scene.shots || []).entries()) {
        shots.push({
          shot_id: String(shot.shot_id || ""),
          scene_id: sceneId,
          number: Number(shot.number || shots.length + 1),
          title: String(shot.title || `镜头 ${shotIndex + 1}`),
          purpose: String(shot.narrative_purpose || shot.purpose || ""),
          shot_size: String(shot.shot_size || ""),
          composition: String(shot.composition || ""),
          camera_angle: String(shot.camera_angle || ""),
          movement: String(shot.movement || shot.camera_motion || ""),
          action: String(shot.action || shot.description || ""),
          dialogue: String(shot.dialogue || ""),
          emotion: String(shot.emotion || ""),
          continuity_cues: Array.isArray(shot.continuity_cues) ? shot.continuity_cues : [],
        });
      }
    }
    return {
      authority_mode: view.authority_mode,
      production_graph_version: Number(snapshot.sequenceWorkspace?.graph_version || 0),
      production_graph_digest: String(snapshot.sequenceWorkspace?.graph_digest || ""),
      studio_state_version: String(snapshot.studioState?.meta?.stateVersion || ""),
      art_direction: view.art_direction,
      shot_grounding: { scenes, shots },
      asset_bible: view.raw || {},
    };
  }

  function buildImageAdmissionPanel() {
    const view = imageAdmissionView();
    const panel = node("section", "image-admission-panel");
    panel.setAttribute("aria-label", "图片准入");
    const head = node("div", "image-admission-head");
    const copy = node("div", "");
    copy.append(
      node("span", "eyebrow", "九项代表集 · 费用硬门"),
      node("h2", "", "图片准入"),
      node("p", "", view.status === "empty"
        ? "先审核资产视觉身份、统一美术方向与镜头依据；确认前不会调用外部能力。"
        : `清单 ${view.manifest?.version || 1} · ${view.items.length} 项 · ${view.budget_contract.disclosure || "公开估算，非最终账单"}`),
    );
    const close = node("button", "studio-icon-button");
    close.type = "button";
    close.title = "收起图片准入";
    close.setAttribute("aria-label", "收起图片准入");
    close.innerHTML = icon("x", 15);
    close.addEventListener("click", () => {
      imageAdmissionOpen = false;
      render();
    });
    head.append(copy, close);
    panel.appendChild(head);
    if (imageAdmissionError) {
      const error = node("div", "image-admission-error");
      error.setAttribute("role", "alert");
      error.append(node("strong", "", "图片准入未改变"), node("p", "", imageAdmissionError));
      panel.appendChild(error);
    }
    if (imageAdmissionPreview) {
      panel.appendChild(buildImageAdmissionReview());
      return panel;
    }
    if (view.status === "empty") {
      const empty = node("div", "image-admission-empty");
      empty.append(
        node("strong", "", "编译不可变九项清单"),
        node("p", "", "3 个角色、1 个主场景、2 个核心道具、3 个镜头关键帧；选择只依据资产类型、出现范围与镜头顺序。"),
      );
      const prepare = node("button", "studio-primary-button", "预览准入清单");
      prepare.type = "button";
      prepare.addEventListener("click", () => void stageImageAdmissionCommand({ type: "compile" }));
      empty.appendChild(prepare);
      panel.appendChild(empty);
      return panel;
    }
    const metrics = node("div", "image-admission-metrics");
    for (const [label, value] of [
      ["公开单价", `$${view.budget_contract.unit_estimate_usd || "0.0377"} / 张`],
      ["硬上限", `$${view.budget_contract.max_estimated_usd || "0.3500"} · ${view.budget_contract.max_dispatches || 9} 次`],
      ["已占用", `${view.budget.dispatches_reserved || 0} 次 · $${view.budget.estimated_reserved_usd || "0.0000"}`],
      ["实际账单", view.actual_usd == null ? "未核验" : `$${view.actual_usd}`],
    ]) {
      const item = node("div", "");
      item.append(node("span", "", label), node("strong", "", value));
      metrics.appendChild(item);
    }
    panel.appendChild(metrics);
    const blocker = node("div", view.capability.keyframe_continuity_ready ? "image-admission-capability ready" : "image-admission-capability");
    blocker.append(
      node("strong", "", view.capability.keyframe_continuity_ready ? "参考图编辑合同已声明" : "关键帧连续性被阻断"),
      node("p", "", view.capability.keyframe_continuity_ready
        ? `最多 ${view.capability.reference_image_slots || 0} 张同项目已批准参考媒体；有引用时只走图片编辑接口。`
        : view.capability.blocker || "当前图片适配器未声明参考图能力。"),
      node("p", "", snapshot.mediaGates?.image ? "图片能力已启用；每次发送前仍需占用预算。" : "图片能力未启用；当前不会发送任何外部请求。"),
    );
    panel.appendChild(blocker);
    const list = node("div", "image-admission-list");
    for (const item of view.items) list.appendChild(buildImageAdmissionItem(item, view));
    panel.appendChild(list);
    const actions = node("div", "image-admission-actions");
    if (view.status === "draft") {
      const lock = node("button", "studio-primary-button", "预览锁定清单");
      lock.type = "button";
      lock.addEventListener("click", () => void stageImageAdmissionCommand({ type: "lock" }));
      actions.appendChild(lock);
    } else if (view.status === "locked") {
      const cancel = node("button", "studio-secondary-button", "停止未发送项目");
      cancel.type = "button";
      cancel.disabled = !view.counts.planned;
      cancel.addEventListener("click", () => void stageImageAdmissionCommand({ type: "cancel_batch" }));
      actions.appendChild(cancel);
    }
    panel.appendChild(actions);
    return panel;
  }

  function buildImageAdmissionItem(item, view) {
    const row = node("article", `image-admission-item state-${String(item.state || "planned")}`);
    const main = node("div", "");
    main.append(
      node("span", "image-admission-item-kind", imageAdmissionItemTypeLabel(item.item_type)),
      node("strong", "", item.label || "待确认图片项目"),
      node("p", "", `${item.aspect_ratio} · ${item.size} · 独立单图`),
    );
    const occurrenceCount = Number(item.occurrence_references?.shot_ids?.length || 0);
    const referenceCount = Number(item.reference_media_ids?.length || 0);
    main.appendChild(node(
      "small",
      "",
      item.item_type === "shot_keyframe"
        ? `镜头已绑定 · ${referenceCount} 张已批准参考图`
        : `${occurrenceCount} 个镜头出现 · 来源已绑定`,
    ));
    main.appendChild(buildImageAdmissionGrounding(item));
    const media = buildImageAdmissionCandidateMedia(item, view);
    if (media.element) main.appendChild(media.element);
    const state = node("span", "image-admission-item-state", imageAdmissionStateLabel(item.state));
    row.append(main, state);
    const actions = node("div", "image-admission-item-actions");
    if (snapshot.mediaGates?.image && view.status === "locked" && item.state === "planned") {
      const generate = node("button", "studio-primary-button", "预览生成");
      generate.type = "button";
      generate.addEventListener("click", () => void stageImageAdmissionCommand({
        type: "reserve_dispatch",
        item_id: item.item_id,
      }));
      actions.appendChild(generate);
    }
    if (snapshot.mediaGates?.image && item.state === "reserved") {
      const resumeSubmit = node("button", "studio-primary-button", "继续发送");
      resumeSubmit.type = "button";
      resumeSubmit.addEventListener("click", () => void dispatchImageAdmissionItem(item));
      actions.appendChild(resumeSubmit);
    }
    if (item.state === "processing" && imageAdmissionItemJobId(item)) {
      const resumePoll = node("button", "studio-secondary-button", "继续检查");
      resumePoll.type = "button";
      resumePoll.addEventListener("click", () => void pollImageAdmissionItem(item));
      actions.appendChild(resumePoll);
    }
    if (view.capability.fixture_mode && item.state === "planned") {
      const fixture = node("button", "studio-secondary-button", "载入零费用测试候选");
      const fixtureFailure = node("button", "studio-secondary-button", "模拟零费用任务失败");
      fixture.type = "button";
      fixtureFailure.type = "button";
      fixture.addEventListener("click", () => void stageImageAdmissionCommand({
        type: "record_candidate",
        item_id: item.item_id,
        fixture: true,
      }));
      fixtureFailure.addEventListener("click", () => void stageImageAdmissionCommand({
        type: "record_failure",
        item_id: item.item_id,
        fixture: true,
        error_category: "deterministic_fixture_failure",
      }));
      actions.append(fixture, fixtureFailure);
    }
    if (item.state === "candidate") {
      const approve = node("button", "studio-primary-button", "批准候选");
      const reject = node("button", "studio-secondary-button", "拒绝候选");
      approve.type = reject.type = "button";
      approve.disabled = !media.canApprove;
      approve.title = media.canApprove ? "批准当前已查看的图片候选" : "候选图片成功加载后才能批准";
      approve.addEventListener("click", () => void stageImageAdmissionCommand({ type: "approve", item_id: item.item_id }));
      reject.addEventListener("click", () => void stageImageAdmissionCommand({ type: "reject", item_id: item.item_id, reason: "人工审核未通过" }));
      actions.append(approve, reject);
    }
    if (["failed", "rejected"].includes(item.state)) {
      const replace = node("button", "studio-secondary-button", "预览替换");
      replace.type = "button";
      replace.addEventListener("click", () => void stageImageAdmissionCommand({ type: "replace", item_id: item.item_id, reason: "创建替换候选" }));
      actions.appendChild(replace);
    }
    if (actions.childElementCount) row.appendChild(actions);
    return row;
  }

  function buildImageAdmissionGrounding(item) {
    const sectionEl = node("section", "image-admission-grounding");
    const prompt = item.prompt_contract || {};
    const sections = Array.isArray(prompt.sections) ? prompt.sections : [];
    for (const title of ["生成目标", "统一美术方向", "资产身份", "保持一致", "镜头依据", "引用资产", "禁止项"]) {
      const entry = sections.find((item) => item?.title === title);
      if (!entry?.content) continue;
      const row = node("div", "");
      row.append(node("span", "", title === "生成目标" ? "生成内容依据" : title), node("p", "", entry.content));
      sectionEl.appendChild(row);
    }
    const evidence = node("details", "");
    evidence.append(
      node("summary", "", "来源与费用"),
      node("p", "", `${item.size} · 单项估算 $${imageAdmissionView().budget_contract.unit_estimate_usd || "0.0377"} · 公开估算，非最终账单`),
    );
    sectionEl.appendChild(evidence);
    return sectionEl;
  }

  function buildImageAdmissionCandidateMedia(item, view) {
    const candidate = item.candidate;
    if (!candidate || !["candidate", "approved", "rejected"].includes(item.state)) {
      return { element: null, canApprove: false };
    }
    const key = imageAdmissionMediaKey(item, view.manifest?.project_id);
    const previewUrl = String(candidate.preview_url || "");
    const state = !previewUrl ? "failed" : imageAdmissionMediaStates.get(key) || "loading";
    const media = node("section", `image-admission-candidate-media state-${state}`);
    media.setAttribute("aria-label", `${item.label || "图片项目"}候选媒体`);
    if (candidate.fixture) {
      media.appendChild(node("small", "image-admission-fixture-note", "测试候选 · 零费用本地证据 · 不代表创作质量"));
    }
    if (state === "failed") {
      const failure = node("div", "image-admission-media-failure");
      failure.setAttribute("role", "alert");
      failure.append(
        node("strong", "", "候选图片加载失败"),
        node("span", "", "批准已禁用；可重新加载，不会发起生成或占用预算。"),
      );
      const retry = node("button", "studio-secondary-button", "重新加载图片");
      retry.type = "button";
      retry.addEventListener("click", () => {
        imageAdmissionMediaStates.delete(key);
        render();
      });
      failure.appendChild(retry);
      media.appendChild(failure);
      return { element: media, canApprove: false };
    }
    const open = node("button", "image-admission-thumbnail-button");
    open.type = "button";
    open.disabled = state !== "loaded";
    open.setAttribute("aria-label", `查看${item.label || "图片项目"}候选大图`);
    open.dataset.admissionMediaKey = key;
    const image = document.createElement("img");
    image.className = "image-admission-candidate-preview";
    image.alt = `${item.label || "图片项目"}候选缩略图`;
    image.src = options.getRuntime?.().toMediaUrl(previewUrl);
    image.addEventListener("load", () => updateImageAdmissionMediaState(key, "loaded"));
    image.addEventListener("error", () => updateImageAdmissionMediaState(key, "failed"));
    open.appendChild(image);
    open.addEventListener("click", () => openImageAdmissionViewer(item, key));
    const meta = node(
      "small",
      "image-admission-media-summary",
      state === "loaded"
        ? `图片已加载 · ${candidate.width}×${candidate.height} · 来源与当前清单绑定`
        : "正在验证本地候选图片…",
    );
    const viewLarge = node("button", "studio-secondary-button image-admission-view-button", "查看大图");
    viewLarge.type = "button";
    viewLarge.disabled = state !== "loaded";
    viewLarge.dataset.admissionMediaKey = key;
    viewLarge.addEventListener("click", () => openImageAdmissionViewer(item, key));
    media.append(open, meta, viewLarge);
    return { element: media, canApprove: state === "loaded" };
  }

  function updateImageAdmissionMediaState(key, state) {
    if (!key || imageAdmissionMediaStates.get(key) === state) return;
    imageAdmissionMediaStates.set(key, state);
    render();
  }

  function openImageAdmissionViewer(item, key) {
    if (imageAdmissionMediaStates.get(key) !== "loaded") return;
    imageAdmissionViewer = {
      key,
      label: item.label || "图片候选",
      previewUrl: item.candidate.preview_url,
      width: item.candidate.width,
      height: item.candidate.height,
      fixture: item.candidate.fixture === true,
    };
    imageAdmissionViewerReturnKey = key;
    render();
    requestAnimationFrame(() => {
      document.querySelector(".image-admission-viewer-close")?.focus();
    });
  }

  function closeImageAdmissionViewer() {
    const returnKey = imageAdmissionViewerReturnKey;
    imageAdmissionViewer = null;
    render();
    requestAnimationFrame(() => {
      const target = [...document.querySelectorAll("[data-admission-media-key]")]
        .find((element) => element.dataset.admissionMediaKey === returnKey);
      target?.focus();
    });
  }

  function buildImageAdmissionViewer() {
    const overlay = node("div", "image-admission-viewer");
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.setAttribute("aria-label", `${imageAdmissionViewer.label}大图查看器`);
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) closeImageAdmissionViewer();
    });
    overlay.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        event.preventDefault();
        closeImageAdmissionViewer();
      }
    });
    const close = node("button", "studio-icon-button image-admission-viewer-close");
    close.type = "button";
    close.setAttribute("aria-label", "关闭大图");
    close.title = "关闭大图";
    close.innerHTML = icon("x", 18);
    close.addEventListener("click", closeImageAdmissionViewer);
    const image = document.createElement("img");
    image.alt = `${imageAdmissionViewer.label}完整候选图片`;
    image.src = options.getRuntime?.().toMediaUrl(imageAdmissionViewer.previewUrl);
    image.addEventListener("error", () => {
      imageAdmissionMediaStates.set(imageAdmissionViewer.key, "failed");
      closeImageAdmissionViewer();
    });
    const caption = node("div", "image-admission-viewer-caption");
    caption.append(
      node("strong", "", imageAdmissionViewer.label),
      node("span", "", `${imageAdmissionViewer.width}×${imageAdmissionViewer.height} · 完整图片`),
    );
    if (imageAdmissionViewer.fixture) {
      caption.appendChild(node("small", "", "零费用本地测试候选 · 不代表创作质量"));
    }
    overlay.append(close, image, caption);
    return overlay;
  }

  function buildImageAdmissionReview() {
    const preview = imageAdmissionPreview;
    const willDispatch = preview.command?.type === "reserve_dispatch";
    const review = node("section", "image-admission-review");
    review.setAttribute("aria-live", "polite");
    review.append(
      node("strong", "", willDispatch ? "确认占用一次额度并生成" : "确认图片准入变更"),
      node("p", "", willDispatch
        ? `确认后将先占用第 ${preview.impact?.dispatches_reserved_after || 0} 次额度，再串行发送这一项；失败也占用次数，不会自动重试。`
        : `将影响 ${preview.impact?.item_count || 0} 项；现在仅供预览，确认后才会保存。`),
    );
    const actions = node("div", "image-admission-actions");
    const cancel = node("button", "studio-secondary-button", "取消");
    const confirm = node("button", "studio-primary-button", "确认");
    cancel.type = confirm.type = "button";
    cancel.addEventListener("click", cancelImageAdmissionCommand);
    confirm.addEventListener("click", () => void confirmImageAdmissionCommand());
    actions.append(cancel, confirm);
    review.appendChild(actions);
    return review;
  }

  async function stageImageAdmissionCommand(command) {
    if (imageAdmissionPreview) return;
    imageAdmissionError = "";
    imageAdmissionOpen = true;
    try {
      const stableCommand = imageAdmissionCommand(command);
      const request = {
        command: stableCommand,
        source: imageAdmissionSource(),
        requested_at: new Date().toISOString(),
      };
      const preview = await options.getRuntime?.().previewImageAdmissionCommand(request);
      imageAdmissionPreview = { ...preview, request };
    } catch (error) {
      imageAdmissionError = options.formatError?.(error) || String(error?.message || error || "图片准入预览失败");
    }
    render();
  }

  async function confirmImageAdmissionCommand() {
    const preview = imageAdmissionPreview;
    if (!preview) return;
    try {
      const response = await options.getRuntime?.().confirmImageAdmissionCommand({
        ...preview.request,
        preview_digest: preview.preview_digest,
      });
      snapshot.imageAdmission = {
        ...(snapshot.imageAdmission || {}),
        status: response?.result?.manifest?.status || "ready",
        manifest: response?.result?.manifest || null,
      };
      const confirmedCommand = preview.request?.command || {};
      imageAdmissionPreview = null;
      imageAdmissionError = "";
      notice = confirmedCommand.type === "reserve_dispatch"
        ? "额度已原子占用，正在发送单项生成请求。"
        : confirmedCommand.type === "approve"
          ? "图片候选已确认并保存到当前项目；可以继续查看已确认图片。"
        : "图片准入清单已更新；未调用外部能力。";
      render();
      if (confirmedCommand.type === "reserve_dispatch") {
        const item = response?.result?.manifest?.items?.find(
          (entry) => entry.item_id === confirmedCommand.item_id,
        );
        if (item) await dispatchImageAdmissionItem(item);
      }
    } catch (error) {
      imageAdmissionError = options.formatError?.(error) || String(error?.message || error || "图片准入确认失败");
      imageAdmissionPreview = null;
    }
    render();
  }

  async function commitImageAdmissionCommand(command) {
    const request = {
      command: imageAdmissionCommand(command),
      source: imageAdmissionSource(),
      requested_at: new Date().toISOString(),
    };
    const preview = await options.getRuntime?.().previewImageAdmissionCommand(request);
    const response = await options.getRuntime?.().confirmImageAdmissionCommand({
      ...request,
      preview_digest: preview.preview_digest,
    });
    snapshot.imageAdmission = {
      ...(snapshot.imageAdmission || {}),
      status: response?.result?.manifest?.status || "ready",
      manifest: response?.result?.manifest || null,
    };
    return response?.result?.manifest || null;
  }

  async function dispatchImageAdmissionItem(item) {
    if (!snapshot.mediaGates?.image) {
      imageAdmissionError = "图片能力未启用；未发送任何外部请求。";
      render();
      return;
    }
    const runtime = options.getRuntime?.();
    const request = imageAdmissionGenerationRequest(
      item,
      imageAdmissionView().manifest?.manifest_id || "",
      new Date().toISOString(),
    );
    imageAdmissionError = "";
    try {
      const preflight = await runtime.preflightKeyframe(request);
      const response = await runtime.generateKeyframe({
        ...request,
        preflight_token: preflight.preflight_token,
      });
      await reconcileImageAdmissionGeneration(item, response);
    } catch (error) {
      try {
        await commitImageAdmissionCommand({
          type: "record_failure",
          item_id: item.item_id,
          error_category: "generation_request_failed",
        });
      } catch {}
      imageAdmissionError = options.formatError?.(error) || String(error?.message || error || "图片生成请求失败");
      notice = "这一项失败且已隔离；Asset Bible 与其他图片项目未改变。";
    }
    render();
  }

  async function pollImageAdmissionItem(item) {
    imageAdmissionError = "";
    try {
      const response = await options.getRuntime?.().pollKeyframe(imageAdmissionItemJobId(item));
      await reconcileImageAdmissionGeneration(item, response);
    } catch (error) {
      imageAdmissionError = options.formatError?.(error) || String(error?.message || error || "图片任务恢复失败");
    }
    render();
  }

  async function reconcileImageAdmissionGeneration(item, response) {
    const result = imageAdmissionGenerationResult(response);
    if (result.candidate) {
      await commitImageAdmissionCommand({
        type: "record_candidate",
        item_id: item.item_id,
        candidate: result.candidate,
      });
      notice = "单项候选已生成，等待你审看；确认后才会保存到项目。";
      return;
    }
    const jobId = result.job_id;
    const status = result.status;
    if (["failed", "blocked", "cancelled"].includes(status)) {
      await commitImageAdmissionCommand({
        type: "record_failure",
        item_id: item.item_id,
        error_category: status || "generation_failed",
      });
      notice = "这一项失败且已隔离；可在预算范围内预览替换。";
      return;
    }
    if (!jobId) throw new Error("图片任务未返回可恢复的任务标识。");
    await commitImageAdmissionCommand(imageAdmissionJobCommand(item.item_id, jobId));
    notice = "图片任务仍在处理中；刷新后可继续检查，不会重复发送。";
  }

  function cancelImageAdmissionCommand() {
    imageAdmissionPreview = null;
    imageAdmissionError = "";
    notice = "图片清单预览已取消；项目与预算没有改变。";
    render();
  }

  async function confirmAssetBibleCommand() {
    const preview = assetCommandPreview;
    if (!preview || assetCommandConfirmPending) return;
    assetCommandConfirmPending = true;
    assetCommandError = "";
    assetCommandRecovery = null;
    render();
    try {
      const currentFingerprint = agentChatContextFingerprint(currentAgentChatContext());
      if (preview.request?.context_fingerprint !== currentFingerprint) {
        throw new Error("当前对象或版本已变化，请重新预览影响范围。");
      }
      const response = await options.getRuntime?.().confirmAssetBibleCommand(
        assetBibleConfirmRequest(preview, snapshot.sequenceWorkspace?.graph_version),
      );
      if (response?.authority_mode === "canonical_production_graph") {
        snapshot.runtimeAssetBible = {
          authority_mode: "canonical_production_graph",
          asset_bible: response.asset_bible,
          graph_version: response.graph_version,
          graph_digest: response.graph_digest,
        };
      } else {
        options.getStore?.().set((state) => {
          state.assetBible = response.asset_bible;
        });
      }
      selectedAssetId = response?.asset_bible?.assets?.find((item) => item.review_state === "candidate")?.stable_id
        || response?.asset_bible?.assets?.find((item) => item.review_state === "approved")?.stable_id
        || "";
      assetCommandPreview = null;
      assetCommandError = "";
      assetCommandRecovery = null;
      mergeAssetIds = new Set();
      assetDraft = null;
      artDirectionDraft = null;
      if (preview.command?.type === "create_asset") {
        assetCreateOpen = false;
        assetCreateDraft = { asset_type: "prop", display_name: "", aliases: "", scene_ids: [], shot_ids: [], evidence: "" };
      }
      resolutionReason = "";
      notice = response?.receipt?.summary || "Asset Bible 已更新。";
    } catch (error) {
      const recovery = assetBibleConfirmRecovery(error);
      assetCommandRecovery = recovery.preserve_preview ? recovery : null;
      assetCommandError = recovery.preserve_preview
        ? recovery.message
        : options.formatError?.(error) || recovery.message;
      if (!recovery.preserve_preview) assetCommandPreview = null;
    }
    assetCommandConfirmPending = false;
    render();
  }

  function cancelAssetBibleCommand() {
    assetCommandPreview = null;
    assetCommandError = "";
    assetCommandRecovery = null;
    assetCommandConfirmPending = false;
    notice = "资产更改预览已取消；项目内容没有改变。";
    render();
  }

  function buildMediaCanvasOverview() {
    const ops = mediaOperationsView();
    const panel = node("section", "media-canvas-overview");
    panel.setAttribute("aria-label", "媒体制作进度");
    const head = node("div", "media-canvas-overview-head");
    head.append(
      node("span", "eyebrow", "制作进度"),
      node("h1", "", ops.script?.title || "制作审片候选"),
      node("p", "", ops.stage?.next_action || "进入故事板，审看当前镜头。"),
    );
    const metrics = buildMetricGrid([
      ["场景", ops.summary?.scene_count],
      ["镜头", ops.summary?.shot_count],
      ["可审看", ops.summary?.ready_shot_count],
      ["时长", `${Number(ops.summary?.duration_sec || 0).toFixed(1)}s`],
    ]);
    const actions = node("div", "media-canvas-overview-actions");
    const review = node("button", "studio-primary-button", "查看故事板");
    review.type = "button";
    review.addEventListener("click", showStoryboard);
    const evidence = node("button", "studio-secondary-button", "查看制作详情");
    evidence.type = "button";
    evidence.addEventListener("click", () => {
      showStoryboard();
      requestAnimationFrame(() => document.querySelector(".media-creator-details summary")?.focus());
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
      progress.innerHTML = '<span>媒体生产</span><strong>已生成媒体 0 / 0</strong><div><i style="width:0%"></i></div>';
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
    progress.innerHTML = `<span>媒体生产</span><strong>已生成媒体 ${generatedMediaCount()} / ${totalShots()}</strong><div><i style="width:${mediaCompletionPercent()}%"></i></div>`;
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
      ? `<span>当前项目</span><strong>${escapeHtml(projectDisplayName())}</strong><span>0 场景 · 0 镜头 · 尚未创建故事事实</span>`
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
    const totals = storyboardTotalSummary();
    heading.append(
      node("div", "", `<span class="eyebrow">场景 ${String(selection.sceneIndex + 1).padStart(2, "0")}</span><h1>${escapeHtml(scene.name)}</h1><p class="storyboard-total-summary">${totals.scene_count} 场景 · ${totals.shot_count} 镜头 · 总时长约 ${Math.round(totals.duration_sec)} 秒</p>`),
      node("span", "storyboard-duration", `${scene.shots.length} 镜头 · ${scene.duration}`),
    );
    heading.firstElementChild.innerHTML = `<span class="eyebrow">场景 ${String(selection.sceneIndex + 1).padStart(2, "0")}</span><h1>${escapeHtml(scene.name)}</h1><p class="storyboard-total-summary">${totals.scene_count} 场景 · ${totals.shot_count} 镜头 · 总时长约 ${Math.round(totals.duration_sec)} 秒</p>`;
    sectionEl.appendChild(heading);
    const grid = node("div", "storyboard-shot-grid");
    grid.classList.toggle("is-sparse", sparse);
    scene.shots.forEach((shot, index) => grid.appendChild(buildShotCard(shot, index)));
    sectionEl.appendChild(grid);
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
    copy.innerHTML = `<span class="eyebrow">镜头审看</span><h1>${escapeHtml(ops.script?.title || snapshot.project?.name || "制作审片")}</h1><p>${escapeHtml(ops.script?.logline || ops.stage?.next_action || "审看当前镜头和画面连续性。")}</p>`;
    const next = node("div", "media-next-action");
    next.append(node("span", "", "下一步"), node("strong", "", ops.stage?.next_action || "选择镜头继续审片"));
    heading.append(copy, next);
    sectionEl.append(heading, buildMediaShotSelector());

    const layout = node("div", "media-ops-layout");
    layout.append(buildMediaPreviewPanel(scene, shot, media), buildMediaSidePanel(ops, media));
    sectionEl.appendChild(layout);

    const creatorDetails = node("details", "media-creator-details");
    creatorDetails.appendChild(node("summary", "", "制作详情"));
    const creatorDetailsBody = node("div", "media-creator-details-body");
    const lower = node("div", "media-ops-lower creator-detail-grid");
    lower.append(buildAssetContinuityPanel(ops, media), buildFinalReviewPanel(ops));
    creatorDetailsBody.append(buildMediaJourney(ops), lower);
    creatorDetails.appendChild(creatorDetailsBody);
    sectionEl.appendChild(creatorDetails);

    const diagnostics = node("details", "media-diagnostics-details");
    diagnostics.appendChild(node("summary", "", "诊断信息"));
    const diagnosticsBody = node("div", "media-diagnostics-details-body");
    diagnosticsBody.append(buildCostAndRecoveryPanel(ops, media), buildMediaEvidenceDrawer(ops));
    diagnostics.appendChild(diagnosticsBody);
    sectionEl.appendChild(diagnostics);
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
    panel.append(node("span", "eyebrow", "连续性"), node("h2", "", "角色、场景与道具"));
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
    panel.append(node("span", "eyebrow", "整段预览"), node("h2", "", "交付检查"));
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
    panel.appendChild(node("p", "media-boundary-copy", "这一版可供审看；最终采用前仍需要人工确认画面质量。"));
    return panel;
  }

  function buildMediaEvidenceDrawer(ops) {
    const details = node("details", "media-evidence-drawer");
    const summary = node("summary", "", "技术证据");
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
    const copilot = currentCopilotState();
    const session = agentChatContexts.get(agentChatContextKey(context));
    if (section === "asset_bible") {
      syncAssetBibleCommandAssistantReceipt(session, assetBibleView());
    }
    const collapsed = isAgentChatCollapsed();
    return buildAgentChatPanel({
      session,
      context: { ...context, context_key: agentChatContextKey(context) },
      store: options.getStore?.(),
      runtime: options.getRuntime?.(),
      collapsed,
      mobileOpen: mobileAgentOpen,
      copilot,
      onNextAction: handleCopilotAction,
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
    for (const [key, label] of [["canvas", "画布"], ["storyboard", "故事板"], ["asset_bible", "资产"], ["context", "项目"], ["agent", "搭档"]]) {
      const active = key === "agent" ? mobileAgentOpen : key === "help" ? helpOpen : section === key;
      const button = node("button", active ? "active" : "", label);
      button.type = "button";
      button.setAttribute("aria-current", active ? "page" : "false");
      button.addEventListener("click", () => {
        if (key === "canvas") {
          openCanvas();
        } else if (key === "storyboard") {
          showStoryboard();
        } else if (key === "asset_bible") {
          showAssetBible();
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

  function handleCopilotAction(action) {
    if (!action?.action) return;
    if (action.action === "start_idea") {
      showCanvas();
      requestAnimationFrame(() => {
        const input = document.querySelector(".canvas-empty-onboarding textarea");
        if (input) input.focus();
        else document.querySelector(".agent-chat-composer textarea")?.focus();
      });
      return;
    }
    if (action.action === "review_current_shot") {
      showStoryboard();
      requestAnimationFrame(() => {
        const video = document.querySelector(".media-viewer video");
        video?.focus();
        void video?.play?.().catch(() => {});
      });
      return;
    }
    if (action.action === "generate_asset_candidates") {
      void stageAssetBibleCommand({ type: "generate_candidates" });
      return;
    }
    if (action.action === "regenerate_asset_candidates") {
      void stageAssetBibleCommand({ type: "regenerate_candidates" });
      return;
    }
    if (action.action === "approve_selected_asset" && selectedAsset()) {
      void stageAssetBibleCommand({ type: "approve", target_id: selectedAsset().stable_id });
      return;
    }
    if (action.action === "lock_asset_bible") {
      void stageAssetBibleCommand({ type: "lock" });
      return;
    }
    if ([
      "image_admission_ready",
      "media_gate_closed",
      "reload_image_candidate",
      "recover_image_admission",
      "review_image_candidates",
      "resume_image_admission",
      "review_image_admission",
    ].includes(action.action)) {
      imageAdmissionOpen = true;
      showAssetBible();
      return;
    }
    if ([
      "review_asset_candidates",
      "resolve_required_occurrences",
      "review_asset_coverage",
      "complete_asset_visual_identity",
      "set_art_direction",
    ].includes(action.action)) {
      showAssetBible();
      return;
    }
    if (action.action === "open_storyboard") {
      showStoryboard();
      return;
    }
    if (action.action === "open_script") {
      showCanvas();
    }
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
    button.disabled = projectIdentityStatus() === "blocked";
    button.addEventListener("click", () => {
      if (key === "canvas") openCanvas();
      else if (key === "asset_bible") showAssetBible();
      else showStoryboard();
    });
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
    window.addEventListener("afs:agent-chat-open-task", () => {
      setAgentChatExpanded(true);
      render();
      requestCanvasSafeAreaUpdate();
    });
    window.addEventListener("afs:embedded-creative-task-finished", () => {
      if (isNarrowAgentLayout()) closeResponsiveAgentOverlay();
      render();
      requestCanvasSafeAreaUpdate();
    });
    window.addEventListener("afs:m6-preview-run-updated", (event) => {
      const run = event.detail?.run;
      if (!isM6RunCurrent(run) || (m6PreviewRun?.run_id && run.run_id !== m6PreviewRun.run_id)) return;
      m6PreviewRun = { ...(m6PreviewRun || {}), ...run };
      syncM6RunToAgent(m6PreviewRun);
      if (run.phase === "cancelled") setPlanningPanelOpen(true);
      render();
    });
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
      if (projectDrawerOpen || contextOpen || mobileAgentOpen || helpOpen || accountMenuOpen) {
        const focusTarget = contextOpen
          ? ".studio-project-button"
          : accountMenuOpen
          ? ".studio-account-button"
          : helpOpen
          ? ".studio-help-context .studio-icon-button"
          : "#product-main";
        projectDrawerOpen = false;
        contextOpen = false;
        helpOpen = false;
        accountMenuOpen = false;
        if (mobileAgentOpen) closeResponsiveAgentOverlay();
        render();
        requestCanvasSafeAreaUpdate();
        requestAnimationFrame(() => document.querySelector(focusTarget)?.focus());
      }
    });
    window.addEventListener("pointerdown", (event) => {
      const target = event.target instanceof Element ? event.target : null;
      if (!target) return;
      let changed = false;
      if (contextOpen && !target.closest(".studio-project-context")) {
        contextOpen = false;
        changed = true;
      }
      if (accountMenuOpen && !target.closest(".studio-account-context")) {
        accountMenuOpen = false;
        changed = true;
      }
      if (helpOpen && !target.closest(".studio-help-context") && !target.closest(".studio-mobile-help-sheet")) {
        helpOpen = false;
        changed = true;
      }
      if (changed) render();
    }, true);
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
      agentCollapsed = isNarrowAgentLayout();
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
    return Boolean(planningPanelOpen);
  }

  function setPlanningPanelOpen(open) {
    planningPanelOpen = Boolean(open);
    writePlanningPanelPreference(currentPlanningPanelPreferenceKey(), planningPanelOpen);
  }

  function syncPlanningPanelPreference({ force = false } = {}) {
    const nextKey = currentPlanningPanelPreferenceKey();
    if (!force && planningPanelPreferenceKey === nextKey) return;
    if (planningPanelPreferenceKey && planningPanelPreferenceKey !== nextKey) {
      m6PreviewPollGeneration += 1;
      m6PreviewRun = null;
      m6PreviewRecovering = false;
    }
    planningPanelPreferenceKey = nextKey;
    planningPanelOpen = readPlanningPanelPreference(nextKey);
  }

  function currentM6ProjectId() {
    return String(snapshot.project?.project_id || "");
  }

  function isM6RuntimeCurrent(runtime, expectedProjectId = currentM6ProjectId()) {
    if (!runtime || !expectedProjectId) return false;
    if (options.isRuntimeCurrent && !options.isRuntimeCurrent(runtime)) return false;
    return String(runtime.projectId || expectedProjectId) === expectedProjectId
      && currentM6ProjectId() === expectedProjectId;
  }

  function isM6RunCurrent(run, runtime = options.getRuntime?.(), expectedProjectId = currentM6ProjectId()) {
    return Boolean(run?.run_id)
      && String(run.project_id || "") === expectedProjectId
      && isM6RuntimeCurrent(runtime, expectedProjectId);
  }

  async function restoreLatestM6PreviewRun(runtime, expectedProjectId = currentM6ProjectId()) {
    if (!isM6RuntimeCurrent(runtime, expectedProjectId)) return;
    try {
      const run = await runtime?.loadLatestM6ScriptPlanPreviewRun?.();
      if (!isM6RunCurrent(run, runtime, expectedProjectId)) return;
      m6PreviewRun = run;
      syncM6RunToAgent(run);
      if (run.phase === "succeeded") {
        stageRecoveredM6Candidate(run);
      } else if (["queued", "running", "running_cancel_requested"].includes(String(run.phase || ""))) {
        Promise.resolve().then(() => observeM6PreviewRun(run, runtime, expectedProjectId));
      }
    } catch {
      // No recoverable M6 preview is a normal project state.
    }
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
    const bible = assetBibleView();
    const asset = section === "asset_bible" ? selectedAsset() : null;
    const copilot = currentCopilotState();
    const context = agentChatContextSnapshot({
      project: snapshot.project,
      studioState,
      section,
      selectedNode: selectedCanvasNode(),
      currentShot: currentShot(),
      selectedAsset: asset,
      assetBible: bible,
      copilot,
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
    const selectedId = section === "storyboard"
      ? currentShot().nodeId || state.selection?.nodeIds?.[0] || ""
      : state.selection?.nodeIds?.[0] || currentShot().nodeId || "";
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
    wrap.setAttribute("role", ["error", "identity"].includes(kind) ? "alert" : "status");
    if (kind === "loading") {
      wrap.append(node("div", "state-spinner"), node("h1", "", message("loading", locale)), node("p", "", "正在恢复项目、场景与镜头上下文。"));
    } else if (kind === "identity") {
      const identity = snapshot.studioState?.ui?.projectIdentity || {};
      const reason = String(identity.reason || "");
      const title = reason === "project_access_denied"
        ? "无权访问此项目"
        : reason === "project_not_found"
          ? "项目不存在"
          : reason === "network_unavailable"
            ? "暂时无法验证项目"
            : "项目身份校验未通过";
      const lockMark = node("span", "product-state-lock");
      lockMark.innerHTML = icon("lock", 20);
      wrap.append(
        lockMark,
        node("h1", "", title),
        node("p", "", identity.message || "为保护项目数据，当前视图没有加载任何项目内容。"),
        node("p", "product-state-preserved", "没有自动切换到其他项目，也未发送修改、生成或 AI 请求。"),
      );
      const actions = node("div", "product-state-actions");
      const retry = node("button", "studio-primary-button", "重试加载");
      retry.type = "button";
      retry.addEventListener("click", () => options.onRetry?.());
      const choose = node("button", "studio-secondary-button", "选择其他项目");
      choose.type = "button";
      choose.addEventListener("click", () => {
        contextOpen = true;
        render();
        requestAnimationFrame(() => document.querySelector(".studio-project-menu button")?.focus());
      });
      actions.append(retry, choose);
      wrap.appendChild(actions);
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
    if (projectIdentityStatus() === "blocked") {
      let workspace = snapshot.workspace;
      try {
        workspace = await runtime.workspaceOverview();
      } catch {
        workspace = null;
      }
      snapshot = clearedProjectSnapshot({ ...snapshot, loading: false, authUser, workspace });
      render();
      return;
    }
    if (projectIdentityStatus() === "cache_read_only") {
      snapshot = {
        ...clearedProjectSnapshot(snapshot),
        loading: false,
        authUser,
        project: cachedProjectSummary(snapshot.studioState),
      };
      render();
      return;
    }
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
        if (project && String(project.project_id || "") !== activeProjectId) {
          const mismatch = new Error("Runtime returned a different project identity");
          mismatch.status = 409;
          mismatch.errorCode = "project_identity_mismatch";
          options.onProjectIdentityInvalid?.(mismatch);
          throw mismatch;
        }
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
      let runtimeAssetBible = null;
      let imageAdmission = null;
      let mediaGates = {};
      if (activeProjectId) {
        const projectRuntime = activeProjectId === requestRuntime.projectId ? requestRuntime : options.createRuntime?.(activeProjectId);
        try { runtimeAssetBible = await projectRuntime?.loadAssetBible?.(); } catch { runtimeAssetBible = null; }
        try { imageAdmission = await projectRuntime?.loadImageAdmission?.(); } catch { imageAdmission = null; }
        try { mediaGates = (await projectRuntime?.health?.())?.["pro" + "vider_gates"] || {}; } catch { mediaGates = {}; }
      }
      snapshot = {
        loading: false,
        workspace,
        project,
        sequenceWorkspace,
        mediaOperations,
        runtimeAssetBible,
        imageAdmission,
        mediaGates,
        mediaCommandPreview: null,
        error: "",
        authUser,
        studioState: options.getStudioState?.() || snapshot.studioState,
      };
      if (activeProjectId) {
        const projectRuntime = activeProjectId === requestRuntime.projectId ? requestRuntime : options.createRuntime?.(activeProjectId);
        await restoreLatestM6PreviewRun(projectRuntime, activeProjectId);
        if (options.isRuntimeCurrent && !options.isRuntimeCurrent(requestRuntime)) return;
      }
    } catch (error) {
      if (options.isRuntimeCurrent && !options.isRuntimeCurrent(requestRuntime)) return;
      snapshot = { ...snapshot, loading: false, project: null, error: options.formatError?.(error) || message("error", locale), authUser };
    }
    render();
  }

  function updateStudioState(studioState, options = {}) {
    const previousIdentity = projectIdentityStatus();
    snapshot = { ...snapshot, studioState };
    const nextIdentity = projectIdentityStatus();
    if (["blocked", "loading"].includes(nextIdentity)) {
      snapshot = clearedProjectSnapshot(snapshot);
      if (previousIdentity !== nextIdentity) agentChatContexts.clear();
      section = "canvas";
      mobileAgentOpen = false;
      agentCollapsed = isNarrowAgentLayout();
    }
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

  function showAssetBible() {
    section = "asset_bible";
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
    if (graphWorkspaceReady()) return graphSceneModel();
    if (mediaOperationsReady()) return mediaSceneModel();
    const legacyApplied = legacyAppliedStoryboardProjection(snapshot.studioState || {});
    if (legacyApplied.status === "ready") {
      const sceneIndex = Math.min(selection.sceneIndex, legacyApplied.scenes.length - 1);
      selection = {
        sceneIndex,
        shotIndex: Math.min(selection.shotIndex, legacyApplied.scenes[sceneIndex].shots.length - 1),
      };
      return legacyApplied.scenes;
    }
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
    if (graphWorkspaceReady()) return graphShotModel();
    if (mediaOperationsReady()) return mediaShotModel();
    const state = snapshot.studioState || {};
    const legacyApplied = legacyAppliedStoryboardProjection(state);
    if (legacyApplied.status === "ready") return legacyApplied.shots;
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

  function hasCanvasContent() {
    if (hasStoryFacts() || graphWorkspaceReady() || mediaOperationsReady()) return true;
    const state = snapshot.studioState || {};
    return Object.keys(state.nodes || {}).length > 0 || Object.keys(state.edges || {}).length > 0;
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
  function assetBibleView() {
    return assetBibleProjection(snapshot.studioState || {}, snapshot.runtimeAssetBible);
  }
  function imageAdmissionView() {
    return imageAdmissionProjection(
      snapshot.imageAdmission,
      Object.fromEntries(imageAdmissionMediaStates),
    );
  }
  function selectedAsset() {
    const view = assetBibleView();
    const selected = view.assets.find((item) => item.stable_id === selectedAssetId);
    if (selected) return selected;
    const fallback = view.active_assets.find((item) => item.review_state === "candidate") || view.active_assets[0] || null;
    if (fallback) selectedAssetId = fallback.stable_id;
    return fallback;
  }
  function currentCopilotState() {
    return deriveProductionCopilotState({
      studioState: snapshot.studioState || {},
      runtimeAssetBible: snapshot.runtimeAssetBible,
      capabilityGates: snapshot.mediaGates || {},
      section,
      selectedAsset: section === "asset_bible" ? selectedAsset() : null,
      imageAdmission: imageAdmissionView(),
      mediaOperations: mediaOperationsReady() ? mediaOperationsView() : null,
      productionGraph: productionGraphWorkspaceProjection(snapshot.sequenceWorkspace),
    });
  }
  function hasStoryFacts() { return shotModel().length > 0; }
  function projectDisplayName() {
    if (projectIdentityStatus() === "blocked") return "项目未载入";
    if (projectIdentityStatus() === "loading") return "正在验证项目";
    const names = [snapshot.project?.name, snapshot.project?.goal, snapshot.studioState?.meta?.projectName]
      .map((value) => String(value || "").trim());
    return names.find(Boolean) || "未命名项目";
  }
  function projectIdentityStatus() {
    return String(snapshot.studioState?.ui?.projectIdentity?.status || "ready");
  }
  function totalShots() { return sceneModel().reduce((sum, scene) => sum + scene.shots.length, 0); }
  function storyboardTotalSummary() {
    const scenes = sceneModel();
    const shotCount = scenes.reduce((sum, scene) => sum + scene.shots.length, 0);
    const durationSec = scenes.reduce((sum, scene) => sum + scene.shots.reduce((shotSum, shot) => shotSum + Number.parseFloat(shot.duration || 0), 0), 0);
    return { scene_count: scenes.length, shot_count: shotCount, duration_sec: durationSec };
  }
  function generatedMediaCount() { return sceneModel().flatMap((scene) => scene.shots).filter((shot) => Boolean(shot.preview)).length; }
  function mediaCompletionPercent() { return totalShots() ? Math.round((generatedMediaCount() / totalShots()) * 100) : 0; }
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
    showAssetBible,
    showCanvas,
    setSection(next) {
      if (next === "agent") {
        setAgentChatExpanded(true);
      } else if (next === "storyboard" || next === "asset_bible") {
        section = next;
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

function clearedProjectSnapshot(snapshot) {
  return {
    ...snapshot,
    project: null,
    sequenceWorkspace: null,
    mediaOperations: null,
    runtimeAssetBible: null,
    imageAdmission: null,
    mediaGates: {},
    mediaCommandPreview: null,
    error: "",
  };
}

function cachedProjectSummary(studioState) {
  const name = String(studioState?.meta?.projectName || "").trim() || "离线项目缓存";
  return {
    project_id: String(studioState?.meta?.projectId || ""),
    name,
    episode: "只读缓存",
    current_stage: "等待重新验证",
    next_action: "重试连接并验证项目身份",
    stages: [],
  };
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

function splitList(value) {
  return String(value || "")
    .split(/[、,，;\n]+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, 24);
}

function assetCommandLabel(value) {
  return {
    generate_candidates: "建立本地确定性资产候选",
    regenerate_candidates: "重新识别并预览替换",
    create_asset: "补充人工审核资产",
    set_art_direction: "确认统一美术方向",
    approve: "批准资产候选",
    reject: "拒绝资产候选",
    edit: "编辑资产候选",
    merge: "合并资产候选",
    split: "拆分资产候选",
    reassign_occurrences: "重分配必要出现范围",
    mark_not_needed: "标记出现范围为无需",
    lock: "锁定 Asset Bible 版本",
  }[String(value || "")] || "更新 Asset Bible";
}

function resolutionStatusLabel(value) {
  return {
    approved: "已由批准资产覆盖",
    pending: "等待资产批准",
    rejected: "引用资产已拒绝",
    superseded: "引用资产已取代",
    orphaned: "引用去向缺失",
    not_needed: "已明确无需",
  }[String(value || "")] || "待解决";
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

function delay(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}
