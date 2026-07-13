import { dedicatedReviewActionSnapshot } from "./candidate-selection-controller.js";
import { dedicatedDeliveryActionSnapshot } from "./production-delivery-controller.js";

const EMPTY = Object.freeze({
  phase: "secure",
  identity: "",
  authUser: null,
  workspace: null,
  project: null,
  projectId: "",
  run: null,
  candidates: [],
  focusedCandidateId: "",
  selectedCandidateId: "",
  reviewSnapshot: null,
  deliverySnapshot: null,
  quality: null,
  exports: [],
  lineage: [],
  busy: "",
  notice: "",
  error: "",
});

export function createReviewDeliveryState(onChange = () => {}) {
  let value = { ...EMPTY };
  let identityEpoch = 0;
  let requestSequence = 0;

  function publish(patch) {
    value = { ...value, ...patch };
    onChange(value);
    return value;
  }

  function setIdentity(user) {
    const next = String(user?.user_id || "").trim();
    if (!next || next !== value.identity) {
      identityEpoch += 1;
      requestSequence += 1;
      value = { ...EMPTY, identity: next, authUser: next ? user : null };
      onChange(value);
      return { changed: true, epoch: identityEpoch };
    }
    publish({ authUser: user });
    return { changed: false, epoch: identityEpoch };
  }

  function clearIdentity() {
    identityEpoch += 1;
    requestSequence += 1;
    value = { ...EMPTY };
    onChange(value);
  }

  function beginLoad(projectId = "") {
    const token = { epoch: identityEpoch, sequence: ++requestSequence };
    publish({
      phase: "loading",
      projectId,
      project: null,
      run: null,
      candidates: [],
      reviewSnapshot: null,
      deliverySnapshot: null,
      quality: null,
      exports: [],
      lineage: [],
      busy: "",
      notice: "",
      error: "",
    });
    return token;
  }

  function beginAction(action) {
    if (value.busy) return null;
    const token = { epoch: identityEpoch, sequence: requestSequence, action };
    publish({ busy: action, notice: "", error: "" });
    return token;
  }

  function isCurrent(token) {
    return Boolean(token && token.epoch === identityEpoch && token.sequence === requestSequence);
  }

  return {
    get: () => value,
    publish,
    setIdentity,
    clearIdentity,
    beginLoad,
    beginAction,
    isCurrent,
    finishAction(token, patch = {}) {
      if (!isCurrent(token)) return false;
      publish({ busy: "", ...patch });
      return true;
    },
  };
}

export function composeReviewDeliveryState({ workspace, project, runsPayload, projectId }) {
  const runs = Array.isArray(runsPayload?.production_runs) ? runsPayload.production_runs : [];
  const run = newestRun(runs);
  if (!run) {
    return {
      phase: "empty",
      workspace,
      project,
      projectId,
      run: null,
      candidates: [],
      focusedCandidateId: "",
      selectedCandidateId: "",
      reviewSnapshot: null,
      deliverySnapshot: null,
      quality: null,
      exports: [],
      lineage: [],
      notice: "",
      error: "",
    };
  }

  const runCandidates = Array.isArray(run.candidates) ? run.candidates : [];
  const candidates = runCandidates.map((candidate, index) => candidateView(candidate, projectId, index));
  const selectedRevision = objectValue(run.selected_revision);
  const selectedCandidateId = safeToken(selectedRevision.candidate_id || selectedRevision.selected_candidate_id);
  const latestDecision = Array.isArray(run.creator_decisions) ? run.creator_decisions.at(-1) : null;
  const rejected = String(run.status || "") === "creator_revision_required" || String(latestDecision?.decision || "") === "reject";
  const focusedCandidateId = selectedCandidateId || candidates.find((item) => item.preview_url)?.candidate_id || candidates[0]?.candidate_id || "";
  const reviewSnapshot = focusedCandidateId
    ? dedicatedReviewActionSnapshot(run, focusedCandidateId)
    : null;
  let deliverySnapshot = null;
  if (selectedCandidateId && !rejected) {
    try {
      deliverySnapshot = dedicatedDeliveryActionSnapshot(run);
    } catch {
      deliverySnapshot = null;
    }
  }
  const quality = qualityProjection(run, selectedRevision, rejected);
  const exports = exactExports(run, selectedRevision, rejected);
  return {
    phase: "ready",
    workspace,
    project,
    projectId,
    run,
    candidates,
    focusedCandidateId,
    selectedCandidateId,
    reviewSnapshot,
    deliverySnapshot,
    quality,
    exports,
    lineage: lineageProjection(run),
    rejected,
    notice: "",
    error: "",
  };
}

export function focusReviewCandidate(state, candidateId) {
  const candidate = state.candidates.find((item) => item.candidate_id === candidateId);
  if (!candidate || !state.run) return state;
  return {
    ...state,
    focusedCandidateId: candidate.candidate_id,
    reviewSnapshot: dedicatedReviewActionSnapshot(state.run, candidate.candidate_id),
    notice: "",
  };
}

export function protectedPreviewDisposition(status) {
  return Number(status) === 401 ? "session_expired" : "unavailable";
}

