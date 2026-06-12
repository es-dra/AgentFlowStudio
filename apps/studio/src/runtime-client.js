// Minimal Studio API client. It sends only project ids, safe node context,
// safe manifests, Studio state JSON, and explicit user-selected image uploads.

const FALLBACK_BASE_URL = "http://127.0.0.1:8790";

export function runtimeBaseUrl() {
  if (typeof window !== "undefined" && window.location?.protocol?.startsWith("http")) {
    return window.location.origin;
  }
  return FALLBACK_BASE_URL;
}

async function requestJson(route, { method = "GET", payload = null } = {}) {
  const response = await fetch(`${runtimeBaseUrl()}${route}`, {
    method,
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: payload == null ? undefined : JSON.stringify(payload),
  });
  const body = await response.text();
  if (!response.ok) throw new Error(runtimeErrorMessage(response, body));
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
    retireVisualAsset(assetId, payload) {
      return requestJson(`/projects/${encoded}/visual-assets/${encodeURIComponent(assetId)}/retire`, { method: "POST", payload });
    },
    generateKeyframe(payload) {
      return requestJson(`/projects/${encoded}/keyframe-generations`, { method: "POST", payload });
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
