import { loadEpisodeAggregate } from "./api-client.mjs";
import {
  activeShot,
  availableAction,
  buildWorkspaceModel,
  createInitialUiState,
  exactRefKey,
  groupShotsByScene,
  inspectShot,
  nextShot,
  selectMode,
  selectSceneFilter,
  selectStatusFilter,
  shouldShowCurrentVersusNext,
  visibleShots,
} from "./state.mjs";

const app = document.querySelector("#app");
const projectId = new URLSearchParams(window.location.search).get("project");
let model = null;
let ui = null;
let resetDialog = null;

const icons = {
  chevron: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m9 18 6-6-6-6"/></svg>',
  lock: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="5" y="10" width="14" height="10" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>',
  shield: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 4.5 6v5.5c0 4.6 3.1 7.8 7.5 9.5 4.4-1.7 7.5-4.9 7.5-9.5V6L12 3Z"/><path d="m9 12 2 2 4-4"/></svg>',
  issue: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4 3 20h18L12 4Z"/><path d="M12 9v5M12 17h.01"/></svg>',
  spark: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3Z"/><path d="m18.5 16 .7 2.3 2.3.7-2.3.7-.7 2.3-.7-2.3-2.3-.7 2.3-.7.7-2.3Z"/></svg>',
};

function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}

function safeThumbnail(url) {
  if (typeof url !== "string") return "";
  if (url.startsWith("data:image/") || url.startsWith("/")) return url;
  try {
    const parsed = new URL(url, window.location.origin);
    return parsed.origin === window.location.origin ? parsed.href : "";
  } catch {
    return "";
  }
}

function lifecycleLabel(shot) {
  if (shot.delivery_invalid) return ["交付失效", "danger"];
  if (shot.production_state === "rework") return ["返工中", "danger"];
  if (shot.lifecycle_state === "locked") return ["已锁定", "success"];
  if (shot.selection_state === "selected") return ["已选候选", "success"];
  if (shot.review_state === "needs_review") return ["人类待审", "warning"];
  if (shot.ai_check_state === "passed") return ["AI 检测通过", "info"];
  return [shot.status_label || "待完善", "neutral"];
}

function renderState(kind, title, message, action = "") {
  app.innerHTML = `<main class="empty-state ${escapeHtml(kind)}">
    <div class="brand-mark" aria-hidden="true">雨</div>
    <h1>${escapeHtml(title)}</h1>
    <p>${escapeHtml(message)}</p>
    ${action}
  </main>`;
}

function renderLoading() {
  renderState("loading", "正在恢复上次的制作现场", "正在读取项目事实与已保存的检查点…");
  app.querySelector("main").setAttribute("aria-busy", "true");
}

function renderError(error) {
  const authAction = error?.kind === "auth" ? '<a class="primary-button" href="/login">重新登录</a>' : '<button class="primary-button" type="button" data-action="retry">重试</button>';
  renderState("error", error?.kind === "auth" ? "需要重新登录" : "未能打开制作工作区", error?.message || "项目暂时无法读取。", authAction);
  app.querySelector('[data-action="retry"]')?.addEventListener("click", hydrate);
}

function renderMissingProject() {
  renderState("empty", "从一个项目开始", "请从项目页进入具体单集，工作区将恢复你上次的检查点。", '<a class="primary-button" href="/projects">返回项目</a>');
}

function statusDot(tone) {
  return `<span class="status-dot ${tone}" aria-hidden="true"></span>`;
}

