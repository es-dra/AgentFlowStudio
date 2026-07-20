const SAFE_ID_RE = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$/;
const SHA256_RE = /^[a-f0-9]{64}$/;

export function normalizeMangaFirstL4AProjection(payload) {
  const projection = payload?.studio_projection && typeof payload.studio_projection === "object"
    ? payload.studio_projection
    : payload;
  if (!projection || typeof projection !== "object" || Array.isArray(projection)) return null;
  if (projection.schema_version !== "afs.manga_first_l4a.studio_projection.v0.1") return null;
  const project = normalizeProject(projection.project);
  const manifestSha = safeDigest(projection.manifest_sha256 || payload?.manifest_sha256);
  if (!project || !manifestSha) return null;
  const shots = arrayOf(projection.shot_status).map(normalizeShot).filter(Boolean);
  const candidates = arrayOf(projection.candidates).map(normalizeCandidate).filter(Boolean);
  const timeline = arrayOf(projection.timeline).map(normalizeTimelineItem).filter(Boolean);
  const qa = normalizeQa(projection.qa);
  const finalDemo = normalizeFinalDemo(projection.final_demo);
  return {
    schema_version: projection.schema_version,
    project,
    manifest_sha256: manifestSha,
    truth_source: safeText(projection.truth_source, 120),
    shot_status: shots,
    candidates,
    timeline,
    qa,
    final_demo: finalDemo,
    provider_dispatch_count: Number(projection.provider_dispatch_count || 0) === 0 ? 0 : null,
    fabricated_state_allowed: false,
  };
}

export function mangaFirstL4AStatusCounts(viewModel) {
  const shots = Array.isArray(viewModel?.shot_status) ? viewModel.shot_status : [];
  return shots.reduce((acc, shot) => {
    const key = shot.status || "unknown";
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

function normalizeProject(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const projectId = safeId(value.project_id);
  if (!projectId) return null;
  return {
    project_id: projectId,
    title: safeText(value.title, 160),
    workload: value.workload === "manga_first" ? "manga_first" : "",
    status: safeText(value.status, 120),
  };
}

function normalizeShot(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const shotId = safeId(value.shot_id);
  if (!shotId) return null;
  return {
    shot_id: shotId,
    sequence: safePositiveInt(value.sequence),
    scene_id: safeId(value.scene_id),
    status: safeText(value.status, 80),
    duration_seconds: safeNumber(value.duration_seconds),
    candidate_count: safePositiveInt(value.candidate_count, 0),
    selected_candidate_id: value.selected_candidate_id ? safeId(value.selected_candidate_id) : null,
  };
}

function normalizeCandidate(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const candidateId = safeId(value.candidate_id);
  const shotId = safeId(value.shot_id);
  if (!candidateId || !shotId) return null;
  return {
    candidate_id: candidateId,
    shot_id: shotId,
    status: safeText(value.status, 80),
    artifact_present: value.artifact_present === true,
    fabricated_state: value.fabricated_state === true,
  };
}

function normalizeTimelineItem(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const shotId = safeId(value.shot_id);
  if (!shotId) return null;
  return {
    shot_id: shotId,
    start_seconds: safeNumber(value.start_seconds),
    end_seconds: safeNumber(value.end_seconds),
  };
}

function normalizeQa(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return { technical_QA: "not_started", visual_creative_QA: "not_started", p1_count: 0 };
  }
  return {
    technical_QA: safeText(value.technical_QA, 80),
    visual_creative_QA: safeText(value.visual_creative_QA, 120),
    p1_count: safePositiveInt(value.p1_count, 0),
    gate: safeText(value.gate, 160),
  };
}

function normalizeFinalDemo(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return { status: "not_available" };
  const out = { status: safeText(value.status, 120) || "not_available" };
  if (value.sha256) out.sha256 = safeDigest(value.sha256);
  if (value.duration_seconds) out.duration_seconds = safeNumber(value.duration_seconds);
  if (value.audio_status) out.audio_status = safeText(value.audio_status, 80);
  return out;
}

function arrayOf(value) {
  return Array.isArray(value) ? value : [];
}

function safeId(value) {
  const text = String(value || "").trim();
  return SAFE_ID_RE.test(text) ? text : "";
}

function safeDigest(value) {
  const text = String(value || "").trim();
  return SHA256_RE.test(text) ? text : "";
}

function safeText(value, maxLen) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, maxLen);
}

function safeNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : 0;
}

function safePositiveInt(value, fallback = 0) {
  const number = Number(value);
  return Number.isInteger(number) && number >= 0 ? number : fallback;
}
