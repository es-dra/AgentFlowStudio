// Minimal Studio API client. It sends only project ids, safe node context,
// safe generation summaries, Studio state JSON, and explicit user-selected image uploads.

const FALLBACK_BASE_URL = "http://127.0.0.1:8790";
const RUNTIME_BASE_STORAGE_KEY = "afs_runtime_base_url";
const RUNTIME_BASE_QUERY_KEYS = ["runtimeBaseUrl", "runtime_base_url", "runtime"];
const LOCAL_STATIC_FALLBACK_PORTS = new Set(["8796"]);
export const AUTH_TOKEN_STORAGE_KEY = "afs_auth_session_token";

export function runtimeBaseUrl() {
  if (typeof window !== "undefined" && window.location?.protocol?.startsWith("http")) {
    const override = explicitRuntimeBaseUrl();
    if (override) return override;
    const current = new URL(window.location.href);
    if (isLocalHost(current.hostname) && LOCAL_STATIC_FALLBACK_PORTS.has(current.port)) {
      return FALLBACK_BASE_URL;
    }
    return current.origin;
  }
  return FALLBACK_BASE_URL;
}

export function runtimeMediaUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  try {
    const url = new URL(raw);
    if (["http:", "https:", "blob:", "data:"].includes(url.protocol)) return raw;
    return "";
  } catch {
    const base = runtimeBaseUrl();
    if (raw.startsWith("/")) return `${base}${raw}`;
    try {
      return new URL(raw, `${base}/`).toString();
    } catch {
      return "";
    }
  }
}

function explicitRuntimeBaseUrl() {
  const values = [];
  try {
    const params = new URLSearchParams(window.location.search || "");
    for (const key of RUNTIME_BASE_QUERY_KEYS) values.push(params.get(key));
  } catch {
    // Ignore malformed URL state and use the local Runtime default.
  }
  try {
    values.push(window.localStorage?.getItem(RUNTIME_BASE_STORAGE_KEY));
  } catch {
    // Ignore inaccessible storage and use the local Runtime default.
  }
  values.push(window.__AFS_RUNTIME_BASE_URL__);
  for (const value of values) {
    const normalized = normalizeRuntimeBaseUrl(value);
    if (normalized) return normalized;
  }
  return "";
}

function normalizeRuntimeBaseUrl(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  try {
    const url = new URL(raw);
    if (!["http:", "https:"].includes(url.protocol)) return "";
    if (!isLocalHost(url.hostname)) return "";
    url.pathname = url.pathname.replace(/\/+$/, "");
    url.search = "";
    url.hash = "";
    return url.toString().replace(/\/$/, "");
  } catch {
    return "";
  }
}

function isLocalHost(hostname) {
  return hostname === "127.0.0.1" || hostname === "localhost" || hostname === "::1" || hostname === "[::1]";
}

async function requestJson(route, { method = "GET", payload = null } = {}) {
  const headers = { "Content-Type": "application/json", Accept: "application/json" };
  const token = authToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let response;
  try {
    response = await fetch(`${runtimeBaseUrl()}${route}`, {
      method,
      headers,
      body: payload == null ? undefined : JSON.stringify(payload),
    });
  } catch (fetchError) {
    const error = new Error("Runtime request failed: network connection interrupted");
    error.status = 0;
    error.route = route;
    error.cause = fetchError;
    throw error;
  }
  const body = await response.text();
  if (!response.ok) {
    const error = new Error(staleRuntimeRouteMessage(response, route, body) || runtimeErrorMessage(response, body));
    error.status = response.status;
    error.route = route;
    throw error;
  }
  return body ? JSON.parse(body) : {};
}

function staleRuntimeRouteMessage(response, route, body) {
  if (response.status !== 404) return "";
  const missingPreflight = /\/(keyframe-generations|video-generations|video-revisions)\/preflight$/.test(route);
  const missingRevisionRoute = /\/video-revisions$/.test(route);
  if (!missingPreflight && !missingRevisionRoute) return "";
  const detail = runtimeErrorMessage(response, body);
  return `${detail}. Runtime Service route is missing for ${route}. Restart the 8790 Runtime Service from the current branch and retry.`;
}

function runtimeErrorMessage(response, body) {
  let detail = "";
  try {
    const payload = body ? JSON.parse(body) : {};
    detail = runtimeErrorDetail(payload);
  } catch {
    detail = cleanTextResponseError(body, response);
  }
  const safeDetail = detail.replace(/Bearer\s+\S+/gi, "Bearer <redacted>").slice(0, 220);
  return safeDetail ? `Runtime request failed (${response.status}): ${safeDetail}` : `Runtime request failed (${response.status})`;
}

function runtimeErrorDetail(payload) {
  const detail = payload?.detail ?? payload?.message ?? "";
  if (Array.isArray(detail)) {
    const text = detail.map(runtimeValidationIssueText).filter(Boolean).join(" / ");
    if (text) return text;
    try {
      return JSON.stringify(detail);
    } catch {
      return "Runtime returned validation error details";
    }
  }
  if (detail && typeof detail === "object") {
    const parts = [
      detail.message,
      detail.reason,
      detail.error,
      detail.detail_code,
      detail.field ? `field=${detail.field}` : "",
    ];
    const text = parts.map((part) => String(part || "").trim()).filter(Boolean).join(" / ");
    if (text) return text;
    try {
      return JSON.stringify(detail);
    } catch {
      return "Runtime returned an object error detail";
    }
  }
  return String(detail || "").trim();
}

function runtimeValidationIssueText(issue) {
  if (!issue || typeof issue !== "object") return String(issue || "").trim();
  const loc = Array.isArray(issue.loc) ? issue.loc.filter((item) => item !== "body").join(".") : "";
  const msg = String(issue.msg || issue.message || issue.type || "").trim();
  return [loc ? `field=${loc}` : "", msg].filter(Boolean).join(": ");
}

