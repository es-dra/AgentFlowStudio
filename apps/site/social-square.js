const AUTH_TOKEN_STORAGE_KEY = "afs_auth_session_token";
const listEl = document.querySelector("[data-social-square-list]");
const formEl = document.querySelector("[data-social-square-form]");
const statusEl = document.querySelector("[data-social-square-status]");
const searchEl = document.querySelector("[data-square-search]");
const filterButtons = Array.from(document.querySelectorAll("[data-square-filter]"));
let requestsCache = [];
let activeFilter = "all";

async function bootSocialSquare() {
  if (!listEl) return;
  bindFilters();
  if (formEl) formEl.addEventListener("submit", submitRequest);
  await refreshRequests();
}

async function refreshRequests() {
  try {
    const response = await fetch("/community/requests", { headers: authHeaders(), cache: "no-store" });
    if (!response.ok) throw new Error("request list unavailable");
    const payload = await response.json();
    requestsCache = Array.isArray(payload.requests) ? payload.requests : [];
    renderRequests();
    renderStats();
  } catch {
    renderStatus("社交广场暂时不可用，请稍后再试。");
  }
}

function bindFilters() {
  searchEl?.addEventListener("input", renderRequests);
  for (const button of filterButtons) {
    button.addEventListener("click", () => {
      activeFilter = button.dataset.squareFilter || "all";
      filterButtons.forEach((item) => item.classList.toggle("active", item === button));
      renderRequests();
    });
  }
}

async function submitRequest(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(formEl).entries());
  if (!authToken()) {
    renderStatus("请先登录，再发布需求。");
    return;
  }
  await mutate("/community/requests", {
    title: data.title,
    body: data.body,
    need_type: data.need_type || "other",
    deliverable_hint: data.deliverable_hint || "",
  });
  formEl.reset();
}

async function acceptRequest(requestId) {
  await mutate(`/community/requests/${encodeURIComponent(requestId)}/accept`);
}

async function submitWork(requestId) {
  const text = await requestText("提交成果", "写下你提交的内容说明、项目节点或成果引用。");
  if (!text.trim()) return;
  await mutate(`/community/requests/${encodeURIComponent(requestId)}/submit`, { text });
}

async function completeRequest(requestId) {
  await mutate(`/community/requests/${encodeURIComponent(requestId)}/complete`);
}

async function closeRequest(requestId) {
  await mutate(`/community/requests/${encodeURIComponent(requestId)}/close`);
}

async function reportRequest(requestId) {
  const reason = await requestText("举报需求", "简要说明举报原因。");
  if (!reason.trim()) return;
  await mutate(`/community/requests/${encodeURIComponent(requestId)}/report`, { reason });
}

async function mutate(url, body = null) {
  if (!authToken()) {
    renderStatus("请先登录，再执行这个操作。");
    return;
  }
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { ...authHeaders(), "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : "{}",
    });
    if (!response.ok) {
      renderStatus(response.status === 403 ? "当前账号不能执行这个操作。" : "操作未完成，请检查登录状态。");
      return;
    }
    renderStatus("社交广场已更新。");
    await refreshRequests();
  } catch {
    renderStatus("操作失败，请稍后再试。");
  }
}

function renderRequests() {
  listEl.replaceChildren();
  const requests = filteredRequests();
  if (!requests.length) {
    listEl.appendChild(emptyCard());
    return;
  }
  for (const request of requests) {
    listEl.appendChild(requestCard(request));
  }
}

function filteredRequests() {
  const query = String(searchEl?.value || "").trim().toLowerCase();
  return requestsCache.filter((request) => {
    const typeOk = activeFilter === "all" || request.need_type === activeFilter;
    const haystack = [
      request.title,
      request.safe_public_summary,
      request.deliverable_hint,
      request.author_display_name,
      request.accepted_by_display_name,
    ].join(" ").toLowerCase();
    return typeOk && (!query || haystack.includes(query));
  });
}

