import { candidatePreviewsFromNode } from "./node-candidate-previews.js";
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
  node: null,
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
      node: null,
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

export function composeReviewDeliveryState({ workspace, project, runsPayload, studioPayload, projectId }) {
  const runs = Array.isArray(runsPayload?.production_runs) ? runsPayload.production_runs : [];
  const studioState = studioPayload?.state && typeof studioPayload.state === "object" ? studioPayload.state : {};
  const nodes = Object.values(studioState.nodes || {}).filter((node) => node && typeof node === "object");
  const preferredRunId = safeToken(studioState.production?.active_run_id)
    || safeToken(nodes.map((node) => node?.params?.creatorSelection?.run_id).find(Boolean));
  const run = runs.find((item) => safeToken(item?.run_id) === preferredRunId) || newestRun(runs);
  if (!run) {
    return {
      phase: "empty",
      workspace,
      project,
      projectId,
      run: null,
      node: null,
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
  const sourceNode = bestCandidateNode(nodes, run);
  const previews = storedCandidatePreviews(sourceNode || {}, projectId);
  const candidates = runCandidates.map((candidate, index) => candidateView(candidate, previews, projectId, index));
  const selectedRevision = objectValue(run.selected_revision);
  const selectedCandidateId = safeToken(selectedRevision.candidate_id || selectedRevision.selected_candidate_id);
  const latestDecision = Array.isArray(run.creator_decisions) ? run.creator_decisions.at(-1) : null;
  const rejected = String(run.status || "") === "creator_revision_required" || String(latestDecision?.decision || "") === "reject";
  const focusedCandidateId = selectedCandidateId || candidates.find((item) => item.preview_url)?.candidate_id || candidates[0]?.candidate_id || "";
  const node = deliveryNode(sourceNode, run, candidates, selectedCandidateId, projectId);
  const reviewSnapshot = focusedCandidateId
    ? dedicatedReviewActionSnapshot(run, focusedCandidateId, node.id)
    : null;
  let deliverySnapshot = null;
  if (selectedCandidateId && !rejected) {
    try {
      deliverySnapshot = dedicatedDeliveryActionSnapshot(run, node);
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
    node,
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
  if (!candidate || !state.run || !state.node) return state;
  return {
    ...state,
    focusedCandidateId: candidate.candidate_id,
    reviewSnapshot: dedicatedReviewActionSnapshot(state.run, candidate.candidate_id, state.node.id),
    notice: "",
  };
}

function newestRun(runs) {
  return [...runs].sort((left, right) => String(right?.updated_at || right?.created_at || "")
    .localeCompare(String(left?.updated_at || left?.created_at || "")))[0] || null;
}

function bestCandidateNode(nodes, run) {
  const runId = safeToken(run?.run_id);
  const candidateIds = new Set((run?.candidates || []).map((item) => safeToken(item?.candidate_id)).filter(Boolean));
  return nodes.find((node) => safeToken(node?.params?.creatorSelection?.run_id) === runId)
    || nodes.find((node) => rawCandidateItems(node).filter((item) => candidateIds.has(safeToken(item?.candidate_id))).length >= 2)
    || null;
}

function candidateView(candidate, previews, projectId, index) {
  const id = safeToken(candidate?.candidate_id);
  const digest = safeDigest(candidate?.canonical_digest);
  const jobId = safeToken(candidate?.parent_job_id);
  const preview = previews.find((item) => item.candidate_id === id
    && safeDigest(item.canonical_digest || item.sha256) === digest
    && safeToken(item.parent_job_id) === jobId) || null;
  const previewUrl = safePreviewUrl(preview?.preview_url || preview?.url, projectId, jobId, id);
  return {
    candidate_id: id,
    canonical_digest: digest,
    parent_job_id: jobId,
    label: `方案 ${String.fromCharCode(65 + index)}`,
    preview_url: previewUrl,
    media_kind: previewUrl.includes("/video-generations/") ? "video" : "image",
    available: Boolean(previewUrl),
    aspect_ratio: String(preview?.aspect_ratio || "").trim(),
  };
}

function deliveryNode(sourceNode, run, candidates, selectedCandidateId, projectId) {
  const selectedCandidate = candidates.find((item) => item.candidate_id === selectedCandidateId);
  const revision = objectValue(run.selected_revision);
  return {
    ...(sourceNode || {}),
    id: safeToken(sourceNode?.id) || "review-delivery",
    type: sourceNode?.type || (candidates.some((item) => item.media_kind === "video") ? "video" : "image"),
    params: {
      ...(sourceNode?.params || {}),
      lastKeyframeJobId: selectedCandidate?.parent_job_id || candidates[0]?.parent_job_id || "",
      lastVideoJobId: selectedCandidate?.parent_job_id || candidates[0]?.parent_job_id || "",
      candidatePreviewUrls: candidates.map((item) => ({
        candidate_id: item.candidate_id,
        canonical_digest: item.canonical_digest,
        parent_job_id: item.parent_job_id,
        project_id: projectId,
        preview_url: item.preview_url,
        status: item.available ? "succeeded" : "",
      })),
      reviewDeliveryCandidates: candidates.map((item) => ({
        candidate_id: item.candidate_id,
        canonical_digest: item.canonical_digest,
        parent_job_id: item.parent_job_id,
      })),
      creatorSelection: {
        status: "persisted",
        authoritative_source: "runtime_production_run",
        run_id: safeToken(run.run_id),
        selected_candidate_id: selectedCandidateId,
        selected_candidate_digest: safeDigest(selectedCandidate?.canonical_digest),
        selected_revision_id: safeToken(revision.revision_id || revision.selected_revision_id),
        selected_revision_digest: safeDigest(
          revision.canonical_digest || revision.revision_digest || revision.selected_revision_digest,
        ),
        checkpoint_version: Number(run?.checkpoint?.version || 0),
        checkpoint_digest: safeDigest(run?.checkpoint?.state_digest),
        selected_parent_job_id: selectedCandidate?.parent_job_id || "",
      },
    },
  };
}

function storedCandidatePreviews(node, projectId) {
  const normalized = candidatePreviewsFromNode(node);
  const raw = rawCandidateItems(node).map((item) => {
    const candidateId = safeToken(item?.candidate_id || item?.id);
    const parentJobId = safeToken(item?.parent_job_id);
    const canonicalDigest = safeDigest(item?.canonical_digest || item?.sha256);
    const previewUrl = safePreviewUrl(item?.preview_url || item?.url || item?.previewUrl, projectId, parentJobId, candidateId);
    return {
      candidate_id: candidateId,
      parent_job_id: parentJobId,
      canonical_digest: canonicalDigest,
      preview_url: previewUrl,
      url: previewUrl,
      aspect_ratio: String(item?.aspect_ratio || "").trim(),
    };
  });
  const byId = new Map();
  for (const item of [...raw, ...normalized]) {
    if (item?.candidate_id && !byId.has(item.candidate_id)) byId.set(item.candidate_id, item);
  }
  return [...byId.values()];
}

function rawCandidateItems(node) {
  const value = node?.params?.candidatePreviewUrls || node?.params?.candidate_previews || node?.params?.candidates;
  return Array.isArray(value) ? value.filter((item) => item && typeof item === "object" && !Array.isArray(item)) : [];
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

function safePreviewUrl(value, projectId, jobId, candidateId) {
  const text = String(value || "").trim();
  if (!text.startsWith(`/projects/${encodeURIComponent(projectId)}/`)
    && !text.startsWith(`/projects/${projectId}/`)) return "";
  if (!text.endsWith(`/candidates/${candidateId}/preview`)) return "";
  if (!text.includes(`/${jobId}/candidates/`)) return "";
  return text;
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
