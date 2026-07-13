import { candidatePreviewsFromNode } from "./node-candidate-previews.js";
import { mergeImageAssets } from "./node-image-assets.js";
import { selectReusableAssetAuthority } from "./reusable-asset-authority.js";

const SHA256_RE = /^[a-f0-9]{64}$/;
const SAFE_ID_RE = /^[A-Za-z0-9][A-Za-z0-9_.-]{0,159}$/;
const DEFAULT_SELECTION_INTENT = "Keep this candidate as the selected production base.";
const AUTO_RESTORE_IN_FLIGHT = new WeakMap();
const PRODUCTION_CREATE_IN_FLIGHT = new WeakMap();

export function candidateSelectionSummary(node) {
  const value = node?.params?.creatorSelection;
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

export function isCandidateSelectable(candidate) {
  const status = String(candidate?.status || candidate?.state || "").trim().toLowerCase();
  const blocked = new Set([
    "failed",
    "failure",
    "error",
    "timeout",
    "timed_out",
    "retryable",
    "blocked",
    "needs_attention",
    "cancelled",
    "partial",
  ]);
  return Boolean(
    candidate?.candidate_id
    && (candidate?.url || candidate?.preview_url)
    && !blocked.has(status)
    && reusableAssetAuthority(candidate),
  );
}

export function buildCreatorDecisionContext(run, node, candidate, decision, revisionIntent, options = {}) {
  const runId = safeIdentifier(run?.run_id, "run_id");
  const nodeId = safeIdentifier(node?.id, "node_id");
  const candidateId = safeIdentifier(candidate?.candidate_id, "candidate_id");
  const canonicalDigest = safeDigest(candidate?.canonical_digest, "canonical_digest");
  const subjectDigest = safeDigest(run?.subject_digest, "subject_digest");
  const checkpointVersion = Number(run?.checkpoint?.version || 0);
  if (!Number.isInteger(checkpointVersion) || checkpointVersion < 1) {
    throw selectionError("invalid_checkpoint", "Production checkpoint is missing or invalid.");
  }
  const jobId = safeIdentifier(candidate?.parent_job_id, "parent_job_id");
  const nodeJobId = String(node?.params?.lastKeyframeJobId || node?.params?.lastVideoJobId || "").trim();
  if (nodeJobId && nodeJobId !== jobId) {
    throw selectionError("lineage_mismatch", "Candidate lineage does not match this node generation job.");
  }
  const normalizedDecision = ["select", "revise", "reject"].includes(decision) ? decision : "select";
  const intent = String(revisionIntent || "").trim() || (normalizedDecision === "select" ? DEFAULT_SELECTION_INTENT : "");
  if (!intent) throw selectionError("missing_revision_intent", "Enter revision intent before requesting a revision.");
  if (intent.length > 800) throw selectionError("revision_intent_too_long", "Revision intent must be 800 characters or fewer.");

  const selectedRevision = objectValue(run?.selected_revision);
  const currentRevisionId = optionalIdentifier(selectedRevision.revision_id || selectedRevision.selected_revision_id);
  if (normalizedDecision === "revise" && !currentRevisionId) {
    throw selectionError("missing_parent_revision", "Refresh the authoritative selection before requesting a revision.");
  }
  const parentRevisionId = currentRevisionId || optionalIdentifier(candidate?.parent_revision_id);
  const suffix = safeIdentifier(
    options.idempotencyKey || `creator-${normalizedDecision}-${shortIdentifier(runId)}-${shortIdentifier(candidateId)}-${checkpointVersion}-${uniqueSuffix(options)}`,
    "idempotency_key",
  );
  const decisionId = safeIdentifier(options.decisionId || `decision-${suffix}`.slice(0, 160), "decision_id");
  const parentCandidateId = optionalIdentifier(candidate?.parent_candidate_id);

  return {
    run_id: runId,
    node_id: nodeId,
    job_id: jobId,
    candidate_id: candidateId,
    canonical_digest: canonicalDigest,
    parent_lineage: {
      parent_job_id: jobId,
      parent_candidate_id: parentCandidateId,
      parent_revision_id: parentRevisionId,
    },
    revision_intent: intent,
    expected_checkpoint_version: checkpointVersion,
    idempotency_key: suffix,
    request: {
      schema_version: "afs_creator_decision.v0.1",
      decision_id: decisionId,
      idempotency_key: suffix,
      expected_checkpoint_version: checkpointVersion,
      subject_digest: subjectDigest,
      decision: normalizedDecision,
      candidate_id: candidateId,
      candidate_digest: canonicalDigest,
      parent_revision_id: parentRevisionId || null,
      revision_intent: intent,
    },
  };
}

export async function restoreCandidateSelection(store, runtime, node) {
  const runId = activeRunId(store, node);
  if (!runtime?.getProductionRun) {
    return recordFailure(store, node.id, "client_contract_missing", "Production readback is unavailable.");
  }
  try {
    requireReusableAssetAuthority(preflightRestorableCandidate(store, node));
    const payload = await runtime.getProductionRun(runId);
    const run = authoritativeRun(payload);
    const result = applyAuthoritativeProductionRun(store, node.id, run, { binding: payload?.studio_binding });
    await store.flushRuntimeSave?.();
    return { ok: true, ...result };
  } catch (error) {
    if (isNonMutatingAuthorityError(error)) return failureResult(error);
    return recordFailure(store, node.id, classifyError(error), publicErrorMessage(error));
  }
}

function preflightRestorableCandidate(store, node) {
  const state = store?.get?.() || {};
  const currentNode = state.nodes?.[node.id] || node;
  const candidates = candidatePreviewsFromNode(currentNode);
  const selectedCandidateId = optionalIdentifier(
    state.production?.selected_candidate_id || candidateSelectionSummary(currentNode).selected_candidate_id,
  );
  if (selectedCandidateId) {
    return candidates.find((candidate) => candidate.candidate_id === selectedCandidateId) || null;
  }
  return candidates.length === 1 ? candidates[0] : null;
}

export async function restoreCandidateSelectionsAfterLoad(store, runtime) {
  if (!store?.get) return { ok: true, skipped: "store_unavailable" };
  if (!runtime?.getProductionRun) return { ok: true, skipped: "authority_unavailable" };
  const state = store.get();
  const runId = optionalIdentifier(state?.production?.active_run_id);
  if (!runId) return { ok: true, skipped: "run_unbound" };
  const node = automaticRestoreTarget(state, runId);
  if (!node) return { ok: true, skipped: "selection_target_unavailable" };
  const existing = AUTO_RESTORE_IN_FLIGHT.get(store);
  if (existing) return existing;
  const pending = restoreCandidateSelection(store, runtime, node);
  AUTO_RESTORE_IN_FLIGHT.set(store, pending);
  try {
    return await pending;
  } finally {
    if (AUTO_RESTORE_IN_FLIGHT.get(store) === pending) AUTO_RESTORE_IN_FLIGHT.delete(store);
  }
}

export async function ensureProductionRunForCandidateSelection(store, runtime, node) {
  const state = store?.get?.() || {};
  const currentNode = state.nodes?.[node?.id] || node;
  const currentRunId = optionalIdentifier(state.production?.active_run_id);
  if (currentRunId && productionRunBelongsToCandidateSelection(currentNode, currentRunId)) {
    return { ok: true, run_id: currentRunId, created: false };
  }
  if (!runtime?.createProductionRun) {
    throw selectionError("client_contract_missing", "Authenticated production run creation is unavailable.");
  }
  const existing = PRODUCTION_CREATE_IN_FLIGHT.get(store);
  if (existing) return existing;
  const pending = createAndBindProductionRun(store, runtime, currentNode);
  PRODUCTION_CREATE_IN_FLIGHT.set(store, pending);
  try {
    return await pending;
  } finally {
    if (PRODUCTION_CREATE_IN_FLIGHT.get(store) === pending) PRODUCTION_CREATE_IN_FLIGHT.delete(store);
  }
}

export async function submitCandidateSelection(store, runtime, node, candidateId, options = {}) {
  return submitCreatorDecision(store, runtime, node, candidateId, "select", options.revisionIntent, options);
}

export async function submitCandidateRevision(store, runtime, node, candidateId, revisionIntent, options = {}) {
  return submitCreatorDecision(store, runtime, node, candidateId, "revise", revisionIntent, options);
}

export async function handleCandidateCreatorAction(store, runtime, node, actionEl) {
  const action = String(actionEl?.dataset?.action || "");
  const candidateId = String(actionEl?.dataset?.candidateId || "");
  const panel = actionEl?.closest?.(".candidate-selection-panel");
  if (actionEl?.disabled || panel?.dataset?.busy === "true" || candidateSelectionSummary(node).status === "saving") {
    return { ok: false, code: "selection_in_flight", message: "Wait for the current creator decision to finish." };
  }
  const revisionIntent = panel?.querySelector?.("[data-candidate-revision-intent]")?.value || "";
  setPanelBusy(panel, true);
  let result;
  try {
    if (action === "candidate-refresh") result = await restoreCandidateSelection(store, runtime, node);
    else if (action === "candidate-revise") result = await submitCandidateRevision(store, runtime, node, candidateId, revisionIntent);
    else result = await submitCandidateSelection(store, runtime, node, candidateId, { revisionIntent });
  } finally {
    setPanelBusy(panel, false);
  }
  updatePanelStatus(panel, result);
  if (result.ok) updatePanelSelection(panel, result.selected_candidate_id);
  return result;
}

export function handleCandidateGridKeydown(event) {
  const choice = event?.target?.closest?.('[role="radio"]');
  if ([" ", "Spacebar", "Enter"].includes(event?.key) && choice && !choice.disabled) {
    event.preventDefault();
    event.stopPropagation();
    choice.click();
    return true;
  }
  if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event?.key)) return false;
  const grid = event.currentTarget;
  const choices = [...(grid?.querySelectorAll?.('[role="radio"]:not([disabled])') || [])];
  if (!choices.length) return false;
  const current = choices.indexOf(event.target?.closest?.('[role="radio"]'));
  const delta = event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 1;
  const next = choices[(Math.max(0, current) + delta + choices.length) % choices.length];
  choices.forEach((choice) => { choice.tabIndex = choice === next ? 0 : -1; });
  next.focus();
  event.preventDefault();
  event.stopPropagation();
  return true;
}

