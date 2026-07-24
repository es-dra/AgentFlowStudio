import { blockProjectIdentity, commitProjectIdentity, projectIdentitySnapshot } from "./project-identity-gate.js";
import { persist, persistTrustedProjectCache, trustedProjectCache } from "./store-persistence.js";
import { shouldKeepLocalOverRemote } from "./store-runtime-save.js";
import {
  hasStudioContent,
  hasStudioMeta,
  initialState,
  normalizeSnapshot,
  replaceSerializable,
  snapshotStudioState,
} from "./store-state.js";
import { verifyStudioCacheAttestation } from "./studio-cache-attestation.js";

export function createStoreProjectTransition({
  getState,
  setState,
  setRuntime,
  runtimePersistence,
  history,
  notify,
}) {
  async function switchProject(projectId, runtime, options = {}) {
    const prepared = await prepareProject(projectId, runtime, options);
    if (prepared.status === "blocked") {
      blockProject(projectId, prepared);
      return { source: "blocked", error: prepared.error, identity: projectIdentitySnapshot() };
    }
    await commitPreparedProject(prepared, runtime, options);
    return {
      source: prepared.source,
      projectId,
      readOnly: prepared.readOnly,
      identity: projectIdentitySnapshot(),
    };
  }

  async function prepareProject(projectId, runtime, options = {}) {
    const targetProjectId = String(projectId || "").trim();
    const accountId = String(options.accountId || "").trim();
    const cached = await trustedProjectCache(targetProjectId, accountId);
    if (String(runtime?.projectId || "") !== targetProjectId) {
      return blockedProject(targetProjectId, accountId, projectIdentityMismatch());
    }
    if (!runtime?.loadStudioState) {
      return preparedProject(targetProjectId, initialState(targetProjectId), { source: "empty", accountId });
    }
    try {
      const payload = await runtime.loadStudioState();
      if (String(payload?.project_id || "") !== targetProjectId) throw projectIdentityMismatch();
      const remoteState = payload?.state;
      if (remoteState && String(remoteState?.meta?.projectId || "") !== targetProjectId) {
        throw projectIdentityMismatch();
      }
      if (options.requireCacheAttestation && remoteState && !await verifyStudioCacheAttestation(
        payload?.cache_identity,
        remoteState,
        { projectId: targetProjectId, accountId },
      )) {
        const error = new Error("Runtime cache identity attestation is invalid");
        error.status = 409;
        error.errorCode = "project_cache_attestation_invalid";
        throw error;
      }
      const remote = normalizeSnapshot({
        ...(remoteState && typeof remoteState === "object" ? remoteState : {}),
        meta: {
          ...(remoteState?.meta && typeof remoteState.meta === "object" ? remoteState.meta : {}),
          projectId: targetProjectId,
        },
      });
      if (cached && shouldKeepLocalOverRemote(cached, remote, payload)) {
        return preparedProject(targetProjectId, cached, {
          source: "local_newer",
          stateVersion: payload?.state_version,
          accountId,
          cacheIdentity: payload?.cache_identity || null,
          cacheState: remoteState,
        });
      }
      const hasRemote = payload?.source === "runtime" && (hasStudioContent(remote) || hasStudioMeta(remoteState));
      return preparedProject(targetProjectId, hasRemote ? remote : initialState(targetProjectId), {
        source: hasRemote ? "runtime" : payload?.source || "empty",
        stateVersion: payload?.state_version,
        accountId,
        cacheIdentity: payload?.cache_identity || null,
        cacheState: remoteState,
      });
    } catch (error) {
      if (isNetworkFailure(error) && cached) {
        return preparedProject(targetProjectId, cached, {
          source: "trusted_cache",
          readOnly: true,
          error,
          accountId,
        });
      }
      return blockedProject(targetProjectId, accountId, error);
    }
  }

  function markProjectLoading(projectId) {
    const state = getState();
    state.ui.projectIdentity = {
      status: "loading",
      requestedProjectId: String(projectId || "").trim(),
      loadedProjectId: "",
      renderedProjectId: "",
      readOnly: true,
      reason: "",
      message: "正在验证目标项目身份并载入权威状态。",
    };
    notify({ full: true });
  }

  async function commitPreparedProject(prepared, runtime, options = {}) {
    if (prepared.cacheIdentity) {
      await persistTrustedProjectCache(prepared.cacheState, prepared.cacheIdentity, {
        accountId: prepared.accountId || options.accountId,
      });
    }
    if (options.isCurrent && !options.isCurrent()) return false;
    setRuntime(runtime);
    runtimePersistence.reset();
    const state = prepared.state;
    setState(state);
    state.meta.projectId = prepared.projectId;
    state.ui.projectIdentity = {
      status: prepared.readOnly ? "cache_read_only" : "ready",
      requestedProjectId: prepared.projectId,
      loadedProjectId: prepared.projectId,
      renderedProjectId: prepared.projectId,
      readOnly: Boolean(prepared.readOnly),
      reason: "",
      message: prepared.readOnly ? "当前显示的是本账号该项目的只读缓存，重新连接并验证后才能修改。" : "",
    };
    runtimePersistence.markHydrated(prepared.stateVersion, snapshotStudioState(state));
    const persistenceMode = prepared.readOnly ? "identity_read_only" : options.persistenceMode;
    if (persistenceMode) runtimePersistence.setMode(persistenceMode);
    clearHistory(history);
    persist(state);
    commitProjectIdentity({
      projectId: prepared.projectId,
      accountId: prepared.accountId || options.accountId,
      cacheProjectId: prepared.readOnly ? prepared.projectId : "",
      readOnly: prepared.readOnly,
    });
    notify({ full: true });
    return true;
  }

  function blockProject(projectId, prepared = {}) {
    runtimePersistence.reset();
    setRuntime(null);
    const state = initialState(projectId);
    setState(state);
    state.meta.projectName = "";
    state.meta.canvasName = "";
    state.nodes = {};
    state.edges = {};
    state.order = [];
    state.assets = [];
    state.assetBible = {};
    state.production = {};
    state.selection = { nodeIds: [], edgeId: null };
    state.ui.saveState = "已阻断";
    state.ui.saveMessage = prepared.message || "项目身份校验未通过，未加载任何项目内容。";
    state.ui.projectIdentity = {
      status: "blocked",
      requestedProjectId: projectId,
      loadedProjectId: "",
      renderedProjectId: "",
      readOnly: true,
      reason: prepared.reason || "project_load_failed",
      message: state.ui.saveMessage,
    };
    clearHistory(history);
    blockProjectIdentity(projectId, {
      accountId: prepared.accountId,
      reason: prepared.reason,
    });
    notify({ full: true });
  }

  return { blockProject, commitPreparedProject, markProjectLoading, prepareProject, switchProject };
}

