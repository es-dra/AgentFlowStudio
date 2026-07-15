import { createRuntimeClient, saveAuthToken } from "../src/runtime-client.js";
import { icon } from "../src/icons.js";

const app = document.querySelector("#app");
const params = new URLSearchParams(window.location.search);

let projectId = safeProjectId(params.get("project")) || "";
let runtime = projectId ? createRuntimeClient(projectId) : createRuntimeClient();
let control = null;
let user = null;
let busy = false;
let notice = "";
let activeTab = params.get("view") || "mission";

const tabs = [
  ["mission", "使命"],
  ["plan", "计划"],
  ["cockpit", "驾驶舱"],
  ["artifacts", "产物"],
  ["review", "审核"],
];

function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" }[char]));
}

function safeProjectId(value) {
  return String(value || "").trim().replace(/[^A-Za-z0-9_.-]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 80);
}

function commandKey(prefix) {
  const raw = `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2, 10)}`;
  return raw.replace(/[^A-Za-z0-9_.:-]+/g, "-");
}

function setProject(nextProjectId) {
  projectId = safeProjectId(nextProjectId);
  runtime = createRuntimeClient(projectId || "production-control");
  const url = new URL(window.location.href);
  if (projectId) url.searchParams.set("project", projectId);
  else url.searchParams.delete("project");
  window.history.replaceState({}, "", url);
}

function syncRouteState() {
  const url = new URL(window.location.href);
  if (projectId) url.searchParams.set("project", projectId);
  if (activeTab) url.searchParams.set("view", activeTab);
  window.history.replaceState({}, "", url);
}

function statusLabel(value) {
  return {
    missing: "未开始",
    recorded: "已记录",
    proposed: "待批准",
    approved: "已批准",
    running: "运行中",
    queued: "排队",
    "waiting-human": "等待人工",
    retrying: "重试中",
    blocked: "阻塞",
    completed: "完成",
    cancelled: "取消",
    active: "可执行",
    paused: "暂停",
    "pause-requested": "暂停中",
    "resume-requested": "恢复中",
    "cancel-requested": "取消中",
  }[value] || value || "未知";
}

function toneForRun(run) {
  if (run.execution_state === "completed") return "ok";
  if (run.execution_state === "waiting-human" || run.blocked) return "warn";
  if (run.control_state === "paused" || run.execution_state === "retrying") return "hold";
  if (run.execution_state === "cancelled") return "danger";
  return "live";
}

function renderShell(content) {
  app.innerHTML = `<div class="pc-shell">
    <header class="pc-topbar">
      <a class="brand" href="/studio/">${icon("grid", 18)}<span>AFS Studio</span></a>
      <nav class="surface-links" aria-label="Studio routes">
        <a href="/studio/">画布</a>
        <a href="${escapeHtml(control?.workspace_entry?.href || "#")}" ${control?.version ? "" : "aria-disabled=\"true\""}>故事板 / 审核</a>
      </nav>
      <div class="session">${user ? `<span>${escapeHtml(user.display_name || user.email || "账号")}</span><button type="button" data-action="logout">${icon("user", 15)}退出</button>` : ""}</div>
    </header>
    ${content}
  </div>`;
  bindGlobal();
}

function renderLoading(message = "正在读取生产控制事实…") {
  renderShell(`<main class="state-screen"><div class="mark">${icon("bolt", 30)}</div><h1>${escapeHtml(message)}</h1></main>`);
}

function renderAuth(status = {}) {
  const invite = status.invite_registration_available
    ? '<label>邀请码<input name="invite_code" autocomplete="one-time-code" /></label>'
    : "";
  renderShell(`<main class="auth-grid">
    <section class="auth-panel">
      <h1>登录生产控制</h1>
      <form data-form="login">
        <label>邮箱<input name="email" type="email" autocomplete="email" required /></label>
        <label>密码<input name="password" type="password" autocomplete="current-password" required /></label>
        <button type="submit" class="primary">${icon("play", 16)}登录</button>
      </form>
    </section>
    <section class="auth-panel muted-panel">
      <h2>创建内部账号</h2>
      <form data-form="register">
        <label>邮箱<input name="email" type="email" autocomplete="email" required /></label>
        <label>显示名<input name="display_name" autocomplete="name" /></label>
        <label>密码<input name="password" type="password" autocomplete="new-password" required /></label>
        ${invite}
        <button type="submit">${icon("plus", 16)}注册并进入</button>
      </form>
    </section>
  </main>`);
  app.querySelector('[data-form="login"]')?.addEventListener("submit", onLogin);
  app.querySelector('[data-form="register"]')?.addEventListener("submit", onRegister);
}

