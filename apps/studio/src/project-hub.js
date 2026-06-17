import { WORKFLOW_STARTERS } from "./workflow-starters.js";
import { icon } from "./icons.js";
import { el, showModal } from "./overlay.js";
import { openCreationProcessPanel } from "./panels/creation-process-panel.js";

export async function renderProjectHub(options) {
  return openProjectHub(options);
}

const PROJECT_HUB_EVENT = "start_project_hub";

export async function openProjectHub({
  state,
  runtime,
  projects = [],
  hiddenProjectCount = 0,
  onSwitchProject,
  onCreateProject,
  onStartWorkflow,
  onOpenAssets,
  onOpenHistory,
}) {
  let closeProjectHub = () => {};
  const modal = el("div", "modal project-hub");
  modal.dataset.event = PROJECT_HUB_EVENT;
  const closeBtn = el("button", "modal-close project-hub-close");
  closeBtn.innerHTML = icon("x", 15);

  const head = el("div", "project-hub-head");
  head.appendChild(el("div", "project-hub-kicker", "AFS Studio"));
  head.appendChild(el("h2", "", "开始创作一个视频项目"));
  head.appendChild(el("p", "project-hub-subtitle", "从作品、素材和频道模板进入画布；真实生成只会在你确认后开始。"));
  head.appendChild(closeBtn);
  modal.appendChild(head);

  modal.appendChild(heroSection(state, {
    onStart: () => {
      closeProjectHub();
      onStartWorkflow?.("story_to_keyframe");
    },
    onAssets: () => {
      closeProjectHub();
      onOpenAssets?.();
    },
  }));

  const runtimeCard = await runtimeReadiness(runtime);
  const grid = el("div", "project-hub-grid");
  grid.appendChild(currentProjectCard(state));
  grid.appendChild(runtimeCard);
  grid.appendChild(providerGateCard(runtimeCard.dataset.providerGates || ""));
  modal.appendChild(grid);

  modal.appendChild(starterSection((starterId) => {
    closeProjectHub();
    onStartWorkflow?.(starterId);
  }));
  modal.appendChild(recentWorksSection(state, () => {
    closeProjectHub();
    onOpenHistory?.();
  }));
  modal.appendChild(recentProjectsSection(projects, hiddenProjectCount, (projectId) => {
    closeProjectHub();
    onSwitchProject?.(projectId);
  }));

  const actions = el("div", "project-hub-actions");
  const current = el("button", "ghost-btn", "继续当前项目");
  current.addEventListener("click", () => close());
  const create = el("button", "primary-btn", "新建项目");
  create.addEventListener("click", () => {
    close();
    onCreateProject?.();
  });
  actions.append(current, create);
  modal.appendChild(actions);

  const close = showModal(modal);
  closeProjectHub = close;
  closeBtn.addEventListener("click", close);
  return close;
}

function heroSection(state, actions) {
  const section = el("section", "project-hub-hero");
  const visual = el("div", "project-hub-visual");
  const heroCards = [
    ["story", "短剧起步", "故事 / 分镜 / 关键帧"],
    ["video", "图生视频", "首帧 / 运动 / 预览"],
    ["revision", "修改迭代", "复用 / 对比 / 卡片"],
  ];
  heroCards.forEach(([tone, title, subtitle], index) => {
    const card = el("div", `project-visual-card ${index === 1 ? "active" : ""}`);
    card.dataset.tone = tone;
    card.innerHTML = `<strong>${escapeHtml(title)}</strong><small>${escapeHtml(subtitle)}</small>`;
    visual.appendChild(card);
  });

  const copy = el("div", "project-hub-hero-copy");
  copy.appendChild(el("span", "", "创作入口"));
  copy.appendChild(el("h3", "", state.meta.projectName || "未命名项目"));
  copy.appendChild(el("p", "", "先选择创作方向，再进入画布细调节点、素材和生成结果。"));
  const cta = el("div", "project-hub-cta-row");
  const start = el("button", "primary-btn hero-cta", "开始创作");
  start.addEventListener("click", actions.onStart);
  const assets = el("button", "ghost-btn hero-cta", "从素材继续");
  assets.addEventListener("click", actions.onAssets);
  cta.append(start, assets);
  copy.appendChild(cta);
  copy.appendChild(commandRow(state));

  section.append(visual, copy);
  return section;
}

