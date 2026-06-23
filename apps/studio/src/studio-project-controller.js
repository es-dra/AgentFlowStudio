import { createRuntimeClient } from "./runtime-client.js";
import { syncRuntimeAssets } from "./runtime-asset-sync.js";
import {
  persistActiveProject,
  recentProjectIds,
  rememberProject,
  safeProjectId,
  syncProjectUrl,
} from "./studio-project-session.js";
import { el, showModal } from "./overlay.js";
import { icon } from "./icons.js";

export function createProjectController({ store, getRuntime, setRuntime, render, onProjectReady }) {
  let projectSummaries = [];
  let showAllProjects = false;
  let currentAuthUser = null;

  async function applyProject(projectId, runtimeClient, { projectName, syncAssets = true } = {}) {
    const safe = safeProjectId(projectId) || "studio-local-001";
    persistActiveProject(safe);
    rememberProject(safe);
    syncProjectUrl(safe);
    setRuntime(runtimeClient);
    await store.switchProject(projectId, runtimeClient);
    if (projectName) {
      store.set((s) => {
        s.meta.projectName = projectName;
        if (!s.meta.canvasName) s.meta.canvasName = "画布 1";
      }, { history: false });
    }
    await store.flushRuntimeSave();
    if (syncAssets) {
      await syncRuntimeAssets(store, runtimeClient);
    }
    await onProjectReady?.(runtimeClient);
    await refreshProjectSummaries();
  }

  async function refreshProjectSummaries() {
    try {
      const payload = await getRuntime().listProjects();
      projectSummaries = Array.isArray(payload?.projects) ? payload.projects : [];
      syncCurrentProjectMetaFromSummaries();
    } catch {
      projectSummaries = [];
    }
    render();
  }

  async function ensureAccessibleStartupProject() {
    await refreshProjectSummaries();
    const runtime = getRuntime();
    if (projectSummaries.some((item) => item.project_id === runtime.projectId)) {
      return;
    }
    if (projectSummaries.length) {
      await switchProject(projectSummaries[0].project_id);
      return;
    }
    if (!currentAuthUser?.user_id) {
      return;
    }
    const projectId = safeProjectId(`studio-${currentAuthUser.user_id}-home`) || "studio-local-001";
    const projectName = `${currentAuthUser.display_name || "AFS"} 的项目`;
    const nextRuntime = createRuntimeClient(projectId);
    await nextRuntime.createProject({ project_id: projectId, goal: projectName });
    await applyProject(projectId, nextRuntime, { projectName, syncAssets: false });
  }

  async function switchProject(projectId) {
    const safe = safeProjectId(projectId) || "studio-local-001";
    if (!safe || safe === getRuntime().projectId) {
      return;
    }
    const nextRuntime = createRuntimeClient(safe);
    await applyProject(safe, nextRuntime);
  }

  async function createNewProject() {
    const name = await requestProjectName();
    if (name === null) return;
    const suffix = Math.random().toString(36).slice(2, 8);
    const projectId = safeProjectId(`studio-${Date.now()}-${suffix}`);
    const projectName = name.trim() || "AFS Studio project";
    const nextRuntime = createRuntimeClient(projectId);
    try {
      await createProjectWithRetry(nextRuntime, { project_id: projectId, goal: projectName });
      await applyProject(projectId, nextRuntime, { projectName, syncAssets: false });
    } catch (error) {
      showProjectCreateError(error);
    }
  }

  function projectOptions(state) {
    const runtime = getRuntime();
    const currentId = runtime.projectId || state.meta.projectId;
    const current = {
      project_id: currentId,
      studio_state_meta: {
        projectName: state.meta.projectName,
        canvasName: state.meta.canvasName,
      },
    };
    const known = projectSummaries.length ? [...projectSummaries] : [];
    if (currentId && !known.some((item) => item.project_id === currentId)) known.unshift(current);
    const recent = recentProjectIds();
    const normal = known.filter((item) => !isTestProject(item)).slice(0, 5);
    const normalIds = new Set(normal.map((item) => item.project_id));
    const visible = showAllProjects ? known : known.filter((item) =>
      item.project_id === currentId || recent.includes(item.project_id) || normalIds.has(item.project_id));
    return visible.length ? visible : [current];
  }

  function hiddenProjectCount(state) {
    const runtime = getRuntime();
    const currentId = state.meta.projectId || runtime.projectId;
    if (showAllProjects) return 0;
    const visibleIds = new Set(projectOptions(state).map((item) => item.project_id));
    return projectSummaries.filter((item) => item.project_id !== currentId && !visibleIds.has(item.project_id)).length;
  }

  return {
    get summaries() {
      return projectSummaries;
    },
    get showAllProjects() {
      return showAllProjects;
    },
    get authUser() {
      return currentAuthUser;
    },
    rememberStartupProject(projectId) {
      rememberProject(projectId || getRuntime().projectId);
    },
    setAuthUser(user) {
      currentAuthUser = user || null;
    },
    toggleProjectFilter() {
      showAllProjects = !showAllProjects;
      render();
    },
    refreshProjectSummaries,
    ensureAccessibleStartupProject,
    switchProject,
    createNewProject,
    projectOptions,
    hiddenProjectCount,
  };

  function syncCurrentProjectMetaFromSummaries() {
    const runtime = getRuntime();
    const currentId = runtime.projectId || store.get().meta.projectId;
    const found = projectSummaries.find((item) => item.project_id === currentId);
    const meta = found?.studio_state_meta || {};
    const projectName = String(meta.projectName || "").trim();
    const canvasName = String(meta.canvasName || "").trim();
    if (!projectName && !canvasName) return;
    store.set((s) => {
      if (projectName) s.meta.projectName = projectName;
      if (canvasName) s.meta.canvasName = canvasName;
    }, { history: false, persist: false });
  }
}