function renderTopbar(current, suggested) {
  const isPrivate = model.project.policy.visibility === "private";
  const noTraining = model.project.policy.training_use === "denied_by_default";
  return `<header class="topbar">
    <div class="identity">
      <div class="brand-mark compact" aria-hidden="true">雨</div>
      <div class="project-copy"><strong>${escapeHtml(model.project.title)}</strong><span>${escapeHtml(model.episode.title)}</span></div>
    </div>
    <nav class="mode-tabs" aria-label="单集工作模式">
      ${[["storyboard", "故事板"], ["review", "审核"], ["delivery", "交付"]].map(([mode, label]) => `<button type="button" data-mode="${mode}" aria-current="${ui.mode === mode ? "page" : "false"}">${label}</button>`).join("")}
    </nav>
    <div class="top-status">
      <span class="save-state">${icons.shield}<span>已恢复 · 当前只读</span></span>
      <span class="privacy-state">${icons.lock}<span>${isPrivate ? "私有" : "项目可见"} · ${noTraining ? "不用于训练" : "按项目设置使用"}</span></span>
      <button class="next-action" type="button" data-action="go-next"><span>建议下一步</span><strong>${escapeHtml(model.nextAction.label)}</strong>${icons.chevron}</button>
    </div>
    <div class="mobile-context">
      <span>当前查看：镜头 ${current.sequence}</span>
      <button type="button" data-action="open-mobile-nav">镜头与问题</button>
    </div>
  </header>`;
}

function sceneIssueCount(scene) {
  return model.shots.filter((shot) => exactRefKey(shot.scene_ref) === exactRefKey(scene.ref) && shot.blocking).length;
}

function renderLeftRail() {
  const filters = [["all", "全部镜头"], ["blocking", "阻断项"], ["needs_review", "待审核"], ["rework", "返工中"]];
  return `<aside class="left-rail" aria-label="场景与问题导航">
    <div class="rail-heading"><h2>场景</h2><span>${model.scenes.length}</span></div>
    <button class="scene-row" type="button" data-scene="all" aria-pressed="${ui.sceneFilterKey === "all"}"><span>全部场景</span><strong>${model.shots.length}</strong></button>
    ${model.scenes.map((scene) => `<button class="scene-row" type="button" data-scene="${escapeHtml(exactRefKey(scene.ref))}" aria-pressed="${ui.sceneFilterKey === exactRefKey(scene.ref)}"><span><small>场景 ${scene.sequence}</small>${escapeHtml(scene.title)}</span><strong>${sceneIssueCount(scene) || ""}</strong></button>`).join("")}
    <div class="rail-heading issue-heading"><h2>定位</h2></div>
    <div class="filter-list">
      ${filters.map(([filter, label]) => `<button type="button" data-filter="${filter}" aria-pressed="${ui.statusFilter === filter}"><span>${filter === "blocking" ? icons.issue : ""}${label}</span><strong>${filter === "all" ? model.shots.length : model.shots.filter((shot) => filter === "blocking" ? shot.blocking : filter === "needs_review" ? shot.review_state === "needs_review" : shot.production_state === "rework").length}</strong></button>`).join("")}
    </div>
    <button class="reset-link" type="button" data-action="reset-recovery">清除本次恢复位置</button>
  </aside>`;
}

function renderShotCard(shot) {
  const [label, tone] = lifecycleLabel(shot);
  const selected = exactRefKey(shot.ref) === ui.activeShotKey;
  const isNext = exactRefKey(shot.ref) === ui.nextShotKey;
  const thumbnail = safeThumbnail(shot.thumbnail_url);
  return `<button class="shot-card" type="button" data-shot="${escapeHtml(exactRefKey(shot.ref))}" aria-pressed="${selected}" ${isNext ? 'data-next="true"' : ""}>
    <span class="frame">
      ${thumbnail ? `<img src="${escapeHtml(thumbnail)}" alt="" />` : '<span class="no-media">暂无候选素材</span>'}
      <strong class="shot-number">${String(shot.sequence).padStart(2, "0")}</strong>
      <span class="duration">${Number(shot.duration_seconds || 0).toFixed(0)}s</span>
      ${shot.blocking ? `<span class="frame-issue" aria-label="存在阻断问题">${icons.issue}</span>` : ""}
    </span>
    <span class="card-meta"><span>${statusDot(tone)}${escapeHtml(label)}</span>${isNext ? "<strong>下一步</strong>" : ""}</span>
    <span class="card-script">${escapeHtml(shot.script?.visual_action || "暂无镜头脚本")}</span>
  </button>`;
}

