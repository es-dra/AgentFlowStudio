// Minimal Studio API client: v1 only calls prompt-optimizations.
// 前端只接触 project_id / job_id / artifact_id / safe manifest，
// 不接触 secret、本地路径、signed URL、媒体字节。

const FALLBACK_BASE_URL = "http://127.0.0.1:8790";

export function runtimeBaseUrl() {
  if (typeof window !== "undefined" && window.location?.protocol?.startsWith("http")) {
    return window.location.origin;
  }
  return FALLBACK_BASE_URL;
}

async function postJson(route, payload) {
  const response = await fetch(`${runtimeBaseUrl()}${route}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.text();
  if (!response.ok) throw new Error(`运行服务请求失败（${response.status}）`);
  return body ? JSON.parse(body) : {};
}

export function createRuntimeClient(projectId = "studio-local-001") {
  return {
    projectId,
    optimizePrompt(payload) {
      return postJson(`/projects/${encodeURIComponent(projectId)}/prompt-optimizations`, payload);
    },
  };
}