function requestProjectName() {
  return new Promise((resolve) => {
    const modal = el("div", "modal compact project-create-modal");
    const head = el("div", "modal-head");
    head.appendChild(el("strong", "", "新建视频项目"));
    const closeBtn = el("button", "modal-close");
    closeBtn.innerHTML = icon("x", 15);
    head.appendChild(el("span", "head-spacer"));
    head.appendChild(closeBtn);

    const body = el("div", "modal-body project-create-body");
    const field = el("label", "modal-field");
    field.appendChild(el("span", "", "项目名称"));
    const input = document.createElement("input");
    input.type = "text";
    input.value = "AFS 内测项目";
    input.maxLength = 80;
    field.appendChild(input);
    const error = el("div", "modal-error");
    error.hidden = true;
    body.append(field, error);

    const actions = el("div", "modal-actions");
    const cancel = el("button", "ghost-btn", "取消");
    const confirm = el("button", "primary-btn", "创建并切换");
    actions.append(cancel, confirm);

    modal.append(head, body, actions);
    let settled = false;
    const close = showModal(modal, { onClose: () => { if (!settled) resolve(null); } });
    const finish = () => {
      if (settled) return;
      const name = input.value.trim();
      if (!name) {
        error.textContent = "请先填写项目名称。";
        error.hidden = false;
        input.focus();
        return;
      }
      settled = true;
      close();
      resolve(name);
    };

    confirm.addEventListener("click", finish);
    cancel.addEventListener("click", () => {
      if (settled) return;
      settled = true;
      close();
      resolve(null);
    });
    closeBtn.addEventListener("click", () => {
      if (settled) return;
      settled = true;
      close();
      resolve(null);
    });
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        finish();
      }
      if (event.key === "Escape") {
        if (settled) return;
        settled = true;
        close();
        resolve(null);
      }
    });
    requestAnimationFrame(() => {
      input.focus();
      input.select();
    });
  });
}

async function createProjectWithRetry(runtime, payload) {
  try {
    return await runtime.createProject(payload);
  } catch (error) {
    if (!isTransientRuntimeError(error)) throw error;
    await delay(900);
    return runtime.createProject(payload);
  }
}

function isTransientRuntimeError(error) {
  const status = Number(error?.status || 0);
  const message = error instanceof Error ? error.message : String(error || "");
  return status === 0 || status === 502 || status === 503 || status === 504 || /network connection interrupted|Failed to fetch|Gateway timeout/i.test(message);
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function showProjectCreateError(error) {
  const message = safeError(error);
  const modal = el("div", "modal compact project-create-modal");
  const head = el("div", "modal-head");
  head.appendChild(el("strong", "", "项目创建失败"));
  const closeBtn = el("button", "modal-close");
  closeBtn.innerHTML = icon("x", 15);
  head.appendChild(el("span", "head-spacer"));
  head.appendChild(closeBtn);
  const body = el("div", "modal-body project-create-body");
  body.appendChild(el("div", "modal-error", `Runtime 没有完成项目创建：${message}`));
  const actions = el("div", "modal-actions");
  const ok = el("button", "primary-btn", "知道了");
  actions.appendChild(ok);
  modal.append(head, body, actions);
  const close = showModal(modal);
  closeBtn.addEventListener("click", close);
  ok.addEventListener("click", close);
}

function safeError(error) {
  const message = error instanceof Error ? error.message : String(error || "unknown error");
  const clean = message.replace(/Bearer\s+\S+/gi, "Bearer <redacted>");
  if (/network connection interrupted|Failed to fetch|Gateway timeout/i.test(clean)) {
    return "Runtime 连接短暂中断。项目可能已经创建，请刷新项目列表后再重试。";
  }
  return clean.slice(0, 180);
}

function isTestProject(item) {
  const id = String(item?.project_id || "").toLowerCase();
  const goal = String(item?.goal || "").toLowerCase();
  const name = String(item?.studio_state_meta?.projectName || "").toLowerCase();
  return /(smoke|qa|debug|test|browser|walkthrough|proj_|codex|frontend|review|loop|joint|gate|regression|probe|upload|optimize|empty)/.test(`${id} ${goal} ${name}`);
}
