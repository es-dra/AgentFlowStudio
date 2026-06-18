const authActions = Array.from(document.querySelectorAll("[data-auth-action]"));
const AUTH_TOKEN_STORAGE_KEY = "afs_auth_session_token";

async function bootHomeEntryState() {
  if (!authActions.length) return;
  try {
    const response = await fetch("/auth/status", {
      headers: authHeaders(),
      cache: "no-store",
    });
    if (!response.ok) return;
    const status = await response.json();
    applyAuthEntryState(status);
  } catch {
    // The homepage remains a plain Studio entry if Runtime auth status is unavailable.
  }
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

function applyAuthEntryState(status) {
  const authRequired = Boolean(status?.auth_required);
  const authenticated = Boolean(status?.authenticated);
  const user = status?.user || null;
  const label = entryLabel({ authRequired, authenticated, user });
  for (const action of authActions) {
    action.textContent = label;
    action.setAttribute("aria-label", label);
    action.dataset.authRequired = authRequired ? "true" : "false";
    action.dataset.authenticated = authenticated ? "true" : "false";
  }
  renderAccountHint({ authRequired, authenticated, user });
}

function entryLabel({ authRequired, authenticated, user }) {
  if (!authRequired) return "打开 Studio";
  if (authenticated) {
    const name = String(user?.display_name || user?.email || "").trim();
    return name ? `进入 ${name} 的 Studio` : "进入我的 Studio";
  }
  return "注册 / 登录后进入";
}

function renderAccountHint({ authRequired, authenticated, user }) {
  if (!authRequired || !authenticated || !user) return;
  const header = document.querySelector(".site-header");
  if (!header || header.querySelector(".site-account-hint")) return;
  const hint = document.createElement("span");
  hint.className = "site-account-hint";
  hint.textContent = user.display_name || user.email || "已登录";
  header.insertBefore(hint, header.querySelector(".nav-action"));
}

bootHomeEntryState();
