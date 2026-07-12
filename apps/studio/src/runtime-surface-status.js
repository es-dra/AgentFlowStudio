const RUNTIME_STATUS_BOUNDARY = "Service health only; provider smoke, generated-media QA, human acceptance, and public readiness are not claimed.";

export function initialRuntimeSurfaceStatus() {
  return {
    state: "checking",
    label: "Runtime checking",
    authLabel: "Auth unknown",
    providerGateLabel: "Provider gates unknown",
    detail: "Checking Runtime Service health and auth boundary.",
  };
}

export function checkingRuntimeSurfaceStatus(currentStatus = null) {
  return {
    ...(currentStatus || initialRuntimeSurfaceStatus()),
    state: "checking",
    label: "Runtime checking",
    detail: "Checking Runtime Service health and auth boundary.",
  };
}

export async function loadRuntimeSurfaceStatus(runtime, { authState = null, formatError = defaultFormatError } = {}) {
  try {
    const health = await runtime.health();
    const resolvedAuthState = authState || await loadAuthStatus(runtime, formatError);
    return runtimeSurfaceStatusFromHealth(health, resolvedAuthState);
  } catch (error) {
    return {
      state: "unavailable",
      label: "Runtime offline",
      authLabel: "Auth unknown",
      providerGateLabel: "Provider gates unknown",
      detail: `Runtime Service health check failed: ${formatError(error)}`,
    };
  }
}

async function loadAuthStatus(runtime, formatError) {
  try {
    return await runtime.authStatus();
  } catch (error) {
    return {
      auth_status_unknown: true,
      blocked: true,
      error: formatError(error),
    };
  }
}

function runtimeSurfaceStatusFromHealth(health, authState) {
  const serviceReady = health?.status === "ready"
    || health?.service_health?.status === "ready"
    || health?.readiness?.service_ready === true;
  const authUnknown = Boolean(authState?.auth_status_unknown || authState?.blocked);
  const authRequired = Boolean(authState?.auth_required ?? health?.auth_required);
  const authenticated = Boolean(authState?.authenticated);
  const authLabel = authUnknown
    ? "Auth unknown"
    : authRequired
      ? (authenticated ? "Signed in" : "Auth required")
      : "Auth off";
  const providerGateLabel = providerGateSummary(health?.provider_gates);
  const statusText = String(health?.status || health?.service_health?.status || "unknown");
  return {
    state: serviceReady ? (authUnknown ? "attention" : "ready") : "attention",
    label: serviceReady ? "Runtime ready" : "Runtime attention",
    authLabel,
    providerGateLabel,
    detail: [
      `Runtime status: ${statusText}`,
      authLabel,
      providerGateLabel,
      RUNTIME_STATUS_BOUNDARY,
    ].filter(Boolean).join(" | "),
  };
}

function providerGateSummary(providerGates) {
  if (!providerGates || typeof providerGates !== "object" || Array.isArray(providerGates)) {
    return "Provider gates unknown";
  }
  const entries = Object.entries(providerGates).filter(([, value]) => typeof value === "boolean");
  if (!entries.length) return "Provider gates unknown";
  const openCount = entries.filter(([, value]) => value).length;
  return openCount ? `${openCount}/${entries.length} provider gates open` : "Provider gates closed";
}

function defaultFormatError(error) {
  return error instanceof Error ? error.message : String(error || "unknown error");
}