export function applyAuthoritativeProductionRun(store, nodeId, run, options = {}) {
  const runId = safeIdentifier(run?.run_id, "run_id");
  const subjectDigest = safeDigest(run?.subject_digest, "subject_digest");
  const checkpointVersion = Number(run?.checkpoint?.version || 0);
  const checkpointDigest = safeDigest(run?.checkpoint?.state_digest, "checkpoint_digest");
  if (!Number.isInteger(checkpointVersion) || checkpointVersion < 1) {
    throw selectionError("invalid_checkpoint", "Production checkpoint is missing or invalid.");
  }
  const selection = selectedIdentity(run);
  if (!selection.candidate_id) {
    throw selectionError("selection_not_persisted", "The production run does not contain an authoritative selection.");
  }
  const candidate = (Array.isArray(run?.candidates) ? run.candidates : [])
    .find((item) => String(item?.candidate_id || "") === selection.candidate_id);
  if (!candidate) throw selectionError("candidate_not_in_run", "The selected candidate is not present in the production run.");
  const canonicalDigest = safeDigest(candidate.canonical_digest, "canonical_digest");
  if (selection.candidate_digest && selection.candidate_digest !== canonicalDigest) {
    throw selectionError("candidate_digest_mismatch", "Selected candidate integrity check failed.");
  }

  const selectedRevision = objectValue(run.selected_revision);
  const revisionId = optionalIdentifier(selectedRevision.revision_id || selectedRevision.selected_revision_id);
  const revisionDigest = optionalDigest(
    selectedRevision.canonical_digest || selectedRevision.revision_digest || selectedRevision.selected_revision_digest,
  );
  const fallbackBinding = {
    schema_version: "afs_studio_production_binding.v0.1",
    authoritative_source: "runtime_production_run",
    compatibility_mode: "backend_authoritative_summary_only",
    active_run_id: runId,
    checkpoint_version: checkpointVersion,
    checkpoint_digest: checkpointDigest,
    subject_digest: subjectDigest,
    selected_candidate_id: selection.candidate_id,
    selected_candidate_digest: canonicalDigest,
    selected_revision_id: revisionId,
    selected_revision_digest: revisionDigest,
    last_export_id: optionalIdentifier(run?.exports?.at?.(-1)?.export_id),
  };
  const binding = validatedStudioBinding(options.binding, fallbackBinding);
  const currentNode = store?.get?.()?.nodes?.[nodeId];
  if (!currentNode) throw selectionError("node_missing", "The selected Studio node no longer exists.");
  const currentPreview = candidatePreviewsFromNode(currentNode)
    .find((item) => String(item?.candidate_id || "") === selection.candidate_id);
  assertVisibleCandidateAuthority(currentPreview, candidate);
  let appliedPreview = false;
  store.set((state) => {
    const node = state.nodes?.[nodeId];
    if (!node) throw selectionError("node_missing", "The selected Studio node no longer exists.");
    const preview = candidatePreviewsFromNode(node)
      .find((item) => String(item?.candidate_id || "") === selection.candidate_id);
    const authority = assertVisibleCandidateAuthority(preview, candidate);
    state.production = binding;
    node.params = node.params || {};
    node.params.creatorSelection = {
      status: "persisted",
      authoritative_source: "runtime_production_run",
      run_id: runId,
      selected_candidate_id: selection.candidate_id,
      selected_candidate_digest: canonicalDigest,
      selected_revision_id: revisionId,
      selected_revision_digest: revisionDigest,
      checkpoint_version: checkpointVersion,
      checkpoint_digest: checkpointDigest,
      selected_parent_job_id: optionalIdentifier(candidate.parent_job_id),
      selected_parent_candidate_id: optionalIdentifier(candidate.parent_candidate_id),
      selected_asset_id: authority.asset_id,
    };
    const previewUrl = preview.preview_url || preview.url;
    node.previewUrl = previewUrl;
    node.params.previewAspectRatio = preview.aspect_ratio || node.params.previewAspectRatio || "9:16";
    if (authority.asset_id) {
      node.params.uploads = mergeImageAssets(node.params.uploads || [], {
        ...authority,
        preview_url: previewUrl,
        width: preview.width || null,
        height: preview.height || null,
        aspect_ratio: preview.aspect_ratio || null,
        role: "selected_candidate",
      }).slice(-4);
    }
    appliedPreview = true;
  }, { history: false });
  return {
    run_id: runId,
    selected_candidate_id: selection.candidate_id,
    selected_candidate_digest: canonicalDigest,
    checkpoint_version: checkpointVersion,
    preview_applied: appliedPreview,
  };
}

