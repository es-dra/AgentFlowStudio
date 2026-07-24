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
import { projectDisplayName, requestProjectName } from "./studio-project-name-dialog.js";
import {
  createProjectWithRetry,
  isTestProject,
  reportProjectCreateClientError,
  reportProjectDeleteClientError,
} from "./studio-project-runtime-ops.js";
import {
  beginProjectIdentityLoad,
  blockProjectIdentity,
  commitProjectListIdentity,
  clearProjectIdentity,
} from "./project-identity-gate.js";
import {
  emptyProjectRuntimeClient, isCanonicalGraphProject,
  isReadOnlyProjectionProject,
  safeProjectRuntimeError as safeError,
} from "./studio-project-controller-policy.js";

const EMPTY_PROJECT_ID = "studio-empty";

export function createProjectController({ store, getRuntime, setRuntime, render, onProjectReady }) {
  let projectSummaries = [];
  let showAllProjects = false;
  let currentAuthUser = null;
  let projectAccessRecovery = null;
  let projectTransitionEpoch = 0;

  async function applyProject(projectId, runtimeClient, {
    projectName,
    syncAssets = true,
    navigation = "replace",
  } = {}) {
    const safe = safeProjectId(projectId);
    if (!safe) {
      await showEmptyProjectState();
      return;
    }
    const transitionEpoch = ++projectTransitionEpoch;
    const transitionCurrent = () => transitionEpoch === projectTransitionEpoch;
    const accountId = String(currentAuthUser?.user_id || "").trim();
    beginProjectIdentityLoad(safe, accountId);
    store.markProjectLoading(safe);
    const readOnlyProjection = isReadOnlyProjectionProject(safe, projectSummaries);
    const prepared = await store.prepareProject(safe, runtimeClient, {
      accountId,
      requireCacheAttestation: Boolean(accountId),
      persistenceMode: readOnlyProjection ? "production_graph_read_only" : "studio_state",
    });
    if (!transitionCurrent()) return { status: "stale" };
    if (prepared.status === "blocked") {
      setRuntime(runtimeClient, { attachStore: false });
      store.blockProject(safe, prepared);
      blockProjectIdentity(safe, { accountId, reason: prepared.reason });
      syncProjectUrl(safe, { replace: navigation !== "push" });
      render();
      return { status: "blocked", reason: prepared.reason, error: prepared.error };
    }
    setRuntime(runtimeClient, { attachStore: false });
    await store.commitPreparedProject(prepared, runtimeClient, {
      accountId,
      isCurrent: transitionCurrent,
      persistenceMode: readOnlyProjection ? "production_graph_read_only" : "studio_state",
    });
    if (!transitionCurrent()) return { status: "stale" };
    persistActiveProject(safe);
    rememberProject(safe);
    syncProjectUrl(safe, { replace: navigation !== "push" });
    if (prepared.readOnly) {
      render();
      return { status: "cache_read_only", source: prepared.source };
    }
    if (projectName) {
      store.set((s) => {
        s.meta.projectName = projectName;
        if (!s.meta.canvasName) s.meta.canvasName = "画布 1";
      }, { history: false });
    }
    if (readOnlyProjection) store.setRuntimePersistenceMode("production_graph_read_only");
    else await store.flushRuntimeSave();
    if (syncAssets && !readOnlyProjection) {
      await syncRuntimeAssets(store, runtimeClient, { isCurrent: transitionCurrent });
    }
    if (!transitionCurrent()) return { status: "stale" };
    await onProjectReady?.(runtimeClient, { isCurrent: transitionCurrent });
    if (!transitionCurrent()) return { status: "stale" };
    await refreshProjectSummaries();
    return { status: prepared.readOnly ? "cache_read_only" : "ready", source: prepared.source };
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
    if (!runtime.projectId || runtime.projectId === EMPTY_PROJECT_ID) {
      await showEmptyProjectState();
      return;
    }
    const summary = projectSummaries.find((item) => item.project_id === runtime.projectId);
    await applyProject(runtime.projectId, runtime, {
      projectName: summary ? projectDisplayName(summary) : "",
      navigation: "replace",
    });
  }

  function currentProjectIsReadOnlyProjection() {
    const runtime = getRuntime();
    const currentId = runtime.projectId || store.get().meta.projectId;
    return isReadOnlyProjectionProject(currentId, projectSummaries);
  }

  function currentProjectHasCanonicalGraphAuthority() {
    return isCanonicalGraphProject(getRuntime().projectId || store.get().meta.projectId, projectSummaries);
  }

  async function recoverProjectAccessDenied(error = null) {
    if (projectAccessRecovery) return projectAccessRecovery;
    projectAccessRecovery = (async () => {
      projectTransitionEpoch += 1;
      const runtime = getRuntime();
      const currentId = runtime.projectId || store.get().meta.projectId;
      const failure = projectIdentityFailure(error);
      const prepared = {
        reason: failure.reason,
        message: failure.message,
        error,
      };
      store.blockProject(currentId, prepared);
      blockProjectIdentity(currentId, {
        accountId: currentAuthUser?.user_id || "",
        reason: prepared.reason,
      });
      syncProjectUrl(currentId);
      render();
      return true;
    })().finally(() => {
      projectAccessRecovery = null;
    });
    return projectAccessRecovery;
  }

  async function switchProject(projectId) {
    const safe = safeProjectId(projectId);
    if (!safe || safe === getRuntime().projectId) {
      return;
    }
    const nextRuntime = createRuntimeClient(safe);
    return applyProject(safe, nextRuntime, { navigation: "push" });
  }

  async function loadRequestedProject(projectId) {
    const safe = safeProjectId(projectId);
    if (!safe || safe === EMPTY_PROJECT_ID) {
      await showEmptyProjectState();
      return { status: "empty" };
    }
    return applyProject(safe, createRuntimeClient(safe), { navigation: "replace" });
  }

  async function retryCurrentProject() {
    const currentId = safeProjectId(getRuntime().projectId || store.get().meta.projectId);
    if (!currentId || currentId === EMPTY_PROJECT_ID) return { status: "empty" };
    return applyProject(currentId, createRuntimeClient(currentId), { navigation: "replace" });
  }

  async function createNewProject() {
    try {
      const name = await requestProjectName(projectSummaries);
      if (name === null) return false;
      const suffix = Math.random().toString(36).slice(2, 8);
      const projectId = safeProjectId(`studio-${Date.now()}-${suffix}`);
      const projectName = name.trim() || "未命名项目";
      const nextRuntime = createRuntimeClient(projectId);
      await createProjectWithRetry(nextRuntime, {
        project_id: projectId,
        project_type: "studio_creator_authoring",
        goal: projectName,
      });
      await applyProject(projectId, nextRuntime, { projectName, syncAssets: false });
      return true;
    } catch (error) {
      reportProjectCreateClientError(getRuntime(), error, safeError);
      showProjectCreateError(error);
      return false;
    }
  }

  async function deleteProject(project) {
    const projectId = safeProjectId(project?.project_id || project);
    if (!projectId) return;
    const label = projectDisplayName(resolveProjectSummary(projectId, project)) || projectId;
    const confirmed = await requestProjectDeleteConfirmation(label);
    if (!confirmed) return;
    try {
      await getRuntime().deleteProject(projectId);
      const currentId = getRuntime().projectId || store.get().meta.projectId;
      await refreshProjectSummaries();
      if (projectId === currentId) {
        const next = projectSummaries.find((item) => item.project_id && item.project_id !== projectId);
        if (next?.project_id) {
          await switchProject(next.project_id);
        } else {
          await showEmptyProjectState();
        }
      }
      showProjectDeleteSuccess(label, projectSummaries.length);
    } catch (error) {
      reportProjectDeleteClientError(getRuntime(), error, projectId, safeError);
      showProjectDeleteError(error);
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
    if (!projectSummaries.length && currentId && currentId !== EMPTY_PROJECT_ID && !known.some((item) => item.project_id === currentId)) {
      known.unshift(current);
    }
    const recent = recentProjectIds();
    const normal = known.filter((item) => !isTestProject(item)).slice(0, 5);
    const normalIds = new Set(normal.map((item) => item.project_id));
    return showAllProjects ? known : known.filter((item) =>
      item.project_id === currentId || recent.includes(item.project_id) || normalIds.has(item.project_id));
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
    recoverProjectAccessDenied,
    currentProjectIsReadOnlyProjection,
    currentProjectHasCanonicalGraphAuthority,
    switchProject,
    loadRequestedProject,
    retryCurrentProject,
    createNewProject,
    deleteProject,
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

  function resolveProjectSummary(projectId, project) {
    if (project && typeof project === "object") return project;
    return projectSummaries.find((item) => item.project_id === projectId) || { project_id: projectId };
  }

  async function showEmptyProjectState() {
    projectTransitionEpoch += 1;
    const nextRuntime = emptyProjectRuntimeClient();
    clearProjectIdentity();
    persistActiveProject(EMPTY_PROJECT_ID);
    syncProjectUrl(EMPTY_PROJECT_ID);
    setRuntime(nextRuntime, { attachStore: false });
    await store.switchProject(EMPTY_PROJECT_ID, nextRuntime);
    commitProjectListIdentity(currentAuthUser?.user_id || "");
    syncProjectUrl("");
    store.set((s) => {
      s.meta.projectName = "暂无项目";
      s.meta.canvasName = "请新建项目";
      s.nodes = {};
      s.edges = {};
      s.order = [];
      s.assets = [];
      s.selection = { nodeIds: [], edgeId: null };
      s.ui.saveState = "本地暂存";
      s.ui.saveMessage = "当前没有项目，请新建项目后开始创作。";
    }, { history: false, persist: false });
    render();
  }
}

function isProjectAccessDeniedError(error) {
  if (!error) return false;
  const code = String(error.errorCode || error.payload?.error || error.payload?.detail?.error || "").trim();
  if (code === "project_access_denied") return true;
  const status = Number(error.status || 0);
  const message = error instanceof Error ? error.message : String(error || "");
  return status === 403 && /project[_ ]access[_ ]denied|没有访问该项目的权限/i.test(message);
}

function projectIdentityFailure(error) {
  const status = Number(error?.status || 0);
  const code = String(error?.errorCode || "").trim();
  if (isProjectAccessDeniedError(error)) {
    return {
      reason: "project_access_denied",
      message: "当前账号无权访问此项目。没有加载其他项目，也未发送任何修改请求。",
    };
  }
  if (status === 404 || code === "project_not_found") {
    return {
      reason: "project_not_found",
      message: "项目不存在或已被移除。没有加载其他项目，也未发送任何修改请求。",
    };
  }
  if (code === "project_identity_mismatch") {
    return {
      reason: "project_identity_mismatch",
      message: "服务返回的项目身份不一致。当前视图已清空，未发送任何修改请求。",
    };
  }
  return {
    reason: "project_load_failed",
    message: "项目身份校验失败。当前视图已清空，未发送任何修改请求。",
  };
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

function requestProjectDeleteConfirmation(projectName) {
  return new Promise((resolve) => {
    const modal = el("div", "modal compact project-delete-modal");
    const head = el("div", "modal-head");
    head.appendChild(el("strong", "", "删除项目"));
    const closeBtn = el("button", "modal-close");
    closeBtn.innerHTML = icon("x", 15);
    head.appendChild(el("span", "head-spacer"));
    head.appendChild(closeBtn);

    const body = el("div", "modal-body project-delete-body");
    body.appendChild(el("p", "", `确定要删除项目“${projectName}”吗？`));
    body.appendChild(el("p", "", "删除后该项目将从项目列表中移除。"));
    body.appendChild(el("p", "modal-error", "此操作可能会删除该项目的画布状态、素材引用、任务记录和生成历史。"));

    const actions = el("div", "modal-actions");
    const cancel = el("button", "ghost-btn", "取消");
    const confirm = el("button", "primary-btn danger", "确认删除");
    actions.append(cancel, confirm);
    modal.append(head, body, actions);

    let settled = false;
    const close = showModal(modal, { onClose: () => { if (!settled) resolve(false); } });
    const finish = (value) => {
      if (settled) return;
      settled = true;
      close();
      resolve(value);
    };
    cancel.addEventListener("click", () => finish(false));
    closeBtn.addEventListener("click", () => finish(false));
    confirm.addEventListener("click", () => finish(true));
  });
}

function showProjectDeleteError(error) {
  const message = safeError(error);
  const modal = el("div", "modal compact project-delete-modal");
  const head = el("div", "modal-head");
  head.appendChild(el("strong", "", "项目删除失败"));
  const closeBtn = el("button", "modal-close");
  closeBtn.innerHTML = icon("x", 15);
  head.appendChild(el("span", "head-spacer"));
  head.appendChild(closeBtn);
  const body = el("div", "modal-body project-delete-body");
  body.appendChild(el("div", "modal-error", `Runtime 没有完成项目删除：${message}`));
  const actions = el("div", "modal-actions");
  const ok = el("button", "primary-btn", "知道了");
  actions.appendChild(ok);
  modal.append(head, body, actions);
  const close = showModal(modal);
  closeBtn.addEventListener("click", close);
  ok.addEventListener("click", close);
}

function showProjectDeleteSuccess(projectName, remainingCount = 0) {
  const modal = el("div", "modal compact project-delete-modal");
  const head = el("div", "modal-head");
  head.appendChild(el("strong", "", "项目删除成功"));
  const closeBtn = el("button", "modal-close");
  closeBtn.innerHTML = icon("x", 15);
  head.appendChild(el("span", "head-spacer"));
  head.appendChild(closeBtn);
  const body = el("div", "modal-body project-delete-body");
  body.appendChild(el("p", "", `项目“${projectName}”已从项目列表中移除。`));
  body.appendChild(el("p", "", remainingCount > 0
    ? "如果删除的是当前项目，系统已自动切换到其他可用项目。"
    : "当前已经没有项目，请点击“新建项目”后继续创作。"));
  const actions = el("div", "modal-actions");
  const ok = el("button", "primary-btn", "知道了");
  actions.appendChild(ok);
  modal.append(head, body, actions);
  const close = showModal(modal);
  closeBtn.addEventListener("click", close);
  ok.addEventListener("click", close);
}
