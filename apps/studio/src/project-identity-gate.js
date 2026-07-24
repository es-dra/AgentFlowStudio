const MUTATION_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);
const PROJECT_ROUTE_RE = /^\/projects\/([^/?#]+)/;

let gate = emptyGate();

export function beginProjectIdentityLoad(projectId, accountId = "") {
  const requested = safeIdentity(projectId);
  gate = {
    ...emptyGate(),
    initialized: true,
    status: "loading",
    requested_project_id: requested,
    url_project_id: requested,
    account_id: safeIdentity(accountId),
  };
  publish();
  return projectIdentitySnapshot();
}

export function commitProjectIdentity({
  projectId,
  accountId = "",
  cacheProjectId = "",
  readOnly = false,
} = {}) {
  const project = safeIdentity(projectId);
  const account = safeIdentity(accountId);
  if (!project) throw identityError("project_identity_missing");
  const ids = [project, cacheProjectId || project].map(safeIdentity);
  if (ids.some((item) => item !== project)) throw identityError("project_identity_mismatch");
  gate = {
    initialized: true,
    status: readOnly ? "cache_read_only" : "ready",
    requested_project_id: project,
    authorized_project_id: readOnly ? "" : project,
    loaded_project_id: project,
    cache_project_id: safeIdentity(cacheProjectId),
    rendered_project_id: project,
    active_project_id: project,
    url_project_id: project,
    account_id: account,
    read_only: Boolean(readOnly),
    reason: "",
  };
  publish();
  return projectIdentitySnapshot();
}

export function blockProjectIdentity(projectId, {
  accountId = "",
  reason = "project_load_failed",
} = {}) {
  const requested = safeIdentity(projectId);
  gate = {
    ...emptyGate(),
    initialized: true,
    status: "blocked",
    requested_project_id: requested,
    url_project_id: requested,
    account_id: safeIdentity(accountId),
    reason: safeIdentity(reason) || "project_load_failed",
  };
  publish();
  return projectIdentitySnapshot();
}

export function clearProjectIdentity() {
  gate = emptyGate();
  publish();
}

export function commitProjectListIdentity(accountId = "") {
  gate = {
    ...emptyGate(),
    initialized: true,
    status: "project_list_ready",
    account_id: safeIdentity(accountId),
    read_only: true,
  };
  publish();
  return projectIdentitySnapshot();
}

export function projectIdentitySnapshot() {
  return { ...gate };
}

export function projectIdentityAllowsMutation(projectId) {
  const project = safeIdentity(projectId);
  if (!gate.initialized) return true;
  if (gate.status !== "ready" || gate.read_only || !project) return false;
  const ids = [
    gate.requested_project_id,
    gate.authorized_project_id,
    gate.loaded_project_id,
    gate.rendered_project_id,
    gate.active_project_id,
    gate.url_project_id,
    browserUrlProjectId(),
  ];
  return ids.every((item) => item === project);
}

export function assertProjectRequestIdentity(route, method = "GET", payload = null) {
  const normalizedMethod = String(method || "GET").toUpperCase();
  if (!MUTATION_METHODS.has(normalizedMethod)) return;
  if (isIdentityBoundaryMutation(route, normalizedMethod)) return;
  if (!gate.initialized) throw identityError("project_identity_not_ready");
  if (String(route || "") === "/projects" && normalizedMethod === "POST") {
    const creationContextReady = gate.status === "project_list_ready"
      || (gate.status === "ready" && !gate.read_only);
    if (creationContextReady && safeIdentity(payload?.project_id)) return;
    throw identityError("project_identity_not_ready");
  }
  const projectId = projectIdForRequest(route, payload);
  if (!projectIdentityAllowsMutation(projectId)) {
    throw identityError(gate.status === "cache_read_only"
      ? "project_cache_read_only"
      : "project_identity_not_ready");
  }
}

function projectIdForRequest(route, payload) {
  const match = String(route || "").match(PROJECT_ROUTE_RE);
  if (match) {
    try {
      return safeIdentity(decodeURIComponent(match[1]));
    } catch {
      return "";
    }
  }
  if (String(route || "") === "/feedback") return safeIdentity(payload?.project_id);
  return "";
}

function isIdentityBoundaryMutation(route, method) {
  const path = String(route || "");
  if (path.startsWith("/auth/")) return true;
  if (path === "/studio/client-events") return true;
  return false;
}

function identityError(code) {
  const error = new Error("当前项目尚未完成身份校验，未发送任何修改请求。");
  error.status = 0;
  error.errorCode = code;
  error.retryable = code !== "project_identity_mismatch";
  return error;
}

function emptyGate() {
  return {
    initialized: false,
    status: "uninitialized",
    requested_project_id: "",
    authorized_project_id: "",
    loaded_project_id: "",
    cache_project_id: "",
    rendered_project_id: "",
    active_project_id: "",
    url_project_id: "",
    account_id: "",
    read_only: true,
    reason: "",
  };
}

function browserUrlProjectId() {
  try {
    if (typeof window === "undefined") return "";
    return safeIdentity(new URLSearchParams(window.location?.search || "").get("project"));
  } catch {
    return "";
  }
}

function safeIdentity(value) {
  return String(value || "").trim().replace(/[^a-zA-Z0-9_.-]+/g, "-").replace(/^[-._]+|[-._]+$/g, "");
}

function publish() {
  try {
    if (typeof window !== "undefined") window.__AFS_PROJECT_IDENTITY__ = projectIdentitySnapshot();
  } catch {
    // The in-memory gate remains authoritative if the diagnostic mirror is unavailable.
  }
}