export function selectedDeliverySubmission(state) {
  const snapshot = state?.deliverySnapshot;
  const run = state?.run;
  const selectedCandidateId = safeToken(state?.selectedCandidateId);
  const selectedCandidate = (Array.isArray(run?.candidates) ? run.candidates : [])
    .find((item) => safeToken(item?.candidate_id) === selectedCandidateId);
  const revision = objectValue(run?.selected_revision);
  const expected = {
    candidate_id: selectedCandidateId,
    candidate_digest: safeDigest(selectedCandidate?.canonical_digest),
    revision_id: safeToken(revision.revision_id || revision.selected_revision_id),
    revision_digest: safeDigest(
      revision.canonical_digest || revision.revision_digest || revision.selected_revision_digest,
    ),
  };
  if (!snapshot || Object.values(expected).some((value) => !value)) return null;
  const snapshotMatches = Object.entries(expected)
    .every(([key, value]) => String(snapshot?.[key] || "") === value);
  return snapshotMatches ? { snapshot } : null;
}

function newestRun(runs) {
  return [...runs].sort((left, right) => String(right?.updated_at || right?.created_at || "")
    .localeCompare(String(left?.updated_at || left?.created_at || "")))[0] || null;
}

function candidateView(candidate, projectId, index) {
  const id = safeToken(candidate?.candidate_id);
  const digest = safeDigest(candidate?.canonical_digest);
  const jobId = safeToken(candidate?.parent_job_id);
  const preview = safePreviewDescriptor(candidate?.safe_preview, projectId, jobId, id);
  return {
    candidate_id: id,
    canonical_digest: digest,
    parent_job_id: jobId,
    label: `方案 ${String.fromCharCode(65 + index)}`,
    preview_url: preview?.preview_url || "",
    media_kind: preview?.media_kind || "",
    available: Boolean(preview),
    aspect_ratio: "",
  };
}

function safePreviewDescriptor(value, projectId, jobId, candidateId) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const keys = Object.keys(value).sort();
  if (keys.length !== 2 || keys[0] !== "media_kind" || keys[1] !== "preview_url") return null;
  const mediaKind = value.media_kind === "image" || value.media_kind === "video" ? value.media_kind : "";
  const previewUrl = String(value.preview_url || "").trim();
  if (!mediaKind || !previewUrl || !safeToken(projectId) || !jobId || !candidateId) return null;
  const match = previewUrl.match(/^\/projects\/([^/]+)\/(keyframe-generations|video-generations)\/([^/]+)\/candidates\/([^/]+)\/preview$/);
  if (!match) return null;
  const [, descriptorProjectId, collection, descriptorJobId, descriptorCandidateId] = match;
  const expectedCollection = mediaKind === "image" ? "keyframe-generations" : "video-generations";
  if (descriptorProjectId !== projectId
    || collection !== expectedCollection
    || descriptorJobId !== jobId
    || descriptorCandidateId !== candidateId) return null;
  return { media_kind: mediaKind, preview_url: previewUrl };
}

function qualityProjection(run, revision, rejected) {
  const revisionId = safeToken(revision.revision_id || revision.selected_revision_id);
  const revisionDigest = safeDigest(revision.canonical_digest || revision.revision_digest || revision.selected_revision_digest);
  const reviews = Array.isArray(run.quality_reviews) ? run.quality_reviews : [];
  const review = rejected || String(run?.status || "") === "quality_rejected" ? null : [...reviews].reverse().find((item) => (
    String(item?.decision || "") === "approve"
    && safeToken(item?.selected_revision_id) === revisionId
    && safeDigest(item?.selected_revision_digest) === revisionDigest
  )) || null;
  const checklist = objectValue(review?.checklist);
  return {
    approved: Boolean(review),
    narrative: checklist.story_intent_preserved === true ? "passed" : "not_checked",
    consistency: checklist.character_continuity_checked === true ? "passed" : "not_checked",
    coverage: checklist.shot_coverage_checked === true ? "passed" : "not_checked",
    revision: checklist.revision_addressed === true ? "passed" : "not_checked",
    audio: "unavailable",
    subtitle: "unavailable",
  };
}

function exactExports(run, revision, rejected) {
  if (rejected) return [];
  const revisionId = safeToken(revision.revision_id || revision.selected_revision_id);
  const revisionDigest = safeDigest(revision.canonical_digest || revision.revision_digest || revision.selected_revision_digest);
  return (Array.isArray(run.exports) ? run.exports : []).filter((item) => (
    safeToken(item?.selected_revision_id) === revisionId
    && safeDigest(item?.selected_revision_digest) === revisionDigest
  )).map((item, index) => ({
    label: `交付包 ${index + 1}`,
    created_at: safeDate(item?.created_at),
  }));
}

function lineageProjection(run) {
  const decisions = Array.isArray(run.creator_decisions) ? run.creator_decisions : [];
  const reviews = Array.isArray(run.quality_reviews) ? run.quality_reviews : [];
  const exports = Array.isArray(run.exports) ? run.exports : [];
  const result = [{ label: "候选方案进入主创审核", state: "complete" }];
  if (decisions.length) result.push({ label: `已记录 ${decisions.length} 次主创决定`, state: "complete" });
  if (run.selected_revision) result.push({ label: "当前修订已形成", state: "complete" });
  if (reviews.length) result.push({ label: `已记录 ${reviews.length} 次质量审核`, state: "complete" });
  if (exports.length) result.push({ label: `已生成 ${exports.length} 个交付包`, state: "complete" });
  return result;
}

function safeToken(value) {
  const text = String(value || "").trim();
  return /^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$/.test(text) ? text : "";
}

function safeDigest(value) {
  const text = String(value || "").trim().toLowerCase();
  return /^[a-f0-9]{64}$/.test(text) ? text : "";
}

function safeDate(value) {
  const date = new Date(String(value || ""));
  return Number.isNaN(date.valueOf()) ? "时间未记录" : date.toLocaleString("zh-CN", { hour12: false });
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}
