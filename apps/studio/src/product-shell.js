import { currentLocale, message, setLocale } from "./i18n.js";
import { icon } from "./icons.js";
import { createDirectorContextStore, findNextProductionTarget, productContextKey } from "./product-shell-context.js";

const DIRECTOR_TABS = [
  ["suggestion", "建议"],
  ["reference", "引用"],
  ["version", "版本"],
];

export function createProductShell(options = {}) {
  let locale = currentLocale();
  let section = "canvas";
  let selection = { sceneIndex: 0, shotIndex: 0 };
  let directorTab = "suggestion";
  let directorCollapsed = false;
  let cockpitOpen = false;
  let contextOpen = false;
  let mobileDirectorOpen = false;
  let notice = "";
  const directorContexts = createDirectorContextStore();
  let snapshot = {
    loading: true,
    workspace: null,
    project: null,
    studioState: null,
    error: "",
    authUser: null,
  };

  function render(next = {}) {
    snapshot = { ...snapshot, ...next };
    snapshot.studioState = snapshot.studioState || options.getStudioState?.() || null;
    const root = document.getElementById("product-shell-root");
    if (!root) return;
    options.parkCanvas?.();
    root.className = `unified-studio-shell ${cockpitOpen ? "cockpit-open" : ""}`;
    root.dataset.view = section;
    root.replaceChildren();
    root.appendChild(buildHeader());
    if (cockpitOpen && snapshot.project) root.appendChild(buildCockpit());
    if (snapshot.loading) root.appendChild(statePanel("loading"));
    else if (snapshot.error) root.appendChild(statePanel("error"));
    else if (!snapshot.project) root.appendChild(statePanel("empty"));
    else root.appendChild(buildWorkspace());
    root.appendChild(buildMobileNav());
  }

  function buildHeader() {
    const header = node("header", "studio-unified-header");
    const brand = node("div", "studio-unified-brand");
    brand.innerHTML = '<strong aria-label="AgentFlow Studio">AFS</strong><span>AgentFlow Studio</span>';

    const project = node("div", "studio-project-context");
    const projectLabel = node("button", "studio-project-button");
    projectLabel.type = "button";
    projectLabel.setAttribute("aria-label", "当前项目与单集");
    projectLabel.innerHTML = `<strong>${escapeHtml(snapshot.project?.name || "项目")}</strong><span>${escapeHtml(snapshot.project?.episode || "第一集")}</span>${icon("chevronDown", 13)}`;
    projectLabel.addEventListener("click", () => {
      contextOpen = !contextOpen;
      render();
    });
    project.appendChild(projectLabel);
    if (contextOpen) project.appendChild(buildProjectMenu());

    const stage = node("button", `studio-stage-button ${cockpitOpen ? "active" : ""}`);
    stage.type = "button";
    stage.setAttribute("aria-expanded", String(cockpitOpen));
    stage.innerHTML = `<span>${escapeHtml(snapshot.project?.current_stage || "分镜制作")}</span>${icon("chevronDown", 13)}`;
    stage.addEventListener("click", () => {
      cockpitOpen = !cockpitOpen;
      render();
    });

    const viewSwitch = node("div", "studio-view-switch");
    viewSwitch.setAttribute("role", "tablist");
    viewSwitch.setAttribute("aria-label", "工作区视图");
    viewSwitch.append(
      viewButton("storyboard", "故事板"),
      viewButton("canvas", "画布"),
    );

    const summary = node("div", "studio-header-summary");
    const progress = Math.max(0, Math.min(100, Number(snapshot.project?.progress_percent || candidateDeliveryProgress(snapshot.project))));
    summary.append(
      statusItem("check", `交付就绪 ${progress}%`, "ok"),
      statusItem("clock", `待处理 ${pendingCount()}`, pendingCount() ? "warning" : "muted"),
    );

    const actions = node("div", "studio-header-actions");
    if (options.onOpenExternalVideoDemo) {
      const externalVideo = node("button", "studio-secondary-button studio-external-video-button");
      externalVideo.type = "button";
      externalVideo.innerHTML = icon("video", 13) + "<span>AI 漫剧</span>";
      externalVideo.addEventListener("click", () => options.onOpenExternalVideoDemo?.());
      actions.appendChild(externalVideo);
    }
    actions.appendChild(buildSaveStatus());
    const language = node("button", "studio-icon-button", locale === "zh-CN" ? "中" : "EN");
    language.type = "button";
    language.setAttribute("aria-label", `${message("language", locale)}：${language.textContent}`);
    language.addEventListener("click", () => {
      locale = setLocale(locale === "zh-CN" ? "en" : "zh-CN");
      render();
    });
    actions.appendChild(language);
    if (snapshot.authUser) {
      const account = node("button", "studio-account-button", userLabel(snapshot.authUser));
      account.type = "button";
      account.setAttribute("aria-label", message("signOut", locale));
      account.addEventListener("click", () => options.onSignOut?.());
      actions.appendChild(account);
    }

    header.append(brand, project, stage, viewSwitch, summary, actions);
    return header;
  }

  function buildProjectMenu() {
    const menu = node("div", "studio-project-menu");
    menu.setAttribute("role", "menu");
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

  function buildCockpit() {
    const project = snapshot.project;
    const panel = node("section", "studio-cockpit");
    panel.setAttribute("aria-label", "项目状态与下一步");
    const copy = node("div", "cockpit-copy");
    copy.append(
      node("span", "eyebrow", "当前阶段"),
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
    panel.append(copy, stages, next);
    return panel;
  }

  function buildWorkspace() {
    const shell = node("div", `studio-unified-workspace ${directorCollapsed ? "director-collapsed" : ""}`);
    shell.dataset.contextKey = currentContextKey();
    shell.appendChild(buildSceneRail());
    const main = section === "canvas" ? buildCanvasWorkspace() : buildStoryboardWorkspace();
    shell.appendChild(main);
    shell.appendChild(buildDirector());
    return shell;
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
    main.appendChild(buildContextBar());
    const stage = node("section", "canvas-workspace-stage");
    stage.setAttribute("aria-label", `画布 · ${currentShot().title}`);
    stage.dataset.canvasTarget = currentShot().nodeId || "empty-project";
    const editor = options.getCanvasShell?.();
    if (editor) stage.appendChild(editor);
    else stage.appendChild(node("p", "canvas-unavailable", "画布编辑当前不可用；项目与审核上下文仍保持在此工作区。"));
    if (notice) {
      const live = node("p", "studio-live-notice", notice);
      live.setAttribute("aria-live", "polite");
      stage.appendChild(live);
    }
    main.append(stage, buildVersionBar());
    return main;
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
      ? `<span>当前项目</span><strong>${escapeHtml(snapshot.project?.name || "未命名项目")}</strong><span>尚未创建场景或镜头</span>`
      : `<span>当前选择</span><strong>场景 ${String(selection.sceneIndex + 1).padStart(2, "0")} · ${escapeHtml(scene.name)}</strong><span>镜头 ${String(selection.shotIndex + 1).padStart(2, "0")} · ${escapeHtml(shot.title)}</span>`;
    const actions = node("div", "context-actions");
    const brief = node("button", "studio-secondary-button", "告诉 AI 导演");
    brief.type = "button";
    brief.addEventListener("click", focusDirectorBrief);
    const review = node("button", "studio-secondary-button", "进入审核");
    review.type = "button";
    review.addEventListener("click", () => {
      directorTab = "version";
      directorCollapsed = false;
      mobileDirectorOpen = true;
      notice = "审核范围已锁定为当前镜头。";
      render();
    });
    const canvas = node("button", "studio-text-button");
    canvas.type = "button";
    canvas.innerHTML = section === "canvas"
      ? `${icon("grid", 13)}在故事板查看`
      : `查看画布${icon("expand", 13)}`;
    canvas.addEventListener("click", () => section === "canvas" ? showOverview() : openCanvas());
    if (empty) actions.append(brief, canvas);
    else actions.append(review, canvas);
    bar.append(selectionContext, actions);
    return bar;
  }

  function buildStoryboardContent() {
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
      node("p", "", "先告诉 AI 导演你想做什么，或粘贴/导入故事材料；确认前不会创建故事事实。"),
    );
    const actions = node("div", "storyboard-empty-actions");
    const brief = node("button", "studio-primary-button", "告诉 AI 导演你想做什么");
    brief.type = "button";
    brief.addEventListener("click", focusDirectorBrief);
    const canvas = node("button", "studio-secondary-button", "打开空白画布");
    canvas.type = "button";
    canvas.addEventListener("click", openCanvas);
    actions.append(brief, canvas);
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
    const versions = node("button", "studio-text-button", "查看版本与恢复");
    versions.type = "button";
    versions.addEventListener("click", () => {
      directorTab = "version";
      directorCollapsed = false;
      mobileDirectorOpen = true;
      render();
    });
    bar.append(script, node("p", "", currentShot().description), versions);
    return bar;
  }

  function buildDirector() {
    const aside = node("aside", `studio-director ${mobileDirectorOpen ? "mobile-open" : ""}`);
    aside.dataset.contextKey = currentContextKey();
    const head = node("header", "director-head");
    const title = node("div");
    title.innerHTML = hasStoryFacts()
      ? `<span class="director-mark">AI</span><span><strong>导演 · 当前镜头</strong><small>${escapeHtml(currentShot().title)}</small></span>`
      : `<span class="director-mark">AI</span><span><strong>导演 · 项目简报</strong><small>${escapeHtml(snapshot.project?.name || "未命名项目")}</small></span>`;
    const collapse = node("button", "studio-icon-button");
    collapse.type = "button";
    collapse.setAttribute("aria-label", directorCollapsed ? "展开 AI 导演" : "收起 AI 导演");
    collapse.setAttribute("aria-expanded", String(!directorCollapsed));
    collapse.innerHTML = icon(directorCollapsed ? "panel" : "chevronDown", 15);
    collapse.addEventListener("click", () => {
      directorCollapsed = !directorCollapsed;
      mobileDirectorOpen = !directorCollapsed;
      render();
    });
    head.append(title, collapse);
    aside.appendChild(head);
    if (directorCollapsed) return aside;

    const tabs = node("div", "director-tabs");
    tabs.setAttribute("role", "tablist");
    for (const [key, label] of DIRECTOR_TABS) {
      const tab = node("button", directorTab === key ? "active" : "", label);
      tab.type = "button";
      tab.setAttribute("role", "tab");
      tab.setAttribute("aria-selected", String(directorTab === key));
      tab.addEventListener("click", () => {
        directorTab = key;
        render();
      });
      tabs.appendChild(tab);
    }
    aside.appendChild(tabs);
    if (directorTab === "reference") aside.appendChild(buildDirectorReferences());
    else if (directorTab === "version") aside.appendChild(buildDirectorVersions());
    else aside.appendChild(buildDirectorSuggestion());
    return aside;
  }

  function buildDirectorSuggestion() {
    if (!hasStoryFacts()) return buildEmptyDirectorSuggestion();
    const body = node("div", "director-body");
    const chat = node("div", "director-chat");
    const shot = currentShot();
    const context = directorContext();
    chat.appendChild(chatBubble("assistant", `建议先检查“${shot.title}”的主体方向与环境关系，再决定是否进入审核。`));
    for (const item of context.conversations.slice(-4)) chat.appendChild(chatBubble(item.role, item.text));
    body.appendChild(chat);

    const references = node("button", "director-reference-summary");
    references.type = "button";
    references.innerHTML = `${icon("link", 14)}<span><strong>参考已绑定</strong><small>脚本场景 · 相邻镜头 · 当前候选</small></span>${icon("chevronDown", 13)}`;
    references.addEventListener("click", () => {
      directorTab = "reference";
      render();
    });
    body.appendChild(references);

    const proposal = node("section", `director-proposal ${context.proposalApplied ? "applied" : ""}`);
    proposal.innerHTML = `<span class="eyebrow">${context.actionLabel ? "当前下一步 · 已定位" : "建议调整 · 不自动执行"}</span><strong>${context.proposalApplied ? "调整已加入当前镜头草稿" : escapeHtml(context.proposalText)}</strong><p>只影响当前镜头；相邻镜头、已确认事实和版本仍保持不变。</p>`;
    const apply = node("button", "studio-primary-button", context.proposalApplied ? "已加入草稿" : "应用到草稿");
    apply.type = "button";
    apply.disabled = context.proposalApplied;
    apply.addEventListener("click", () => {
      const applied = options.onApplyDirectorDraft?.(shot.nodeId, context.proposalText);
      if (applied === false) {
        notice = "当前镜头还没有可写入的画布节点，建议已保留在本次讨论中。";
        render();
        return;
      }
      context.proposalApplied = true;
      notice = "导演建议已加入当前镜头草稿，正在保存；尚未提交审核。";
      render();
    });
    proposal.appendChild(apply);
    body.appendChild(proposal);

    body.appendChild(buildDirectorComposer("围绕当前镜头继续讨论…"));
    return body;
  }

  function buildEmptyDirectorSuggestion() {
    const body = node("div", "director-body");
    const chat = node("div", "director-chat");
    const context = directorContext();
    chat.appendChild(chatBubble("assistant", "先告诉我你想做什么，或粘贴/导入剧本材料。我会先整理 Brief、Bible、Arc、Episode、Scene、Shot 和 ProductionRecipe，等你确认后再创建场景与镜头。"));
    for (const item of context.conversations.slice(-4)) chat.appendChild(chatBubble(item.role, item.text));
    body.appendChild(chat);
    const proposal = node("section", "director-proposal");
    proposal.innerHTML = '<span class="eyebrow">当前下一步</span><strong>等待创作简报</strong><p>空项目不会自动带入示例、进度、参考或分镜。</p>';
    body.appendChild(proposal);
    body.appendChild(buildDirectorComposer("描述你想制作的 90–120 秒内容…"));
    return body;
  }

  function buildDirectorComposer(placeholder) {
    const context = directorContext();
    const form = node("form", "director-composer");
    const input = document.createElement("textarea");
    input.rows = 2;
    input.placeholder = placeholder;
    input.setAttribute("aria-label", "向 AI 导演提问");
    const send = node("button", "studio-icon-button");
    send.type = "submit";
    send.setAttribute("aria-label", "发送");
    send.innerHTML = icon("arrowUp", 16);
    form.append(input, send);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      context.conversations.push(
        { role: "user", text },
        { role: "assistant", text: hasStoryFacts() ? "我会把建议限制在当前镜头，并先列出影响范围再等待你确认。" : "我会先整理成创作简报和制作配方草案，等你确认后再创建场景与镜头。" },
      );
      render();
    });
    return form;
  }

  function buildDirectorReferences() {
    const body = node("div", "director-body director-reference-list");
    if (!hasStoryFacts()) {
      body.appendChild(node("p", "director-note", "还没有绑定脚本、镜头、参考集或候选素材。"));
      return body;
    }
    const refs = [
      ["脚本场景", currentScene().name, "当前"],
      ["相邻镜头", selection.shotIndex > 0 ? currentScene().shots[selection.shotIndex - 1].title : "场景开场", "上下文"],
      ["当前候选", currentShot().title, "v3"],
    ];
    for (const [type, title, meta] of refs) {
      const item = node("article", "director-reference-item");
      item.append(node("span", "", icon("image", 15)), node("div", "", `<small>${escapeHtml(type)}</small><strong>${escapeHtml(title)}</strong>`), node("span", "", meta));
      item.children[1].innerHTML = `<small>${escapeHtml(type)}</small><strong>${escapeHtml(title)}</strong>`;
      body.appendChild(item);
    }
    body.appendChild(node("p", "director-note", "引用只用于当前建议，不会自动改变已确认事实。"));
    return body;
  }

  function buildDirectorVersions() {
    const body = node("div", "director-body director-version-panel");
    if (!hasStoryFacts()) {
      body.appendChild(node("p", "director-note", "还没有可恢复的故事版本；确认创作简报后才会产生版本记录。"));
      return body;
    }
    body.append(
      node("p", "director-note", "版本与恢复按需展开；当前仅显示与所选镜头有关的记录。"),
      versionRow("当前候选", "v3", "待审核"),
      versionRow("已确认版本", "v2", "可恢复"),
    );
    const recovery = node("button", "studio-secondary-button", "恢复上一确认版本");
    recovery.type = "button";
    recovery.addEventListener("click", () => {
      notice = "已进入恢复预览；确认前不会覆盖当前草稿。";
      render();
    });
    body.appendChild(recovery);
    return body;
  }

  function buildMobileNav() {
    const nav = node("nav", "product-mobile-nav");
    nav.setAttribute("aria-label", "移动端项目与审核导航");
    for (const [key, label] of [["storyboard", "故事板"], ["context", "项目"], ["review", "审核"], ["director", "导演"]]) {
      const button = node("button", section === key ? "active" : "", label);
      button.type = "button";
      button.setAttribute("aria-current", section === key ? "page" : "false");
      button.addEventListener("click", () => {
        section = key;
        if (key === "context") cockpitOpen = true;
        if (key === "review") directorTab = "version";
        if (key === "review" || key === "director") {
          directorCollapsed = false;
          mobileDirectorOpen = true;
        }
        render();
        requestAnimationFrame(() => document.getElementById("product-main")?.focus());
      });
      nav.appendChild(button);
    }
    return nav;
  }

  function viewButton(key, label) {
    const active = section === key;
    const button = node("button", active ? "active" : "", label);
    button.type = "button";
    button.setAttribute("role", "tab");
    button.setAttribute("aria-selected", String(active));
    button.addEventListener("click", () => key === "canvas" ? openCanvas() : showOverview());
    return button;
  }

  function activateNextAction() {
    const target = findNextProductionTarget(sceneModel(), selection);
    if (!target) {
      focusDirectorBrief();
      return;
    }
    const actionLabel = snapshot.project?.next_action || "继续当前镜头制作";
    cockpitOpen = false;
    directorTab = "suggestion";
    directorCollapsed = false;
    mobileDirectorOpen = true;
    selectContext(target.sceneIndex, target.shotIndex, {
      actionLabel,
      noticeText: `已定位到场景 ${String(target.sceneIndex + 1).padStart(2, "0")} · 镜头 ${String(target.shotIndex + 1).padStart(2, "0")}，导演建议已按当前下一步准备。`,
    });
  }

  function selectContext(sceneIndex, shotIndex, { actionLabel = "", noticeText = "" } = {}) {
    const scenes = sceneModel();
    if (!scenes.length) {
      selection = { sceneIndex: 0, shotIndex: 0 };
      directorTab = "suggestion";
      directorCollapsed = false;
      mobileDirectorOpen = true;
      notice = noticeText || "先完成创作简报，确认后再创建故事事实。";
      syncCanvasSelection();
      render();
      requestAnimationFrame(() => document.getElementById("product-main")?.focus());
      return;
    }
    const nextSceneIndex = Math.max(0, Math.min(Number(sceneIndex || 0), scenes.length - 1));
    const nextShotIndex = Math.max(0, Math.min(Number(shotIndex || 0), scenes[nextSceneIndex].shots.length - 1));
    selection = { sceneIndex: nextSceneIndex, shotIndex: nextShotIndex };
    directorTab = "suggestion";
    notice = noticeText;
    const context = directorContext();
    if (actionLabel) {
      context.actionLabel = actionLabel;
      context.proposalText = `${actionLabel}：先复核“${currentShot().title}”的画面目标与阻塞项`;
      context.proposalApplied = false;
    }
    syncCanvasSelection();
    render();
    requestAnimationFrame(focusCurrentContext);
  }

  function syncCanvasSelection() {
    options.onSelectCanvasNode?.(currentShot().nodeId || "");
  }

  function focusDirectorBrief() {
    directorTab = "suggestion";
    directorCollapsed = false;
    mobileDirectorOpen = true;
    notice = "AI 导演已切到项目简报；确认前不会创建场景或镜头。";
    render();
    requestAnimationFrame(() => document.querySelector(".director-composer textarea")?.focus());
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

  function directorContext() {
    return directorContexts.get(currentContextKey());
  }

  function openCanvas() {
    const opened = options.onOpenCanvas?.();
    if (opened === false) {
      section = "storyboard";
      mobileDirectorOpen = false;
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
      let project = null;
      if (activeProjectId) {
        const projectRuntime = activeProjectId === requestRuntime.projectId ? requestRuntime : options.createRuntime?.(activeProjectId);
        const payload = await projectRuntime?.projectOverview?.();
        if (options.isRuntimeCurrent && !options.isRuntimeCurrent(requestRuntime)) return;
        project = payload?.project || null;
      }
      snapshot = { loading: false, workspace, project, error: "", authUser, studioState: options.getStudioState?.() || snapshot.studioState };
    } catch (error) {
      if (options.isRuntimeCurrent && !options.isRuntimeCurrent(requestRuntime)) return;
      snapshot = { ...snapshot, loading: false, project: null, error: options.formatError?.(error) || message("error", locale), authUser };
    }
    render();
  }

  function updateStudioState(studioState) {
    snapshot = { ...snapshot, studioState };
    if (document.getElementById("app")?.classList.contains("product-mode")) render();
  }

  function showOverview() {
    section = "storyboard";
    mobileDirectorOpen = false;
    render();
  }

  function showCanvas() {
    if (!options.getCanvasShell?.()) return false;
    section = "canvas";
    syncCanvasSelection();
    render();
    return true;
  }

  function sceneModel() {
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
    const state = snapshot.studioState || {};
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

  function currentScene() { return sceneModel()[selection.sceneIndex] || emptyScene(); }
  function currentShot() { return currentScene().shots[selection.shotIndex] || emptyShot(); }
  function hasStoryFacts() { return shotModel().length > 0; }
  function totalShots() { return sceneModel().reduce((sum, scene) => sum + scene.shots.length, 0); }
  function totalReadyShots() { return sceneModel().flatMap((scene) => scene.shots).filter((shot) => shot.state === "ready").length; }
  function completionPercent() { return totalShots() ? Math.round((totalReadyShots() / totalShots()) * 100) : 0; }
  function pendingCount() { return Number(snapshot.project?.decision_inbox?.pending_count || 0) + Number(snapshot.project?.crew?.blocked_count || 0); }
  function shotStateLabel(state) { return state === "ready" ? "已确认" : state === "blocked" ? "待处理" : "草稿"; }

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
    showCanvas,
    setSection(next) { section = next; render(); },
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

function chatBubble(role, text) {
  const bubble = node("div", `director-bubble ${role}`);
  bubble.append(node("span", "director-avatar", role === "user" ? "我" : "AI"), node("p", "", text));
  return bubble;
}

function versionRow(label, version, state) {
  const row = node("article", "director-version-row");
  row.append(node("div", "", `<strong>${escapeHtml(label)}</strong><small>${escapeHtml(version)}</small>`), node("span", "", state));
  row.firstElementChild.innerHTML = `<strong>${escapeHtml(label)}</strong><small>${escapeHtml(version)}</small>`;
  return row;
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
  return ["建立空间", "脚步特写", "人物回望", "眼神细节", "继续前行", "环境过渡"][index % 6];
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
