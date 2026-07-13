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
  const staleId = safeRecoveryProjectId(staleProjectId);
  const nextId = safeRecoveryProjectId(nextProjectId);
  const event = {
    event_type: "project_access_recovered",
    severity: "warning",
    message: safeRecoveryMessage(safeError(error || "project access denied")),
    action: "recover_project_access",
    project_id: staleId,
    details: {
      stale_project_id: staleId,
      next_project_id: nextId,
    },
    generated_at: new Date().toISOString(),
  };
  try {
    const pending = runtime?.recordClientEvent?.(event);
    pending?.catch?.(() => {});
  } catch {
    // A successful recovery warning must never break the Studio.
  }
  return event;
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

function safeRecoveryProjectId(value) {
  return String(value || "")
    .trim()
    .replace(/[^0-9A-Za-z_.:-]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 160);
}

function safeRecoveryMessage(value) {
  return String(value || "Project access recovered")
    .replace(/Bearer\s+\S+|api[_-]?key\s*[:=]\s*\S+|[a-z]:\\|\/home\/|\/users\//gi, "<redacted>")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 240) || "Project access recovered";
}
