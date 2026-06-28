import { icon } from "./icons.js";
import { el, showModal } from "./overlay.js";
import { formatRuntimeError } from "./runtime-error-utils.js";

export async function ensureAuthSession(runtime, options = {}) {
  let status;
  try {
    status = await runtime.authStatus();
  } catch {
    return { auth_required: false, authenticated: false, user: null };
  }
  if (!status?.auth_required || status.authenticated) return status;
  return showAuthGate(runtime, options);
}

export async function signOut(runtime) {
  try {
    await runtime.logout();
  } catch {
    // Local session cleanup happens in runtime.logout().finally().
  }
}

function showAuthGate(runtime, { onAuthenticated } = {}) {
  return new Promise((resolve) => {
    let mode = "register";
    let settled = false;
    const modal = el("div", "modal compact auth-modal");
    const head = el("div", "modal-head auth-head");
    const title = el("div", "auth-title");
    title.appendChild(el("span", "auth-mark", "AFS"));
    title.appendChild(el("strong", "", "内测账号"));
    head.appendChild(title);
    const tabs = el("div", "modal-tabs");
    const registerTab = el("button", "modal-tab active", "注册");
    const loginTab = el("button", "modal-tab", "登录");
    tabs.append(registerTab, loginTab);
    head.appendChild(el("span", "head-spacer"));
    head.appendChild(tabs);

    const body = el("div", "modal-body auth-body");
    const intro = el("p", "auth-copy", "请输入分发的邀请码完成注册。登录后，项目会保存在自己的账号空间中。");
    const email = field("邮箱", "email", "name@example.com");
    const password = field("密码", "password", "至少 8 位");
    const displayName = field("昵称", "text", "可选");
    const inviteCode = field("邀请码", "text", "由管理员分发");
    const error = el("div", "modal-error");
    error.hidden = true;
    body.append(intro, email.wrap, password.wrap, displayName.wrap, inviteCode.wrap, error);

    const actions = el("div", "modal-actions auth-actions");
    const submit = el("button", "primary-btn", "注册并进入");
    actions.appendChild(submit);
    modal.append(head, body, actions);

    const close = showModal(modal, {
      closeOnOutside: false,
      onClose: () => {
        if (!settled) resolve({ auth_required: true, authenticated: false, user: null });
      },
    });

    registerTab.addEventListener("click", () => setMode("register"));
    loginTab.addEventListener("click", () => setMode("login"));
    submit.addEventListener("click", submitAuth);
    for (const input of [email.input, password.input, displayName.input, inviteCode.input]) {
      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") submitAuth();
      });
    }

    function setMode(nextMode) {
      mode = nextMode;
      registerTab.classList.toggle("active", mode === "register");
      loginTab.classList.toggle("active", mode === "login");
      displayName.wrap.hidden = mode !== "register";
      inviteCode.wrap.hidden = mode !== "register";
      submit.textContent = mode === "register" ? "注册并进入" : "登录";
      intro.textContent = mode === "register"
        ? "请输入分发的邀请码完成注册。登录后，项目会保存在自己的账号空间中。"
        : "使用已注册的邮箱和密码进入你的项目空间。";
      error.hidden = true;
    }

    async function submitAuth() {
      error.hidden = true;
      submit.disabled = true;
      submit.innerHTML = `${icon("clock", 14)}<span>处理中</span>`;
      try {
        const payload = {
          email: email.input.value.trim(),
          password: password.input.value,
        };
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
      } finally {
        submit.disabled = false;
        submit.textContent = mode === "register" ? "注册并进入" : "登录";
      }
    }

    requestAnimationFrame(() => email.input.focus());
  });
}

function field(label, type, placeholder) {
  const wrap = el("label", "modal-field auth-field");
  wrap.appendChild(el("span", "", label));
  const input = document.createElement("input");
  input.type = type;
  input.placeholder = placeholder;
  input.autocomplete = type === "password" ? "current-password" : "on";
  wrap.appendChild(input);
  return { wrap, input };
}

function safeError(error) {
  return formatRuntimeError(error, "????");
}