function commandRow(state) {
  const row = el("div", "project-hub-command-row");
  row.appendChild(commandPill("节点", state.order.length));
  row.appendChild(commandPill("素材", state.assets.length));
  row.appendChild(commandPill("生成中", Object.values(state.nodes || {}).filter((node) => node.status === "generating").length));
  row.appendChild(commandPill("画布", state.meta.canvasName || "画布 1"));
  return row;
}

function commandPill(label, value) {
  const pill = el("span", "project-hub-command-pill");
  pill.innerHTML = `<strong>${escapeHtml(value)}</strong><small>${escapeHtml(label)}</small>`;
  return pill;
}

function currentProjectCard(state) {
  const card = el("div", "project-hub-card featured");
  card.innerHTML = [
    "<span>当前项目</span>",
    `<strong>${escapeHtml(state.meta.projectName || "未命名项目")}</strong>`,
    `<small>${escapeHtml(state.meta.canvasName || "画布 1")} · ${state.order.length} 个节点 · ${state.assets.length} 个素材</small>`,
    "<em>项目细节已收进顶部切换菜单</em>",
  ].join("");
  return card;
}

async function runtimeReadiness(runtime) {
  const card = el("div", "project-hub-card runtime-card");
  card.innerHTML = "<span>创作服务</span><strong>检查中</strong><small>正在读取当前状态</small>";
  try {
    const health = await runtime?.health?.();
    const gates = health?.provider_gates || {};
    card.dataset.providerGates = JSON.stringify(gates);
    card.innerHTML = [
      "<span>创作服务</span>",
      `<strong>${health?.status === "ready" ? "已连接" : "未就绪"}</strong>`,
      `<small>项目保存 ${health?.capabilities?.projects ? "可用" : "未开启"} · 本地草稿 ${health?.runtime_root_persisted ? "可恢复" : "临时"}</small>`,
    ].join("");
  } catch {
    card.innerHTML = "<span>创作服务</span><strong>离线</strong><small>本地画布仍可编辑</small>";
  }
  return card;
}

function providerGateCard(serializedGates) {
  let gates = {};
  try { gates = JSON.parse(serializedGates || "{}"); } catch { gates = {}; }
  const card = el("div", "project-hub-card provider-card");
  card.innerHTML = [
    "<span>生成能力</span>",
    "<strong>按需开启</strong>",
    `<small><span class="provider-gate-pill">文案 ${gateText(gates.llm)}</span><span class="provider-gate-pill">图片 ${gateText(gates.image)}</span><span class="provider-gate-pill">视频 ${gateText(gates.video)}</span></small>`,
    "<em>开始真实生成前会再次确认。</em>",
  ].join("");
  return card;
}

function starterSection(onStartWorkflow) {
  const section = el("section", "project-hub-section starter-section");
  section.appendChild(sectionHead("创作频道", "按目标选择起点，自动铺开可编辑节点。"));
  const starters = el("div", "workflow-starter-grid");
  WORKFLOW_STARTERS.forEach((starter, index) => {
    const card = el("button", "workflow-starter-card");
    card.dataset.tone = starter.tone || "story";
    card.innerHTML = [
      `<span class="starter-index">${String(index + 1).padStart(2, "0")}</span>`,
      `<span class="starter-icon">${icon(starter.icon, 16)}</span>`,
      `<strong>${escapeHtml(starter.label)}</strong>`,
      `<small>${escapeHtml(starter.summary)}</small>`,
      `<em>${escapeHtml(starter.tag || "草稿")}</em>`,
    ].join("");
    card.addEventListener("click", () => onStartWorkflow?.(starter.id));
    starters.appendChild(card);
  });
  section.appendChild(starters);
  return section;
}