function renderProjectSetup() {
  renderShell(`<main class="state-screen project-setup">
    <div class="mark">${icon("folder", 28)}</div>
    <h1>新建生产控制项目</h1>
    <form data-form="project">
      <label>项目名称<input name="goal" value="AI-native production control vertical slice" maxlength="120" required /></label>
      <button type="submit" class="primary">${icon("plus", 16)}创建项目</button>
    </form>
  </main>`);
  app.querySelector('[data-form="project"]')?.addEventListener("submit", onCreateProject);
}

function renderApp() {
  if (!control) {
    renderProjectSetup();
    return;
  }
  syncRouteState();
  const content = `<div class="pc-app">
    <aside class="pc-sidebar">
      <div class="pc-title">
        <span class="mark">${icon("bolt", 22)}</span>
        <div><strong>生产控制</strong><small>${statusLabel(control.plan.status)}</small></div>
      </div>
      <nav class="tabs">${tabs.map(([key, label]) => `<button type="button" data-tab="${key}" aria-current="${activeTab === key ? "page" : "false"}">${label}</button>`).join("")}</nav>
      <div class="ledger-box">
        <span>事件账本</span>
        <strong>v${control.version}</strong>
        <small>${control.event_count} 个事件 · ${control.outbox_count} 个待投递</small>
        <button type="button" data-action="rebuild">${icon("retry", 14)}重建校验</button>
      </div>
    </aside>
    <main class="pc-main">
      ${renderHeader()}
      ${renderActiveTab()}
    </main>
    <aside class="agent-rail">
      ${renderAgentRail()}
    </aside>
  </div>`;
  renderShell(content);
  bindApp();
}

function renderHeader() {
  const progress = control.runs.length
    ? Math.round((control.runs.filter((run) => run.execution_state === "completed").length / control.runs.length) * 100)
    : 0;
  return `<section class="overview-band">
    <div>
      <span class="eyeless">提供方已关闭 · 调度 ${control.provider_dispatch_count}</span>
      <h1>${control.mission.objective ? escapeHtml(control.mission.objective) : "使命等待记录"}</h1>
      <p>${notice ? escapeHtml(notice) : "所有控制命令写入同一条可重建事件账本。"}</p>
    </div>
    <div class="metrics" aria-label="生产摘要">
      <div><strong>${control.plan.task_specs.length || control.tasks.length}</strong><span>任务</span></div>
      <div><strong>${control.runs.length}</strong><span>运行</span></div>
      <div><strong>${progress}%</strong><span>进度</span></div>
      <div><strong>${control.artifacts.length}</strong><span>写回</span></div>
    </div>
  </section>`;
}

function renderActiveTab() {
  if (activeTab === "plan") return renderPlan();
  if (activeTab === "cockpit") return renderCockpit();
  if (activeTab === "artifacts") return renderArtifacts();
  if (activeTab === "review") return renderReview();
  return renderMission();
}

function renderMission() {
  const disabled = control.mission.status === "recorded";
  return `<section class="work-surface">
    <header><h2>使命</h2><p>${disabled ? "使命已进入账本。" : "定义本次生产目标与边界。"}</p></header>
    <form data-form="mission" class="mission-form">
      <label>目标<textarea name="objective" rows="5" ${disabled ? "disabled" : ""}>${escapeHtml(control.mission.objective || "制作一个无提供方调用的 AI-native 生产控制纵切，覆盖使命、计划、审批、运行、写回、连续性与交付读回。")}</textarea></label>
      <div class="constraint-grid">
        <label>边界 1<input name="constraint" ${disabled ? "disabled" : ""} value="提供方闸门保持关闭。" /></label>
        <label>边界 2<input name="constraint" ${disabled ? "disabled" : ""} value="镜头局部返工必须保留未受影响镜头事实。" /></label>
      </div>
      <button type="submit" class="primary" ${disabled || busy ? "disabled" : ""}>${icon("check", 16)}保存使命</button>
    </form>
  </section>`;
}

