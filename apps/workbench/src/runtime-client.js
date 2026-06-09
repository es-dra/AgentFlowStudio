export const DEFAULT_RUNTIME_BASE_URL = "http://127.0.0.1:8790";

export function normalizeBaseUrl(value) {
  const trimmed = String(value || DEFAULT_RUNTIME_BASE_URL).trim();
  return trimmed.replace(/\/+$/, "");
}

async function requestJson(baseUrl, route, options = {}) {
  const response = await fetch(`${normalizeBaseUrl(baseUrl)}${route}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.headers || {}),
    },
  });
  const body = await response.text();
  if (!response.ok) {
    throw new Error(body || `${response.status} ${response.statusText}`);
  }
  return body ? JSON.parse(body) : {};
}

function postJson(baseUrl, route, payload) {
  return requestJson(baseUrl, route, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

export function createRuntimeClient(baseUrl = DEFAULT_RUNTIME_BASE_URL) {
  return {
    baseUrl: normalizeBaseUrl(baseUrl),
    health() {
      return requestJson(baseUrl, "/health");
    },
    capabilities() {
      return requestJson(baseUrl, "/capabilities");
    },
    projects() {
      return requestJson(baseUrl, "/projects");
    },
    createProject(payload) {
      return postJson(baseUrl, "/projects", payload);
    },
    importProject(manifest) {
      return postJson(baseUrl, "/projects/import", { manifest });
    },
    registerSourceAsset(projectId, payload) {
      return postJson(baseUrl, `/projects/${encodeURIComponent(projectId)}/source-assets`, payload);
    },
    registerContentCard(projectId, payload) {
      return postJson(baseUrl, `/projects/${encodeURIComponent(projectId)}/content-cards`, payload);
    },
    draftCanvas(projectId, payload) {
      return postJson(baseUrl, `/projects/${encodeURIComponent(projectId)}/canvas-draft`, payload);
    },
    updateSceneInspector(projectId, payload) {
      return postJson(baseUrl, `/projects/${encodeURIComponent(projectId)}/scene-inspector`, payload);
    },
    recordReviewDecision(projectId, payload) {
      return postJson(baseUrl, `/projects/${encodeURIComponent(projectId)}/review-decisions`, payload);
    },
    exportProject(projectId) {
      return requestJson(baseUrl, `/projects/${encodeURIComponent(projectId)}/export`);
    },
    workbenchState(projectId) {
      return requestJson(baseUrl, `/projects/${encodeURIComponent(projectId)}/workbench-state`);
    },
    artifact(artifactId) {
      return requestJson(baseUrl, `/artifacts/${encodeURIComponent(artifactId)}`);
    },
    runAssetTest(payload) {
      return postJson(baseUrl, "/runs/asset-test", payload);
    },
    recordFeedback(payload) {
      return postJson(baseUrl, "/feedback", payload);
    },
    runTwoRoundValidate(payload) {
      return postJson(baseUrl, "/runs/two-round-validate", payload);
    },
    providerValidationPlan(payload) {
      return postJson(baseUrl, "/provider/validation-plan", payload);
    },
  };
}
