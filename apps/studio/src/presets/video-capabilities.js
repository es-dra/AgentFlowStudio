export const AFS_VIDEO_DURATION_SECONDS = Array.from({ length: 15 }, (_, index) => index + 1);
export const GENERATION_PATH_CONTRACT_SCHEMA_VERSION = "afs_generation_path_contract.v1";
export const DEFAULT_VIDEO_GENERATION_PATH = "i2v_first_frame";

export const VIDEO_GENERATION_PATH_CONTRACTS = Object.freeze({
  t2v: {
    schema_version: GENERATION_PATH_CONTRACT_SCHEMA_VERSION,
    path_id: "t2v",
    label: "Text to video",
    required_inputs: ["prompt_text"],
    optional_inputs: ["optimized_prompt", "duration_sec", "resolution", "aspect_ratio", "motion", "context_subgraph"],
    allowed_media_families: { inputs: ["text"], output: "video" },
    provider_capability: "video.t2v",
    adoption_state: "planned",
    safety_preflight: { provider_calls_started: false, media_bytes_required_by_preflight: false },
  },
  i2v_first_frame: {
    schema_version: GENERATION_PATH_CONTRACT_SCHEMA_VERSION,
    path_id: "i2v_first_frame",
    label: "Image to video from first frame",
    required_inputs: ["prompt_text", "first_frame_image_asset_id"],
    optional_inputs: ["optimized_prompt", "input_source", "duration_sec", "resolution", "aspect_ratio", "motion", "context_subgraph"],
    allowed_media_families: { inputs: ["text", "image"], output: "video" },
    provider_capability: "video.i2v.first_frame",
    adoption_state: "supported",
    safety_preflight: { provider_calls_started: false, media_bytes_required_by_preflight: false },
  },
  i2v_first_last: {
    schema_version: GENERATION_PATH_CONTRACT_SCHEMA_VERSION,
    path_id: "i2v_first_last",
    label: "Image to video from first and last frames",
    required_inputs: ["prompt_text", "first_frame_image_asset_id", "last_frame_image_asset_id"],
    optional_inputs: ["optimized_prompt", "input_source", "duration_sec", "resolution", "aspect_ratio", "motion", "context_subgraph"],
    allowed_media_families: { inputs: ["text", "image"], output: "video" },
    provider_capability: "video.i2v.first_last_frame",
    adoption_state: "supported",
    safety_preflight: { provider_calls_started: false, media_bytes_required_by_preflight: false },
  },
  reference_video: {
    schema_version: GENERATION_PATH_CONTRACT_SCHEMA_VERSION,
    path_id: "reference_video",
    label: "Reference video to video",
    required_inputs: ["prompt_text", "reference_video_artifact_id"],
    optional_inputs: ["optimized_prompt", "duration_sec", "resolution", "aspect_ratio", "motion", "context_subgraph"],
    allowed_media_families: { inputs: ["text", "video"], output: "video" },
    provider_capability: "video.reference_video",
    adoption_state: "blocked",
    safety_preflight: { provider_calls_started: false, media_bytes_required_by_preflight: false },
  },
  director_to_keyframe: {
    schema_version: GENERATION_PATH_CONTRACT_SCHEMA_VERSION,
    path_id: "director_to_keyframe",
    label: "Director setup to keyframe",
    required_inputs: ["prompt_text", "director_setup"],
    optional_inputs: ["optimized_prompt", "context_subgraph", "aspect_ratio"],
    allowed_media_families: { inputs: ["text", "director"], output: "image" },
    provider_capability: "image.keyframe.director",
    adoption_state: "supported",
    safety_preflight: { provider_calls_started: false, media_bytes_required_by_preflight: false },
  },
  director_to_video: {
    schema_version: GENERATION_PATH_CONTRACT_SCHEMA_VERSION,
    path_id: "director_to_video",
    label: "Director setup to video",
    required_inputs: ["prompt_text", "director_setup"],
    optional_inputs: ["optimized_prompt", "duration_sec", "resolution", "aspect_ratio", "motion", "context_subgraph"],
    allowed_media_families: { inputs: ["text", "director"], output: "video" },
    provider_capability: "video.director",
    adoption_state: "planned",
    safety_preflight: { provider_calls_started: false, media_bytes_required_by_preflight: false },
  },
});

