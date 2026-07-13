import { reportClientError } from "./client-error-reporter.js";

export function reportProjectCreateClientError(runtime, error, safeError) {
  const message = safeError(error);
  reportClientError({
    event_type: "project_create_failed",
    severity: "error",
    message,
    action: "create_project",
    runtime,
    error,
  });
}

export function reportProjectDeleteClientError(runtime, error, projectId, safeError) {
  const message = safeError(error);
  reportClientError({
    event_type: "project_delete_failed",
    severity: "error",
    message,
    action: "delete_project",
    project_id: projectId,
    runtime,
    error,
    details: { project_id: projectId },
  });
}

export function reportProjectAccessRecovery(runtime, error, staleProjectId, nextProjectId, safeError) {
  reportClientError({
    event_type: "project_access_recovered",
    severity: "warning",
    message: safeError(error || "project access denied"),
    action: "recover_project_access",
    project_id: staleProjectId,
    runtime,
    error,
    details: {
      stale_project_id: staleProjectId,
      next_project_id: nextProjectId,
    },
  });
}

export async function createProjectWithRetry(runtime, payload) {
  try {
    return await runtime.createProject(payload);
  } catch (error) {
    if (!isTransientRuntimeError(error)) throw error;
    await delay(900);
    return runtime.createProject(payload);
  }
}

export function isTestProject(item) {
  const id = String(item?.project_id || "").toLowerCase();
  const goal = String(item?.goal || "").toLowerCase();
  const name = String(item?.studio_state_meta?.projectName || "").toLowerCase();
  return /(smoke|qa|debug|test|browser|walkthrough|proj_|codex|frontend|review|loop|joint|gate|regression|probe|upload|optimize|empty)/.test(`${id} ${goal} ${name}`);
}

function isTransientRuntimeError(error) {
  const status = Number(error?.status || 0);
  const message = error instanceof Error ? error.message : String(error || "");
  return status === 0 || status === 502 || status === 503 || status === 504 || /network connection interrupted|Failed to fetch|Gateway timeout/i.test(message);
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
