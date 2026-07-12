import { hasStudioContent } from "./store-state.js";

const SAVE_AUTH_REQUIRED_EVENT = "afs:studio-save-auth-required";

export function snapshotKey(snapshot) {
  return JSON.stringify(snapshot);
}

export function runtimeSaveFailureState(error) {
  const status = Number(error?.status || 0);
  if (status === 401 || status === 403) {
    dispatchSaveAuthRequired(status);
    return {
      saveState: "需要登录",
      saveMessage: "保存未完成，当前修改已保留在本地；请重新登录后点击重试保存。",
    };
  }
  if (error?.status === 409 || status === 409) {
    return {
      saveState: "保存冲突",
      saveMessage: "项目已在其他窗口更新，当前修改已保留在本地；请先确认最新版本，避免覆盖较新的服务器状态。",
    };
  }
  return {
    saveState: "保存失败",
    saveMessage: "运行服务保存失败，当前修改已保留在本地；请检查连接后重试保存。",
  };
}

export function shouldKeepLocalOverRemote(localState, remoteState, payload) {
  if (!hasStudioContent(localState) || payload?.source !== "runtime") return false;
  const localUpdated = timestampMs(localState.meta?.updated_at);
  const remoteUpdated = Math.max(
    timestampMs(payload?.saved_at),
    timestampMs(remoteState?.meta?.updated_at),
  );
  return localUpdated > remoteUpdated;
}

function dispatchSaveAuthRequired(status) {
  try {
    if (typeof window === "undefined" || typeof window.dispatchEvent !== "function") return;
    window.dispatchEvent(new CustomEvent(SAVE_AUTH_REQUIRED_EVENT, { detail: { status } }));
  } catch {
    /* Auth recovery is best-effort; dirty state remains visible if event dispatch is unavailable. */
  }
}

function timestampMs(value) {
  const parsed = Date.parse(String(value || ""));
  return Number.isFinite(parsed) ? parsed : 0;
}