function automaticRestoreTarget(state, runId) {
  const nodes = Object.values(state?.nodes || {}).filter((node) => (
    candidatePreviewsFromNode(node).some((candidate) => reusableAssetAuthority(candidate))
  ));
  const bound = nodes.find((node) => candidateSelectionSummary(node).run_id === runId);
  if (bound) return bound;
  const selectedCandidateId = optionalIdentifier(state?.production?.selected_candidate_id);
  if (selectedCandidateId) {
    const matched = nodes.filter((node) => candidatePreviewsFromNode(node)
      .some((candidate) => candidate.candidate_id === selectedCandidateId));
    if (matched.length === 1) return matched[0];
  }
  return nodes.length === 1 ? nodes[0] : null;
}

async function submitCreatorDecision(store, runtime, node, candidateId, decision, revisionIntent, options) {
  const hasBoundRun = Boolean(optionalIdentifier(store?.get?.()?.production?.active_run_id));
  if (!runtime?.getProductionRun || !runtime?.submitCreatorDecision || (!hasBoundRun && !runtime?.createProductionRun)) {
    return recordFailure(store, node.id, "client_contract_missing", "Creator decision API is unavailable.");
  }
  try {
    const preflightNode = store?.get?.()?.nodes?.[node.id] || node;
    const preflightCandidate = candidatePreviewsFromNode(preflightNode)
      .find((item) => item.candidate_id === String(candidateId || ""));
    requireReusableAssetAuthority(preflightCandidate);
    await ensureProductionRunForCandidateSelection(store, runtime, node);
    const runId = activeRunId(store, node);
    const beforePayload = await runtime.getProductionRun(runId);
    const before = authoritativeRun(beforePayload);
    if (beforePayload?.studio_binding?.active_run_id) {
      validatedStudioBinding(beforePayload.studio_binding, productionBindingFromRun(before));
    }
    const candidate = (Array.isArray(before.candidates) ? before.candidates : [])
      .find((item) => String(item?.candidate_id || "") === String(candidateId || ""));
    if (!candidate) throw selectionError("candidate_not_in_run", "Candidate is not present in the authoritative production run.");
    const currentNode = store?.get?.()?.nodes?.[node.id] || node;
    const visible = candidatePreviewsFromNode(currentNode).find((item) => item.candidate_id === candidate.candidate_id);
    assertVisibleCandidateAuthority(visible, candidate);
    recordPending(store, node.id, decision);
    const context = buildCreatorDecisionContext(before, currentNode, candidate, decision, revisionIntent, options);
    const submitted = await runtime.submitCreatorDecision(runId, context.request);
    const afterPayload = await runtime.getProductionRun(runId);
    const after = authoritativeRun(afterPayload);
    const applied = applyAuthoritativeProductionRun(store, node.id, after, { binding: afterPayload?.studio_binding });
    const duplicate = Boolean(submitted?.idempotent_replay || submitted?.duplicate);
    if (duplicate) recordStatus(store, node.id, "duplicate_replayed", "Duplicate request was not re-applied; authoritative state was restored.");
    await store.flushRuntimeSave?.();
    return { ok: true, duplicate, context, ...applied };
  } catch (error) {
    if (isNonMutatingAuthorityError(error)) return failureResult(error);
    return recordFailure(store, node.id, classifyError(error), publicErrorMessage(error));
  }
}