function renderPlan() {
  const approved = control.plan.status === "approved";
  const specs = control.plan.task_specs.length ? control.plan.task_specs : defaultTasks();
  return `<section class="work-surface">
    <header><h2>计划</h2><p>${approved ? "计划已批准并创建运行。" : "批准前可以编辑边界。"}</p></header>
    <form data-form="plan" class="plan-form">
      ${specs.map((task, index) => `<fieldset>
        <legend>${escapeHtml(task.title || `任务 ${index + 1}`)}</legend>
        <input name="title" value="${escapeHtml(task.title || `任务 ${index + 1}`)}" ${approved ? "disabled" : ""} />
        <textarea name="boundary" rows="3" ${approved ? "disabled" : ""}>${escapeHtml(task.boundary)}</textarea>
      </fieldset>`).join("")}
      <div class="form-actions">
        <button type="submit" ${approved || busy ? "disabled" : ""}>${icon("pencil", 16)}保存计划</button>
        <button type="button" class="primary" data-action="approve-plan" ${approved || !control.plan.task_specs.length || busy ? "disabled" : ""}>${icon("check", 16)}批准并启动</button>
      </div>
    </form>
  </section>`;
}

function renderCockpit() {
  if (!control.runs.length) return emptyPanel("驾驶舱", "批准计划后会出现运行队列。");
  return `<section class="run-board">
    ${control.runs.map((run, index) => `<article class="run-row ${toneForRun(run)}">
      <div class="run-main">
        <span class="run-index">${String(index + 1).padStart(2, "0")}</span>
        <div><h3>${escapeHtml(run.task_title)}</h3><p>${escapeHtml(run.boundary)}</p></div>
      </div>
      <div class="run-state">
        <strong>${statusLabel(run.execution_state)}</strong>
        <span>${statusLabel(run.control_state)} · 第 ${run.attempt_count} 次尝试</span>
        <small>${escapeHtml(run.simulated_cost_label)}</small>
      </div>
      <div class="run-actions" data-run="${escapeHtml(run.run_id)}">
        ${run.control_state === "paused"
          ? button("resume", "恢复", "play")
          : button("pause", "暂停", "clock")}
        ${button("retry", "重试", "retry")}
        ${run.waiting_human ? button("decide_human", "确认", "check") : button("waiting_human", "人工", "user")}
        ${run.blocked ? button("clear_blocker", "放行", "check") : button("block", "阻塞", "lock")}
        ${button("provider_gate", "闸门", "lock")}
        ${button("writeback", "写回", "bookmark")}
        ${button("complete", "完成", "check")}
      </div>
    </article>`).join("")}
  </section>`;
}

function renderArtifacts() {
  if (!control.artifacts.length) return emptyPanel("产物", "运行写回后会出现受影响与保护事实。");
  return `<section class="artifact-surface">
    <header><h2>产物</h2><p>写回使用追加命令，绑定来源任务、运行与尝试。</p></header>
    <div class="artifact-list">
      ${control.artifacts.map((artifact, index) => `<article>
        <strong>写回 ${index + 1}</strong>
        <p>${escapeHtml(operationLabel(artifact.operation))} · 来源 ${escapeHtml(taskName(artifact.task_id))}</p>
        <dl>
          <div><dt>受影响</dt><dd>${escapeHtml(refLabel(artifact.affected_ref))}</dd></div>
          <div><dt>保护</dt><dd>${artifact.protected_refs.map(refLabel).map(escapeHtml).join("、")}</dd></div>
          <div><dt>尝试</dt><dd>已记录尝试来源</dd></div>
        </dl>
      </article>`).join("")}
    </div>
  </section>`;
}