export const DEFAULT_STUDIO_VIDEO_CAPABILITIES = normalizeVideoCapabilities({
  source: "studio_cached_model_projection",
  supportedDurationsSec: [5, 10],
  supportedInputModes: ["first_frame"],
  supportedResolutions: ["720p"],
  supportedAspectRatios: ["16:9", "9:16"],
  supportedGenerationPaths: ["i2v_first_frame", "i2v_first_last"],
  generationPathContracts: VIDEO_GENERATION_PATH_CONTRACTS,
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
  const generationPathContracts = normalizeGenerationPathContracts(raw.generationPathContracts || raw.generation_path_contracts);
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
    supportedGenerationPaths: normalizeStringList(
      raw.supportedGenerationPaths || raw.supported_generation_paths || supportedGenerationPathIds(generationPathContracts),
    ),
    generationPathContract: normalizeGenerationPathContract(
      raw.generationPathContract || raw.generation_path_contract || raw.generation_path,
    ),
    generationPathContracts,
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

export function generationPathContract(pathId = DEFAULT_VIDEO_GENERATION_PATH) {
  const cleanPathId = stringValue(pathId);
  return normalizeGenerationPathContract(VIDEO_GENERATION_PATH_CONTRACTS[cleanPathId] || cleanPathId);
}

export function normalizeGenerationPathContract(value = {}) {
  const raw = typeof value === "string" ? { path_id: value } : objectValue(value);
  const requestedPathId = stringValue(raw.pathId || raw.path_id);
  const fallback = requestedPathId
    ? VIDEO_GENERATION_PATH_CONTRACTS[requestedPathId] || unknownGenerationPathContract(requestedPathId)
    : VIDEO_GENERATION_PATH_CONTRACTS[DEFAULT_VIDEO_GENERATION_PATH];
  const source = { ...fallback, ...raw };
  const media = objectValue(source.allowedMediaFamilies || source.allowed_media_families);
  const preflight = objectValue(source.safePreflight || source.safe_preflight || source.safetyPreflight || source.safety_preflight);
  const adoptionState = stringValue(source.adoptionState || source.adoption_state || fallback.adoption_state);
  return {
    schemaVersion: stringValue(source.schemaVersion || source.schema_version || GENERATION_PATH_CONTRACT_SCHEMA_VERSION),
    pathId: stringValue(source.pathId || source.path_id || fallback.path_id),
    label: stringValue(source.label || fallback.label),
    requiredInputs: normalizeStringList(source.requiredInputs || source.required_inputs || fallback.required_inputs),
    optionalInputs: normalizeStringList(source.optionalInputs || source.optional_inputs || fallback.optional_inputs),
    allowedMediaFamilies: {
      inputs: normalizeStringList(media.inputs || fallback.allowed_media_families.inputs),
      output: stringValue(media.output || fallback.allowed_media_families.output),
    },
    providerCapability: stringValue(source.providerCapability || source.provider_capability || fallback.provider_capability),
    adoptionState,
    safePreflight: {
      providerCallsStarted: Boolean(preflight.providerCallsStarted || preflight.provider_calls_started),
      mediaBytesRequiredByPreflight: Boolean(preflight.mediaBytesRequiredByPreflight || preflight.media_bytes_required_by_preflight),
      providerSubmitAllowed: preflight.providerSubmitAllowed ?? preflight.provider_submit_allowed ?? adoptionState === "supported",
      preflightBlocked: Boolean(preflight.preflightBlocked ?? preflight.preflight_blocked ?? adoptionState !== "supported"),
    },
  };
}

function unknownGenerationPathContract(pathId) {
  return {
    schema_version: GENERATION_PATH_CONTRACT_SCHEMA_VERSION,
    path_id: pathId || "unknown",
    label: pathId || "Unknown generation path",
    required_inputs: [],
    optional_inputs: [],
    allowed_media_families: { inputs: [], output: "unknown" },
    provider_capability: "unknown",
    adoption_state: "blocked",
    safety_preflight: {
      provider_calls_started: false,
      media_bytes_required_by_preflight: false,
      provider_submit_allowed: false,
      preflight_blocked: true,
    },
  };
}

function normalizeGenerationPathContracts(value = {}) {
  const provided = value && typeof value === "object" && !Array.isArray(value) ? value : {};
  const raw = Object.keys(provided).length ? provided : VIDEO_GENERATION_PATH_CONTRACTS;
  return Object.fromEntries(
    Object.entries(raw).map(([pathId, contract]) => [pathId, normalizeGenerationPathContract({ path_id: pathId, ...objectValue(contract) })]),
  );
}

function supportedGenerationPathIds(contracts) {
  return Object.values(contracts || {})
    .filter((contract) => contract?.adoptionState === "supported" && contract?.allowedMediaFamilies?.output === "video")
    .map((contract) => contract.pathId);
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