function requestCard(request) {
  const card = document.createElement("article");
  card.className = "square-card";

  const meta = document.createElement("div");
  meta.className = "square-card-meta";
  meta.append(textPill(typeLabel(request.need_type)), textPill(statusLabel(request.status)));

  const title = document.createElement("strong");
  title.textContent = request.title || "未命名需求";

  const summary = document.createElement("p");
  summary.textContent = request.safe_public_summary || "需求发布者暂未补充说明。";

  const deliverable = document.createElement("small");
  deliverable.className = "deliverable";
  deliverable.textContent = request.deliverable_hint ? `期望交付：${request.deliverable_hint}` : "期望交付：发布者暂未填写。";

  const footer = document.createElement("div");
  footer.className = "square-card-footer";
  footer.append(smallText(`发布者：${request.author_display_name || "创作者"}`));
  if (request.accepted_by_display_name) footer.append(smallText(`承接：${request.accepted_by_display_name}`));
  footer.append(smallText(timeLabel(request.updated_at)));

  const actions = document.createElement("div");
  actions.className = "square-card-actions";
  actions.append(
    actionButton("承接", () => acceptRequest(request.request_id), request.status !== "open"),
    actionButton("提交成果", () => submitWork(request.request_id), request.status !== "accepted"),
    actionButton("确认完成", () => completeRequest(request.request_id), !["accepted", "submitted"].includes(request.status)),
    actionButton("关闭", () => closeRequest(request.request_id), !["open", "accepted", "submitted"].includes(request.status)),
    actionButton("举报", () => reportRequest(request.request_id), false, "ghost"),
  );

  card.append(meta, title, summary, deliverable, footer, actions);
  if (request.submission?.text) card.appendChild(submissionView(request.submission));
  return card;
}

function submissionView(submission) {
  const box = document.createElement("div");
  box.className = "square-submission";
  box.appendChild(smallText("已提交成果"));
  const p = document.createElement("p");
  p.textContent = submission.text;
  box.appendChild(p);
  return box;
}

function renderStats() {
  const counts = { open: 0, accepted: 0, submitted: 0, completed: 0 };
  for (const request of requestsCache) {
    if (request.status in counts) counts[request.status] += 1;
  }
  for (const [key, value] of Object.entries(counts)) {
    const el = document.querySelector(`[data-square-stat="${key}"]`);
    if (el) el.textContent = String(value);
  }
}

function actionButton(label, onClick, disabled, tone = "") {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.disabled = disabled;
  if (tone) button.dataset.tone = tone;
  button.addEventListener("click", onClick);
  return button;
}

function textPill(text) {
  const span = document.createElement("span");
  span.textContent = text;
  return span;
}

function smallText(text) {
  const span = document.createElement("small");
  span.textContent = text;
  return span;
}

function emptyCard() {
  const card = document.createElement("article");
  card.className = "square-empty";
  card.textContent = "还没有符合条件的公开需求。";
  return card;
}

function typeLabel(value) {
  return { script: "脚本", image: "设定图", video: "视频", workflow: "工作流", other: "其他" }[value] || "其他";
}

function statusLabel(value) {
  return { open: "开放", accepted: "已承接", submitted: "待确认", completed: "已完成", closed: "已关闭" }[value] || "开放";
}

function timeLabel(value) {
  if (!value) return "刚刚更新";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "刚刚更新";
  return `更新：${date.toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" })}`;
}

function renderStatus(message) {
  if (statusEl) statusEl.textContent = message;
}

function authHeaders() {
  const headers = { Accept: "application/json" };
  const token = authToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  return headers;
}

function authToken() {
  try {
    return String(globalThis.localStorage?.getItem(AUTH_TOKEN_STORAGE_KEY) || "").trim();
  } catch {
    return "";
  }
}

function requestText(title, placeholder) {
  return new Promise((resolve) => {
    const backdrop = document.createElement("div");
    backdrop.className = "square-dialog-backdrop";
    const dialog = document.createElement("div");
    dialog.className = "square-dialog";
    const heading = document.createElement("strong");
    heading.textContent = title;
    const input = document.createElement("textarea");
    input.maxLength = 1200;
    input.placeholder = placeholder;
    const actions = document.createElement("div");
    actions.className = "square-dialog-actions";
    const cancel = document.createElement("button");
    cancel.type = "button";
    cancel.textContent = "取消";
    const confirm = document.createElement("button");
    confirm.type = "button";
    confirm.textContent = "提交";
    confirm.className = "primary";
    actions.append(cancel, confirm);
    dialog.append(heading, input, actions);
    backdrop.appendChild(dialog);
    document.body.appendChild(backdrop);
    const finish = (value) => {
      backdrop.remove();
      resolve(value);
    };
    cancel.addEventListener("click", () => finish(""));
    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop) finish("");
    });
    confirm.addEventListener("click", () => finish(input.value.trim()));
    input.addEventListener("keydown", (event) => {
      if (event.key === "Escape") finish("");
      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") finish(input.value.trim());
    });
    requestAnimationFrame(() => input.focus());
  });
}

bootSocialSquare();
