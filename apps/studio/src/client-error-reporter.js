const MAX_REPORTS_PER_MINUTE = 8;
const DUPLICATE_SUPPRESS_MS = 30000;
const SENSITIVE_KEY_PATTERN = /token|authorization|cookie|secret|api[_-]?key|password|base64|data_url|prompt|script|content/i;
const SENSITIVE_TEXT_PATTERN = /(Bearer\s+\S+|api[_-]?key\s*[:=]\s*\S+|data:image\/[^;]+;base64,[a-z0-9+/=]+|[a-z]:\\|\/home\/|\/users\/)/gi;

const state = {
  runtime: null,
  projectId: "",
  recent: new Map(),
  windowStart: 0,
  sentInWindow: 0,
  installed: false,
};

export function installClientErrorReporter({ getRuntime, getProjectId } = {}) {
  if (state.installed || typeof window === "undefined") return;
  state.installed = true;
  window.addEventListener("error", (event) => {
    if (isNonActionableBrowserNotification(event)) {
      if (event.cancelable) event.preventDefault();
      return;
    }
    reportClientError({
      event_type: "window_error",
      severity: "error",
      action: "global_error",
      message: event?.message || "Uncaught frontend error",
      error: event?.error || null,
      details: {
        filename: safeFilename(event?.filename),
        line: event?.lineno || 0,
        column: event?.colno || 0,
      },
      getRuntime,
      getProjectId,
    });
  });
  window.addEventListener("unhandledrejection", (event) => {
    reportClientError({
      event_type: "unhandled_rejection",
      severity: "error",
      action: "promise_rejection",
      message: errorMessage(event?.reason) || "Unhandled frontend promise rejection",
      error: event?.reason || null,
      getRuntime,
      getProjectId,
    });
  });
}

export function isNonActionableBrowserNotification(eventOrMessage) {
  const event = typeof eventOrMessage === "object" && eventOrMessage !== null
    ? eventOrMessage
    : null;
  if (event?.error || Number(event?.lineno || 0) > 0 || Number(event?.colno || 0) > 0) {
    return false;
  }
  const message = event ? event.message : eventOrMessage;
  const normalized = String(message || "").trim().replace(/\.$/, "").toLowerCase();
  return normalized === "resizeobserver loop limit exceeded"
    || normalized === "resizeobserver loop completed with undelivered notifications";
}

export function reportClientError({
  event_type = "client_error",
  severity = "error",
  message = "",
  action = "",
  project_id = "",
  details = {},
  error = null,
  runtime = null,
  getRuntime = null,
  getProjectId = null,
} = {}) {
  const runtimeClient = runtime || resolveRuntime(getRuntime);
  const projectId = project_id || resolveProjectId(getProjectId, runtimeClient);
  const cleanMessage = sanitizeText(message || errorMessage(error) || "Frontend error");
  const cleanDetails = sanitizeDetails({
    ...details,
    error_name: error?.name || details?.error_name || "",
    error_code: error?.errorCode || details?.error_code || "",
    route: error?.route || details?.route || "",
    stack: stackSummary(error),
    user_agent: typeof navigator !== "undefined" ? navigator.userAgent : "",
    url_path: typeof window !== "undefined" ? window.location?.pathname || "" : "",
  });
  const key = `${event_type}|${action}|${cleanMessage}`.slice(0, 300);
  if (!shouldReport(key)) return;

  try {
    console.error("studio_client_error", { event_type, action, message: cleanMessage, details: cleanDetails });
  } catch {
    // Console may be unavailable.
  }
  try {
    runtimeClient?.recordClientEvent?.({
      event_type: sanitizeEventType(event_type),
      severity: ["info", "warning", "error"].includes(severity) ? severity : "error",
      message: cleanMessage,
      project_id: String(projectId || "").slice(0, 160),
      action: sanitizeEventType(action || "frontend"),
      details: cleanDetails,
      generated_at: new Date().toISOString(),
    }).catch(() => {});
  } catch {
    // Error reporting must never break the UI.
  }
}

function resolveRuntime(getRuntime) {
  try {
    return typeof getRuntime === "function" ? getRuntime() : state.runtime;
  } catch {
    return state.runtime;
  }
}

function resolveProjectId(getProjectId, runtimeClient) {
  try {
    return typeof getProjectId === "function" ? getProjectId() : runtimeClient?.projectId || state.projectId || "";
  } catch {
    return runtimeClient?.projectId || state.projectId || "";
  }
}

function shouldReport(key) {
  const now = Date.now();
  if (!state.windowStart || now - state.windowStart > 60000) {
    state.windowStart = now;
    state.sentInWindow = 0;
  }
  if (state.sentInWindow >= MAX_REPORTS_PER_MINUTE) return false;
  const last = state.recent.get(key) || 0;
  if (now - last < DUPLICATE_SUPPRESS_MS) return false;
  state.recent.set(key, now);
  state.sentInWindow += 1;
  for (const [item, at] of state.recent.entries()) {
    if (now - at > DUPLICATE_SUPPRESS_MS * 2) state.recent.delete(item);
  }
  return true;
}

function sanitizeDetails(value) {
  const result = {};
  for (const [key, item] of Object.entries(value || {})) {
    if (SENSITIVE_KEY_PATTERN.test(key)) continue;
    if (item == null || item === "") continue;
    if (typeof item === "number" || typeof item === "boolean") {
      result[key.slice(0, 80)] = item;
    } else {
      result[key.slice(0, 80)] = sanitizeText(item).slice(0, 180);
    }
  }
  return result;
}

function sanitizeText(value) {
  return String(value || "")
    .replace(SENSITIVE_TEXT_PATTERN, "<redacted>")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 240);
}

function sanitizeEventType(value) {
  return String(value || "client_error").toLowerCase().replace(/[^a-z0-9_.-]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 80) || "client_error";
}

function errorMessage(error) {
  if (!error) return "";
  if (error instanceof Error) return error.message;
  return String(error || "");
}

function stackSummary(error) {
  const stack = String(error?.stack || "");
  if (!stack) return "";
  return stack.split("\n").slice(0, 3).map((line) => sanitizeText(safeFilename(line))).join(" | ").slice(0, 220);
}

function safeFilename(value) {
  return String(value || "").replace(SENSITIVE_TEXT_PATTERN, "<redacted>").slice(0, 180);
}