function assertVisibleCandidateAuthority(visible, authoritative) {
  if (!visible || !isCandidateSelectable(visible)) {
    throw selectionError("candidate_authority_mismatch", "Visible candidate authority is incomplete. Refresh generation results before selecting.");
  }
  const visibleId = optionalIdentifier(visible.candidate_id);
  const authoritativeId = optionalIdentifier(authoritative?.candidate_id);
  const visibleDigest = optionalDigest(visible.canonical_digest || visible.sha256);
  const authoritativeDigest = optionalDigest(authoritative?.canonical_digest);
  const visibleJobId = optionalIdentifier(visible.parent_job_id);
  const authoritativeJobId = optionalIdentifier(authoritative?.parent_job_id);
  if (!visibleId || !authoritativeId || !visibleDigest || !authoritativeDigest || !visibleJobId || !authoritativeJobId
    || visibleId !== authoritativeId || visibleDigest !== authoritativeDigest || visibleJobId !== authoritativeJobId) {
    throw selectionError("candidate_authority_mismatch", "Visible candidate integrity or lineage no longer matches production authority. Refresh generation results before selecting.");
  }
  return requireReusableAssetAuthority(visible);
}

function reusableAssetAuthority(candidate) {
  if (!candidate?.reusable_asset_authority) return null;
  return selectReusableAssetAuthority(candidate, [candidate.reusable_asset_authority]);
}

