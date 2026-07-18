const ACTIVE_PROJECT_KEY = "afs_studio_active_project_id";
const RECENT_PROJECTS_KEY = "afs_studio_recent_project_ids";
const SESSION_PROJECT_KEY = "afs_studio_session_project_id";

export function initialProjectId() {
  const params = new URLSearchParams(window.location.search || "");
  const fromQuery = safeProjectId(params.get("project"));
  if (fromQuery) return fromQuery;
  const stored = safeProjectId(localStorage.getItem(ACTIVE_PROJECT_KEY));
  return stored || sessionProjectId();
}

export function persistActiveProject(projectId) {
  const safe = safeProjectId(projectId);
  if (!safe) return;
  localStorage.setItem(ACTIVE_PROJECT_KEY, safe);
}

export function safeProjectId(value) {
  const text = String(value || "").trim().replace(/[^a-zA-Z0-9_.-]+/g, "-").replace(/^[-._]+|[-._]+$/g, "");
  return text || "";
}

export function rememberProject(projectId) {
  const safe = safeProjectId(projectId);
  if (!safe) return;
  const ids = [safe, ...recentProjectIds().filter((item) => item !== safe)].slice(0, 8);
  try {
    localStorage.setItem(RECENT_PROJECTS_KEY, JSON.stringify(ids));
  } catch {
    /* Local recent project cache is best-effort. */
  }
}

export function recentProjectIds() {
  try {
    const parsed = JSON.parse(localStorage.getItem(RECENT_PROJECTS_KEY) || "[]");
    return Array.isArray(parsed) ? parsed.map(safeProjectId).filter(Boolean).slice(0, 8) : [];
  } catch {
    return [];
  }
}

export function syncProjectUrl(projectId) {
  const url = new URL(window.location.href);
  const safe = safeProjectId(projectId);
  if (safe) url.searchParams.set("project", safe);
  else url.searchParams.delete("project");
  window.history.replaceState({}, "", url);
}

export function clearProjectSession() {
  try {
    localStorage.removeItem(ACTIVE_PROJECT_KEY);
    localStorage.removeItem(RECENT_PROJECTS_KEY);
    localStorage.removeItem(SESSION_PROJECT_KEY);
  } catch {
    // Runtime ownership remains authoritative when local storage is blocked.
  }
  try {
    const url = new URL(window.location.href);
    url.searchParams.delete("project");
    window.history.replaceState({}, "", url);
  } catch {
    // URL cleanup is best-effort during identity teardown.
  }
}

function sessionProjectId() {
  try {
    const stored = safeProjectId(localStorage.getItem(SESSION_PROJECT_KEY));
    if (stored) return stored;
    const next = createSessionProjectId();
    localStorage.setItem(SESSION_PROJECT_KEY, next);
    return next;
  } catch {
    return createSessionProjectId();
  }
}

function createSessionProjectId() {
  const suffix = Math.random().toString(36).slice(2, 8);
  return safeProjectId(`studio-${Date.now()}-${suffix}`);
}
