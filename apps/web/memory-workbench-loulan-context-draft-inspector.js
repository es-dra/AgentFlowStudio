const CONTEXT_DRAFT_TYPE = "loulan_next_generation_context_bundle_draft";

export function isLoulanContextDraftArtifact(type) {
  return type === CONTEXT_DRAFT_TYPE;
}

export function loulanContextDraftTypeLabel(type) {
  return isLoulanContextDraftArtifact(type) ? "Loulan next context bundle draft" : "";
}

export function loulanContextDraftFocusTargets() {
  return ["project", "assets", "memory-loaded", "next-pass"];
}

export function loulanContextDraftStatus(payload) {
  return payload.status || "review ready";
}

export function loulanContextDraftFacts(payload) {
  const boundary = objectValue(payload.claim_boundary);
  const gates = objectValue(payload.gates);
  const projection = objectValue(payload.afs_projection_check);
  return [
    fact("project_id", payload.project_id || "unknown"),
    fact("target_next_block", payload.target_next_block || "unknown"),
    fact("eligible_context_refs", arrayValue(payload.eligible_context_refs).length),
    fact("blocked_refs_by_status", blockedCountsText(payload.blocked_context_refs_by_status)),
    fact("review_evidence_refs", arrayValue(payload.review_evidence_refs).length),
    fact("b01_keyframe_human_review", gates.b01_keyframe_human_review || "unknown"),
    fact("provider_image_gate", gates.provider_image_gate || "unknown"),
    fact("provider_video_gate", gates.provider_video_gate || "unknown"),
    fact("provider_calls_started", yesNo(boundary.provider_calls_started)),
    fact("new_media_generated", yesNo(boundary.new_media_generated)),
    fact("durable_memory_write", yesNo(boundary.durable_memory_write)),
    fact("eligible_refs_match_package", yesNo(projection.eligible_refs_match_package)),
  ];
}

function blockedCountsText(value) {
  return Object.entries(objectValue(value))
    .map(([status, refs]) => `${status}: ${arrayValue(refs).length}`)
    .join(", ") || "none";
}

function fact(label, value) {
  return { label, value: String(value) };
}

function yesNo(value) {
  return value === true ? "true" : "false";
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
