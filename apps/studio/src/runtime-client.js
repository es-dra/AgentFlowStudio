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
  if (!response.ok) throw new Error(`运行服务请求失败（${response.status}）`);
  return body ? JSON.parse(body) : {};
}

export function createRuntimeClient(projectId = "studio-local-001") {
  const encoded = encodeURIComponent(projectId);
  return {
    projectId,
    optimizePrompt(payload) {
      return requestJson(`/projects/${encoded}/prompt-optimizations`, { method: "POST", payload });
    },
    uploadImageAsset(payload) {
      return requestJson(`/projects/${encoded}/image-assets`, { method: "POST", payload });
    },
    generateKeyframe(payload) {
      return requestJson(`/projects/${encoded}/keyframe-generations`, { method: "POST", payload });
    },
    loadStudioState() {
      return requestJson(`/projects/${encoded}/studio-state`);
    },
    saveStudioState(state) {
      return requestJson(`/projects/${encoded}/studio-state`, { method: "PUT", payload: { state } });
    },
  };
}