function recentWorksSection(state, onOpenHistory) {
  const section = el("section", "project-hub-section recent-works-section");
  section.appendChild(sectionHead("最近作品", "查看输出并回到创作过程。"));
  const works = Object.values(state.nodes || {})
    .filter((node) => node.previewUrl || node.result)
    .slice(-4)
    .reverse();
  const grid = el("div", "recent-work-grid");
  if (!works.length) {
    grid.appendChild(el("div", "project-hub-empty work-empty", "完成的图片、视频和脚本会在这里形成作品卡。"));
  }
  for (const node of works) {
    grid.appendChild(recentWorkCard(state, node));
  }
  section.appendChild(grid);
  const more = el("button", "ghost-btn recent-work-more", "打开作品库");
  more.addEventListener("click", onOpenHistory);
  section.appendChild(more);
  return section;
}

function recentWorkCard(state, node) {
  const card = el("article", `recent-work-card ${node.type || "text"}`);
  const thumb = el("div", "recent-work-thumb");
  if (node.previewUrl && node.type === "image") {
    const img = document.createElement("img");
    img.src = node.previewUrl;
    img.alt = "";
    img.loading = "lazy";
    thumb.appendChild(img);
  } else {
    thumb.innerHTML = icon(node.type === "video" ? "video" : node.type === "image" ? "image" : "script", 18);
  }
  const copy = el("div", "recent-work-copy");
  copy.innerHTML = [
    `<span>${escapeHtml(workType(node))}</span>`,
    `<strong>${escapeHtml(node.title || "未命名输出")}</strong>`,
    `<small>${escapeHtml(workSummary(node))}</small>`,
  ].join("");
  const inspect = el("button", "mini-btn", "查看创作过程");
  inspect.addEventListener("click", () => openCreationProcessPanel(state, node));
  card.append(thumb, copy, inspect);
  return card;
}

function recentProjectsSection(projects, hiddenProjectCount, onSwitchProject) {
  const section = el("section", "project-hub-section recent-projects-section");
  section.appendChild(sectionHead("最近项目", "快速回到最近创作项目。"));
  const projectList = el("div", "project-hub-projects");
  const recent = projects.slice(0, 5);
  if (!recent.length) {
    projectList.appendChild(el("div", "project-hub-empty", "暂无创作项目。"));
  }
  for (const project of recent) {
    const item = el("button", "project-hub-project");
    item.innerHTML = [
      `<strong>${escapeHtml(projectLabel(project))}</strong>`,
      `<small>${escapeHtml(project.project_id || "")}</small>`,
      `<span>${escapeHtml(project.updated_at || project.created_at || "local state")}</span>`,
    ].join("");
    item.addEventListener("click", () => onSwitchProject?.(project.project_id));
    projectList.appendChild(item);
  }
  section.appendChild(projectList);
  if (hiddenProjectCount) {
    section.appendChild(el("div", "project-hub-note", `已折叠 ${hiddenProjectCount} 个测试项目，可在顶部项目菜单展开。`));
  }
  section.appendChild(el("div", "project-hub-safe-note", "隐私保护：页面只显示摘要，不显示账号凭据、临时下载链接或原始文件内容。"));
  return section;
}

function sectionHead(title, subtitle) {
  const head = el("div", "project-hub-section-head");
  head.appendChild(el("h3", "", title));
  head.appendChild(el("p", "", subtitle));
  return head;
}

const gateText = (value) => (value ? "可用" : "未开");

function projectLabel(project) {
  return project?.studio_state_meta?.projectName || project?.goal || project?.project_id || "未命名项目";
}

function workType(node) {
  if (node.type === "video") return "视频作品";
  if (node.type === "image") return "关键帧";
  if (node.type === "script") return "脚本";
  return "创作记录";
}

function workSummary(node) {
  if (node.previewUrl) return "已有预览，可继续复用";
  if (node.result) return String(node.result).replace(/\s+/g, " ").slice(0, 72);
  return "本地草稿";
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}
