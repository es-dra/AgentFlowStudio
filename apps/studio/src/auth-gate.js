import { icon } from "./icons.js";
import { el, showModal } from "./overlay.js";
import { formatRuntimeError } from "./runtime-error-utils.js";

export async function ensureAuthSession(runtime, options = {}) {
  let status;
  try {
    status = await runtime.authStatus();
  } catch (error) {
    return showAuthStatusBlocked(runtime, options, error);
  }
  if (!status?.auth_required || status.authenticated) return status;
  return showAuthGate(runtime, options);
}

export async function signOut(runtime) {
  try {
    await runtime.logout();
  } catch {
    // runtime.logout() always clears the local token.
  }
}

function showAuthGate(runtime, { onAuthenticated } = {}) {
  return new Promise((resolve) => {
    let mode = "login";
    let settled = false;
    const modal = el("div", "modal compact auth-modal");
    modal.setAttribute("aria-label", "AgentFlow Studio 账户登录");
    const head = el("div", "modal-head auth-head");
    const title = el("div", "auth-title");
    title.appendChild(el("span", "auth-mark", "AFS"));
    title.appendChild(el("strong", "", "制作工作空间"));
    head.appendChild(title);
    const tabs = el("div", "modal-tabs");
    const loginTab = el("button", "modal-tab active", "登录");
    const registerTab = el("button", "modal-tab", "注册");
    tabs.append(loginTab, registerTab);
    head.appendChild(el("span", "head-spacer"));
    head.appendChild(tabs);

    const body = el("div", "modal-body auth-body");
    const intro = el("p", "auth-copy", "登录后进入你的工作空间。账户确认前不会加载任何项目、画布或交付内容。");
    const email = field("邮箱", "email", "name@example.com", "username");
    const password = field("密码", "password", "至少 8 位", "current-password");
    const displayName = field("姓名", "text", "团队成员姓名", "name");
    const inviteCode = field("邀请码", "text", "由管理员分发", "off");
    displayName.wrap.hidden = true;
    inviteCode.wrap.hidden = true;
    const error = el("div", "modal-error");
    error.setAttribute("role", "alert");
    error.hidden = true;
    body.append(intro, email.wrap, password.wrap, displayName.wrap, inviteCode.wrap, error);

    const actions = el("div", "modal-actions auth-actions");
    const submit = el("button", "primary-btn", "登录工作空间");
    actions.appendChild(submit);
    modal.append(head, body, actions);

    const close = showModal(modal, {
      closeOnOutside: false,
      closeOnEscape: false,
      initialFocus: email.input,
      ariaLabel: "登录 AgentFlow Studio 制作工作空间",
      onClose: () => {
        if (!settled) resolve({ auth_required: true, authenticated: false, user: null });
      },
    });

    loginTab.addEventListener("click", () => setMode("login"));
    registerTab.addEventListener("click", () => setMode("register"));
    submit.addEventListener("click", submitAuth);
    for (const input of [email.input, password.input, displayName.input, inviteCode.input]) {
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") submitAuth();
      });
    }

    function setMode(nextMode) {
      mode = nextMode;
      loginTab.classList.toggle("active", mode === "login");
      registerTab.classList.toggle("active", mode === "register");
      displayName.wrap.hidden = mode !== "register";
      inviteCode.wrap.hidden = mode !== "register";
      submit.textContent = mode === "register" ? "注册并进入" : "登录工作空间";
      intro.textContent = mode === "register"
        ? "使用团队邀请码创建账户。注册完成前不会加载任何项目内容。"
        : "登录后进入你的工作空间。账户确认前不会加载任何项目、画布或交付内容。";
      password.input.autocomplete = mode === "register" ? "new-password" : "current-password";
      error.hidden = true;
    }

    async function submitAuth() {
      error.hidden = true;
      submit.disabled = true;
      submit.innerHTML = `${icon("clock", 14)}<span>正在确认…</span>`;
      try {
        const payload = { email: email.input.value.trim(), password: password.input.value };
        const response = mode === "register"
          ? await runtime.register({
              ...payload,
              display_name: displayName.input.value.trim(),
              invite_code: inviteCode.input.value.trim(),
            })
          : await runtime.login(payload);
        onAuthenticated?.(response.user || null);
        settled = true;
        close();
        resolve({ auth_required: true, authenticated: true, user: response.user || null });
      } catch (authError) {
        error.textContent = safeError(authError);
        error.hidden = false;
        error.focus?.();
      } finally {
        submit.disabled = false;
        submit.textContent = mode === "register" ? "注册并进入" : "登录工作空间";
      }
    }
  });
}

function showAuthStatusBlocked(runtime, options, initialError) {
  return new Promise((resolve) => {
    let settled = false;
    const modal = el("div", "modal compact auth-modal auth-status-blocked-modal");
    const head = el("div", "modal-head auth-head");
    const title = el("div", "auth-title");
    title.appendChild(el("span", "auth-mark", "AFS"));
    title.appendChild(el("strong", "", "无法确认账户状态"));
    head.appendChild(title);

    const body = el("div", "modal-body auth-body");
    body.appendChild(el("p", "auth-copy", "为了保护项目内容，当前已暂停项目加载、同步和 Runtime 写入，也不会显示画布或交付数据。请恢复连接后重试。"));
    const error = el("div", "modal-error", safeError(initialError));
    error.setAttribute("role", "alert");
    body.appendChild(error);

    const actions = el("div", "modal-actions auth-actions");
    const retry = el("button", "primary-btn", "重试账号状态检查");
    actions.appendChild(retry);
    modal.append(head, body, actions);

    const close = showModal(modal, {
      closeOnOutside: false,
      closeOnEscape: false,
      initialFocus: retry,
      ariaLabel: "账户状态检查失败",
      onClose: () => {
        if (!settled) resolve({ auth_status_unknown: true, blocked: true, authenticated: false, user: null });
      },
    });

    retry.addEventListener("click", async () => {
      retry.disabled = true;
      retry.innerHTML = `${icon("clock", 14)}<span>检查中…</span>`;
      error.hidden = true;
      try {
        const status = await runtime.authStatus();
        settled = true;
        close();
        resolve(!status?.auth_required || status.authenticated ? status : await showAuthGate(runtime, options));
      } catch (statusError) {
        error.textContent = safeError(statusError);
        error.hidden = false;
        retry.disabled = false;
        retry.textContent = "重试账号状态检查";
      }
    });
  });
}

function field(label, type, placeholder, autocomplete) {
  const wrap = el("label", "modal-field auth-field");
  wrap.appendChild(el("span", "", label));
  const input = document.createElement("input");
  input.type = type;
  input.placeholder = placeholder;
  input.autocomplete = autocomplete;
  input.required = type !== "text" || label === "邀请码";
  input.setAttribute("aria-label", label);
  wrap.appendChild(input);
  return { wrap, input };
}

function safeError(error) {
  return formatRuntimeError(error, "账户请求失败，请检查连接后重试。");
}