function renderStoryboard() {
  const shots = visibleShots(model, ui);
  const groups = groupShotsByScene(model, shots);
  if (!groups.length) return '<section class="workspace-empty"><h2>没有符合条件的镜头</h2><p>试试更换场景或问题筛选。</p></section>';
  return `<section class="storyboard" aria-label="故事板镜头工作面">
    ${groups.map(({ scene, shots: groupShots }) => `<section class="scene-group" data-scene-group="${escapeHtml(exactRefKey(scene.ref))}">
      <header><div><span>场景 ${scene.sequence}</span><h2>${escapeHtml(scene.title)}</h2></div><p>${groupShots.length} 个镜头</p></header>
      <div class="shot-grid">${groupShots.map(renderShotCard).join("")}</div>
    </section>`).join("")}
  </section>`;
}

function renderReviewMode() {
  const shot = activeShot(model, ui);
  return `<section class="focused-mode"><header><span>同一镜头事实</span><h2>镜头 ${shot.sequence} · 审核</h2><p>评论、人工判断和修改请求都记录在当前精确版本上。</p></header><div class="review-sheet"><div><h3>审核状态</h3><p>${escapeHtml(lifecycleLabel(shot)[0])}</p></div><div><h3>镜头脚本</h3><p>${escapeHtml(shot.script?.visual_action || "暂无脚本")}</p></div><div><h3>审核意见</h3><p>${escapeHtml(shot.review_note || "暂无审核意见。")}</p></div></div></section>`;
}

function renderDeliveryMode() {
  const missing = Number(model.delivery.missing_asset_count ?? model.truth.missing_asset_count ?? 0);
  const playable = model.delivery.playable_preview_available === true || model.truth.playable_preview_available === true;
  return `<section class="focused-mode delivery-mode"><header><span>交付状态</span><h2>${playable ? "可以检查预览" : "暂时无法生成可播放预览"}</h2><p>${missing ? `仍缺少 ${missing} 项素材。请先完成镜头选版、审核与锁定。` : "镜头事实已齐备，可进入预览检查。"}</p></header><div class="delivery-sheet"><div><strong>${missing}</strong><span>缺少素材</span></div><div><strong>${model.truth.generation_dispatch_count ?? 0}</strong><span>已开始生成任务</span></div><div><strong>${playable ? "可用" : "不可用"}</strong><span>可播放预览</span></div></div><button class="primary-button" type="button" disabled>冻结交付版本</button></section>`;
}

function renderCenter() {
  const current = activeShot(model, ui);
  const suggested = nextShot(model, ui);
  return `<main class="center-stage">
    <div class="stage-heading">
      <div><span>${ui.mode === "storyboard" ? "单集制作" : ui.mode === "review" ? "镜头审核" : "交付准备"}</span><h1>${ui.mode === "storyboard" ? "故事板" : ui.mode === "review" ? `镜头 ${current.sequence} 审核` : "单集交付"}</h1></div>
      <div class="focus-context"><span>当前查看：镜头 ${current.sequence}</span>${shouldShowCurrentVersusNext(ui) ? `<button type="button" data-action="go-next">建议下一步：镜头 ${suggested.sequence}</button>` : `<strong>与建议下一步一致</strong>`}</div>
    </div>
    ${model.recovery ? `<div class="recovery-bar"><span>已恢复：${escapeHtml(model.recovery.label || "上次工作位置")}</span>${Number.isInteger(model.recovery.reconfirmed_count) ? `<strong>${model.recovery.reconfirmed_count}/${model.recovery.reconfirmed_total} 项已确认</strong>` : ""}</div>` : ""}
    ${ui.mode === "storyboard" ? renderStoryboard() : ui.mode === "review" ? renderReviewMode() : renderDeliveryMode()}
  </main>`;
}

