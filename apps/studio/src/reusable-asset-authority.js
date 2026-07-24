const AUTHORITY_SCHEMA_VERSION = "afs_studio_reusable_asset_authority.v0.1";
const SAFE_ASSET_ID_RE = /^[A-Za-z0-9][A-Za-z0-9_.-]*$/;
const SAFE_JOB_ID_RE = /^[A-Za-z0-9][A-Za-z0-9_.-]*$/;
const SAFE_CANDIDATE_ID_RE = /^candidate_\d{3}$/;
const SHA256_RE = /^[a-f0-9]{64}$/;
const CANDIDATE_PREVIEW_ROUTE_RE = /^\/projects\/([A-Za-z0-9_.-]+)\/keyframe-generations\/([A-Za-z0-9_.-]+)\/candidates\/(candidate_\d{3})\/preview$/;
const IMAGE_ASSET_PREVIEW_ROUTE_RE = /^\/projects\/([A-Za-z0-9_.-]+)\/image-assets\/([A-Za-z0-9_.-]+)\/preview$/;

export function selectReusableAssetAuthority(candidate, assets) {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return null;
  if (!Array.isArray(assets)) return null;
  const candidateId = exactString(candidate.candidate_id, SAFE_CANDIDATE_ID_RE);
  const parentJobId = exactString(candidate.parent_job_id, SAFE_JOB_ID_RE);
  const canonicalDigest = exactString(candidate.canonical_digest, SHA256_RE);
  const previewRoute = validatedCandidatePreviewRoute(candidate);
  if (!candidateId || !parentJobId || !canonicalDigest || !previewRoute) return null;
  const matching = assets.filter((asset) => (
    asset
    && typeof asset === "object"
    && !Array.isArray(asset)
    && exactString(asset.source_candidate_id, SAFE_CANDIDATE_ID_RE) === candidateId
  ));
  if (matching.length !== 1) return null;
  return validatedAuthority(matching[0], {
    candidateId,
    parentJobId,
    canonicalDigest,
    projectId: previewRoute.project_id,
  });
}

export function validatedCandidatePreviewRoute(candidate) {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return null;
  const hasCandidateId = candidate.candidate_id !== undefined && candidate.candidate_id !== null && candidate.candidate_id !== "";
  const hasParentJobId = candidate.parent_job_id !== undefined && candidate.parent_job_id !== null && candidate.parent_job_id !== "";
  const candidateId = hasCandidateId ? exactString(candidate.candidate_id, SAFE_CANDIDATE_ID_RE) : "";
  const parentJobId = hasParentJobId ? exactString(candidate.parent_job_id, SAFE_JOB_ID_RE) : "";
  const projectId = exactString(candidate.project_id, SAFE_JOB_ID_RE);
  if ((hasCandidateId && !candidateId) || (hasParentJobId && !parentJobId) || !projectId) return null;
  const values = [
    candidate.preview_url,
    candidate.url,
    candidate.previewUrl,
    candidate.image_asset_preview_url,
    candidate.imageAssetPreviewUrl,
  ]
    .filter((value) => value !== undefined && value !== null && value !== "");
  if (!values.length) return null;
  const parsed = values.map(parseCandidatePreviewRoute);
  if (parsed.some((item) => !item)) return null;
  const first = parsed[0];
  if (parsed.some((item) => item.route !== first.route)) return null;
  if ((parentJobId && first.job_id !== parentJobId) || (candidateId && first.candidate_id !== candidateId)) return null;
  if (projectId !== first.project_id) return null;
  return Object.freeze(first);
}

function validatedAuthority(asset, candidate) {
  if ("schema_version" in asset && asset.schema_version !== AUTHORITY_SCHEMA_VERSION) return null;
  const assetId = exactString(asset.asset_id, SAFE_ASSET_ID_RE);
  const sourceCandidateId = exactString(asset.source_candidate_id, SAFE_CANDIDATE_ID_RE);
  const sourceJobId = exactString(asset.source_job_id, SAFE_JOB_ID_RE);
  const sourceCandidateDigest = exactString(asset.source_candidate_digest, SHA256_RE);
  const sha256 = exactString(asset.sha256, SHA256_RE);
  if (!assetId || asset.status !== "succeeded") return null;
  if (asset.role !== "generated_keyframe_reference" || asset.source_kind !== "keyframe_candidate") return null;
  if (sourceCandidateId !== candidate.candidateId || sourceJobId !== candidate.parentJobId) return null;
  if (sourceCandidateDigest !== candidate.canonicalDigest || sha256 !== sourceCandidateDigest) return null;
  const mediaEvidence = validatedMediaEvidence(asset, {
    assetId,
    projectId: candidate.projectId,
  });
  return Object.freeze({
    schema_version: AUTHORITY_SCHEMA_VERSION,
    asset_id: assetId,
    role: "generated_keyframe_reference",
    source_kind: "keyframe_candidate",
    status: "succeeded",
    source_job_id: sourceJobId,
    source_candidate_id: sourceCandidateId,
    source_candidate_digest: sourceCandidateDigest,
    sha256,
    ...(mediaEvidence || {}),
  });
}

function validatedMediaEvidence(asset, expected) {
  const supplied = [
    asset.preview_url,
    asset.mime_type,
    asset.width,
    asset.height,
  ].some((value) => value !== undefined && value !== null && value !== "");
  if (!supplied) return null;
  const preview = parseImageAssetPreviewRoute(asset.preview_url);
  const mimeType = asset.mime_type === "image/png" || asset.mime_type === "image/jpeg" ? asset.mime_type : "";
  const width = safeDimension(asset.width);
  const height = safeDimension(asset.height);
  if (!preview || preview.projectId !== expected.projectId || preview.assetId !== expected.assetId) return null;
  if (!mimeType || !width || !height) return null;
  return {
    mime_type: mimeType,
    width,
    height,
    preview_url: preview.route,
  };
}

function parseImageAssetPreviewRoute(value) {
  if (typeof value !== "string" || value !== value.trim()) return null;
  const match = value.match(IMAGE_ASSET_PREVIEW_ROUTE_RE);
  return match ? { route: value, projectId: match[1], assetId: match[2] } : null;
}

function safeDimension(value) {
  const number = Number(value);
  return Number.isInteger(number) && number > 0 && number <= 20000 ? number : 0;
}

function exactString(value, pattern) {
  if (typeof value !== "string" || value !== value.trim() || !pattern.test(value)) return "";
  return value;
}

function parseCandidatePreviewRoute(value) {
  if (typeof value !== "string" || value !== value.trim()) return null;
  const match = value.match(CANDIDATE_PREVIEW_ROUTE_RE);
  if (!match) return null;
  return {
    route: value,
    preview_url: value,
    project_id: match[1],
    job_id: match[2],
    candidate_id: match[3],
  };
}
