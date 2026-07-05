export const AFS_VIDEO_DURATION_SECONDS = Array.from({ length: 15 }, (_, index) => index + 1);

export const DEFAULT_STUDIO_VIDEO_CAPABILITIES = normalizeVideoCapabilities({
  source: "studio_cached_model_projection",
  supportedDurationsSec: [5, 10],
  supportedInputModes: ["first_frame"],
  supportedResolutions: ["720p"],
  supportedAspectRatios: ["16:9", "9:16"],
});

export function videoDurationLabel(seconds) {
  return `${Number(seconds) || 5}s`;
}

export function parseVideoDurationSeconds(value) {
  const match = String(value || "").match(/\d+/);
  return match ? Number(match[0]) : 5;
}

export function normalizeVideoCapabilities(value = {}) {
  const raw = capabilityPayload(value);
  const duration = objectValue(raw.durationSeconds || raw.duration_seconds || raw.duration);
  const input = objectValue(raw.inputModes || raw.input_modes);
  const resolution = objectValue(raw.resolutions);
  const ratio = objectValue(raw.aspectRatios || raw.aspect_ratios);
  return {
    source: stringValue(raw.source || raw.capability_source || ""),
    providerServiceId: stringValue(raw.providerServiceId || raw.provider_service_id || ""),
    providerCallsStarted: Boolean(raw.providerCallsStarted || raw.provider_calls_started),
    durationSeconds: {
      requested: numberOrNull(duration.requested),
      allowed: normalizeSecondsList(raw.supportedDurationsSec || raw.supported_durations_sec || duration.allowed),
      supported: duration.supported !== false,
      requestContract: duration.requestContract || duration.request_contract || null,
    },
    inputModes: {
      requested: stringValue(input.requested),
      allowed: normalizeStringList(raw.supportedInputModes || raw.supported_input_modes || input.allowed),
      supported: input.supported !== false,
    },
    resolutions: {
      requested: stringValue(resolution.requested),
      allowed: normalizeStringList(raw.supportedResolutions || raw.supported_resolutions || resolution.allowed),
      supported: resolution.supported !== false,
    },
    aspectRatios: {
      requested: stringValue(ratio.requested),
      allowed: normalizeStringList(raw.supportedAspectRatios || raw.supported_aspect_ratios || ratio.allowed),
      supported: ratio.supported !== false,
    },
  };
}

export function videoCapabilitiesFromNode(node, fallback = {}) {
  const cached = node?.params?.videoProviderCapabilities;
  if (cached) return normalizeVideoCapabilities(cached);
  return normalizeVideoCapabilities(fallback);
}

export function videoDurationOptions(capabilities = {}, { includeUnsupported = true } = {}) {
  const normalized = normalizeVideoCapabilities(capabilities);
  const allowed = new Set(normalized.durationSeconds.allowed);
  const limited = allowed.size > 0;
  return AFS_VIDEO_DURATION_SECONDS
    .map((seconds) => {
      const supported = !limited || allowed.has(seconds);
      if (!supported && !includeUnsupported) return null;
      const value = videoDurationLabel(seconds);
      return {
        value,
        label: supported ? value : `${value} - unsupported`,
        disabled: !supported,
        supported,
        reason: supported ? "" : "unsupported_duration",
      };
    })
    .filter(Boolean);
}

export function supportedVideoDurationLabels(capabilities = {}) {
  return videoDurationOptions(capabilities, { includeUnsupported: false }).map((item) => item.value);
}

export function clampVideoDurationLabel(value, capabilities = {}, fallback = "5s") {
  const seconds = parseVideoDurationSeconds(value);
  const normalized = normalizeVideoCapabilities(capabilities);
  const allowed = normalized.durationSeconds.allowed;
  if (allowed.length && !allowed.includes(seconds)) return videoDurationLabel(allowed[0]);
  if (AFS_VIDEO_DURATION_SECONDS.includes(seconds)) return videoDurationLabel(seconds);
  return fallback;
}

export function videoPreflightBlocks(preflight) {
  const blocks = preflight?.blocked_unsupported_combinations;
  return Array.isArray(blocks) ? blocks.filter((item) => item && typeof item === "object") : [];
}

export function videoPreflightBlockMessage(preflight) {
  const blocks = videoPreflightBlocks(preflight);
  if (!blocks.length) return "";
  const first = blocks[0];
  const details = objectValue(first.details);
  const allowed = Array.isArray(details.allowed) ? details.allowed : first.allowed;
  const allowedText = Array.isArray(allowed) && allowed.length
    ? ` Supported values: ${allowed.map((item) => String(item).endsWith("s") ? item : `${item}s`).join(", ")}.`
    : "";
  return `Video preflight blocked before provider submit: ${first.error || first.reason || "unsupported_combination"}.${allowedText} Provider calls not started.`;
}

function capabilityPayload(value) {
  if (!value || typeof value !== "object") return {};
  if (value.provider_capability_limits && typeof value.provider_capability_limits === "object") {
    return value.provider_capability_limits;
  }
  return value;
}

function normalizeSecondsList(values) {
  const seen = new Set();
  const result = [];
  for (const item of Array.isArray(values) ? values : []) {
    const seconds = Number(item);
    if (!Number.isInteger(seconds) || seconds <= 0 || seen.has(seconds)) continue;
    seen.add(seconds);
    result.push(seconds);
  }
  return result.sort((a, b) => a - b);
}

function normalizeStringList(values) {
  const seen = new Set();
  const result = [];
  for (const item of Array.isArray(values) ? values : []) {
    const value = stringValue(item);
    if (!value || seen.has(value)) continue;
    seen.add(value);
    result.push(value);
  }
  return result;
}

function numberOrNull(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function stringValue(value) {
  return String(value || "").trim();
}