function renderFacts(shot) {
  if (!shot.facts?.length) return '<p class="muted">当前镜头没有额外的连续性要点。</p>';
  return `<dl class="fact-list">${shot.facts.map((fact) => `<div><dt>${escapeHtml(fact.label)}</dt><dd>${escapeHtml(fact.value)}${fact.status === "conflict" ? '<span class="fact-conflict">不一致</span>' : ""}</dd></div>`).join("")}</dl>`;
}

function renderCandidates(shot) {
  if (!shot.candidates?.length) return '<p class="muted">还没有可比较的候选版本。</p>';
  const adopt = availableAction(shot, "adopt_candidate");
  const reason = adopt.enabled ? "本页当前只读，修改与保存尚未开放。" : adopt.reason;
  return `<div class="candidate-list">${shot.candidates.map((candidate) => `<article><header><strong>${escapeHtml(candidate.label)}</strong><span>${escapeHtml(candidate.status_label || "候选")}</span></header><p>${escapeHtml(candidate.summary || "无额外说明")}</p></article>`).join("")}</div><button class="inspector-action" type="button" disabled>暂不能采用</button><p class="action-reason">${escapeHtml(reason || "当前状态不允许这项操作。")}</p>`;
}

function renderProposal(shot) {
  const proposal = shot.agent_proposal;
  if (!proposal) return "";
  return `<section class="proposal"><header>${icons.spark}<div><strong>${escapeHtml(proposal.title || "制作建议")}</strong><span>仅影响当前对象</span></div></header><p>${escapeHtml(proposal.summary || "")}</p>${proposal.declared_impact_count != null ? `<div class="proposal-scope"><span>预计影响 ${proposal.declared_impact_count} 个镜头</span><span>实际已应用 ${proposal.applied_count || 0} 个</span></div>` : ""}<div class="proposal-actions"><button type="button" disabled>预览影响</button><button type="button" disabled>拒绝</button></div><p class="action-reason">本页当前只读，建议操作尚未开放。</p></section>`;
}

function renderInspector() {
  const shot = activeShot(model, ui);
  const [label, tone] = lifecycleLabel(shot);
  return `<aside class="inspector" aria-label="当前镜头上下文">
    <header class="inspector-heading"><div><button class="mobile-back" type="button" data-action="back-to-shots">返回镜头列表</button><span>当前查看</span><h2>镜头 ${shot.sequence}</h2></div><span class="shot-status">${statusDot(tone)}${escapeHtml(label)}</span></header>
    <section><h3>脚本</h3><p class="script-copy">${escapeHtml(shot.script?.visual_action || "暂无镜头脚本")}</p>${shot.script?.dialogue?.map((line) => `<p class="dialogue"><strong>${escapeHtml(line.speaker)}</strong>${escapeHtml(line.text)}</p>`).join("") || ""}</section>
    <section><div class="section-title"><h3>角色与场景事实</h3><span>来自当前精确版本</span></div>${renderFacts(shot)}</section>
    ${shot.continuity_issue ? `<section class="continuity-alert"><header>${icons.issue}<div><h3>连续性需要处理</h3><p>${escapeHtml(shot.continuity_issue.summary)}</p></div></header><div class="impact-scope"><span>预计影响：${escapeHtml(String(shot.continuity_issue.declared_impact_count ?? 0))}</span><span>实际已应用：${escapeHtml(String(shot.continuity_issue.applied_count ?? 0))}</span></div></section>` : ""}
    <section><div class="section-title"><h3>候选与版本</h3><span>仅当前镜头</span></div>${renderCandidates(shot)}</section>
    ${renderProposal(shot)}
  </aside>`;
}