function requireReusableAssetAuthority(candidate) {
  const authority = reusableAssetAuthority(candidate);
  if (!authority) {
    throw selectionError(
      "candidate_asset_authority_mismatch",
      "Candidate reusable asset integrity is incomplete. Refresh generation results before selecting.",
    );
  }
  return authority;
}

async function createAndBindProductionRun(store, runtime, node) {
  const request = await buildProductionRunCreateRequest(store, runtime, node);
  const payload = await runtime.createProductionRun(request);
  const run = authoritativeRun(payload);
  validateCreatedProductionRun(run, request);
  if (!payload?.studio_binding?.active_run_id) {
    throw selectionError("binding_contract_missing", "Production creation did not return an authoritative Studio binding.");
  }
  const binding = validatedStudioBinding(payload?.studio_binding, productionBindingFromRun(run));
  store.set((state) => {
    state.production = binding;
    const currentNode = state.nodes?.[node.id];
    if (currentNode) {
      currentNode.params = currentNode.params || {};
      currentNode.params.creatorSelection = {
        status: "run_bound",
        run_id: binding.active_run_id,
        selected_parent_job_id: request.candidates[0].parent_job_id,
      };
    }
  }, { history: false, persist: false });
  return {
    ok: true,
    created: !Boolean(payload?.idempotent_replay),
    duplicate: Boolean(payload?.idempotent_replay),
    run_id: binding.active_run_id,
    checkpoint_version: binding.checkpoint_version,
  };
}

async function buildProductionRunCreateRequest(store, runtime, node) {
  const projectId = safeIdentifier(runtime?.projectId || store?.get?.()?.meta?.projectId, "project_id");
  const nodeId = safeIdentifier(node?.id, "node_id");
  const candidates = candidatePreviewsFromNode(node).filter(isCandidateSelectable).map((candidate) => {
    const candidateId = safeIdentifier(candidate?.candidate_id, "candidate_id");
    const canonicalDigest = safeDigest(candidate?.canonical_digest || candidate?.sha256, "canonical_digest");
    const parentJobId = safeIdentifier(candidate?.parent_job_id || node?.params?.lastKeyframeJobId, "parent_job_id");
    return {
      candidate_id: candidateId,
      canonical_digest: canonicalDigest,
      parent_job_id: parentJobId,
      parent_candidate_id: optionalIdentifier(candidate?.parent_candidate_id) || null,
      parent_revision_id: null,
      shot_id: optionalIdentifier(candidate?.shot_id || node?.params?.structuredShot?.shot_id) || null,
      safe_artifact_refs: [],
    };
  });
  if (!candidates.length) {
    throw selectionError("candidate_contract_incomplete", "Candidate integrity metadata is unavailable; refresh generation results before selecting.");
  }
  const parentJobId = candidates[0].parent_job_id;
  if (candidates.some((candidate) => candidate.parent_job_id !== parentJobId)) {
    throw selectionError("candidate_lineage_mismatch", "Visible candidates do not share one authoritative generation job.");
  }
  const subjectDigest = await sha256Hex(JSON.stringify({
    schema_version: "afs_studio_production_subject.v0.1",
    project_id: projectId,
    node_id: nodeId,
    parent_job_id: parentJobId,
    candidates: candidates.map(({ candidate_id, canonical_digest }) => ({ candidate_id, canonical_digest })),
  }));
  return {
    schema_version: "afs_runtime_production_run.v0.1",
    run_id: derivedIdentifier("production", parentJobId),
    idempotency_key: derivedIdentifier("create", `${projectId}-${nodeId}-${parentJobId}`),
    subject_digest: subjectDigest,
    candidates,
  };
}