function preparedProject(projectId, state, {
  source,
  stateVersion = "",
  readOnly = false,
  error = null,
  accountId = "",
  cacheIdentity = null,
  cacheState = null,
} = {}) {
  const completeState = initialState(projectId);
  replaceSerializable(completeState, normalizeSnapshot(state));
  completeState.meta.projectId = projectId;
  return {
    status: "prepared",
    projectId,
    state: completeState,
    source,
    stateVersion: String(stateVersion || ""),
    readOnly: Boolean(readOnly),
    accountId,
    cacheIdentity,
    cacheState,
    error,
  };
}

function projectIdentityMismatch() {
  const error = new Error("Runtime returned a different project identity");
  error.status = 409;
  error.errorCode = "project_identity_mismatch";
  return error;
}

function blockedProject(projectId, accountId, error) {
  return {
    status: "blocked",
    projectId,
    source: "blocked",
    reason: projectLoadFailureReason(error),
    message: projectLoadFailureMessage(error),
    accountId,
    error,
  };
}

function isNetworkFailure(error) {
  return Number(error?.status || 0) === 0
    || String(error?.errorCode || "") === "network_connection_interrupted";
}

function projectLoadFailureReason(error) {
  const status = Number(error?.status || 0);
  if (status === 401) return "authentication_required";
  if (status === 403) return "project_access_denied";
  if (status === 404) return "project_not_found";
  if (String(error?.errorCode || "") === "project_identity_mismatch") return "project_identity_mismatch";
  if (isNetworkFailure(error)) return "network_unavailable";
  return "project_load_failed";
}

function projectLoadFailureMessage(error) {
  const reason = projectLoadFailureReason(error);
  if (reason === "project_access_denied") return "当前账号无权访问此项目。没有加载其他项目，也未发送任何修改请求。";
  if (reason === "project_not_found") return "项目不存在或已被移除。没有加载其他项目，也未发送任何修改请求。";
  if (reason === "authentication_required") return "登录状态已失效。项目内容已清空，请重新登录后再试。";
  if (reason === "network_unavailable") return "暂时无法验证此项目，且没有可信的同项目缓存。未显示其他项目内容。";
  if (reason === "project_identity_mismatch") return "服务返回的项目身份不一致。为保护项目数据，已停止加载和修改。";
  return "项目加载失败。当前视图未显示任何项目事实，也未发送修改请求。";
}

function clearHistory(history) {
  history.past = [];
  history.future = [];
}
