// Minimal Studio API client. It sends only project ids, safe node context,
// safe manifests, Studio state JSON, and explicit user-selected image uploads.

const FALLBACK_BASE_URL = "http://127.0.0.1:8790";
const RUNTIME_BASE_STORAGE_KEY = "afs_runtime_base_url";
const RUNTIME_BASE_QUERY_KEYS = ["runtimeBaseUrl", "runtime_base_url", "runtime"];

export function runtimeBaseUrl() {
  if (typeof window !== "undefined" && window.location?.protocol?.startsWith("http")) {
    const override = explicitRuntimeBaseUrl();
    if (override) return override;
    const current = new URL(window.location.href);
    if (isLocalHost(current.hostname) && current.port && current.port !== "8790") {
      return FALLBACK_BASE_URL;
    }
    return current.origin;
  }
  return FALLBACK_BASE_URL;
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
  const response = await fetch(`${runtimeBaseUrl()}${route}`, {
    method,
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: payload == null ? undefined : JSON.stringify(payload),
  });
  const body = await response.text();
  if (!response.ok) {
    const error = new Error(runtimeErrorMessage(response, body));
    error.status = response.status;
    error.route = route;
    throw error;
  }
  return body ? JSON.parse(body) : {};
}

function runtimeErrorMessage(response, body) {
  let detail = "";
  try {
    const payload = body ? JSON.parse(body) : {};
    detail = String(payload?.detail || payload?.message || "").trim();
  } catch {
    detail = String(body || "").trim();
  }
  const safeDetail = detail.replace(/Bearer\s+\S+/gi, "Bearer <redacted>").slice(0, 220);
  return safeDetail ? `Runtime request failed (${response.status}): ${safeDetail}` : `Runtime request failed (${response.status})`;
}

export function createRuntimeClient(projectId = "studio-local-001") {
  const encoded = encodeURIComponent(projectId);
  return {
    projectId,
    listProjects() {
      return requestJson("/projects");
    },
    createProject(payload) {
      return requestJson("/projects", { method: "POST", payload });
    },
    optimizePrompt(payload) {
      return requestJson(`/projects/${encoded}/prompt-optimizations`, { method: "POST", payload });
    },
    uploadImageAsset(payload) {
      return requestJson(`/projects/${encoded}/image-assets`, { method: "POST", payload });
    },
    listImageAssets() {
      return requestJson(`/projects/${encoded}/image-assets`);
    },
    promoteVisualAsset(payload) {
      return requestJson(`/projects/${encoded}/visual-assets/promote`, { method: "POST", payload });
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
    preflightVideo(payload) {
      return requestJson(`/projects/${encoded}/video-generations/preflight`, { method: "POST", payload });
    },
    generateVideo(payload) {
      return requestJson(`/projects/${encoded}/video-generations`, { method: "POST", payload });
    },
    pollVideo(jobId) {
      return requestJson(`/projects/${encoded}/video-generations/${encodeURIComponent(jobId)}/poll`, { method: "POST" });
    },
    cancelVideo(jobId) {
      return requestJson(`/projects/${encoded}/video-generations/${encodeURIComponent(jobId)}/cancel`, { method: "POST" });
    },
    loadStudioState() {
      return requestJson(`/projects/${encoded}/studio-state`);
    },
    saveStudioState(state) {
      return requestJson(`/projects/${encoded}/studio-state`, { method: "PUT", payload: { state } });
    },
  };
}