function validateCreatedProductionRun(run, request) {
  const runId = safeIdentifier(run?.run_id, "run_id");
  if (runId !== request.run_id) throw selectionError("creation_readback_mismatch", "Production run identity changed during creation.");
  const subjectDigest = safeDigest(run?.subject_digest, "subject_digest");
  if (subjectDigest !== request.subject_digest) {
    throw selectionError("creation_readback_mismatch", "Production subject integrity changed during creation.");
  }
  const actual = Array.isArray(run?.candidates) ? run.candidates : [];
  if (actual.length !== request.candidates.length) {
    throw selectionError("creation_readback_mismatch", "Production candidate inventory changed during creation.");
  }
  const expectedById = new Map(request.candidates.map((candidate) => [candidate.candidate_id, candidate]));
  for (const candidate of actual) {
    const candidateId = safeIdentifier(candidate?.candidate_id, "candidate_id");
    const expected = expectedById.get(candidateId);
    if (!expected
      || safeDigest(candidate?.canonical_digest, "canonical_digest") !== expected.canonical_digest
      || safeIdentifier(candidate?.parent_job_id, "parent_job_id") !== expected.parent_job_id) {
      throw selectionError("creation_readback_mismatch", "Production candidate lineage changed during creation.");
    }
  }
}

function authoritativeRun(payload) {
  const run = payload?.production_run || payload?.safe_summary?.production_run || payload;
  if (!run || typeof run !== "object" || Array.isArray(run)) {
    throw selectionError("invalid_readback", "Production readback did not return a safe run summary.");
  }
  return run;
}

function selectedIdentity(run) {
  const revision = objectValue(run?.selected_revision);
  const decisions = Array.isArray(run?.creator_decisions) ? run.creator_decisions : [];
  const latest = [...decisions].reverse().find((item) => ["select", "revise"].includes(String(item?.decision || ""))) || {};
  return {
    candidate_id: optionalIdentifier(revision.candidate_id || revision.selected_candidate_id || latest.candidate_id),
    candidate_digest: optionalDigest(revision.candidate_digest || revision.selected_candidate_digest || latest.candidate_digest),
  };
}

function productionBindingFromRun(run) {
  const runId = safeIdentifier(run?.run_id, "run_id");
  const subjectDigest = safeDigest(run?.subject_digest, "subject_digest");
  const checkpointVersion = Number(run?.checkpoint?.version || 0);
  const checkpointDigest = safeDigest(run?.checkpoint?.state_digest, "checkpoint_digest");
  if (!Number.isInteger(checkpointVersion) || checkpointVersion < 1) {
    throw selectionError("invalid_checkpoint", "Production checkpoint is missing or invalid.");
  }
  const selection = selectedIdentity(run);
  const candidate = selection.candidate_id
    ? (Array.isArray(run?.candidates) ? run.candidates : []).find((item) => item?.candidate_id === selection.candidate_id)
    : null;
  if (selection.candidate_id && !candidate) {
    throw selectionError("candidate_not_in_run", "The selected candidate is not present in the production run.");
  }
  const candidateDigest = candidate ? safeDigest(candidate.canonical_digest, "canonical_digest") : "";
  if (selection.candidate_digest && selection.candidate_digest !== candidateDigest) {
    throw selectionError("candidate_digest_mismatch", "Selected candidate integrity check failed.");
  }
  const revision = objectValue(run?.selected_revision);
  return {
    schema_version: "afs_studio_production_binding.v0.1",
    authoritative_source: "runtime_production_run",
    compatibility_mode: "backend_authoritative_summary_only",
    active_run_id: runId,
    checkpoint_version: checkpointVersion,
    checkpoint_digest: checkpointDigest,
    subject_digest: subjectDigest,
    selected_candidate_id: selection.candidate_id,
    selected_candidate_digest: candidateDigest,
    selected_revision_id: optionalIdentifier(revision.revision_id || revision.selected_revision_id),
    selected_revision_digest: optionalDigest(
      revision.canonical_digest || revision.revision_digest || revision.selected_revision_digest,
    ),
    last_export_id: optionalIdentifier(run?.exports?.at?.(-1)?.export_id),
  };
}

