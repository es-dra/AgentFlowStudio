const ACTIVE_PROJECT_KEY = "afs_studio_active_project_id";
const RECENT_PROJECTS_KEY = "afs_studio_recent_project_ids";

export function initialProjectId() {
  const params = new URLSearchParams(window.location.search || "");
  const fromQuery = safeProjectId(params.get("project"));
  if (fromQuery) return fromQuery;
  const stored = safeProjectId(localStorage.getItem(ACTIVE_PROJECT_KEY));
  return stored || "studio-local-001";
}

export function persistActiveProject(projectId) {
  localStorage.setItem(ACTIVE_PROJECT_KEY, safeProjectId(projectId) || "studio-local-001");
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
  url.searchParams.set("project", safeProjectId(projectId) || "studio-local-001");
  window.history.replaceState({}, "", url);
}
