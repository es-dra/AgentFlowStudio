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

async function requestJson(route, { method = "GET", payload = null, meta = null } = {}) {
  const requestMeta = buildRequestMeta(route, method, payload, meta);
  const headers = { "Content-Type": "application/json", Accept: "application/json" };
  headers["X-Client-Request-ID"] = requestMeta.client_request_id;
  if (requestMeta.user_action) headers["X-User-Action"] = requestMeta.user_action;
  if (requestMeta.node_id) headers["X-Studio-Node-ID"] = requestMeta.node_id;
  if (requestMeta.node_type) headers["X-Studio-Node-Type"] = requestMeta.node_type;
  const token = authToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  let response;
  logStudioRequestStarted(requestMeta);
  const started = Date.now();
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
    error.clientRequestId = requestMeta.client_request_id;
    error.cause = fetchError;
    logStudioRequestFinished(requestMeta, { status: "network_error", status_code: 0, elapsed_ms: Date.now() - started });
    throw error;
  }
  const body = await response.text();
  if (!response.ok) {
    const parsed = parseRuntimeErrorPayload(response, body);
    const error = new Error(staleRuntimeRouteMessage(response, route, body, parsed) || runtimeErrorMessage(response, body, parsed));
    error.status = response.status;
    error.route = route;
    error.payload = parsed?.payload || null;
    error.errorCode = parsed?.error || "";
    error.requestId = parsed?.request_id || response.headers.get("X-Request-ID") || "";
    error.clientRequestId = parsed?.client_request_id || response.headers.get("X-Client-Request-ID") || requestMeta.client_request_id;
    logStudioRequestFinished(requestMeta, {
      status: "failed",
      status_code: response.status,
      request_id: error.requestId,
      error: error.errorCode,
      stage: parsed?.stage || "",
      elapsed_ms: Date.now() - started,
    });
    throw error;
  }
  const result = body ? JSON.parse(body) : {};
  logStudioRequestFinished(requestMeta, {
    status: "succeeded",
    status_code: response.status,
    request_id: response.headers.get("X-Request-ID") || result?.request_id || "",
    elapsed_ms: Date.now() - started,
  });
  return result;
}

function staleRuntimeRouteMessage(response, route, body, parsed = null) {
  if (response.status !== 404) return "";
  const missingPreflight = /\/(keyframe-generations|video-generations|video-revisions)\/preflight$/.test(route);
  const missingRevisionRoute = /\/video-revisions$/.test(route);
  if (!missingPreflight && !missingRevisionRoute) return "";
  const detail = runtimeErrorMessage(response, body, parsed);
  return `${detail}. Runtime Service route is missing for ${route}. Restart the 8790 Runtime Service from the current branch and retry.`;
}

function runtimeErrorMessage(response, body, parsed = null) {
  let detail = "";
  if (parsed?.message || parsed?.error) {
    detail = [parsed.message, parsed.user_action ? `建议：${parsed.user_action}` : "", parsed.request_id ? `请求编号：${parsed.request_id}` : ""]
      .filter(Boolean)
      .join(" ");
  } else {
    detail = cleanTextResponseError(body, response);
  }
  const safeDetail = detail.replace(/Bearer\s+\S+/gi, "Bearer <redacted>").slice(0, 220);
  return safeDetail ? `Runtime request failed (${response.status}): ${safeDetail}` : `Runtime request failed (${response.status})`;
}

function parseRuntimeErrorPayload(response, body) {
  try {
    const payload = body ? JSON.parse(body) : {};
    const detail = payload?.detail && typeof payload.detail === "object" ? payload.detail : payload;
    if (!detail || typeof detail !== "object" || Array.isArray(detail)) {
      return {
        payload,
        message: Array.isArray(detail) ? validationErrorMessage(detail) : String(payload?.detail || payload?.message || response.statusText || "").trim(),
        error: "",
      };
    }
    return {
      payload,
      error: String(detail.error || detail.detail_code || payload.error || "").trim(),
      message: String(detail.message || payload.message || "").trim(),
      user_action: String(detail.user_action || "").trim(),
      request_id: String(detail.request_id || payload.request_id || "").trim(),
      client_request_id: String(detail.client_request_id || payload.client_request_id || "").trim(),
      project_id: String(detail.project_id || payload.project_id || "").trim(),
      node_id: String(detail.node_id || payload.node_id || "").trim(),
      action: String(detail.action || "").trim(),
      stage: String(detail.stage || "").trim(),
      details: detail.details && typeof detail.details === "object" ? detail.details : {},
    };
  } catch {
    return { payload: null, message: cleanTextResponseError(body, response), error: "" };
  }
}