function renderReview() {
  const continuity = control.continuity;
  return `<section class="review-grid">
    <article>
      <h2>连续性</h2>
      <p>${continuity.shot_local_rework_protected ? "局部返工保护已记录。" : "等待写回保护证据。"}</p>
      <div class="fact-pills">
        <span>${continuity.affected_refs.length} 个受影响</span>
        <span>${continuity.protected_refs.length} 个受保护</span>
        <span>${continuity.impact_assessment_count} 个影响评估</span>
      </div>
    </article>
    <article>
      <h2>审核 / 交付</h2>
      <p>${control.review.delivery_readback === "internal_delivery_packet_ready" ? "交付读回可检查。" : "交付读回等待产物。"}</p>
      <a class="primary link-button" href="${escapeHtml(control.workspace_entry.href)}">${icon("frames", 16)}打开故事板 / 审核</a>
    </article>
    <article>
      <h2>非声明</h2>
      <ul>${control.review.non_claims.map((item) => `<li>${escapeHtml(nonClaimLabel(item))}</li>`).join("")}</ul>
    </article>
  </section>`;
}

function renderAgentRail() {
  const suggestions = [];
  if (control.mission.status !== "recorded") suggestions.push("先记录使命。");
  else if (!control.plan.task_specs.length) suggestions.push("生成三段式计划。");
  else if (control.plan.status !== "approved") suggestions.push("审批后会原子创建任务与运行。");
  else if (!control.artifacts.length) suggestions.push("选择一个运行执行追加写回。");
  else suggestions.push("检查审核 / 交付读回。");
  return `<section>
    <h2>确定性建议</h2>
    <p>提供方已关闭 · 没有 LLM 调用</p>
    <ol>${suggestions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>
  </section>
  <section>
    <h2>恢复</h2>
    <p>重新加载 / 重启后从事件账本重建。</p>
    <strong>${control.recovery.ledger_rebuildable ? "可重建" : "待检查"}</strong>
  </section>`;
}

function defaultTasks() {
  return [
    { title: "镜头拆解", boundary: "拆解使命为局部镜头与连续性检查。" },
    { title: "候选写回", boundary: "在提供方关闭状态下生成确定性候选与成本标签。" },
    { title: "审核交付", boundary: "汇总写回、连续性和交付读回证据。" },
  ];
}

function button(action, label, iconName) {
  return `<button type="button" data-run-action="${action}" ${busy ? "disabled" : ""}>${icon(iconName, 14)}${label}</button>`;
}

function emptyPanel(title, text) {
  return `<section class="work-surface empty-work"><header><h2>${escapeHtml(title)}</h2><p>${escapeHtml(text)}</p></header></section>`;
}

function taskName(taskId) {
  const spec = control.plan.task_specs.find((task) => task.task_id === taskId);
  return spec?.title || "任务";
}

function operationLabel(value) {
  return {
    shot_local_rework: "镜头局部返工",
    artifact_writeback: "产物写回",
  }[value] || "产物写回";
}

function nonClaimLabel(value) {
  return {
    not_provider_smoke: "未运行提供方冒烟验证",
    not_generated_media_qa: "未做生成媒体质检",
    not_human_acceptance: "未声明人工验收",
    not_business_validation: "未声明业务验证",
  }[value] || "未声明额外验证";
}

function refLabel(ref) {
  if (!ref) return "无";
  const objectType = {
    episode_shot: "镜头",
    shot: "镜头",
    artifact: "产物",
  }[ref.object_type] || "对象";
  return `${objectType} ${String(ref.object_id || "").replace("shot-", "")}`;
}

function bindGlobal() {
  app.querySelector('[data-action="logout"]')?.addEventListener("click", async () => {
    try { await runtime.logout(); } catch { saveAuthToken(""); }
    user = null;
    control = null;
    await init();
  });
}

function bindApp() {
  app.querySelectorAll("[data-tab]").forEach((button) => button.addEventListener("click", () => {
    activeTab = button.dataset.tab;
    renderApp();
  }));
  app.querySelector('[data-form="mission"]')?.addEventListener("submit", onMission);
  app.querySelector('[data-form="plan"]')?.addEventListener("submit", onPlan);
  app.querySelector('[data-action="approve-plan"]')?.addEventListener("click", onApprovePlan);
  app.querySelector('[data-action="rebuild"]')?.addEventListener("click", onRebuild);
  app.querySelectorAll("[data-run-action]").forEach((button) => button.addEventListener("click", () => {
    const runId = button.closest("[data-run]")?.dataset.run;
    void runAction(runId, button.dataset.runAction);
  }));
}

