import { normalizeMangaFirstL4AProjection } from "./manga-first-l4a-projection.js";
import { createRuntimeClient } from "./runtime-client.js";

const SHA256_RE = /^[a-f0-9]{64}$/;

export async function createMangaFirstL4BWorkspace({
  projectId,
  brief,
  idempotencyKey = "",
  includeManifest = false,
  runtimeClient = null,
} = {}) {
  const client = runtimeClient || createRuntimeClient(projectId);
  const response = await client.createMangaFirstProductionTruth(brief, {
    idempotencyKey: idempotencyKey || `manga-first-l4b-${projectId}-v1`,
    includeManifest,
  });
  return normalizeMangaFirstL4BWorkspace(response);
}

export async function loadMangaFirstL4BWorkspace({ projectId, runtimeClient = null } = {}) {
  const client = runtimeClient || createRuntimeClient(projectId);
  const response = await client.loadMangaFirstWorkspace();
  return normalizeMangaFirstL4BWorkspace(response);
}

export async function approveMangaFirstL4BReferenceSet({
  projectId,
  referenceApprovalGate,
  runtimeClient = null,
  decisionId = "",
} = {}) {
  const client = runtimeClient || createRuntimeClient(projectId);
  const gate = referenceApprovalGate || {};
  const response = await client.approveMangaFirstReferenceSet({
    decision_id: decisionId || `manga-reference-approval-${Date.now()}`,
    expected_aggregate_version: gate.aggregate_version,
    reference_set_digest: gate.reference_set_digest,
  });
  return normalizeMangaFirstL4BWorkspace(response);
}

export function normalizeMangaFirstL4BWorkspace(payload) {
  const workspace = payload?.studio_workspace && typeof payload.studio_workspace === "object"
    ? payload.studio_workspace
    : payload;
  if (!workspace || typeof workspace !== "object" || Array.isArray(workspace)) return null;
  if (workspace.schema_version !== "afs.manga_first_l4b.studio_workspace.v0.1") return null;
  const projection = normalizeMangaFirstL4AProjection({ studio_projection: workspace.studio_projection });
  if (!projection) return null;
  const authority = normalizeAuthority(workspace.truth_authority);
  if (!authority || authority.second_fact_source_allowed !== false) return null;
  const referenceApprovalGate = normalizeReferenceApprovalGate(workspace.reference_approval_gate || workspace.studio_projection?.reference_approval_gate);
  return {
    schema_version: workspace.schema_version,
    project_id: safeText(workspace.project_id, 160),
    truth_authority: authority,
    project: projection.project,
    shot_status: projection.shot_status,
    candidates: projection.candidates,
    timeline: projection.timeline,
    qa: projection.qa,
    final_demo: projection.final_demo,
    reference_approval_gate: referenceApprovalGate,
    assembly_contract: normalizeAssemblyContract(workspace.assembly_contract),
    provider_dispatch_count: Number(workspace.provider_dispatch_count || 0) === 0 ? 0 : null,
    fabricated_state_allowed: false,
    non_claims: arrayOf(workspace.non_claims).map((item) => safeText(item, 160)).filter(Boolean),
  };
}

function normalizeAuthority(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const aggregateSha = safeDigest(value.aggregate_sha256);
  const manifestArtifact = normalizeArtifactRef(value.manifest_artifact);
  const checkpointArtifact = normalizeArtifactRef(value.checkpoint_artifact);
  if (!aggregateSha || !manifestArtifact || !checkpointArtifact) return null;
  return {
    primary: value.primary === "ProductionProjectAggregate" ? "ProductionProjectAggregate" : "",
    aggregate_sha256: aggregateSha,
    manifest_artifact: manifestArtifact,
    checkpoint_artifact: checkpointArtifact,
    second_fact_source_allowed: value.second_fact_source_allowed === true ? true : false,
  };
}

function normalizeArtifactRef(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const artifactId = safeText(value.artifact_id, 160);
  if (!artifactId || /\/|\\|:/.test(artifactId)) return null;
  return {
    artifact_id: artifactId,
    artifact_type: safeText(value.artifact_type, 120),
    filename: safeText(value.filename, 160),
    role: safeText(value.role, 120),
    media_type: safeText(value.media_type, 120),
  };
}

function normalizeAssemblyContract(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  return {
    schema_version: safeText(value.schema_version, 120),
    manual_editing_required: value.manual_editing_required === true ? true : false,
    final_mp4_required: value.final_mp4?.required === true,
    otio_required: value.timeline_otio?.required === true,
    proxy_required: value.proxy_media?.required === true,
    lineage_required: value.lineage_manifest?.required === true,
  };
}

function normalizeReferenceApprovalGate(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {
      status: "unknown",
      status_label: "参考设定状态未知",
      provider_ready: false,
      approval_required_before_provider: true,
    };
  }
  return {
    schema_version: safeText(value.schema_version, 120),
    status: value.status === "confirmed" ? "confirmed" : "pending_human",
    status_label: safeText(value.status_label, 80) || (value.status === "confirmed" ? "参考设定已确认" : "参考设定待确认"),
    approval_state: safeText(value.approval_state, 80),
    human_confirmed: value.human_confirmed === true,
    reference_set_ref: normalizeEntityRef(value.reference_set_ref),
    reference_set_digest: safeDigest(value.reference_set_digest),
    aggregate_version: safePositiveInt(value.aggregate_version, 0),
    provider_ready: value.provider_ready === true,
    bound_shot_count: safePositiveInt(value.bound_shot_count, 0),
    shot_count: safePositiveInt(value.shot_count, 0),
    approval_required_before_provider: value.approval_required_before_provider !== false,
    non_claims: arrayOf(value.non_claims).map((item) => safeText(item, 120)).filter(Boolean),
  };
}

function normalizeEntityRef(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const entityId = safeText(value.entity_id, 160);
  const versionId = safeText(value.version_id, 160);
  if (!entityId || !versionId || /\/|\\|:/.test(`${entityId}${versionId}`)) return null;
  return {
    entity_type: safeText(value.entity_type, 80),
    entity_id: entityId,
    version_id: versionId,
  };
}

function arrayOf(value) {
  return Array.isArray(value) ? value : [];
}

function safeDigest(value) {
  const text = String(value || "").trim();
  return SHA256_RE.test(text) ? text : "";
}

function safeText(value, maxLen) {
  return String(value || "").replace(/\s+/g, " ").trim().slice(0, maxLen);
}

function safePositiveInt(value, fallback = 0) {
  const number = Number(value);
  return Number.isInteger(number) && number >= 0 ? number : fallback;
}