function validationErrorMessage(items) {
  if (!Array.isArray(items) || !items.length) return "";
  const first = items[0] || {};
  const field = Array.isArray(first.loc) ? first.loc.join(".") : "";
  return [first.msg || "请求参数校验失败", field ? `字段：${field}` : ""].filter(Boolean).join(" ");
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

function buildRequestMeta(route, method, payload, meta) {
  const inferred = inferRequestMeta(route, method, payload);
  return {
    ...inferred,
    ...(meta || {}),
    route,
    method,
    client_request_id: String(meta?.client_request_id || inferred.client_request_id || newClientRequestId()),
    started_at: new Date().toISOString(),
  };
}

function inferRequestMeta(route, method, payload) {
  const nodeParameters = payload?.node_parameters && typeof payload.node_parameters === "object" ? payload.node_parameters : {};
  const contextTarget = payload?.context_subgraph?.target_node_id || "";
  return {
    client_request_id: "",
    user_action: inferUserAction(route, method),
    project_id: projectIdFromRoute(route),
    node_id: String(payload?.node_id || contextTarget || nodeParameters.node_id || "").slice(0, 120),
    node_type: String(payload?.node_type || nodeParameters.node_type || "").slice(0, 80),
    generation_kind: inferGenerationKind(route),
    provider_service_id: String(payload?.provider_service_id || "").slice(0, 120),
    has_first_frame: Boolean(payload?.first_frame_image_asset_id),
    first_frame_image_asset_id: String(payload?.first_frame_image_asset_id || "").slice(0, 120),
    video_input_source_mode: String(payload?.input_source?.source_mode || "").slice(0, 80),
    duration_sec: payload?.duration_sec,
    resolution: payload?.resolution,
    aspect_ratio: payload?.aspect_ratio,
    candidate_count: payload?.candidate_count,
  };
}

function inferUserAction(route, method) {
  if (/\/video-generations\/preflight$/.test(route)) return "preflight_video_generation";
  if (/\/video-generations\/[^/]+\/poll$/.test(route)) return "poll_video_generation";
  if (/\/video-generations$/.test(route) && method === "POST") return "click_generate_video";
  if (/^\/projects\/[^/]+$/.test(route) && method === "DELETE") return "delete_project";
  if (/\/keyframe-generations\/preflight$/.test(route)) return "preflight_keyframe_generation";
  if (/\/keyframe-generations$/.test(route) && method === "POST") return "click_generate_keyframe";
  if (/\/prompt-optimizations$/.test(route)) return "click_optimize_prompt";
  if (/\/image-assets$/.test(route) && method === "POST") return "upload_image_asset";
  if (/\/feedback-candidate-promotions$/.test(route) && method === "POST") return "record_feedback_candidate_promotion";
  if (/\/feedback-candidate-context-overlays$/.test(route) && method === "POST") return "record_feedback_candidate_context_overlay";
  if (/\/human-gate-decisions$/.test(route) && method === "POST") return "record_human_gate_decision";
  if (/\/studio-state$/.test(route) && method === "PUT") return "save_studio_state";
  return "";
}

function inferGenerationKind(route) {
  if (route.includes("/video-generations")) return "video";
  if (route.includes("/video-revisions")) return "video_revision";
  if (route.includes("/keyframe-generations")) return "keyframe";
  if (route.includes("/prompt-optimizations")) return "prompt_optimization";
  return "";
}

function projectIdFromRoute(route) {
  const match = String(route || "").match(/^\/projects\/([^/]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

function newClientRequestId() {
  const random = typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID().replace(/-/g, "").slice(0, 12)
    : Math.random().toString(16).slice(2, 14);
  return `cli_${random}`;
}

function logStudioRequestStarted(meta) {
  safeConsoleInfo("studio_request_started", safeRequestLogPayload(meta));
}

function logStudioRequestFinished(meta, patch) {
  safeConsoleInfo("studio_request_finished", safeRequestLogPayload({ ...meta, ...patch }));
}

function safeRequestLogPayload(value) {
  const payload = {};
  for (const [key, item] of Object.entries(value || {})) {
    if (item == null || item === "") continue;
    if (/token|authorization|prompt|secret|base64|data/i.test(key)) continue;
    payload[key] = typeof item === "string" ? item.slice(0, 180) : item;
  }
  return payload;
}

function safeConsoleInfo(label, payload) {
  try {
    console.info(label, payload);
  } catch {
    // Console may be unavailable in embedded test contexts.
  }
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
    deleteProject(projectId) {
      return requestJson(`/projects/${encodeURIComponent(projectId || this.projectId)}`, { method: "DELETE" });
    },
    recordClientEvent(payload) {
      return requestJson("/studio/client-events", { method: "POST", payload });
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
    recordFeedbackCandidatePromotion(payload) {
      return requestJson(`/projects/${encoded}/feedback-candidate-promotions`, { method: "POST", payload });
    },
    recordFeedbackCandidateContextOverlay(payload) {
      return requestJson(`/projects/${encoded}/feedback-candidate-context-overlays`, { method: "POST", payload });
    },
    recordHumanGateDecision(payload) {
      return requestJson(`/projects/${encoded}/human-gate-decisions`, { method: "POST", payload });
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
