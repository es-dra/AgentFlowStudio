import { currentLocale, message, setLocale } from "./i18n.js";
import { icon } from "./icons.js";
import { findNextProductionTarget, productContextKey } from "./product-shell-context.js";
import { buildAgentChatPanel } from "./agent-chat-panel.js";
import { agentChatContextKey, agentChatContextSnapshot, createAgentChatContextStore, submitAgentChatMessage } from "./agent-chat-lifecycle.js";

export function createProductShell(options = {}) {
  let locale = currentLocale();
  let section = "canvas";
  let selection = { sceneIndex: 0, shotIndex: 0 };
  let agentCollapsed = false;
  let projectDrawerOpen = false;
  let contextOpen = false;
  let mobileAgentOpen = false;
  let notice = "";
  let agentChatWidth = readAgentChatWidth();
  const agentChatContexts = createAgentChatContextStore();
  let snapshot = {
    loading: true,
    workspace: null,
    project: null,
    studioState: null,
    error: "",
    authUser: null,
  };
  bindShellEvents();

  function render(next = {}) {
    snapshot = { ...snapshot, ...next };
    snapshot.studioState = snapshot.studioState || options.getStudioState?.() || null;
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

    const navigator = node("button", `studio-stage-button ${projectDrawerOpen ? "active" : ""}`);
    navigator.type = "button";
    navigator.setAttribute("aria-label", "打开项目导航");
    navigator.setAttribute("aria-controls", "studio-context-drawer");
    navigator.setAttribute("aria-expanded", String(projectDrawerOpen));
    navigator.innerHTML = `<span>项目导航</span>${icon("chevronDown", 13)}`;
    navigator.addEventListener("click", () => {
      projectDrawerOpen = !projectDrawerOpen;
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

    header.append(brand, project, navigator, viewSwitch, summary, actions);
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
    panel.append(close, copy, stages, scenes, next);
    return panel;
  }

  function buildWorkspace() {
    const emptyCanvas = section === "canvas" && !hasStoryFacts();
    const canvasActive = section === "canvas";
    const shell = node("div", `studio-unified-workspace ${agentCollapsed ? "agent-collapsed" : ""} ${mobileAgentOpen ? "agent-mobile-open" : ""} ${canvasActive ? "canvas-section" : "storyboard-section"} ${emptyCanvas ? "canvas-empty-project" : ""}`);
    shell.dataset.contextKey = currentContextKey();
    shell.style.setProperty("--agent-chat-width", `${agentChatWidth}px`);
    if (section === "storyboard" && !emptyCanvas) shell.appendChild(buildSceneRail());
    const main = section === "canvas" ? buildCanvasWorkspace() : buildStoryboardWorkspace();
    shell.appendChild(main);
    shell.appendChild(buildAgentChat());
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
    main.appendChild(stage);
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
      agentCollapsed = false;
      mobileAgentOpen = true;
      notice = "版本记录只随画布事实读取；恢复命令需要在 Agent Chat 中预览和确认。";
      render();
    });
    bar.append(script, node("p", "", currentShot().description), versions);
    return bar;
  }

  function buildAgentChat() {
    const context = currentAgentChatContext();
    const session = agentChatContexts.get(agentChatContextKey(context));
    return buildAgentChatPanel({
      session,
      context: { ...context, context_key: agentChatContextKey(context) },
      store: options.getStore?.(),
      runtime: options.getRuntime?.(),
      collapsed: agentCollapsed,
      mobileOpen: mobileAgentOpen,
      onToggleCollapse: () => {
        agentCollapsed = !agentCollapsed;
        mobileAgentOpen = !agentCollapsed;
        render();
        requestCanvasSafeAreaUpdate();
      },
      onOpen: () => {
        agentCollapsed = false;
        mobileAgentOpen = true;
      },
      onResizeStart: bindAgentResize,
      onRender: () => render(),
    });
  }

  function buildMobileNav() {
    const nav = node("nav", "product-mobile-nav");
    nav.setAttribute("aria-label", "移动端 Studio 导航");
    for (const [key, label] of [["canvas", "画布"], ["storyboard", "故事板"], ["context", "项目"], ["agent", "Agent"]]) {
      const active = key === "agent" ? mobileAgentOpen : section === key;
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
          mobileAgentOpen = false;
        } else {
          agentCollapsed = false;
          mobileAgentOpen = true;
        }
        render();
        requestCanvasSafeAreaUpdate();
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
    agentCollapsed = false;
    mobileAgentOpen = true;
    selectContext(target.sceneIndex, target.shotIndex, {
      actionLabel,
      noticeText: `已定位到场景 ${String(target.sceneIndex + 1).padStart(2, "0")} · 镜头 ${String(target.shotIndex + 1).padStart(2, "0")}，Agent Chat 已绑定当前上下文。`,
    });
  }

  function selectContext(sceneIndex, shotIndex, { actionLabel = "", noticeText = "" } = {}) {
    const scenes = sceneModel();
    if (!scenes.length) {
      selection = { sceneIndex: 0, shotIndex: 0 };
      agentCollapsed = false;
      mobileAgentOpen = true;
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
    agentCollapsed = false;
    mobileAgentOpen = true;
    notice = "Agent Chat 已绑定当前画布上下文；确认前不会创建场景或镜头。";
    render();
    requestCanvasSafeAreaUpdate();
    requestAnimationFrame(() => document.querySelector(".agent-chat-composer textarea")?.focus());
  }

  function submitToAgentChat(messageText) {
    const context = currentAgentChatContext();
    const session = agentChatContexts.get(agentChatContextKey(context));
    const result = submitAgentChatMessage(session, messageText, context);
    agentCollapsed = false;
    mobileAgentOpen = true;
    if (result.status === "empty") focusAgentComposer();
    else render();
    requestCanvasSafeAreaUpdate();
    requestAnimationFrame(() => document.querySelector(".agent-chat-composer textarea")?.focus());
    return result;
  }

  function bindShellEvents() {
    window.addEventListener("afs:agent-chat-submit", (event) => {
      submitToAgentChat(event.detail?.message || "");
    });
    window.addEventListener("afs:agent-chat-focus", () => focusAgentComposer());
    window.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      if (projectDrawerOpen || contextOpen || mobileAgentOpen) {
        projectDrawerOpen = false;
        contextOpen = false;
        mobileAgentOpen = false;
        render();
        requestCanvasSafeAreaUpdate();
      }
    });
  }

  function bindAgentResize(event) {
    if (!event?.pointerId || agentCollapsed) return;
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
    return agentChatContextSnapshot({
      project: snapshot.project,
      studioState: snapshot.studioState,
      section,
      selectedNode: selectedCanvasNode(),
      currentShot: currentShot(),
    });
  }

  function selectedCanvasNode() {
    const state = snapshot.studioState || {};
    const selectedId = state.selection?.nodeIds?.[0] || currentShot().nodeId || "";
    return selectedId ? state.nodes?.[selectedId] || null : null;
  }

  function openCanvas() {
    const opened = options.onOpenCanvas?.();
    if (opened === false) {
      section = "storyboard";
      mobileAgentOpen = false;
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

  function showStoryboard() {
    section = "storyboard";
    mobileAgentOpen = false;
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
    showStoryboard,
    showCanvas,
    setSection(next) {
      if (next === "agent") {
        agentCollapsed = false;
        mobileAgentOpen = true;
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

function requestCanvasSafeAreaUpdate() {
  requestAnimationFrame(() => window.dispatchEvent(new CustomEvent("afs:canvas-safe-area-changed")));
}