async function onLogin(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  await guarded(async () => {
    const session = await runtime.login({ email: form.get("email"), password: form.get("password") });
    user = session.user;
    await ensureProjectAndRefresh();
  }, "登录失败");
}

async function onRegister(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  await guarded(async () => {
    const session = await runtime.register({
      email: form.get("email"),
      password: form.get("password"),
      display_name: form.get("display_name") || "",
      invite_code: form.get("invite_code") || "",
    });
    user = session.user;
    await ensureProjectAndRefresh();
  }, "注册失败");
}

async function onCreateProject(event) {
  event.preventDefault();
  const goal = new FormData(event.currentTarget).get("goal")?.toString().trim() || "AI-native production control";
  const id = projectId || safeProjectId(`production-control-${Date.now()}`);
  await guarded(async () => {
    setProject(id);
    await runtime.createProject({ project_id: id, goal, project_type: "short_video_campaign", status: "in_progress" });
    await refresh();
  }, "创建项目失败");
}

async function onMission(event) {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const constraints = form.getAll("constraint").map((item) => String(item || "").trim()).filter(Boolean);
  await mutate(
    runtime.recordProductionControlMission({
      expected_version: control.version,
      objective: String(form.get("objective") || "").trim(),
      constraints,
      created_at: new Date().toISOString(),
    }, commandKey("mission")),
    "使命已保存",
    "mission",
  );
}

async function onPlan(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const fields = [...form.querySelectorAll("fieldset")].map((fieldset) => ({
    title: fieldset.querySelector('[name="title"]')?.value || "任务",
    boundary: fieldset.querySelector('[name="boundary"]')?.value || "确定性任务边界",
    capability: "deterministic.worker",
    dependency_task_ids: [],
  }));
  await mutate(
    runtime.saveProductionControlPlan({
      expected_version: control.version,
      tasks: fields,
      estimated_cost_max: 0,
      created_at: new Date().toISOString(),
    }, commandKey("plan")),
    "计划已保存",
    "plan",
  );
}

async function onApprovePlan() {
  await mutate(
    runtime.approveProductionControlPlan({ expected_version: control.version, created_at: new Date().toISOString() }, commandKey("approve")),
    "计划已批准，运行已启动",
    "cockpit",
  );
}

async function runAction(runId, action) {
  if (!runId || !action) return;
  await mutate(
    runtime.runProductionControlAction(runId, {
      expected_version: control.version,
      action,
      decision_option: "确认继续",
      note: action === "block" ? "等待局部证据确认。" : "",
      created_at: new Date().toISOString(),
    }, commandKey(action)),
    "操作已追加到账本",
    action === "writeback" ? "artifacts" : "cockpit",
  );
}

async function onRebuild() {
  await guarded(async () => {
    const result = await runtime.rebuildProductionControl();
    notice = result.ok ? "重建校验通过" : "重建校验未通过";
    await refresh(false);
  }, "重建校验失败");
}

async function mutate(promise, message, nextTab) {
  await guarded(async () => {
    const result = await promise;
    control = result.control;
    notice = message;
    activeTab = nextTab || activeTab;
    renderApp();
  }, "命令失败");
}

async function guarded(fn, fallback) {
  if (busy) return;
  busy = true;
  try {
    await fn();
  } catch (error) {
    notice = error?.message || fallback;
    if (control) renderApp();
    else renderProjectSetup();
  } finally {
    busy = false;
    if (control) renderApp();
  }
}

async function ensureProjectAndRefresh() {
  if (projectId) {
    await refresh();
    return;
  }
  renderProjectSetup();
}

async function refresh(render = true) {
  if (!projectId) {
    control = null;
    if (render) renderProjectSetup();
    return;
  }
  runtime = createRuntimeClient(projectId);
  try {
    const payload = await runtime.getProductionControl();
    control = payload.control;
    if (render) renderApp();
  } catch (error) {
    control = null;
    notice = error?.message || "";
    renderProjectSetup();
  }
}

async function init() {
  renderLoading();
  try {
    const status = await runtime.authStatus();
    if (status.auth_required && !status.authenticated) {
      renderAuth(status);
      return;
    }
    user = status.user || null;
    await ensureProjectAndRefresh();
  } catch {
    renderAuth({});
  }
}

init();
