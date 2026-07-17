import { currentLocale, message, setLocale } from "./i18n.js";
import { icon } from "./icons.js";
import { createDirectorContextStore, findNextProductionTarget, productContextKey } from "./product-shell-context.js";
import { composeReviewDeliveryState, focusReviewCandidate, selectedDeliverySubmission } from "./review-delivery-state.js";

const DIRECTOR_TABS = [
  ["suggestion", "建议"],
  ["reference", "引用"],
  ["version", "版本"],
];

const REVIEW_QUALITY_FIELDS = [
  ["story_intent_preserved", "叙事意图", "确认故事重点、情绪走向和信息层级没有偏离。", "narrative"],
  ["character_continuity_checked", "画面一致性", "确认角色、场景与关键视觉设定保持连续。", "consistency"],
  ["shot_coverage_checked", "镜头覆盖", "确认必要镜头与交付构图已覆盖。", "coverage"],
  ["revision_addressed", "改版要求", "确认本轮修改原因已经被处理。", "revision"],
];

export function createProductShell(options = {}) {
  let locale = currentLocale();
  let section = "storyboard";
  let selection = { sceneIndex: 0, shotIndex: 0 };
  let directorTab = "suggestion";
  let directorCollapsed = false;
  let cockpitOpen = false;
  let contextOpen = false;
  let mobileDirectorOpen = false;
  let notice = "";
  let reviewBusy = "";
  let reviewNotice = "";
  let reviewError = "";
  const directorContexts = createDirectorContextStore();
  let snapshot = {
    loading: true,
    workspace: null,
    project: null,
    reviewDelivery: null,
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
      viewButton("review", "审核交付"),
    );

    const summary = node("div", "studio-header-summary");
    const progress = Math.max(0, Math.min(100, Number(snapshot.project?.progress_percent || candidateDeliveryProgress(snapshot.project))));
    summary.append(
      statusItem("check", `交付就绪 ${progress}%`, "ok"),
      statusItem("clock", `待处理 ${pendingCount()}`, pendingCount() ? "warning" : "muted"),
    );

    const actions = node("div", "studio-header-actions");
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
        if (item.project_id !== snapshot.project?.project_id) {
          reviewNotice = "";
          reviewError = "";
          notice = "";
          snapshot = {
            ...snapshot,
            loading: true,
            project: projectSummaryShell(item),
            reviewDelivery: null,
            studioState: null,
          };
          render();
        }
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
    const canvasActive = section === "canvas";
    const emptyCanvas = canvasActive && !hasStoryFacts();
    const shell = node("div", [
      "studio-unified-workspace",
      directorCollapsed ? "director-collapsed" : "",
      canvasActive ? "canvas-section" : "",
      emptyCanvas ? "canvas-empty-project" : "",
    ].filter(Boolean).join(" "));
    shell.dataset.contextKey = currentContextKey();
    if (!emptyCanvas) shell.appendChild(buildSceneRail());
    const main = section === "canvas"
      ? buildCanvasWorkspace()
      : section === "review"
        ? buildReviewWorkspace()
        : buildStoryboardWorkspace();
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
      showReview({ noticeText: "审核交付已绑定当前项目与选择。" });
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
    if (notice) {
      const live = node("p", "studio-live-notice", notice);
      live.setAttribute("aria-live", "polite");
      body.appendChild(live);
    }
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
      showReview({ noticeText: "版本、恢复与交付状态已在当前 Studio 中打开。" });
    });
    bar.append(script, node("p", "", currentShot().description), versions);
    return bar;
  }

  function buildReviewWorkspace() {
    const main = node("main", "studio-workspace-main studio-review-workspace");
    main.id = "product-main";
    main.tabIndex = -1;
    main.appendChild(buildContextBar());
    const reviewState = currentReviewState();
    const stage = node("section", "studio-review-stage");
    stage.setAttribute("aria-label", "审核、恢复与交付");
    stage.append(buildReviewHeading(reviewState), buildReviewContent(reviewState));
    if (notice || reviewNotice || reviewError) {
      const live = node("p", `studio-live-notice ${reviewError ? "error" : ""}`, reviewError || reviewNotice || notice);
      live.setAttribute("aria-live", "polite");
      stage.appendChild(live);
    }
    main.append(stage, buildVersionBar());
    return main;
  }

  function buildReviewHeading(reviewState) {
    const head = node("div", "studio-review-heading");
    const copy = node("div");
    copy.append(
      node("span", "eyebrow", "审核交付"),
      node("h1", "", snapshot.project?.name || "当前项目"),
      node("p", "", hasStoryFacts()
        ? `当前选择：${currentShot().title}`
        : "当前项目还没有可审核的场景或镜头"),
    );
    const status = node("span", `studio-review-status ${reviewState.phase === "ready" ? "ready" : "pending"}`, reviewStatusLabel(reviewState));
    head.append(copy, status);
    return head;
  }

  function buildReviewContent(reviewState) {
    if (!reviewState || reviewState.phase === "empty") return buildEmptyReviewContent();
    if (reviewState.phase !== "ready") {
      const panel = node("div", "studio-review-empty");
      panel.append(node("strong", "", "暂时无法读取审核状态"), node("span", "", "请刷新当前项目后再继续。"));
      return panel;
    }
    const layout = node("div", "studio-review-layout");
    layout.append(buildReviewCandidatePanel(reviewState), buildReviewActionPanel(reviewState));
    return layout;
  }

  function buildEmptyReviewContent() {
    const panel = node("div", "studio-review-empty");
    panel.append(
      node("strong", "", "还没有可审核的制作版本"),
      node("span", "", "候选、批准、恢复与交付包只会来自当前项目的制作记录；这里不会显示示例或推断结果。"),
    );
    const actions = node("div", "studio-review-empty-actions");
    const brief = node("button", "studio-primary-button", "告诉 AI 导演你想做什么");
    brief.type = "button";
    brief.addEventListener("click", focusDirectorBrief);
    const canvas = node("button", "studio-secondary-button", "查看同源画布");
    canvas.type = "button";
    canvas.addEventListener("click", openCanvas);
    actions.append(brief, canvas);
    panel.appendChild(actions);
    return panel;
  }

  function buildReviewCandidatePanel(reviewState) {
    const panel = node("section", "studio-review-candidates");
    panel.setAttribute("aria-labelledby", "studio-review-candidates-heading");
    const head = node("header", "");
    head.append(
      node("h2", "", "当前候选"),
      node("span", "", `${reviewState.candidates.length} 个方案`),
    );
    head.querySelector("h2").id = "studio-review-candidates-heading";
    panel.appendChild(head);
    const list = node("div", "studio-review-candidate-list");
    list.setAttribute("role", "list");
    for (const [index, candidate] of reviewState.candidates.entries()) {
      const card = node("button", `studio-review-candidate ${candidate.candidate_id === reviewState.focusedCandidateId ? "active" : ""}`);
      card.type = "button";
      card.setAttribute("role", "listitem");
      card.setAttribute("aria-label", `${candidate.label}${candidate.candidate_id === reviewState.selectedCandidateId && !reviewState.rejected ? "，当前版本" : ""}`);
      card.innerHTML = `<strong>${escapeHtml(candidate.label || `方案 ${index + 1}`)}</strong><span>${candidate.available ? "预览可用" : "预览暂不可用"}</span><small>${candidate.candidate_id === reviewState.selectedCandidateId && !reviewState.rejected ? "当前版本" : "待比较"}</small>`;
      card.addEventListener("click", () => {
        reviewNotice = `${candidate.label || "候选"} 已设为当前查看对象。`;
        reviewError = "";
        if (snapshot.reviewDelivery?.candidates) snapshot.reviewDelivery = focusReviewCandidate(snapshot.reviewDelivery, candidate.candidate_id);
        render();
      });
      list.appendChild(card);
    }
    panel.appendChild(list);
    panel.appendChild(buildReviewLineage(reviewState));
    return panel;
  }

  function buildReviewLineage(reviewState) {
    const details = node("details", "studio-review-lineage");
    const summary = node("summary", "", "查看版本沿革");
    const list = node("ol");
    for (const item of reviewState.lineage || []) {
      const row = node("li", "", item.label || "制作记录已更新");
      list.appendChild(row);
    }
    if (!list.children.length) list.appendChild(node("li", "", "尚未形成版本沿革。"));
    details.append(summary, list);
    return details;
  }

  function buildReviewActionPanel(reviewState) {
    const panel = node("aside", "studio-review-actions");
    panel.setAttribute("aria-label", "审核决定与交付准备");
    panel.append(buildReviewFacts(reviewState), buildReviewAnnotation(), buildReviewChecklist(reviewState));
    const actions = node("div", "studio-review-action-grid");
    actions.append(
      reviewActionButton("select", "选为当前版本", reviewCanSelect(reviewState)),
      reviewActionButton("revise", "要求返修", reviewCanRevise(reviewState)),
      reviewActionButton("reject", "退回候选", Boolean(reviewState.reviewSnapshot)),
      reviewActionButton("approve", reviewState.quality?.approved ? "质量门禁已通过" : "批准当前修订", reviewCanApprove(reviewState)),
      reviewActionButton("export", reviewState.exports.length ? "再次生成交付包" : "生成交付包", reviewCanExport(reviewState)),
    );
    panel.appendChild(actions);
    return panel;
  }

  function buildReviewFacts(reviewState) {
    const facts = node("section", "studio-review-surface");
    facts.appendChild(node("h2", "", "交付状态"));
    const selected = reviewState.candidates.find((item) => item.candidate_id === reviewState.selectedCandidateId);
    facts.append(
      reviewFact("当前方案", selected && !reviewState.rejected ? selected.label : "未选择"),
      reviewFact("质量门禁", reviewState.quality?.approved ? "已通过" : "待检查"),
      reviewFact("交付包", reviewState.exports.length ? `${reviewState.exports.length} 个` : "未生成"),
      reviewFact("恢复状态", reviewState.rejected ? "已退回，等待新修订" : "暂无可恢复版本"),
    );
    return facts;
  }

  function buildReviewAnnotation() {
    const surface = node("section", "studio-review-surface");
    surface.appendChild(node("h2", "", "本轮意见"));
    const label = node("label", "studio-review-note");
    label.appendChild(node("span", "", "给制作团队的修改说明"));
    const textarea = document.createElement("textarea");
    textarea.rows = 4;
    textarea.maxLength = 800;
    textarea.dataset.revisionNote = "true";
    textarea.placeholder = "例如：保留构图，降低背景亮度，让人物表情更清楚。";
    textarea.disabled = Boolean(reviewBusy);
    label.appendChild(textarea);
    surface.append(label, node("small", "", "说明只会随返修或退回决定保存。"));
    return surface;
  }

  function buildReviewChecklist(reviewState) {
    const surface = node("section", "studio-review-surface");
    surface.appendChild(node("h2", "", "交付检查"));
    const fieldset = node("fieldset", "studio-review-checklist");
    fieldset.disabled = Boolean(reviewBusy || !reviewCanApprove(reviewState) || reviewState.quality?.approved);
    const legend = node("legend", "sr-only", "质量门禁检查项");
    fieldset.appendChild(legend);
    for (const [name, title, copy, key] of REVIEW_QUALITY_FIELDS) {
      const row = node("label", "studio-review-check");
      const input = document.createElement("input");
      input.type = "checkbox";
      input.dataset.qualityCheck = name;
      input.checked = reviewState.quality?.[key] === "passed";
      const text = node("span");
      text.append(node("strong", "", title), node("small", "", copy));
      row.append(input, text, node("em", "", input.checked ? "已检查" : "未检查"));
      fieldset.appendChild(row);
    }
    surface.append(fieldset, node("small", "", "音频与字幕检查未接入时保持不可用，不会显示为通过。"));
    return surface;
  }

  function currentReviewState() {
    return snapshot.reviewDelivery || {
      phase: "empty",
      candidates: [],
      selectedCandidateId: "",
      focusedCandidateId: "",
      reviewSnapshot: null,
      deliverySnapshot: null,
      quality: null,
      exports: [],
      lineage: [],
    };
  }

  function reviewStatusLabel(reviewState) {
    if (reviewState.phase === "ready") return reviewState.quality?.approved ? "交付可复核" : "等待审核";
    if (reviewState.phase === "empty") return "暂无制作版本";
    return "读取受限";
  }

  function reviewSelectedCandidate(reviewState) {
    return reviewState.candidates?.find((item) => item.candidate_id === reviewState.selectedCandidateId) || null;
  }

  function reviewFocusedCandidate(reviewState) {
    return reviewState.candidates?.find((item) => item.candidate_id === reviewState.focusedCandidateId) || null;
  }

  function reviewCanSelect(reviewState) {
    return Boolean(reviewState.reviewSnapshot && reviewFocusedCandidate(reviewState)?.available);
  }

  function reviewCanRevise(reviewState) {
    return Boolean(reviewState.reviewSnapshot && reviewState.selectedCandidateId && reviewFocusedCandidate(reviewState)?.available);
  }

  function reviewCanApprove(reviewState) {
    return Boolean(reviewSelectedCandidate(reviewState)?.available && selectedDeliverySubmission(reviewState) && !reviewState.quality?.approved);
  }

  function reviewCanExport(reviewState) {
    return Boolean(reviewSelectedCandidate(reviewState)?.available && selectedDeliverySubmission(reviewState) && reviewState.quality?.approved);
  }

  function reviewFact(label, value) {
    const row = node("div", "studio-review-fact");
    row.append(node("span", "", label), node("strong", "", value));
    return row;
  }

  function projectSummaryShell(item) {
    return {
      project_id: item.project_id || "",
      name: item.name || item.studio_state_meta?.projectName || "未命名项目",
      episode: item.episode || "未创建分集",
      current_stage: "正在切换项目",
      progress_percent: 0,
      decision_inbox: { pending_count: 0 },
      crew: { blocked_count: 0 },
    };
  }

  function reviewSuccessMessage(action) {
    return ({
      select: "当前方案已保存，并已读取最新版本。",
      revise: "返修要求已保存，并已读取最新版本。",
      reject: "退回决定已保存，批准与导出已撤销。",
      approve: "当前修订的质量门禁已通过。",
      export: "交付包已生成，并已读取交付记录。",
    })[action] || "状态已更新。";
  }

  function reviewWriteError(result) {
    if (["auth_required", "delivery_auth_required"].includes(result?.code)) return "账户状态已变化，请重新登录后继续。";
    if (result?.code === "missing_revision_intent") return "请先写明修改原因。";
    if (result?.code === "delivery_checklist_incomplete") return "请完成所有可用的交付检查。";
    if (result?.stale) return result.message || "版本已发生变化，请读取最新状态后重试。";
    return result?.message || "这次操作没有保存。请读取最新状态后重试。";
  }

  function reviewActionButton(action, label, enabled) {
    const button = node("button", action === "reject" ? "studio-danger-button" : action === "select" || action === "approve" ? "studio-primary-button" : "studio-secondary-button", label);
    button.type = "button";
    button.disabled = Boolean(reviewBusy || !enabled);
    button.setAttribute("aria-disabled", String(button.disabled));
    button.addEventListener("click", () => handleReviewAction(action));
    return button;
  }

  async function handleReviewAction(action) {
    const reviewState = currentReviewState();
    if (!reviewState || reviewState.phase !== "ready" || reviewBusy) return;
    const note = String(document.querySelector("[data-revision-note]")?.value || "").trim();
    const checklist = Object.fromEntries([...document.querySelectorAll("[data-quality-check]")].map((input) => [input.dataset.qualityCheck, input.checked === true]));
    if (["revise", "reject"].includes(action) && !note) {
      reviewError = "请先写明修改原因，再提交这次主创决定。";
      document.querySelector("[data-revision-note]")?.focus();
      render();
      return;
    }
    if (action === "approve" && Object.values(checklist).some((checked) => checked !== true)) {
      reviewError = "请逐项完成叙事、画面一致性、镜头覆盖与改版要求检查。";
      document.querySelector("[data-quality-check]:not(:checked)")?.focus();
      render();
      return;
    }
    if (["approve", "export"].includes(action) && !selectedDeliverySubmission(reviewState)) {
      reviewError = "当前交付版本与权威选择不一致，请读取最新状态。";
      render();
      return;
    }
    reviewBusy = action;
    reviewNotice = "";
    reviewError = "";
    render();
    const result = await options.onReviewAction?.(action, { state: reviewState, note, checklist });
    reviewBusy = "";
    if (result?.ok) {
      reviewNotice = reviewSuccessMessage(action);
      reviewError = "";
      await options.onRefreshReview?.();
      if (reviewNotice) {
        const messageText = reviewNotice;
        reviewNotice = messageText;
        render();
      }
      return;
    }
    reviewError = reviewWriteError(result);
    render();
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
      ["当前场景", currentScene().name, "事实"],
      ["当前镜头", currentShot().title, "事实"],
    ];
    if (selection.shotIndex > 0) {
      refs.push(["相邻镜头", currentScene().shots[selection.shotIndex - 1].title, "上下文"]);
    }
    for (const [type, title, meta] of refs) {
      const item = node("article", "director-reference-item");
      item.append(node("span", "", icon("image", 15)), node("div", "", `<small>${escapeHtml(type)}</small><strong>${escapeHtml(title)}</strong>`), node("span", "", meta));
      item.children[1].innerHTML = `<small>${escapeHtml(type)}</small><strong>${escapeHtml(title)}</strong>`;
      body.appendChild(item);
    }
    body.appendChild(node("p", "director-note", "当前没有可验证的 ReferenceSet 或候选素材版本；AI 导演只使用项目、场景与镜头上下文。"));
    return body;
  }

  function buildDirectorVersions() {
    const body = node("div", "director-body director-version-panel");
    if (!hasStoryFacts()) {
      body.appendChild(node("p", "director-note", "还没有可恢复的故事版本；确认创作简报后才会产生版本记录。"));
      return body;
    }
    body.appendChild(node("p", "director-note", "还没有已确认版本、恢复点或可恢复候选。当前仅保存草稿；审核与导出能力正在合并到统一 Studio。"));
    const recovery = node("button", "studio-secondary-button", "暂无可恢复版本");
    recovery.type = "button";
    recovery.disabled = true;
    recovery.setAttribute("aria-disabled", "true");
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
        if (key === "storyboard") {
          showOverview();
          return;
        }
        if (key === "review") {
          showReview();
          requestAnimationFrame(() => document.getElementById("product-main")?.focus());
          return;
        }
        section = key;
        if (key === "context") cockpitOpen = true;
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
    button.addEventListener("click", () => {
      if (key === "canvas") openCanvas();
      else if (key === "review") showReview();
      else showOverview();
    });
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

  function syncSelectionFromCanvasNode(nodeId, { renderAfter = true } = {}) {
    const target = findShotSelectionByNodeId(nodeId);
    if (!target) return false;
    if (selection.sceneIndex === target.sceneIndex && selection.shotIndex === target.shotIndex) return true;
    selection = { sceneIndex: target.sceneIndex, shotIndex: target.shotIndex };
    directorTab = "suggestion";
    notice = "";
    if (renderAfter) render();
    return true;
  }

  function findShotSelectionByNodeId(nodeId) {
    const targetId = String(nodeId || "");
    if (!targetId) return null;
    const scenes = sceneModel();
    for (let sceneIndex = 0; sceneIndex < scenes.length; sceneIndex += 1) {
      const shotIndex = scenes[sceneIndex].shots.findIndex((shot) => shot.nodeId === targetId);
      if (shotIndex >= 0) return { sceneIndex, shotIndex };
    }
    return null;
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
      let reviewDelivery = null;
      if (activeProjectId) {
        const projectRuntime = activeProjectId === requestRuntime.projectId ? requestRuntime : options.createRuntime?.(activeProjectId);
        const [payload, runsPayload] = await Promise.all([
          projectRuntime?.projectOverview?.(),
          projectRuntime?.listProductionRuns?.().catch(() => ({ production_runs: [] })),
        ]);
        if (options.isRuntimeCurrent && !options.isRuntimeCurrent(requestRuntime)) return;
        project = payload?.project || null;
        reviewDelivery = composeReviewDeliveryState({ workspace, project, runsPayload, projectId: activeProjectId });
      }
      snapshot = { loading: false, workspace, project, reviewDelivery, error: "", authUser, studioState: options.getStudioState?.() || snapshot.studioState };
    } catch (error) {
      if (options.isRuntimeCurrent && !options.isRuntimeCurrent(requestRuntime)) return;
      snapshot = { ...snapshot, loading: false, project: null, error: options.formatError?.(error) || message("error", locale), authUser };
    }
    render();
  }

  function updateStudioState(studioState) {
    snapshot = { ...snapshot, studioState };
    syncSelectionFromStudioState(studioState);
    if (document.getElementById("app")?.classList.contains("product-mode")) render();
  }

  function syncSelectionFromStudioState(studioState) {
    const nodeIds = studioState?.selection?.nodeIds;
    if (!Array.isArray(nodeIds) || nodeIds.length !== 1) return false;
    return syncSelectionFromCanvasNode(nodeIds[0], { renderAfter: false });
  }

  function showOverview() {
    section = "storyboard";
    mobileDirectorOpen = false;
    syncSectionUrl("storyboard");
    render();
  }

  function showCanvas() {
    if (!options.getCanvasShell?.()) return false;
    section = "canvas";
    syncCanvasSelection();
    syncSectionUrl("canvas");
    render();
    return true;
  }

  function showReview({ noticeText = "" } = {}) {
    section = "review";
    directorTab = "version";
    directorCollapsed = false;
    mobileDirectorOpen = false;
    if (noticeText) notice = noticeText;
    syncSectionUrl("review");
    render();
  }

  function syncSectionUrl(next) {
    try {
      const url = new URL(window.location.href);
      if (next === "review") url.searchParams.set("stage", "review");
      else if (next === "canvas") url.searchParams.set("stage", "canvas");
      else if (["review", "canvas"].includes(url.searchParams.get("stage"))) url.searchParams.delete("stage");
      window.history.replaceState({}, "", url.toString());
    } catch {
      // URL synchronization is best-effort; the Studio state remains authoritative.
    }
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
    showReview,
    syncSelectionFromCanvasNode,
    setSection(next) {
      if (next === "canvas") return openCanvas();
      if (next === "review") return showReview();
      return showOverview();
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