function validatedStudioBinding(value, fallback) {
  const source = objectValue(value);
  if (!source.active_run_id) return fallback;
  const binding = {
    schema_version: String(source.schema_version || ""),
    authoritative_source: String(source.authoritative_source || ""),
    compatibility_mode: String(source.compatibility_mode || ""),
    active_run_id: safeIdentifier(source.active_run_id, "binding_run_id"),
    checkpoint_version: Number(source.checkpoint_version || 0),
    checkpoint_digest: safeDigest(source.checkpoint_digest, "binding_checkpoint_digest"),
    subject_digest: safeDigest(source.subject_digest, "binding_subject_digest"),
    selected_candidate_id: optionalIdentifier(source.selected_candidate_id),
    selected_candidate_digest: optionalDigest(source.selected_candidate_digest),
    selected_revision_id: optionalIdentifier(source.selected_revision_id),
    selected_revision_digest: optionalDigest(source.selected_revision_digest),
    last_export_id: optionalIdentifier(source.last_export_id),
  };
  for (const key of [
    "active_run_id",
    "checkpoint_version",
    "checkpoint_digest",
    "subject_digest",
    "selected_candidate_id",
    "selected_candidate_digest",
    "selected_revision_id",
    "selected_revision_digest",
  ]) {
    if (binding[key] !== fallback[key]) {
      throw selectionError("binding_integrity_mismatch", `Authoritative Studio binding disagrees with production run field ${key}.`);
    }
  }
  if (binding.schema_version !== "afs_studio_production_binding.v0.1"
    || binding.authoritative_source !== "runtime_production_run"
    || binding.compatibility_mode !== "backend_authoritative_summary_only") {
    throw selectionError("binding_contract_mismatch", "Authoritative Studio binding contract is unsupported.");
  }
  return binding;
}

function activeRunId(store, node) {
  const value = store?.get?.()?.production?.active_run_id || candidateSelectionSummary(node).run_id;
  return safeIdentifier(value, "active_run_id");
}

function productionRunBelongsToCandidateSelection(node, runId) {
  const summary = candidateSelectionSummary(node);
  const parentJobId = currentCandidateSelectionParentJobId(node);
  return Boolean(
    parentJobId
    && optionalIdentifier(summary.run_id) === runId
    && optionalIdentifier(summary.selected_parent_job_id) === parentJobId
  );
}

function currentCandidateSelectionParentJobId(node) {
  const nodeJobId = optionalIdentifier(node?.params?.lastKeyframeJobId || node?.params?.lastVideoJobId);
  if (!nodeJobId) return "";
  const candidateJobIds = new Set(
    candidatePreviewsFromNode(node)
      .filter(isCandidateSelectable)
      .map((candidate) => optionalIdentifier(candidate?.parent_job_id))
      .filter(Boolean),
  );
  return candidateJobIds.size === 1 && candidateJobIds.has(nodeJobId) ? nodeJobId : "";
}

function recordPending(store, nodeId, action) {
  recordStatus(store, nodeId, "saving", action === "revise" ? "Saving revision request…" : "Saving selection…");
}

function recordFailure(store, nodeId, code, message) {
  recordStatus(store, nodeId, code, message);
  return { ok: false, code, message };
}

function failureResult(error) {
  return { ok: false, code: classifyError(error), message: publicErrorMessage(error) };
}

function isNonMutatingAuthorityError(error) {
  return new Set([
    "candidate_authority_mismatch",
    "candidate_asset_authority_mismatch",
    "candidate_digest_mismatch",
    "binding_integrity_mismatch",
    "binding_contract_mismatch",
  ]).has(classifyError(error));
}

function recordStatus(store, nodeId, status, message) {
  store?.set?.((state) => {
    const node = state.nodes?.[nodeId];
    if (!node) return;
    node.params = node.params || {};
    node.params.creatorSelection = {
      ...candidateSelectionSummary(node),
      status,
      message,
    };
  }, { history: false });
}

function classifyError(error) {
  if (error?.code) return String(error.code);
  if (Number(error?.status) === 409) return "stale_checkpoint";
  if ([401, 403].includes(Number(error?.status))) return "auth_required";
  return "retry_required";
}

