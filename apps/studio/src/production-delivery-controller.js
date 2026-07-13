import {
  applyAuthoritativeProductionRun,
  candidateSelectionSummary,
} from "./candidate-selection-controller.js";
import { candidatePreviewsFromNode } from "./node-candidate-previews.js";

const SHA256_RE = /^[a-f0-9]{64}$/;
const SAFE_ID_RE = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$/;
const DELIVERY_ACTIONS = new Set(["production-delivery-refresh", "production-quality-approve", "production-export"]);
const IN_FLIGHT = new WeakMap();

export function productionDeliverySummary(node) {
  const value = node?.params?.productionDelivery;
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function representativeEpisodeBindingSummary(run) {
  const binding = objectValue(run?.representative_episode_binding);
  if (!Object.keys(binding).length) return {};
  const characterRefs = exactEntityRefs(binding.character_refs, 3, "character");
  const sceneRefs = exactEntityRefs(binding.scene_refs, 3, "scene");
  const shotRefs = exactEntityRefs(binding.shot_refs, 15, "shot");
  const assetRefs = exactAssetRefs(binding.asset_refs);
  const counts = objectValue(binding.counts);
  if (Number(counts.characters) !== characterRefs.length
    || Number(counts.scenes) !== sceneRefs.length
    || Number(counts.shots) !== shotRefs.length
    || Number(counts.assets) !== assetRefs.length) {
    throw deliveryError("delivery_episode_counts_invalid", "Representative episode inventory counts are not authoritative.");
  }
  const readiness = objectValue(binding.asset_readiness);
  const pendingMediaCount = assetRefs.filter((item) => item.status === "missing").length;
  const providerNeededCount = assetRefs.filter((item) => item.provider_needed).length;
  if (Number(readiness.pending_media_count) !== pendingMediaCount
    || Number(readiness.provider_needed_count) !== providerNeededCount
    || Boolean(readiness.all_assets_ready) !== (pendingMediaCount === 0)) {
    throw deliveryError("delivery_episode_readiness_invalid", "Representative episode asset readiness is inconsistent.");
  }
  const lineage = Array.isArray(binding.lineage) ? binding.lineage.map((item) => ({
    source_ref: safeLineageRef(item?.source_ref, "source_ref"),
    target_ref: safeLineageRef(item?.target_ref, "target_ref"),
    relation: safeIdentifier(item?.relation, "lineage_relation"),
  })) : [];
  if (lineage.length < 2) {
    throw deliveryError("delivery_episode_lineage_invalid", "Representative episode lineage is incomplete.");
  }
  return {
    authoritative_source: "runtime_production_run_checkpoint",
    package_sha256: safeDigest(binding.package_sha256, "episode_package_sha256"),
    binding_digest: safeDigest(binding.binding_digest, "episode_binding_digest"),
    episode_id: safeIdentifier(binding.episode_id, "episode_id"),
    episode_version_id: safeIdentifier(binding.episode_version_id, "episode_version_id"),
    character_count: characterRefs.length,
    scene_count: sceneRefs.length,
    shot_count: shotRefs.length,
    asset_count: assetRefs.length,
    pending_media_count: pendingMediaCount,
    provider_needed_count: providerNeededCount,
    all_assets_ready: pendingMediaCount === 0,
    creator_decision_ref: safeIdentifier(binding.creator_decision_ref, "creator_decision_ref"),
    propagation_complete: binding.propagation_complete === true,
    lineage,
  };
}

export function productionDeliveryAuthority(run, node) {
  const latestDecision = Array.isArray(run?.creator_decisions) ? run.creator_decisions.at(-1) : null;
  if (String(run?.status || "") === "creator_revision_required" || String(latestDecision?.decision || "") === "reject") {
    throw deliveryError("delivery_creator_rejected", "The current revision was rejected and must be selected or revised again.");
  }
  const selection = candidateSelectionSummary(node);
  const selectedCandidateId = optionalIdentifier(selection.selected_candidate_id);
  if (!selectedCandidateId) {
    throw deliveryError("delivery_selection_missing", "Select one production candidate before quality approval or export.");
  }
  const runId = safeIdentifier(run?.run_id, "run_id");
  if (optionalIdentifier(selection.run_id) !== runId) {
    throw deliveryError("delivery_run_stale", "The selected candidate belongs to a different production run. Refresh before continuing.");
  }
  const candidates = Array.isArray(run?.candidates) ? run.candidates : [];
  const visibleCandidates = visibleDeliveryCandidates(node);
  if (candidates.length < 2 || visibleCandidates.length < 2) {
    throw deliveryError("delivery_candidate_inventory_incomplete", "At least two production candidates are required for this delivery gate.");
  }
  const revision = objectValue(run?.selected_revision);
  const revisionCandidateId = optionalIdentifier(revision.candidate_id || revision.selected_candidate_id);
  if (revisionCandidateId !== selectedCandidateId) {
    throw deliveryError("delivery_candidate_stale", "The visible candidate is no longer the authoritative production selection.");
  }
  const selectedRevisionId = optionalIdentifier(selection.selected_revision_id);
  const revisionId = optionalIdentifier(revision.revision_id || revision.selected_revision_id);
  if (!selectedRevisionId || selectedRevisionId !== revisionId) {
    throw deliveryError("delivery_revision_stale", "The visible revision is stale. Refresh the selected production revision.");
  }
  const selectedCandidateDigest = safeDigest(selection.selected_candidate_digest, "selected_candidate_digest");
  const selectedRevisionDigest = safeDigest(selection.selected_revision_digest, "selected_revision_digest");
  const candidate = candidates.find((item) => optionalIdentifier(item?.candidate_id) === selectedCandidateId);
  if (!candidate || safeDigest(candidate.canonical_digest, "candidate_digest") !== selectedCandidateDigest) {
    throw deliveryError("delivery_candidate_stale", "The selected candidate integrity no longer matches production authority.");
  }
  const revisionCandidateDigest = safeDigest(
    revision.candidate_digest || revision.selected_candidate_digest,
    "revision_candidate_digest",
  );
  const revisionDigest = safeDigest(
    revision.canonical_digest || revision.revision_digest || revision.selected_revision_digest,
    "revision_digest",
  );
  if (revisionCandidateDigest !== selectedCandidateDigest || revisionDigest !== selectedRevisionDigest) {
    throw deliveryError("delivery_revision_stale", "The selected revision integrity no longer matches production authority.");
  }
  const parentJobId = safeIdentifier(candidate.parent_job_id, "parent_job_id");
  const selectionJobId = optionalIdentifier(selection.selected_parent_job_id);
  const revisionJobId = optionalIdentifier(revision.parent_job_id) || parentJobId;
  const nodeJobId = optionalIdentifier(node?.params?.lastKeyframeJobId || node?.params?.lastVideoJobId);
  if (!selectionJobId || !nodeJobId || selectionJobId !== parentJobId || revisionJobId !== parentJobId || nodeJobId !== parentJobId) {
    throw deliveryError("delivery_lineage_stale", "The selected candidate lineage no longer belongs to this Studio node generation job.");
  }
  const visible = visibleCandidates.find((item) => optionalIdentifier(item?.candidate_id) === selectedCandidateId);
  if (!visible
    || safeDigest(visible.canonical_digest || visible.sha256, "visible_candidate_digest") !== selectedCandidateDigest
    || safeIdentifier(visible.parent_job_id, "visible_parent_job_id") !== parentJobId) {
    throw deliveryError("delivery_candidate_stale", "The visible candidate no longer matches the exact selected production candidate.");
  }
  const checkpointVersion = Number(run?.checkpoint?.version || 0);
  if (!Number.isInteger(checkpointVersion) || checkpointVersion < 1) {
    throw deliveryError("delivery_checkpoint_invalid", "Production checkpoint is unavailable.");
  }
  return {
    run_id: runId,
    candidate_id: selectedCandidateId,
    candidate_digest: selectedCandidateDigest,
    revision_id: selectedRevisionId,
    revision_digest: selectedRevisionDigest,
    parent_job_id: parentJobId,
    checkpoint_version: checkpointVersion,
  };
}

export function buildQualityApprovalRequest(run, node, options = {}) {
  const authority = productionDeliveryAuthority(run, node);
  const revision = objectValue(run?.selected_revision);
  const checklist = normalizedChecklist(options.checklist);
  if (Object.values(checklist).some((checked) => checked !== true)) {
    throw deliveryError("delivery_checklist_incomplete", "Complete every quality check before approval.");
  }
  const reviewId = safeIdentifier(options.reviewId || uniqueIdentifier("quality-review", authority), "review_id");
  const idempotencyKey = safeIdentifier(options.idempotencyKey || reviewId, "idempotency_key");
  return {
    schema_version: "afs_production_quality_review.v0.1",
    review_id: reviewId,
    idempotency_key: idempotencyKey,
    expected_checkpoint_version: authority.checkpoint_version,
    reviewed_subject_digest: safeDigest(revision.subject_digest || run?.subject_digest, "reviewed_subject_digest"),
    selected_revision_id: authority.revision_id,
    selected_revision_digest: authority.revision_digest,
    decision: "approve",
    checklist,
    note: "Studio quality checklist approved for this exact revision; workflow gate only, not human acceptance.",
  };
}

export function buildProductionExportRequest(run, node, options = {}) {
  const authority = productionDeliveryAuthority(run, node);
  if (!approvedReviewForAuthority(run, authority)) {
    throw deliveryError("delivery_quality_required", "Approve the exact selected revision before export.");
  }
  const exportId = safeIdentifier(options.exportId || uniqueIdentifier("studio-export", authority), "export_id");
  const idempotencyKey = safeIdentifier(options.idempotencyKey || exportId, "idempotency_key");
  return {
    schema_version: "afs_production_export.v0.1",
    export_id: exportId,
    idempotency_key: idempotencyKey,
    expected_checkpoint_version: authority.checkpoint_version,
    selected_revision_id: authority.revision_id,
    selected_revision_digest: authority.revision_digest,
  };
}

export function dedicatedDeliveryActionSnapshot(run, node) {
  const authority = productionDeliveryAuthority(run, node);
  return {
    ...authority,
    checkpoint_digest: safeDigest(run?.checkpoint?.state_digest, "checkpoint_digest"),
  };
}

export async function submitDedicatedQualityApproval(runtime, snapshot, node, checklist, options = {}) {
  return submitDedicatedDeliveryMutation(runtime, snapshot, node, "quality", checklist, options);
}

export async function submitDedicatedProductionExport(runtime, snapshot, node, options = {}) {
  return submitDedicatedDeliveryMutation(runtime, snapshot, node, "export", null, options);
}

async function submitDedicatedDeliveryMutation(runtime, snapshot, node, action, checklist, options) {
  const runId = optionalIdentifier(snapshot?.run_id);
  const writer = action === "quality" ? runtime?.recordProductionQualityReview : runtime?.exportProductionRun;
  if (!runId || !runtime?.getProductionRun || !writer) {
    return { ok: false, code: "delivery_client_missing", message: "当前无法完成交付操作。" };
  }
  let lastAuthoritativeRun = null;
  try {
    const before = authoritativeRun(await runtime.getProductionRun(runId));
    lastAuthoritativeRun = before;
    assertDedicatedDeliverySnapshot(snapshot, dedicatedDeliveryActionSnapshot(before, node));
    const request = action === "quality"
      ? buildQualityApprovalRequest(before, node, { checklist, ...options })
      : buildProductionExportRequest(before, node, options);
    const submitted = await writer.call(runtime, runId, request);
    const after = authoritativeRun(await runtime.getProductionRun(runId));
    lastAuthoritativeRun = after;
    const authority = productionDeliveryAuthority(after, node);
    if (action === "quality" && !approvedReviewForAuthority(after, authority)) {
      throw deliveryError("delivery_quality_readback_missing", "Quality approval was not present in authoritative readback.");
    }
    if (action === "export") {
      const exported = objectValue(submitted?.export || latestExport(after));
      if (optionalIdentifier(exported.selected_revision_id) !== authority.revision_id
        || safeDigest(exported.selected_revision_digest, "export_revision_digest") !== authority.revision_digest) {
        throw deliveryError("delivery_export_readback_mismatch", "Export readback does not match the exact selected revision.");
      }
    }
    return {
      ok: true,
      duplicate: Boolean(submitted?.idempotent_replay),
      status: action === "quality" ? "approved" : "exported",
      production_run: after,
    };
  } catch (error) {
    const code = classifyError(error);
    const stale = Number(error?.status) === 409 || isDedicatedDeliveryStaleCode(code);
    if (stale && runtime?.getProductionRun && runId) {
      try {
        lastAuthoritativeRun = authoritativeRun(await runtime.getProductionRun(runId));
      } catch {
        // A full reload remains the only recovery when readback also fails.
      }
    }
    return {
      ok: false,
      code,
      stale,
      message: stale ? "制作状态已变化，请读取最新版本后再继续。" : publicErrorMessage(error),
      production_run: lastAuthoritativeRun,
    };
  }
}

export async function handleProductionDeliveryAction(store, runtime, node, actionEl) {
  const action = String(actionEl?.dataset?.action || "");
  if (!DELIVERY_ACTIONS.has(action)) return { ok: false, code: "delivery_action_unknown" };
  if (!store?.get || !runtime?.getProductionRun) {
    return recordFailure(store, node?.id, "delivery_client_missing", "Authenticated production delivery readback is unavailable.");
  }
  if ((productionDeliverySummary(node).status || "").endsWith("ing") || IN_FLIGHT.has(store)) {
    return { ok: false, code: "delivery_in_flight", message: "Wait for the current production delivery action to finish." };
  }
  const panel = actionEl?.closest?.(".production-delivery-panel");
  setPanelBusy(panel, true);
  const task = runDeliveryAction(store, runtime, node, action, panel);
  IN_FLIGHT.set(store, task);
  try {
    const result = await task;
    updatePanelStatus(panel, result);
    return result;
  } finally {
    if (IN_FLIGHT.get(store) === task) IN_FLIGHT.delete(store);
    setPanelBusy(panel, false);
  }
}

async function runDeliveryAction(store, runtime, node, action, panel) {
  const currentNode = store.get()?.nodes?.[node.id] || node;
  const selection = candidateSelectionSummary(currentNode);
  const runId = optionalIdentifier(selection.run_id);
  if (!runId) return recordFailure(store, node.id, "delivery_selection_missing", "Select one production candidate before delivery review.");
  try {
    const beforePayload = await runtime.getProductionRun(runId);
    const before = authoritativeRun(beforePayload);
    const beforeAuthority = productionDeliveryAuthority(before, currentNode);
    if (action === "production-delivery-refresh") {
      applyAuthoritativeProductionRun(store, node.id, before, { binding: beforePayload?.studio_binding });
      const state = deliveryStateFromRun(before, beforeAuthority, "ready");
      recordDeliveryState(store, node.id, state);
      await store.flushRuntimeSave?.();
      return { ok: true, ...state };
    }
    if (action === "production-quality-approve") {
      if (!runtime?.recordProductionQualityReview) {
        throw deliveryError("delivery_client_missing", "Quality approval API is unavailable.");
      }
      const request = buildQualityApprovalRequest(before, currentNode, { checklist: checklistFromPanel(panel) });
      recordPending(store, node.id, "quality_saving", "Saving approval for the exact selected revision…");
      const submitted = await runtime.recordProductionQualityReview(runId, request);
      const afterPayload = await runtime.getProductionRun(runId);
      const after = authoritativeRun(afterPayload);
      const authority = productionDeliveryAuthority(after, store.get()?.nodes?.[node.id] || currentNode);
      const review = approvedReviewForAuthority(after, authority);
      if (!review) throw deliveryError("delivery_quality_readback_missing", "Quality approval was not present in authoritative readback.");
      applyAuthoritativeProductionRun(store, node.id, after, { binding: afterPayload?.studio_binding });
      const state = deliveryStateFromRun(after, authority, "approved", {
        quality_review_id: optionalIdentifier(review.review_id),
        quality_decision: "approve",
        message: submitted?.idempotent_replay ? "Quality approval restored from an idempotent replay." : "Exact revision approved for production export.",
      });
      recordDeliveryState(store, node.id, state);
      await store.flushRuntimeSave?.();
      return { ok: true, duplicate: Boolean(submitted?.idempotent_replay), ...state };
    }
    if (!runtime?.exportProductionRun) throw deliveryError("delivery_client_missing", "Production export API is unavailable.");
    const request = buildProductionExportRequest(before, currentNode);
    recordPending(store, node.id, "exporting", "Exporting the exact approved revision…");
    const submitted = await runtime.exportProductionRun(runId, request);
    const afterPayload = await runtime.getProductionRun(runId);
    const after = authoritativeRun(afterPayload);
    const authority = productionDeliveryAuthority(after, store.get()?.nodes?.[node.id] || currentNode);
    const exported = objectValue(submitted?.export || latestExport(after));
    if (optionalIdentifier(exported.selected_revision_id) !== authority.revision_id
      || safeDigest(exported.selected_revision_digest, "export_revision_digest") !== authority.revision_digest) {
      throw deliveryError("delivery_export_readback_mismatch", "Export readback does not match the exact selected revision.");
    }
    applyAuthoritativeProductionRun(store, node.id, after, { binding: afterPayload?.studio_binding });
    const state = deliveryStateFromRun(after, authority, "exported", {
      quality_review_id: optionalIdentifier(approvedReviewForAuthority(after, authority)?.review_id),
      quality_decision: "approve",
      last_export_id: safeIdentifier(exported.export_id, "export_id"),
      delivery_sha256: safeDigest(exported.delivery_sha256, "delivery_sha256"),
      message: submitted?.idempotent_replay ? "Exact export restored from an idempotent replay." : "Exact approved revision exported.",
    });
    recordDeliveryState(store, node.id, state);
    await store.flushRuntimeSave?.();
    return { ok: true, duplicate: Boolean(submitted?.idempotent_replay), ...state };
  } catch (error) {
    return recordFailure(store, node.id, classifyError(error), publicErrorMessage(error));
  }
}

function deliveryStateFromRun(run, authority, fallbackStatus, overrides = {}) {
  const review = approvedReviewForAuthority(run, authority);
  const exported = latestExport(run);
  const exactExport = exported
    && optionalIdentifier(exported.selected_revision_id) === authority.revision_id
    && optionalDigest(exported.selected_revision_digest) === authority.revision_digest
    ? exported
    : null;
  return {
    status: exactExport ? "exported" : review ? "approved" : fallbackStatus,
    run_id: authority.run_id,
    selected_candidate_id: authority.candidate_id,
    selected_candidate_digest: authority.candidate_digest,
    selected_revision_id: authority.revision_id,
    selected_revision_digest: authority.revision_digest,
    parent_job_id: authority.parent_job_id,
    checkpoint_version: authority.checkpoint_version,
    quality_review_id: optionalIdentifier(review?.review_id),
    quality_decision: review ? "approve" : "",
    last_export_id: optionalIdentifier(exactExport?.export_id),
    delivery_sha256: optionalDigest(exactExport?.delivery_sha256),
    representative_episode: representativeEpisodeBindingSummary(run),
    message: exactExport ? "Exact approved revision exported." : review ? "Exact revision approved for production export." : "Ready for quality approval.",
    ...overrides,
  };
}

function approvedReviewForAuthority(run, authority) {
  if (String(run?.status || "") === "quality_rejected") return null;
  const reviews = Array.isArray(run?.quality_reviews) ? run.quality_reviews : [];
  return [...reviews].reverse().find((review) => (
    String(review?.decision || "") === "approve"
    && optionalIdentifier(review?.selected_revision_id) === authority.revision_id
    && optionalDigest(review?.selected_revision_digest) === authority.revision_digest
  )) || null;
}

function latestExport(run) {
  const exports = Array.isArray(run?.exports) ? run.exports : [];
  return exports.at(-1) || null;
}

function normalizedChecklist(value) {
  const source = objectValue(value);
  return {
    story_intent_preserved: source.story_intent_preserved === true,
    character_continuity_checked: source.character_continuity_checked === true,
    shot_coverage_checked: source.shot_coverage_checked === true,
    revision_addressed: source.revision_addressed === true,
  };
}

function visibleDeliveryCandidates(node) {
  const standard = candidatePreviewsFromNode(node);
  if (standard.length >= 2) return standard;
  const dedicated = Array.isArray(node?.params?.reviewDeliveryCandidates)
    ? node.params.reviewDeliveryCandidates
    : [];
  return dedicated.map((item) => ({
    candidate_id: optionalIdentifier(item?.candidate_id),
    canonical_digest: optionalDigest(item?.canonical_digest),
    parent_job_id: optionalIdentifier(item?.parent_job_id),
  })).filter((item) => item.candidate_id && item.canonical_digest && item.parent_job_id);
}

function checklistFromPanel(panel) {
  const fields = ["story_intent_preserved", "character_continuity_checked", "shot_coverage_checked", "revision_addressed"];
  return Object.fromEntries(fields.map((name) => [
    name,
    Boolean(panel?.querySelector?.(`[data-delivery-check="${name}"]`)?.checked),
  ]));
}

function authoritativeRun(payload) {
  const run = payload?.production_run || payload?.safe_summary?.production_run || payload;
  if (!run || typeof run !== "object" || Array.isArray(run)) {
    throw deliveryError("delivery_readback_invalid", "Production readback did not return a safe run summary.");
  }
  return run;
}

function recordPending(store, nodeId, status, message) {
  recordDeliveryState(store, nodeId, { ...productionDeliverySummary(store?.get?.()?.nodes?.[nodeId]), status, message });
}

function recordFailure(store, nodeId, code, message) {
  recordDeliveryState(store, nodeId, { ...productionDeliverySummary(store?.get?.()?.nodes?.[nodeId]), status: code, message });
  return { ok: false, code, message };
}

function recordDeliveryState(store, nodeId, value) {
  store?.set?.((state) => {
    const node = state.nodes?.[nodeId];
    if (!node) return;
    node.params = node.params || {};
    node.params.productionDelivery = value;
  }, { history: false });
}

function setPanelBusy(panel, busy) {
  if (!panel) return;
  panel.dataset.busy = busy ? "true" : "false";
  panel.setAttribute?.("aria-busy", busy ? "true" : "false");
  panel.querySelectorAll?.("button, input").forEach((control) => { control.disabled = busy; });
}

function updatePanelStatus(panel, result) {
  const status = panel?.querySelector?.("[data-production-delivery-status]");
  if (!status) return;
  status.dataset.state = result?.status || result?.code || "idle";
  status.textContent = result?.message || (result?.ok ? "Production delivery state refreshed." : "Production delivery action failed.");
}

function uniqueIdentifier(prefix, authority) {
  const stamp = Date.now().toString(36);
  const nonce = Math.random().toString(36).slice(2, 8);
  return `${prefix}-${String(authority.run_id).slice(0, 36)}-${String(authority.revision_id).slice(0, 36)}-${stamp}-${nonce}`.slice(0, 160);
}

function classifyError(error) {
  if (error?.code) return String(error.code);
  if (Number(error?.status) === 409) return "delivery_stale_checkpoint";
  if (Number(error?.status) === 401 || Number(error?.status) === 403) return "delivery_auth_required";
  return "delivery_failed";
}

function assertDedicatedDeliverySnapshot(expected, current) {
  const fields = [
    "run_id",
    "candidate_id",
    "candidate_digest",
    "revision_id",
    "revision_digest",
    "parent_job_id",
    "checkpoint_version",
    "checkpoint_digest",
  ];
  if (fields.some((field) => String(expected?.[field] ?? "") !== String(current?.[field] ?? ""))) {
    throw deliveryError("delivery_stale_snapshot", "The visible delivery state no longer matches production authority.");
  }
}

function isDedicatedDeliveryStaleCode(code) {
  return new Set([
    "delivery_stale_snapshot",
    "delivery_stale_checkpoint",
    "delivery_run_stale",
    "delivery_candidate_stale",
    "delivery_revision_stale",
    "delivery_lineage_stale",
    "delivery_checkpoint_invalid",
    "delivery_creator_rejected",
  ]).has(String(code || ""));
}

function publicErrorMessage(error) {
  const code = classifyError(error);
  const messages = {
    delivery_stale_checkpoint: "Production state changed. Refresh the exact selection before continuing.",
    delivery_auth_required: "Authentication is required for production delivery.",
  };
  return messages[code] || String(error?.message || "Production delivery action failed.");
}

function safeIdentifier(value, field) {
  const id = String(value || "").trim();
  if (!SAFE_ID_RE.test(id)) throw deliveryError(`delivery_${field}_invalid`, `Production ${field} is missing or invalid.`);
  return id;
}

function optionalIdentifier(value) {
  const id = String(value || "").trim();
  return SAFE_ID_RE.test(id) ? id : "";
}

function safeDigest(value, field) {
  const digest = String(value || "").trim().toLowerCase();
  if (!SHA256_RE.test(digest)) throw deliveryError(`delivery_${field}_invalid`, `Production ${field} is missing or invalid.`);
  return digest;
}

function optionalDigest(value) {
  const digest = String(value || "").trim().toLowerCase();
  return SHA256_RE.test(digest) ? digest : "";
}

function exactEntityRefs(value, expectedCount, label) {
  if (!Array.isArray(value) || value.length !== expectedCount) {
    throw deliveryError(`delivery_episode_${label}_refs_invalid`, `Representative episode ${label} refs are incomplete.`);
  }
  const refs = value.map((item) => ({
    entity_id: safeIdentifier(item?.entity_id, `${label}_id`),
    current_approved_version_id: safeIdentifier(item?.current_approved_version_id, `${label}_version_id`),
  }));
  if (new Set(refs.map((item) => item.entity_id)).size !== refs.length) {
    throw deliveryError(`delivery_episode_${label}_refs_invalid`, `Representative episode ${label} refs are duplicated.`);
  }
  return refs;
}

function exactAssetRefs(value) {
  if (!Array.isArray(value) || value.length !== 25) {
    throw deliveryError("delivery_episode_asset_refs_invalid", "Representative episode asset refs are incomplete.");
  }
  const refs = value.map((item) => {
    const status = String(item?.status || "");
    if (!new Set(["missing", "ready"]).has(status)) {
      throw deliveryError("delivery_episode_asset_status_invalid", "Representative episode asset readiness is invalid.");
    }
    if (typeof item?.provider_needed !== "boolean" || (status === "missing" && !item.provider_needed)) {
      throw deliveryError("delivery_episode_provider_gate_invalid", "Missing representative episode assets must retain the provider gate.");
    }
    return {
      asset_id: safeIdentifier(item?.asset_id, "asset_id"),
      current_revision_id: safeIdentifier(item?.current_revision_id, "asset_revision_id"),
      status,
      provider_needed: item.provider_needed,
    };
  });
  if (new Set(refs.map((item) => item.asset_id)).size !== refs.length) {
    throw deliveryError("delivery_episode_asset_refs_invalid", "Representative episode asset refs are duplicated.");
  }
  return refs;
}

function safeLineageRef(value, field) {
  const identifier = optionalIdentifier(value);
  if (identifier) return identifier;
  return safeDigest(value, field);
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function deliveryError(code, message) {
  const error = new Error(message);
  error.code = code;
  return error;
}
