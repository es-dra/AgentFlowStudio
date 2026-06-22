const AUTH_TOKEN_STORAGE_KEY = "afs_auth_session_token";
const listEl = document.querySelector("[data-social-square-list]");
const formEl = document.querySelector("[data-social-square-form]");
const statusEl = document.querySelector("[data-social-square-status]");

async function bootSocialSquare() {
  if (!listEl) return;
  await refreshRequests();
  if (formEl) formEl.addEventListener("submit", submitRequest);
}

async function refreshRequests() {
  try {
    const response = await fetch("/community/requests", { headers: authHeaders(), cache: "no-store" });
    if (!response.ok) throw new Error("request list unavailable");
    const payload = await response.json();
    renderRequests(Array.isArray(payload.requests) ? payload.requests : []);
  } catch {
    renderStatus("社交广场暂时不可用，请稍后再试。");
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
  const text = globalThis.prompt?.("写下你提交的内容说明或项目引用。") || "";
  if (!text.trim()) return;
  await mutate(`/community/requests/${encodeURIComponent(requestId)}/submit`, { text });
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

function renderRequests(requests) {
  listEl.replaceChildren();
  if (!requests.length) {
    listEl.appendChild(emptyCard());
    return;
  }
  for (const request of requests) {
    listEl.appendChild(requestCard(request));
  }
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

  const footer = document.createElement("div");
  footer.className = "square-card-footer";
  footer.append(smallText(`发布者：${request.author_display_name || "创作者"}`));
  if (request.accepted_by_display_name) footer.append(smallText(`承接：${request.accepted_by_display_name}`));

  const actions = document.createElement("div");
  actions.className = "square-card-actions";
  actions.append(actionButton("承接需求", () => acceptRequest(request.request_id), request.status !== "open"));
  actions.append(actionButton("提交成果", () => submitWork(request.request_id), request.status !== "accepted"));

  card.append(meta, title, summary, footer, actions);
  return card;
}

function actionButton(label, onClick, disabled) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.disabled = disabled;
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
  card.textContent = "还没有公开需求。";
  return card;
}

function typeLabel(value) {
  return { script: "脚本", image: "设定图", video: "视频", workflow: "工作流", other: "其他" }[value] || "其他";
}

function statusLabel(value) {
  return { open: "开放", accepted: "已承接", submitted: "待确认", completed: "已完成", closed: "已关闭" }[value] || "开放";
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

bootSocialSquare();