function publicErrorMessage(error) {
  const code = classifyError(error);
  if (code === "stale_checkpoint") return "Selection was not saved because production state changed. Refresh and try again.";
  if (code === "auth_required") return "Sign in to the project before creating or changing a production selection.";
  if (code === "candidate_not_selectable") return "Failed or retryable candidates cannot be selected.";
  if (code === "missing_revision_intent") return "Enter revision intent before requesting a revision.";
  if (error?.publicMessage) return error.publicMessage;
  return "Selection was not saved. Retry after refreshing authoritative production state.";
}

function selectionError(code, publicMessage) {
  const error = new Error(publicMessage);
  error.code = code;
  error.publicMessage = publicMessage;
  return error;
}

function safeIdentifier(value, field) {
  const token = String(value || "").trim();
  if (!SAFE_ID_RE.test(token)) throw selectionError(`invalid_${field}`, `${field} is missing or invalid.`);
  return token;
}

function optionalIdentifier(value) {
  const token = String(value || "").trim();
  return token && SAFE_ID_RE.test(token) ? token : "";
}

function derivedIdentifier(prefix, value) {
  const normalized = String(value || "")
    .trim()
    .replace(/[^A-Za-z0-9_.-]+/g, "-")
    .replace(/^[^A-Za-z0-9]+|[^A-Za-z0-9]+$/g, "");
  return safeIdentifier(`${prefix}-${normalized}`.slice(0, 160).replace(/[^A-Za-z0-9]+$/g, ""), `${prefix}_id`);
}

async function sha256Hex(value) {
  if (!globalThis.crypto?.subtle || typeof TextEncoder === "undefined") {
    throw selectionError("digest_unavailable", "This browser cannot create the production integrity subject.");
  }
  const digest = await globalThis.crypto.subtle.digest("SHA-256", new TextEncoder().encode(String(value || "")));
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function safeDigest(value, field) {
  const digest = String(value || "").trim().toLowerCase();
  if (!SHA256_RE.test(digest)) throw selectionError(`invalid_${field}`, `${field} is missing or invalid.`);
  return digest;
}

function optionalDigest(value) {
  const digest = String(value || "").trim().toLowerCase();
  return SHA256_RE.test(digest) ? digest : "";
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function uniqueSuffix(options) {
  const now = Number(options.now ?? Date.now()).toString(36);
  const random = String(options.nonce ?? Math.random().toString(36).slice(2, 10));
  return `${now}-${random}`.replace(/[^A-Za-z0-9_.-]/g, "").slice(0, 32);
}

function shortIdentifier(value) {
  const token = String(value || "");
  if (token.length <= 32) return token;
  return `${token.slice(0, 18)}-${token.slice(-12)}`;
}

function updatePanelStatus(panel, result) {
  const status = panel?.querySelector?.("[data-candidate-selection-status]");
  if (!status) return;
  status.textContent = result.ok
    ? result.duplicate ? "Duplicate request ignored; authoritative selection restored." : "Selection saved and read back from production state."
    : result.message;
  status.dataset.state = result.ok ? (result.duplicate ? "duplicate_replayed" : "persisted") : result.code;
}

function setPanelBusy(panel, busy) {
  if (!panel) return;
  panel.dataset.busy = busy ? "true" : "false";
  panel.setAttribute?.("aria-busy", busy ? "true" : "false");
  const controls = panel.querySelectorAll?.([
    '[data-action="candidate-select"]',
    '[data-action="candidate-revise"]',
    '[data-action="candidate-refresh"]',
    "[data-candidate-revision-intent]",
  ].join(",")) || [];
  for (const control of controls) {
    if (busy) {
      control.__candidateBusyWasDisabled = Boolean(control.disabled);
      control.disabled = true;
    } else {
      control.disabled = Boolean(control.__candidateBusyWasDisabled);
      delete control.__candidateBusyWasDisabled;
    }
  }
  if (!busy) return;
  const status = panel.querySelector?.("[data-candidate-selection-status]");
  if (status) {
    status.dataset.state = "saving";
    status.textContent = "Saving creator decision and reading back authoritative state…";
  }
}

function updatePanelSelection(panel, candidateId) {
  for (const choice of panel?.querySelectorAll?.('[role="radio"]') || []) {
    const selected = choice.dataset.candidateId === candidateId;
    choice.setAttribute("aria-checked", selected ? "true" : "false");
    choice.classList.toggle("selected", selected);
    choice.tabIndex = selected ? 0 : -1;
    const label = choice.querySelector?.(".candidate-selected-label");
    if (label) label.textContent = selected ? "已选择" : "可选择";
  }
  const revise = panel?.querySelector?.('[data-action="candidate-revise"]');
  if (revise) {
    revise.dataset.candidateId = candidateId || "";
    revise.disabled = !candidateId;
  }
}