function cleanTextResponseError(body, response) {
  const raw = String(body || "").trim();
  if (!raw) return response.statusText || "";
  if (/^\s*</.test(raw) || /<html|<body|<\/\w+>/i.test(raw)) {
    return response.status === 504
      ? "Gateway timeout while waiting for image generation; checking saved Runtime assets may recover the result."
      : (response.statusText || "HTTP response was not JSON");
  }
  return raw.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

export function authToken() {
  try {
    return String(window.localStorage?.getItem(AUTH_TOKEN_STORAGE_KEY) || "").trim();
  } catch {
    return "";
  }
}

export function saveAuthToken(token) {
  try {
    if (token) window.localStorage?.setItem(AUTH_TOKEN_STORAGE_KEY, String(token));
    else window.localStorage?.removeItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    /* Browser storage can be blocked; authenticated API calls will fail safely. */
  }
}

function persistSession(payload) {
  if (payload?.session_token) saveAuthToken(payload.session_token);
  return payload;
}

export function createRuntimeClient(projectId = "studio-local-001") {
  const encoded = encodeURIComponent(projectId);
  return {
    projectId,
    health() {
      return requestJson("/health");
    },
    authStatus() {
      return requestJson("/auth/status");
    },
    me() {
      return requestJson("/auth/me");
    },
    login(payload) {
      return requestJson("/auth/login", { method: "POST", payload }).then(persistSession);
    },
    register(payload) {
      return requestJson("/auth/register", { method: "POST", payload }).then(persistSession);
    },
    logout() {
      return requestJson("/auth/logout", { method: "POST" }).finally(() => saveAuthToken(""));
    },
    listProjects() {
      return requestJson("/projects");
    },
    createProject(payload) {
      return requestJson("/projects", { method: "POST", payload });
    },
    optimizePrompt(payload) {
      return requestJson(`/projects/${encoded}/prompt-optimizations`, { method: "POST", payload });
    },
    breakdownStoryboard(payload) {
      return requestJson(`/projects/${encoded}/storyboard-breakdowns`, { method: "POST", payload });
    },
    planShotAssets(payload) {
      return requestJson(`/projects/${encoded}/shot-asset-plans`, { method: "POST", payload });
    },
    uploadImageAsset(payload) {
      return requestJson(`/projects/${encoded}/image-assets`, { method: "POST", payload });
    },
    deleteImageAsset(assetId) {
      return requestJson(`/projects/${encoded}/image-assets/${encodeURIComponent(assetId)}`, { method: "DELETE" });
    },
    listImageAssets() {
      return requestJson(`/projects/${encoded}/image-assets`);
    },
    toMediaUrl(value) {
      return runtimeMediaUrl(value);
    },
    draftAssetCard(payload) {
      return requestJson(`/projects/${encoded}/asset-card-drafts`, { method: "POST", payload });
    },
    promoteVisualAsset(payload) {
      return requestJson(`/projects/${encoded}/visual-assets/promote`, { method: "POST", payload });
    },
    promoteVideoAsset(payload) {
      return requestJson(`/projects/${encoded}/video-assets/promote`, { method: "POST", payload });
    },
    listVisualAssets(status = "fixed") {
      return requestJson(`/projects/${encoded}/visual-assets?status=${encodeURIComponent(status)}`);
    },
    getVisualAsset(assetId) {
      return requestJson(`/projects/${encoded}/visual-assets/${encodeURIComponent(assetId)}`);
    },
    retireVisualAsset(assetId, payload) {
      return requestJson(`/projects/${encoded}/visual-assets/${encodeURIComponent(assetId)}/retire`, { method: "POST", payload });
    },
    preflightKeyframe(payload) {
      return requestJson(`/projects/${encoded}/keyframe-generations/preflight`, { method: "POST", payload });
    },
    generateKeyframe(payload) {
      return requestJson(`/projects/${encoded}/keyframe-generations`, { method: "POST", payload });
    },
    pollKeyframe(jobId) {
      return requestJson(`/projects/${encoded}/keyframe-generations/${encodeURIComponent(jobId)}/poll`, { method: "POST" });
    },
    preflightVideo(payload) {
      return requestJson(`/projects/${encoded}/video-generations/preflight`, { method: "POST", payload });
    },
    generateVideo(payload) {
      return requestJson(`/projects/${encoded}/video-generations`, { method: "POST", payload });
    },
    preflightVideoRevision(payload) {
      return requestJson(`/projects/${encoded}/video-revisions/preflight`, { method: "POST", payload });
    },
    generateVideoRevision(payload) {
      return requestJson(`/projects/${encoded}/video-revisions`, { method: "POST", payload });
    },
    pollVideo(jobId) {
      return requestJson(`/projects/${encoded}/video-generations/${encodeURIComponent(jobId)}/poll`, { method: "POST" });
    },
    cancelVideo(jobId) {
      return requestJson(`/projects/${encoded}/video-generations/${encodeURIComponent(jobId)}/cancel`, { method: "POST" });
    },
    recordFeedback(feedback) {
      return requestJson("/feedback", {
        method: "POST",
        payload: { project_id: projectId, feedback, generated_at: new Date().toISOString() },
      });
    },
    loadStudioState() {
      return requestJson(`/projects/${encoded}/studio-state`);
    },
    saveStudioState(state, expectedVersion = "") {
      const payload = { state };
      if (expectedVersion) payload.expected_version = expectedVersion;
      return requestJson(`/projects/${encoded}/studio-state`, { method: "PUT", payload });
    },
    spriteChat(payload) {
      return requestJson(`/projects/${encoded}/sprite/chat`, { method: "POST", payload });
    },
  };
}