function renderResetDialog() {
  return `<dialog class="confirm-dialog" aria-labelledby="reset-title"><form method="dialog"><h2 id="reset-title">清除本次恢复位置？</h2><p>下次进入时将回到建议下一步。项目事实和已审核版本不会被删除。</p><p class="dialog-dependency">本页当前只读，清除操作尚未开放。</p><div><button value="cancel">取消</button><button class="danger-button" value="confirm" disabled>确认清除</button></div></form></dialog>`;
}

function bindEvents() {
  app.querySelectorAll("[data-mode]").forEach((button) => button.addEventListener("click", () => { ui = selectMode(ui, button.dataset.mode); render(); }));
  app.querySelectorAll("[data-shot]").forEach((button) => button.addEventListener("click", () => {
    const shot = model.shots.find((item) => exactRefKey(item.ref) === button.dataset.shot);
    if (shot) {
      ui = inspectShot(ui, shot.ref); render();
      if (window.matchMedia("(max-width: 760px)").matches) {
        requestAnimationFrame(() => app.querySelector(".inspector")?.scrollIntoView({ block: "start" }));
      }
    }
  }));
  app.querySelectorAll("[data-scene]").forEach((button) => button.addEventListener("click", () => {
    const scene = model.scenes.find((item) => exactRefKey(item.ref) === button.dataset.scene);
    ui = selectSceneFilter(ui, scene?.ref || "all"); render();
  }));
  app.querySelectorAll("[data-filter]").forEach((button) => button.addEventListener("click", () => { ui = selectStatusFilter(ui, button.dataset.filter); render(); }));
  app.querySelectorAll('[data-action="go-next"]').forEach((button) => button.addEventListener("click", () => {
    const suggested = nextShot(model, ui); ui = inspectShot(ui, suggested.ref); render();
    requestAnimationFrame(() => app.querySelector('[data-shot][data-next="true"]')?.focus());
  }));
  app.querySelector('[data-action="open-mobile-nav"]')?.addEventListener("click", () => app.querySelector(".center-stage")?.scrollIntoView({ block: "start" }));
  app.querySelector('[data-action="back-to-shots"]')?.addEventListener("click", () => app.querySelector(".center-stage")?.scrollIntoView({ block: "start" }));
  app.querySelector('[data-action="reset-recovery"]')?.addEventListener("click", () => resetDialog.showModal());
}

function restoreViewport() {
  const shot = nextShot(model, ui);
  const target = app.querySelector(`[data-shot="${CSS.escape(exactRefKey(shot.ref))}"]`);
  if (target && model.recovery?.scroll_to_active) target.scrollIntoView({ block: "center" });
  if (target && model.recovery?.focus_active) target.focus({ preventScroll: true });
}

function render() {
  const current = activeShot(model, ui);
  const suggested = nextShot(model, ui);
  app.innerHTML = `<div class="workspace-shell">
    ${model.evidenceEnvironment === "test" ? '<div class="evidence-banner" role="status">测试证据环境 · 不代表真实生产数据</div>' : ""}
    ${renderTopbar(current, suggested)}
    <div class="workspace-layout">${renderLeftRail()}${renderCenter()}${renderInspector()}</div>
    <footer><span id="workspace-status" tabindex="-1">项目事实已从服务恢复</span><span>${model.delivery.missing_asset_count ?? model.truth.missing_asset_count ?? 0} 项素材仍缺失 · ${model.truth.playable_preview_available ? "可检查预览" : "暂无可播放预览"}</span></footer>
    ${renderResetDialog()}
  </div>`;
  resetDialog = app.querySelector("dialog");
  bindEvents();
}

async function hydrate() {
  if (!projectId) { renderMissingProject(); return; }
  renderLoading();
  try {
    const payload = await loadEpisodeAggregate(projectId);
    model = buildWorkspaceModel(payload);
    ui = createInitialUiState(model);
    render();
    requestAnimationFrame(restoreViewport);
  } catch (error) {
    if (error?.name !== "AbortError") renderError(error);
  }
}

hydrate();
