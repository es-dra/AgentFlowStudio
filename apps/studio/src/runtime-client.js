// Minimal Studio API client. It sends only project ids, safe node context,
// safe generation summaries, Studio state JSON, and explicit user-selected image uploads.

import { assertProjectRequestIdentity } from "./project-identity-gate.js";

const RUNTIME_BASE_STORAGE_KEY = "afs_runtime_base_url";
const RUNTIME_BASE_QUERY_KEYS = ["runtimeBaseUrl", "runtime_base_url", "runtime"];
export const AUTH_TOKEN_STORAGE_KEY = "afs_auth_session_token";

export function runtimeBaseUrl() {
  if (typeof window !== "undefined" && window.location?.protocol?.startsWith("http")) {
    const override = explicitRuntimeBaseUrl();
    if (override) return override;
    return new URL(window.location.href).origin;
  }
  return explicitRuntimeBaseUrl();
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
  if (typeof window !== "undefined") values.push(window.__AFS_RUNTIME_BASE_URL__);
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

async function requestJson(route, { method = "GET", payload = null, meta = null, headers: extraHeaders = null, signal = null } = {}) {
  assertProjectRequestIdentity(route, method, payload);
  const requestMeta = buildRequestMeta(route, method, payload, meta);
  const headers = { "Content-Type": "application/json", Accept: "application/json" };
  headers["X-Client-Request-ID"] = requestMeta.client_request_id;
  if (requestMeta.user_action) headers["X-User-Action"] = requestMeta.user_action;
  if (requestMeta.node_id) headers["X-Studio-Node-ID"] = requestMeta.node_id;
  if (requestMeta.node_type) headers["X-Studio-Node-Type"] = requestMeta.node_type;
  for (const [name, value] of Object.entries(extraHeaders || {})) {
    if (value != null && String(value).trim()) headers[name] = String(value);
  }
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
      signal,
    });
  } catch (fetchError) {
    const error = new Error("Runtime request failed: network connection interrupted");
    error.status = 0;
    error.route = route;
    error.clientRequestId = requestMeta.client_request_id;
    error.cause = fetchError;
    error.errorCode = fetchError?.name === "AbortError"
      ? "request_aborted"
      : "network_connection_interrupted";
    error.retryable = true;
    logStudioRequestFinished(requestMeta, { status: "network_error", status_code: 0, elapsed_ms: Date.now() - started });
    throw error;
  }
  const body = await response.text();
  if (!response.ok) {
    const parsed = parseRuntimeErrorPayload(response, body, requestMeta);
    const error = new Error(staleRuntimeRouteMessage(response, route, body, parsed) || runtimeErrorMessage(response, body, parsed, requestMeta));
    error.status = response.status;
    error.route = route;
    error.payload = parsed?.payload || null;
    error.errorCode = parsed?.error || "";
    error.requestId = parsed?.request_id || response.headers.get("X-Request-ID") || "";
    error.clientRequestId = parsed?.client_request_id || response.headers.get("X-Client-Request-ID") || requestMeta.client_request_id;
    error.generationKind = requestMeta.generation_kind || "";
    dispatchAuthBoundaryRequired(error, route);
    dispatchProjectAccessDenied(error, parsed);
    dispatchProjectIdentityInvalid(error, parsed);
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

function dispatchAuthBoundaryRequired(error, route) {
  if (Number(error?.status || 0) !== 401 || String(route || "").startsWith("/auth/")) return;
  saveAuthToken("");
  try {
    window.dispatchEvent(new CustomEvent("afs:auth-session-expired", {
      detail: { route, request_id: error.requestId || "" },
    }));
  } catch {
    // The Runtime client can run in tests without a browser event target.
  }
}

function dispatchProjectAccessDenied(error, parsed = null) {
  if (error?.errorCode !== "project_access_denied") return;
  try {
    window.dispatchEvent(new CustomEvent("afs:project-access-denied", {
      detail: {
        project_id: parsed?.project_id || projectIdFromRoute(error.route),
        route: error.route,
        request_id: error.requestId,
        client_request_id: error.clientRequestId,
      },
    }));
  } catch {
    // The Studio can run under tests without a browser event target.
  }
}

function dispatchProjectIdentityInvalid(error, parsed = null) {
  const status = Number(error?.status || 0);
  const route = String(error?.route || "");
  const coreProjectLoad = /\/projects\/[^/]+\/(?:studio-state|product-overview)$/.test(route);
  if (status !== 403 && !(status === 404 && coreProjectLoad)) return;
  try {
    window.dispatchEvent(new CustomEvent("afs:project-identity-invalid", {
      detail: {
        project_id: parsed?.project_id || projectIdFromRoute(route),
        status,
        error_code: error?.errorCode || (status === 404 ? "project_not_found" : "project_access_denied"),
        request_id: error?.requestId || "",
        client_request_id: error?.clientRequestId || "",
      },
    }));
  } catch {
    // The Studio can run under tests without a browser event target.
  }
}

function staleRuntimeRouteMessage(response, route, body, parsed = null) {
  if (response.status !== 404) return "";
  const missingPreflight = /\/(keyframe-generations|keyframe-local-edits|video-generations|video-revisions)\/preflight$/.test(route);
  const missingRevisionRoute = /\/video-revisions$/.test(route);
  if (!missingPreflight && !missingRevisionRoute) return "";
  return "当前功能暂时不可用，请刷新页面后重试。";
}

function runtimeErrorMessage(response, body, parsed = null, requestMeta = null) {
  if (response.status === 422 && parsed?.field?.startsWith("创作内容")) {
    return "请先输入创作想法或剧本文本。";
  }
  let detail = "";
  if (parsed?.message || parsed?.error) {
    detail = [
      parsed.message,
      parsed.field ? `字段：${parsed.field}` : "",
      parsed.user_action ? `建议：${parsed.user_action}` : "",
    ]
      .filter(Boolean)
      .join(" ");
  } else {
    detail = cleanTextResponseError(body, response, requestMeta);
  }
  const safeDetail = cleanRuntimeErrorText(detail, 220);
  return safeDetail || "请求暂时失败，请稍后重试。";
}

function parseRuntimeErrorPayload(response, body, requestMeta = null) {
  try {
    const payload = body ? JSON.parse(body) : {};
    const detail = payload?.detail && typeof payload.detail === "object" ? payload.detail : payload;
    if (!detail || typeof detail !== "object" || Array.isArray(detail)) {
      const validation = Array.isArray(detail) ? validationErrorSummary(detail) : { message: "", field: "" };
      return {
        payload,
        message: validation.message || String(payload?.detail || payload?.message || response.statusText || "").trim(),
        field: validation.field,
        error: "",
      };
    }
    const details = detail.details && typeof detail.details === "object" ? detail.details : {};
    return {
      payload,
      error: String(detail.error || detail.detail_code || payload.error || "").trim(),
      message: cleanRuntimeErrorText(
        detail.message || payload.message || (typeof payload.detail === "string" ? payload.detail : ""),
        220,
      ),
      field: validationFieldMessage(details.fields || detail.fields),
      user_action: cleanRuntimeErrorText(detail.user_action, 220),
      request_id: cleanRuntimeErrorText(detail.request_id || payload.request_id, 120),
      client_request_id: cleanRuntimeErrorText(detail.client_request_id || payload.client_request_id, 120),
      project_id: cleanRuntimeErrorText(detail.project_id || payload.project_id, 120),
      node_id: cleanRuntimeErrorText(detail.node_id || payload.node_id, 120),
      action: cleanRuntimeErrorText(detail.action, 80),
      stage: cleanRuntimeErrorText(detail.stage, 80),
      details,
    };
  } catch {
    return { payload: null, message: cleanTextResponseError(body, response, requestMeta), error: "" };
  }
}

function validationErrorMessage(items) {
  return validationErrorSummary(items).message;
}

function validationErrorSummary(items) {
  if (!Array.isArray(items) || !items.length) return { message: "", field: "" };
  const first = items[0] || {};
  const field = safeFieldName(Array.isArray(first.loc) ? first.loc.join(".") : first.field);
  return {
    message: cleanRuntimeErrorText(first.msg || "请求参数校验失败", 160),
    field,
  };
}

function validationFieldMessage(value) {
  const fields = Array.isArray(value) ? value : [];
  if (!fields.length) return "";
  const first = fields[0] || {};
  const field = safeFieldName(Array.isArray(first.loc) ? first.loc.join(".") : (first.field || first.loc));
  const message = cleanRuntimeErrorText(first.message || first.msg, 160);
  const type = cleanRuntimeErrorText(first.type, 120);
  const suffix = fields.length > 1 ? `；共 ${fields.length} 项` : "";
  if (field && message) return `${field}（${message}${type ? ` / ${type}` : ""}${suffix}）`;
  return [field, message || type].filter(Boolean).join("：") + suffix;
}

function cleanRuntimeErrorText(value, limit = 220) {
  if (value == null) return "";
  if (Array.isArray(value)) return validationFieldMessage(value) || value.map((item) => cleanRuntimeErrorText(item, 80)).filter(Boolean).join(" ");
  if (typeof value === "object") {
    const field = validationFieldMessage(value.fields);
    if (field) return field.slice(0, limit);
    for (const key of ["reason", "message", "detail", "error_description"]) {
      const text = cleanRuntimeErrorText(value[key], limit);
      if (text) return text;
    }
    const pairs = [];
    for (const [key, item] of Object.entries(value)) {
      if (pairs.length >= 3) break;
      if (/token|secret|authorization|cookie|base64|bytes|raw|provider/i.test(key)) continue;
      if (item && typeof item === "object") continue;
      const text = cleanRuntimeErrorText(item, 80);
      if (text) pairs.push(`${key}=${text}`);
    }
    return pairs.join(" ").slice(0, limit);
  }
  return String(value || "")
    .replace(/\[object Object\]/g, " ")
    .replace(/Bearer\s+\S+/gi, "Bearer <redacted>")
    .replace(/Authorization\s*[:=]\s*\S+/gi, "Authorization=<redacted>")
    .replace(/\b(?:token|secret|credential)\s*[:=]\s*\S+/gi, "<redacted>")
    .replace(/\bdata:[^\s"'<>]+/gi, "<media-bytes-redacted>")
    .replace(/\bdata[_ -]?base64\b/gi, "<redacted>")
    .replace(/[A-Za-z]:\\[^\s"'<>]+/g, "<local-path-redacted>")
    .replace(/\/(?:home|Users|mnt|var|tmp|opt)\/[^\s"'<>]+/g, "<local-path-redacted>")
    .replace(/https?:\/\/[^\s"'<>]+/g, "<url-redacted>")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, limit);
}

function safeFieldName(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  const parts = raw.split(".").filter((part) => part && part !== "body");
  const labels = parts.map((part) => {
    const normalized = part.toLowerCase().replace(/[^a-z0-9_.-]+/g, "_");
    const known = {
      data_base64: "上传图片内容",
      mime_type: "图片类型",
      filename: "文件名",
      reference_target: "参考目标",
      role: "绑定角色",
      node_id: "节点",
      source_text: "创作内容",
    };
    return known[normalized] || normalized.slice(0, 80);
  }).filter(Boolean);
  return labels.join(".").slice(0, 120);
}

function cleanTextResponseError(body, response, requestMeta = null) {
  const raw = String(body || "").trim();
  if (!raw) return response.statusText || "";
  if (/^\s*</.test(raw) || /<html|<body|<\/\w+>/i.test(raw)) {
    if (response.status === 504) {
      const kind = String(requestMeta?.generation_kind || "");
      if (kind === "text") return "文本处理等待超时；原文已保留，可以恢复同一文本预览或稍后重试。";
      if (kind === "keyframe" || kind === "image") return "图片处理等待超时；可以检查同一任务的已保存结果。";
      if (kind === "video" || kind === "video_revision" || kind === "external_video") {
        return "视频处理等待超时；可以检查同一任务的已保存结果。";
      }
      return "请求等待超时；当前项目内容未改变。";
    }
    return response.statusText || "服务返回了无法读取的响应";
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
    external_video_engine: String(payload?.engine || "").slice(0, 80),
    duration_sec: payload?.duration_sec,
    resolution: payload?.resolution,
    aspect_ratio: payload?.aspect_ratio,
    candidate_count: payload?.candidate_count,
  };
}

function inferUserAction(route, method) {
  if (/\/video-generations\/preflight$/.test(route)) return "preflight_video_generation";
  if (/\/external-video-jobs\/[^/]+\/poll$/.test(route)) return "poll_external_video_generation";
  if (/\/external-video-jobs$/.test(route) && method === "POST") return "create_external_video_generation";
  if (/\/video-generations\/[^/]+\/poll$/.test(route)) return "poll_video_generation";
  if (/\/video-generations$/.test(route) && method === "POST") return "click_generate_video";
  if (/^\/projects\/[^/]+$/.test(route) && method === "DELETE") return "delete_project";
  if (/\/keyframe-local-edits\/preflight$/.test(route)) return "preflight_keyframe_local_edit";
  if (/\/keyframe-generations\/preflight$/.test(route)) return "preflight_keyframe_generation";
  if (/\/keyframe-generations$/.test(route) && method === "POST") return "click_generate_keyframe";
  if (/\/prompt-optimizations$/.test(route)) return "click_optimize_prompt";
  if (/\/image-assets$/.test(route) && method === "POST") return "upload_image_asset";
  if (/\/feedback-candidate-promotions$/.test(route) && method === "POST") return "record_feedback_candidate_promotion";
  if (/\/feedback-candidate-context-overlays$/.test(route) && method === "POST") return "record_feedback_candidate_context_overlay";
  if (/\/human-gate-decisions$/.test(route) && method === "POST") return "record_human_gate_decision";
  if (/\/accepted-generation-plan-packets\/preview$/.test(route) && method === "POST") return "preview_accepted_generation_plan_packet";
  if (/\/script-revisions$/.test(route) && method === "POST") return "create_script_revision";
  if (/\/script-revisions\/[^/]+\/select$/.test(route) && method === "POST") return "select_script_revision";
  if (/\/analysis-candidates$/.test(route) && method === "POST") return "submit_structured_analysis_candidate";
  if (/\/core-assets\/commands\/preview$/.test(route) && method === "POST") return "preview_core_asset_command";
  if (/\/core-assets\/commands\/confirm$/.test(route) && method === "POST") return "confirm_core_asset_command";
  if (/\/core-assets\/commands\/undo$/.test(route) && method === "POST") return "undo_core_asset_command";
  if (/\/production-plan-truth$/.test(route) && method === "GET") return "load_production_plan_truth";
  if (/\/story-plan-candidates$/.test(route) && method === "POST") return "submit_story_plan_candidate";
  if (/\/story-plan-candidates\/[^/]+\/confirm$/.test(route) && method === "POST") return "confirm_story_plan_candidate";
  if (/\/production-plan-commands\/preview$/.test(route) && method === "POST") return "preview_production_plan_command";
  if (/\/production-plan-commands\/confirm$/.test(route) && method === "POST") return "confirm_production_plan_command";
  if (/\/production-plan-commands\/undo$/.test(route) && method === "POST") return "undo_production_plan_command";
  if (/\/m3-zero-cost\/context-packs\/preview$/.test(route) && method === "POST") return "preview_m3_context_pack";
  if (/\/m3-zero-cost\/context-packs\/confirm$/.test(route) && method === "POST") return "confirm_m3_context_pack";
  if (/\/m3-zero-cost\/context-packs\/undo$/.test(route) && method === "POST") return "undo_m3_context_pack";
  if (/\/m3-zero-cost\/audit-truth$/.test(route) && method === "GET") return "load_m3_zero_cost_audit_truth";
  if (/\/m6\/script-plan-asset-bible\/preview$/.test(route) && method === "POST") return "preview_m6_script_plan_asset_bible";
  if (/\/m6\/script-plan-asset-bible\/preview-runs\/latest$/.test(route) && method === "GET") return "recover_latest_m6_script_plan_preview";
  if (/\/m6\/script-plan-asset-bible\/preview-runs\/by-client\//.test(route) && method === "GET") return "recover_m6_script_plan_preview";
  if (/\/m6\/script-plan-asset-bible\/preview-runs\/[^/]+\/cancel$/.test(route) && method === "POST") return "cancel_m6_script_plan_preview";
  if (/\/m6\/script-plan-asset-bible\/preview-runs\/[^/]+$/.test(route) && method === "GET") return "poll_m6_script_plan_preview";
  if (/\/m6\/script-plan-asset-bible\/confirm$/.test(route) && method === "POST") return "confirm_m6_script_plan_asset_bible";
  if (/\/manga-first-l4b\/production-truth$/.test(route) && method === "POST") return "create_manga_first_production_truth";
  if (/\/manga-first-l4b\/workspace$/.test(route) && method === "GET") return "load_manga_first_workspace";
  if (/\/manga-first-l4b\/reference-set-approvals$/.test(route) && method === "POST") return "approve_manga_first_reference_set";
  if (/\/production-runs$/.test(route) && method === "POST") return "create_production_run";
  if (/\/commercial-production\/sample$/.test(route) && method === "POST") return "create_commercial_production_sample";
  if (/\/commercial-production\/stage-gate\/lock$/.test(route) && method === "POST") return "lock_commercial_production_scope";
  if (/\/commercial-production\/revision-requests\/local-rewrite$/.test(route) && method === "POST") return "request_commercial_production_local_rewrite";
  if (/\/domain-crew\/tasks\/[^/]+\/claim$/.test(route) && method === "POST") return "claim_domain_crew_task";
  if (/\/domain-crew\/tasks$/.test(route) && method === "POST") return "create_domain_crew_task";
  if (/\/domain-crew\/messages$/.test(route) && method === "POST") return "send_domain_crew_message";
  if (/\/domain-crew\/handoffs\/[^/]+\/decisions$/.test(route) && method === "POST") return "decide_domain_crew_handoff";
  if (/\/domain-crew\/handoffs$/.test(route) && method === "POST") return "create_domain_crew_handoff";
  if (/\/domain-crew\/conflicts\/[^/]+\/arbitrations$/.test(route) && method === "POST") return "arbitrate_domain_crew_conflict";
  if (/\/domain-crew\/conflicts$/.test(route) && method === "POST") return "escalate_domain_crew_conflict";
  if (/\/domain-crew\/propagation-reconfirmations\/[^/]+\/actions$/.test(route) && method === "POST") return "reconfirm_domain_crew_propagation";
  if (/\/domain-crew$/.test(route) && method === "POST") return "create_domain_crew";
  if (/\/creator-decisions$/.test(route) && method === "POST") return "submit_creator_decision";
  if (/\/quality-reviews$/.test(route) && method === "POST") return "record_production_quality_review";
  if (/\/exports$/.test(route) && method === "POST") return "export_selected_production_revision";
  if (/\/studio-state$/.test(route) && method === "PUT") return "save_studio_state";
  return "";
}

function inferGenerationKind(route) {
  if (route.includes("/embedded-creative-actions") || route.includes("/script-plan-asset-bible") || route.includes("/agent-chat/conversation")) return "text";
  if (route.includes("/keyframe-local-edits")) return "keyframe_local_edit";
  if (route.includes("/external-video-jobs")) return "external_video";
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

export function createRuntimeClient(projectId = "") {
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
    workspaceOverview() {
      return requestJson("/product/workspace-overview");
    },
    projectOverview() {
      return requestJson(`/projects/${encoded}/product-overview`);
    },
    sequenceWorkspace() {
      return requestJson(`/projects/${encoded}/m5/sequence-workspace`);
    },
    adaptiveCanvasOperations(runId = "paid-media-v2") {
      const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
      return requestJson(`/projects/${encoded}/adaptive-canvas-v2/operations-review${query}`);
    },
    previewAdaptiveCanvasOperation(payload) {
      return requestJson(`/projects/${encoded}/adaptive-canvas-v2/operations/command-preview`, { method: "POST", payload });
    },
    confirmFilmCandidate(payload) {
      return requestJson(`/projects/${encoded}/m4/film-candidates/confirm`, { method: "POST", payload });
    },
    previewSequenceImpact(payload) {
      return requestJson(`/projects/${encoded}/m5/impact-preview`, { method: "POST", payload });
    },
    confirmSequenceMutation(payload) {
      return requestJson(`/projects/${encoded}/m5/mutations/confirm`, { method: "POST", payload });
    },
    confirmSequenceAction(payload) {
      return requestJson(`/projects/${encoded}/m5/actions/confirm`, { method: "POST", payload });
    },
    newM6PreviewClientRequestId() {
      return newClientRequestId();
    },
    previewM6ScriptPlanAssetBible(payload, clientRequestId = "") {
      const stableRequestId = String(clientRequestId || newClientRequestId());
      return requestJson(`/projects/${encoded}/m6/script-plan-asset-bible/preview`, {
        method: "POST",
        payload,
        meta: { client_request_id: stableRequestId },
      });
    },
    recoverM6ScriptPlanPreviewByClient(clientRequestId) {
      return requestJson(`/projects/${encoded}/m6/script-plan-asset-bible/preview-runs/by-client/${encodeURIComponent(clientRequestId)}`);
    },
    loadM6ScriptPlanPreviewRun(runId) {
      return requestJson(`/projects/${encoded}/m6/script-plan-asset-bible/preview-runs/${encodeURIComponent(runId)}`);
    },
    loadLatestM6ScriptPlanPreviewRun() {
      return requestJson(`/projects/${encoded}/m6/script-plan-asset-bible/preview-runs/latest`);
    },
    cancelM6ScriptPlanPreviewRun(runId) {
      return requestJson(`/projects/${encoded}/m6/script-plan-asset-bible/preview-runs/${encodeURIComponent(runId)}/cancel`, {
        method: "POST",
        payload: {},
      });
    },
    confirmM6ScriptPlanAssetBible(payload) {
      return requestJson(`/projects/${encoded}/m6/script-plan-asset-bible/confirm`, { method: "POST", payload });
    },
    loadAssetBible() {
      return requestJson(`/projects/${encoded}/m6/asset-bible`);
    },
    previewAssetBibleCommand(payload) {
      return requestJson(`/projects/${encoded}/m6/asset-bible/commands/preview`, { method: "POST", payload });
    },
    confirmAssetBibleCommand(payload) {
      return requestJson(`/projects/${encoded}/m6/asset-bible/commands/confirm`, { method: "POST", payload });
    },
    getCandidateFactReview(query = {}) {
      const revisionId = String(query?.source_revision_id || "").trim();
      const suffix = revisionId ? `?source_revision_id=${encodeURIComponent(revisionId)}` : "";
      return requestJson(`/projects/${encoded}/candidate-facts/review${suffix}`);
    },
    refreshCandidateFactReview(payload) {
      return requestJson(`/projects/${encoded}/candidate-facts/review/refresh`, { method: "POST", payload });
    },
    applyCandidateFactAction(payload) {
      return requestJson(`/projects/${encoded}/candidate-facts/actions`, { method: "POST", payload });
    },
    loadImageAdmission() {
      return requestJson(`/projects/${encoded}/m6/image-admission`);
    },
    previewImageAdmissionCommand(payload) {
      return requestJson(`/projects/${encoded}/m6/image-admission/commands/preview`, { method: "POST", payload });
    },
    confirmImageAdmissionCommand(payload) {
      return requestJson(`/projects/${encoded}/m6/image-admission/commands/confirm`, { method: "POST", payload });
    },
    loadVideoAdmission() {
      return requestJson(`/projects/${encoded}/m6/video-admission`);
    },
    loadVideoAdmissionLane(shotId) {
      return requestJson(`/projects/${encoded}/m6/video-admission/lanes/${encodeURIComponent(String(shotId || ""))}`);
    },
    previewVideoAdmissionCommand(payload) {
      return requestJson(`/projects/${encoded}/m6/video-admission/commands/preview`, { method: "POST", payload });
    },
    previewVideoAdmissionLaneCommand(shotId, payload) {
      return requestJson(`/projects/${encoded}/m6/video-admission/lanes/${encodeURIComponent(String(shotId || ""))}/commands/preview`, { method: "POST", payload });
    },
    confirmVideoAdmissionCommand(payload) {
      return requestJson(`/projects/${encoded}/m6/video-admission/commands/confirm`, { method: "POST", payload });
    },
    confirmVideoAdmissionLaneCommand(shotId, payload) {
      return requestJson(`/projects/${encoded}/m6/video-admission/lanes/${encodeURIComponent(String(shotId || ""))}/commands/confirm`, { method: "POST", payload });
    },
    createMangaFirstProductionTruth(brief, { idempotencyKey = "", includeManifest = false } = {}) {
      return requestJson(`/projects/${encoded}/manga-first-l4b/production-truth`, {
        method: "POST",
        payload: {
          brief,
          idempotency_key: idempotencyKey || `manga-first-l4b-${projectId}-v1`,
          include_manifest: includeManifest === true,
        },
      });
    },
    loadMangaFirstWorkspace() {
      return requestJson(`/projects/${encoded}/manga-first-l4b/workspace`);
    },
    approveMangaFirstReferenceSet(payload) {
      return requestJson(`/projects/${encoded}/manga-first-l4b/reference-set-approvals`, { method: "POST", payload });
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
    preflightKeyframeLocalEdit(payload) {
      return requestJson(`/projects/${encoded}/keyframe-local-edits/preflight`, { method: "POST", payload });
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
    generateExternalVideo(payload) {
      return requestJson(`/projects/${encoded}/external-video-jobs`, { method: "POST", payload });
    },
    pollExternalVideo(jobId) {
      return requestJson(`/projects/${encoded}/external-video-jobs/${encodeURIComponent(jobId)}/poll`, { method: "POST" });
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
    previewAcceptedGenerationPlanPacket(payload = {}) {
      return requestJson(`/projects/${encoded}/accepted-generation-plan-packets/preview`, {
        method: "POST",
        payload: { fixture_mode: "default_unconfirmed", ...payload },
      });
    },
    createScriptRevision(payload) {
      return requestJson(`/projects/${encoded}/script-revisions`, { method: "POST", payload });
    },
    selectScriptRevision(revisionId) {
      return requestJson(`/projects/${encoded}/script-revisions/${encodeURIComponent(revisionId)}/select`, { method: "POST" });
    },
    loadScriptTruth() {
      return requestJson(`/projects/${encoded}/script-truth`);
    },
    submitStructuredAnalysisCandidate(revisionId, payload) {
      return requestJson(`/projects/${encoded}/script-revisions/${encodeURIComponent(revisionId)}/analysis-candidates`, {
        method: "POST",
        payload,
      });
    },
    previewCoreAssetCommand(payload) {
      return requestJson(`/projects/${encoded}/core-assets/commands/preview`, { method: "POST", payload });
    },
    confirmCoreAssetCommand(payload) {
      return requestJson(`/projects/${encoded}/core-assets/commands/confirm`, { method: "POST", payload });
    },
    undoCoreAssetCommand(payload) {
      return requestJson(`/projects/${encoded}/core-assets/commands/undo`, { method: "POST", payload });
    },
    loadProductionPlanTruth() {
      return requestJson(`/projects/${encoded}/production-plan-truth`);
    },
    submitStoryPlanCandidate(payload) {
      return requestJson(`/projects/${encoded}/story-plan-candidates`, { method: "POST", payload });
    },
    confirmStoryPlanCandidate(candidateDigest, payload) {
      return requestJson(`/projects/${encoded}/story-plan-candidates/${encodeURIComponent(candidateDigest)}/confirm`, {
        method: "POST",
        payload,
      });
    },
    previewProductionPlanCommand(payload) {
      return requestJson(`/projects/${encoded}/production-plan-commands/preview`, { method: "POST", payload });
    },
    confirmProductionPlanCommand(payload) {
      return requestJson(`/projects/${encoded}/production-plan-commands/confirm`, { method: "POST", payload });
    },
    undoProductionPlanCommand(payload) {
      return requestJson(`/projects/${encoded}/production-plan-commands/undo`, { method: "POST", payload });
    },
    loadM3ZeroCostAuditTruth() {
      return requestJson(`/projects/${encoded}/m3-zero-cost/audit-truth`);
    },
    loadM3KnowledgePack() {
      return requestJson(`/projects/${encoded}/m3-zero-cost/knowledge-pack`);
    },
    previewM3ContextPack(payload) {
      return requestJson(`/projects/${encoded}/m3-zero-cost/context-packs/preview`, { method: "POST", payload });
    },
    confirmM3ContextPack(payload) {
      return requestJson(`/projects/${encoded}/m3-zero-cost/context-packs/confirm`, { method: "POST", payload });
    },
    undoM3ContextPack(payload) {
      return requestJson(`/projects/${encoded}/m3-zero-cost/context-packs/undo`, { method: "POST", payload });
    },
    recordM3FeedbackCandidate(payload) {
      return requestJson(`/projects/${encoded}/m3-zero-cost/feedback-candidates`, { method: "POST", payload });
    },
    recordM3PromotionDecision(payload) {
      return requestJson(`/projects/${encoded}/m3-zero-cost/promotion-decisions`, { method: "POST", payload });
    },
    recordM3EvaluationReport(payload) {
      return requestJson(`/projects/${encoded}/m3-zero-cost/evaluation-reports`, { method: "POST", payload });
    },
    createProductionRun(payload) {
      return requestJson(`/projects/${encoded}/production-runs`, { method: "POST", payload });
    },
    listProductionRuns() {
      return requestJson(`/projects/${encoded}/production-runs`);
    },
    getProductionRun(runId) {
      return requestJson(`/projects/${encoded}/production-runs/${encodeURIComponent(runId)}`);
    },
    submitCreatorDecision(runId, payload) {
      return requestJson(`/projects/${encoded}/production-runs/${encodeURIComponent(runId)}/creator-decisions`, {
        method: "POST",
        payload,
      });
    },
    recordProductionQualityReview(runId, payload) {
      return requestJson(`/projects/${encoded}/production-runs/${encodeURIComponent(runId)}/quality-reviews`, {
        method: "POST",
        payload,
      });
    },
    exportProductionRun(runId, payload) {
      return requestJson(`/projects/${encoded}/production-runs/${encodeURIComponent(runId)}/exports`, {
        method: "POST",
        payload,
      });
    },
    getDomainCrew() {
      return requestJson(`/projects/${encoded}/domain-crew`);
    },
    createDomainCrew(payload) {
      return requestJson(`/projects/${encoded}/domain-crew`, { method: "POST", payload });
    },
    createDomainCrewTask(payload) {
      return requestJson(`/projects/${encoded}/domain-crew/tasks`, { method: "POST", payload });
    },
    claimDomainCrewTask(taskId, payload) {
      return requestJson(`/projects/${encoded}/domain-crew/tasks/${encodeURIComponent(taskId)}/claim`, { method: "POST", payload });
    },
    sendDomainCrewMessage(payload) {
      return requestJson(`/projects/${encoded}/domain-crew/messages`, { method: "POST", payload });
    },
    createDomainCrewHandoff(payload) {
      return requestJson(`/projects/${encoded}/domain-crew/handoffs`, { method: "POST", payload });
    },
    decideDomainCrewHandoff(handoffId, payload) {
      return requestJson(`/projects/${encoded}/domain-crew/handoffs/${encodeURIComponent(handoffId)}/decisions`, { method: "POST", payload });
    },
    createDomainCrewConflict(payload) {
      return requestJson(`/projects/${encoded}/domain-crew/conflicts`, { method: "POST", payload });
    },
    arbitrateDomainCrewConflict(conflictId, payload) {
      return requestJson(`/projects/${encoded}/domain-crew/conflicts/${encodeURIComponent(conflictId)}/arbitrations`, { method: "POST", payload });
    },
    reconfirmDomainCrewPropagation(affectedRefId, payload) {
      return requestJson(`/projects/${encoded}/domain-crew/propagation-reconfirmations/${encodeURIComponent(affectedRefId)}/actions`, {
        method: "POST",
        payload,
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
    loadEpisodeWorkspace(episodeId, episodeVersionId) {
      const episode = encodeURIComponent(episodeId);
      const version = encodeURIComponent(episodeVersionId);
      return requestJson(`/projects/${encoded}/episodes/${episode}/versions/${version}/workspace`);
    },
    loadCreatorWorkspace() {
      return requestJson(`/projects/${encoded}/creator-workspace`);
    },
    previewShotImpact(payload) {
      return requestJson(`/projects/${encoded}/episode-production-aggregate/shot-impact-preview`, {
        method: "POST",
        payload,
      });
    },
    previewShotRestore(payload) {
      return requestJson(`/projects/${encoded}/episode-production-aggregate/shot-restore-preview`, {
        method: "POST",
        payload,
      });
    },
    diffShotVersions(payload) {
      return requestJson(`/projects/${encoded}/episode-production-aggregate/shot-version-diff`, {
        method: "POST",
        payload,
      });
    },
    executeEpisodeCommand(payload, idempotencyKey) {
      return requestJson(`/projects/${encoded}/episode-production-aggregate/commands`, {
        method: "POST",
        payload,
        headers: { "Idempotency-Key": idempotencyKey },
      });
    },
    createCreatorProductionRequest(payload, idempotencyKey) {
      return requestJson(`/projects/${encoded}/creator-production-requests`, {
        method: "POST",
        payload,
        headers: { "Idempotency-Key": idempotencyKey },
      });
    },
    getProductionControl() {
      return requestJson(`/projects/${encoded}/production-control`);
    },
    getCreatorGoldenTrial() {
      return requestJson(`/projects/${encoded}/creator-golden-trial`);
    },
    getCommercialProduction() {
      return requestJson(`/projects/${encoded}/commercial-production`);
    },
    createCommercialProductionSample(payload, idempotencyKey) {
      return requestJson(`/projects/${encoded}/commercial-production/sample`, {
        method: "POST",
        payload,
        headers: { "Idempotency-Key": idempotencyKey },
      });
    },
    lockCommercialProductionStageGate(payload, idempotencyKey) {
      return requestJson(`/projects/${encoded}/commercial-production/stage-gate/lock`, {
        method: "POST",
        payload,
        headers: { "Idempotency-Key": idempotencyKey },
      });
    },
    requestCommercialProductionLocalRewrite(payload, idempotencyKey) {
      return requestJson(`/projects/${encoded}/commercial-production/revision-requests/local-rewrite`, {
        method: "POST",
        payload,
        headers: { "Idempotency-Key": idempotencyKey },
      });
    },
    recordCreatorGoldenTrialMission(payload, idempotencyKey) {
      return requestJson(`/projects/${encoded}/creator-golden-trial/mission`, {
        method: "POST",
        payload,
        headers: { "Idempotency-Key": idempotencyKey },
      });
    },
    approveCreatorGoldenTrial(payload, idempotencyKey) {
      return requestJson(`/projects/${encoded}/creator-golden-trial/approve`, {
        method: "POST",
        payload,
        headers: { "Idempotency-Key": idempotencyKey },
      });
    },
    dispatchCreatorGoldenTrialNext(payload, idempotencyKey) {
      return requestJson(`/projects/${encoded}/creator-golden-trial/dispatch-next`, {
        method: "POST",
        payload,
        headers: { "Idempotency-Key": idempotencyKey },
      });
    },
    recordProductionControlMission(payload, idempotencyKey) {
      return requestJson(`/projects/${encoded}/production-control/mission`, {
        method: "POST",
        payload,
        headers: { "Idempotency-Key": idempotencyKey },
      });
    },
    saveProductionControlPlan(payload, idempotencyKey) {
      return requestJson(`/projects/${encoded}/production-control/plan`, {
        method: "POST",
        payload,
        headers: { "Idempotency-Key": idempotencyKey },
      });
    },
    approveProductionControlPlan(payload, idempotencyKey) {
      return requestJson(`/projects/${encoded}/production-control/plan/approve`, {
        method: "POST",
        payload,
        headers: { "Idempotency-Key": idempotencyKey },
      });
    },
    runProductionControlAction(runId, payload, idempotencyKey) {
      return requestJson(`/projects/${encoded}/production-control/runs/${encodeURIComponent(runId)}/actions`, {
        method: "POST",
        payload,
        headers: { "Idempotency-Key": idempotencyKey },
      });
    },
    rebuildProductionControl() {
      return requestJson(`/projects/${encoded}/production-control/integrity/rebuild`, { method: "POST" });
    },
    spriteChat(payload) {
      return requestJson(`/projects/${encoded}/sprite/chat`, { method: "POST", payload });
    },
    agentChatConversation(payload, options = {}) {
      return requestJson(`/projects/${encoded}/agent-chat/conversation`, {
        method: "POST",
        payload,
        signal: options?.signal || null,
      });
    },
    newEmbeddedCreativeClientRequestId() {
      return newClientRequestId();
    },
    previewEmbeddedCreativeAction(payload, options = {}) {
      const stableRequestId = String(options?.clientRequestId || newClientRequestId());
      return requestJson(`/projects/${encoded}/embedded-creative-actions/preview`, {
        method: "POST",
        payload,
        meta: { client_request_id: stableRequestId },
        signal: options?.signal || null,
      });
    },
    recoverEmbeddedCreativeActionByClient(clientRequestId) {
      return requestJson(`/projects/${encoded}/embedded-creative-actions/by-client/${encodeURIComponent(clientRequestId)}`);
    },
    applyEmbeddedCreativeShotPlan(clientRequestId, payload) {
      return requestJson(
        `/projects/${encoded}/embedded-creative-actions/by-client/${encodeURIComponent(clientRequestId)}/apply-shot-plan`,
        { method: "POST", payload },
      );
    },
  };
}
