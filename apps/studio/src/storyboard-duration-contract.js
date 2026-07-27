export const DEFAULT_SHORT_FILM_DURATION_SECONDS = 120;
export const MIN_STORYBOARD_DURATION_SECONDS = 5;
export const MAX_STORYBOARD_DURATION_SECONDS = 3600;

export function isValidStoryboardDuration(value) {
  return normalizedDuration(value) !== null;
}

export function productionBriefForSource(sourceText, override = null) {
  const selected = normalizedDuration(override?.target_duration_seconds);
  if (selected !== null) {
    const source = String(override?.duration_source || "creator_selected");
    return {
      target_duration_seconds: selected,
      duration_source: ["script_explicit", "creator_default", "creator_selected"].includes(source)
        ? source
        : "creator_selected",
      tolerance_seconds: normalizedTolerance(override?.tolerance_seconds, selected, source),
      requires_creator_confirmation: true,
      ...sourceBinding(override),
    };
  }
  const declared = declaredDurations(sourceText);
  if (declared.values.length === 1) {
    const target = declared.values[0];
    return {
      target_duration_seconds: target,
      duration_source: "script_explicit",
      tolerance_seconds: declared.approximate ? Math.max(2, round2(target * 0.1)) : 1,
      requires_creator_confirmation: true,
    };
  }
  return {
    target_duration_seconds: DEFAULT_SHORT_FILM_DURATION_SECONDS,
    duration_source: "creator_default",
    tolerance_seconds: round2(DEFAULT_SHORT_FILM_DURATION_SECONDS * 0.1),
    requires_creator_confirmation: true,
    ...(declared.values.length > 1 ? { source_duration_conflict: true } : {}),
    ...sourceBinding(override),
  };
}

function sourceBinding(value) {
  const revisionId = String(value?.source_revision_id || "").replace(/[^A-Za-z0-9_.:-]/g, "").slice(0, 140);
  const digest = String(value?.source_digest || "").trim().toLowerCase();
  return {
    ...(revisionId ? { source_revision_id: revisionId } : {}),
    ...(/^[a-f0-9]{64}$/.test(digest) ? { source_digest: digest } : {}),
  };
}

export function shotPlanDurationAssessment(plan, brief = null) {
  const productionBrief = productionBriefForSource("", brief);
  const shots = (Array.isArray(plan?.scenes) ? plan.scenes : [])
    .flatMap((scene) => Array.isArray(scene?.shots) ? scene.shots : []);
  const durations = shots.map((shot) => normalizedDuration(shot?.duration_sec));
  const hasShotDurations = durations.length > 0 && durations.every((value) => value !== null);
  const candidate = hasShotDurations
    ? round2(durations.reduce((sum, value) => sum + value, 0))
    : normalizedDuration(plan?.estimated_duration_sec) || 0;
  const target = productionBrief.target_duration_seconds;
  const tolerance = productionBrief.tolerance_seconds;
  const delta = round2(candidate - target);
  const withinTolerance = candidate > 0 && Math.abs(delta) <= tolerance;
  return {
    ...productionBrief,
    candidate_duration_seconds: candidate,
    provider_estimated_duration_seconds: normalizedDuration(
      plan?.provider_estimated_duration_sec ?? plan?.estimated_duration_sec,
    ) || 0,
    duration_delta_seconds: delta,
    within_tolerance: withinTolerance,
    apply_allowed: withinTolerance,
    status: withinTolerance ? "within_target" : "outside_target",
  };
}

export function productionBriefLabel(brief) {
  const safe = productionBriefForSource("", brief);
  return safe.duration_source === "script_explicit"
    ? "沿用剧本时长"
    : safe.duration_source === "creator_selected"
    ? "创作者设定"
    : "短片默认";
}

function declaredDurations(sourceText) {
  const text = String(sourceText || "");
  const matches = [];
  const patterns = [
    /(?:总时长|总长度|成片时长|目标时长)\s*(约|大约|大概|近)?\s*(\d+(?:\.\d+)?)\s*(秒|分钟)/gi,
    /(\d+(?:\.\d+)?)\s*(秒|分钟)\s*(?:短片|影片|故事|成片)/gi,
    /(?:total\s+duration)\s*(?:is|of|:)?\s*(approximately|about|around)?\s*(\d+(?:\.\d+)?)\s*(seconds?|minutes?)/gi,
  ];
  patterns.forEach((pattern, index) => {
    for (const match of text.matchAll(pattern)) {
      const marker = index === 1 ? "" : String(match[1] || "");
      const value = Number(index === 1 ? match[1] : match[2]);
      const unit = String(index === 1 ? match[2] : match[3]).toLowerCase();
      if (!Number.isFinite(value) || value <= 0) continue;
      const seconds = unit.includes("分钟") || unit.startsWith("minute") ? value * 60 : value;
      const normalized = normalizedDuration(seconds);
      if (normalized !== null) matches.push({ value: normalized, approximate: Boolean(marker) });
    }
  });
  const values = [...new Set(matches.map((item) => item.value))].sort((left, right) => left - right);
  return {
    values,
    approximate: matches.some((item) => item.approximate),
  };
}

function normalizedTolerance(value, target, source) {
  const number = Number(value);
  if (Number.isFinite(number) && number >= 0 && number <= target) return round2(number);
  if (source === "creator_default") return round2(target * 0.1);
  return 1;
}

function normalizedDuration(value) {
  const number = Number(value);
  if (
    !Number.isFinite(number)
    || number < MIN_STORYBOARD_DURATION_SECONDS
    || number > MAX_STORYBOARD_DURATION_SECONDS
  ) return null;
  return round2(number);
}

function round2(value) {
  return Math.round(Number(value || 0) * 100) / 100;
}
