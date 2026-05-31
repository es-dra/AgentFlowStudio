const LOULAN_DIRECT_TYPES = new Set([
  "loulan_afs_b01_feedback_loop_gate",
  "loulan_afs_b01_decision_crosswalk",
  "loulan_b01_human_review_decision_template",
  "loulan_b01_decision_apply_plan_draft",
  "loulan_b01_decision_validation_report",
  "loulan_b01_decision_apply_result",
  "loulan_unified_asset_registry",
  "loulan_next_generation_context_bundle_draft",
  "loulan_image2_request_manifest",
  "loulan_kling_i2v_request_manifest",
  "loulan_character_asset_manifest",
  "loulan_character_asset_versions",
  "loulan_prop_asset_versions",
  "loulan_shot_list_manifest",
]);

export function buildLoulanManifestSetView(workspace, fallback) {
  if (workspace?.loulanPackage) return fallback;
  const bundle = memoryBundleFor(workspace).filter((artifact) => LOULAN_DIRECT_TYPES.has(artifact.artifactType));
  if (bundle.length < 2) return fallback;
  const byType = Object.fromEntries(bundle.map((artifact) => [artifact.artifactType, artifact.payload || {}]));
  const registry = byType.loulan_unified_asset_registry || {};
  const context = byType.loulan_next_generation_context_bundle_draft || {};
  const b01Template = byType.loulan_b01_human_review_decision_template || {};
  const image2 = byType.loulan_image2_request_manifest || {};
  const kling = byType.loulan_kling_i2v_request_manifest || {};
  const shotList = byType.loulan_shot_list_manifest || {};
  const eligibleRefs = arrayValue(context.eligible_context_refs).map(refText).filter(Boolean);
  const blockedRefs = blockedRefsFromContext(context);
  const pendingB01 = pendingDecisionCount(b01Template);
  const state = context.status || b01Template.status || (blockedRefs.length ? "blocked" : "review ready");
  const target = context.target_next_block || "next block";
  return {
    ...fallback,
    contract_type: "loulan_manifest_set",
    state,
    project: projectSummary({ bundle, registry, target }),
    assets: [...eligibleAssets(eligibleRefs), ...blockedAssets(blockedRefs)].slice(0, 12),
    bundle_summary: bundleSummary({ bundle, registry, context, b01Template, image2, kling, shotList, eligibleRefs, blockedRefs, pendingB01 }),
    memory_loaded: [...eligibleMemoryRefs(eligibleRefs), ...blockedMemoryRefs(blockedRefs)].slice(0, 16),
    lanes: manifestSetLanes({ target, eligibleRefs, blockedRefs, state }),
    protocol_summary: protocolSummary({ bundle, registry, context, b01Template }),
    review: {
      storyboard_adherence: `${arrayValue(shotList.shots).length || "unknown"} shots selected for manifest review.`,
      visual_consistency: `${eligibleRefs.length} eligible refs; ${blockedRefs.length} refs blocked from memory context.`,
      boundary: "Selected Loulan manifests are review evidence, not approval or durable Memory.",
    },
    feedback: {
      status: "planned",
      summary: "Feedback remains an operator draft until B01 decisions are filled and validated.",
    },
    feedback_draft: manifestSetFeedbackDraft({ registry, state, target }),
    next_pass: {
      status: state,
      action: `${target} blocked: ${eligibleRefs.length} eligible refs, ${blockedRefs.length} blocked refs; B01 human review required before next generation context.`,
    },
    timeline: manifestSetTimeline({ state, target, pendingB01, eligibleRefs, blockedRefs }),
  };
}

function projectSummary({ bundle, registry, target }) {
  const projectId = registry.project_id || "Loulan project";
  return {
    title: "Loulan manifest set",
    brief: `${bundle.length} selected Loulan manifests; target ${target}; ${projectId}`,
    format: "horizontal_16_9 manifest review",
    route: "selected local JSON manifests; no provider call",
  };
}

function bundleSummary({ bundle, registry, context, b01Template, image2, kling, shotList, eligibleRefs, blockedRefs, pendingB01 }) {
  const shots = arrayValue(shotList.shots);
  return [
    { id: "manifest-coverage", title: "Manifest coverage", status: "review ready", detail: `${bundle.length} selected Loulan manifests` },
    { id: "asset-registry", title: "Asset registry", status: blockedRefs.length ? "blocked" : "review ready", detail: `${registry.summary?.total_assets ?? "unknown"} assets; ${eligibleRefs.length} eligible, ${blockedRefs.length} blocked` },
    { id: "b01-human-review", title: "B01 human review", status: b01Template.status || context.gates?.b01_keyframe_human_review || "not_supplied", detail: `${pendingB01} pending B01 decisions` },
    { id: "request-manifests", title: "Request manifests", status: requestStatus(image2, kling), detail: `${arrayValue(image2.requests).length} Image2 requests; ${arrayValue(kling.requests).length} Kling I2V requests` },
    { id: "project-manifests", title: "Project manifests", status: shotStatus(shots), detail: `${shots.length} shots; character assets selected: ${String(Boolean(bundle.find((item) => item.artifactType === "loulan_character_asset_manifest")))}; prop assets selected: ${String(Boolean(bundle.find((item) => item.artifactType === "loulan_prop_asset_versions")))}` },
    { id: "context-draft", title: "Next context draft", status: context.status || "not_supplied", detail: `${context.target_next_block || "next block"}; ${arrayValue(context.review_evidence_refs).length} review evidence refs` },
  ];
}

function protocolSummary({ bundle, registry, context, b01Template }) {
  const boundary = context.claim_boundary || registry.claim_boundary || {};
  return {
    title: "Loulan manifest-set review protocol",
    status: context.status || b01Template.status || "review ready",
    controls: [
      { label: "manifest coverage", status: "review ready", detail: `${bundle.length} selected Loulan manifests` },
      { label: "B01 human review", status: b01Template.status || context.gates?.b01_keyframe_human_review || "not_supplied", detail: `${pendingDecisionCount(b01Template)} pending decisions` },
      { label: "provider image gate", status: context.gates?.provider_image_gate || "blocked_no_call", detail: "no image provider call from browser" },
      { label: "provider video gate", status: context.gates?.provider_video_gate || "blocked_no_call", detail: "no video provider call from browser" },
      { label: "provider calls started", status: "blocked", detail: String(Boolean(boundary.provider_calls_started)) },
      { label: "new media generated", status: "blocked", detail: String(Boolean(boundary.new_media_generated)) },
      { label: "durable memory write", status: "blocked", detail: String(Boolean(boundary.durable_memory_write || boundary.writes_long_term_memory)) },
    ],
    boundaries: [
      { label: "human acceptance", status: "blocked", detail: "not_recorded" },
      { label: "business validation", status: "blocked", detail: "not_validated" },
      { label: "candidate promotion", status: "blocked", detail: "requires explicit human decision" },
    ],
  };
}

function manifestSetLanes({ target, eligibleRefs, blockedRefs, state }) {
  return [
    {
      id: "baseline-lane",
      title: "Manifest Review",
      status: "review ready",
      input: "selected Loulan manifests",
      output: `${eligibleRefs.length} eligible refs and ${blockedRefs.length} blocked refs identified`,
    },
    {
      id: "memory-lane",
      title: "Next Context Draft",
      status: state === "review ready" ? "planned" : "blocked",
      input: `${target} context bundle draft`,
      output: state === "review ready" ? "ready for explicit review" : "blocked until B01 human review and promotion gates",
    },
  ];
}

function manifestSetTimeline({ state, target, pendingB01, eligibleRefs, blockedRefs }) {
  return [
    { label: "Manifest Set", status: "review ready", detail: "selected local Loulan JSON only" },
    { label: "B01 Human Review", status: pendingB01 ? "blocked_pending_human_review" : "review ready", detail: `${pendingB01} pending decisions` },
    { label: "Context Eligibility", status: blockedRefs.length ? "blocked" : "review ready", detail: `${eligibleRefs.length} eligible; ${blockedRefs.length} blocked` },
    { label: "Next Block", status: state, detail: `${target} remains no-call` },
  ];
}

function manifestSetFeedbackDraft({ registry, state, target }) {
  const event = {
    schema_version: "0.1.0",
    artifact_type: "agentflow_feedback_event",
    target_type: "loulan_manifest_set",
    target_id: registry.project_id || "loulan_manifest_set",
    decision: "note",
    draft_status: "draft_not_persisted",
    reason_tags: ["loulan_manifest_set", state, target],
    writes_long_term_memory: false,
  };
  return {
    mode: "loulan_manifest_set",
    status: event.draft_status,
    title: "Loulan Manifest Set Feedback Draft",
    detail: "Browser-local preview; copy for review, do not persist as durable memory.",
    json_text: JSON.stringify(event, null, 2),
    copy_enabled: true,
  };
}

function eligibleAssets(refs) {
  return refs.map((ref) => ({ id: ref, label: ref, detail: "eligible for next context draft", status: "approved" }));
}

function blockedAssets(refs) {
  return refs.map((item) => ({ id: item.ref, label: item.ref, detail: `blocked by ${item.status}`, status: "blocked" }));
}

function eligibleMemoryRefs(refs) {
  return refs.map((ref) => ({
    id: ref,
    title: ref,
    why_eligible: "listed in selected next context draft eligible refs",
    source_evidence_refs: [ref],
    promotion_status: "eligible_context_ref",
    request_projection: "can seed next context only after gates stay valid",
    feedback_effect: "reduces repeated asset restatement",
  }));
}

function blockedMemoryRefs(refs) {
  return refs.map((item) => ({
    id: item.ref,
    title: item.ref,
    why_eligible: `blocked by ${item.status}`,
    source_evidence_refs: [item.ref],
    promotion_status: `blocked_${item.status}`,
    request_projection: "not loaded into next context",
    feedback_effect: "requires repair, rejection, or explicit promotion",
  }));
}

function blockedRefsFromContext(context) {
  return Object.entries(objectValue(context.blocked_context_refs_by_status)).flatMap(([status, refs]) =>
    arrayValue(refs).map((ref) => ({ status, ref: refText(ref) })).filter((item) => item.ref),
  );
}

function refText(ref) {
  if (typeof ref === "string") return ref;
  const data = objectValue(ref);
  return data.memory_ref || data.asset_id || data.ref || data.id || data.current_ref || "";
}

function requestStatus(image2, kling) {
  const blocked = [...arrayValue(image2.requests), ...arrayValue(kling.requests)].some((request) => String(request?.status || "").startsWith("blocked_"));
  return blocked ? "blocked" : "review ready";
}

function shotStatus(shots) {
  return shots.some((shot) => String(shot?.quality_status || "").includes("pending")) ? "pending_human_review" : "review ready";
}

function pendingDecisionCount(payload) {
  return arrayValue(payload.decision_items).filter((item) => item?.decision === "pending_human_review").length;
}

function memoryBundleFor(workspace) {
  return Array.isArray(workspace?.memoryBundle) ? workspace.memoryBundle : [];
}

function objectValue(value) {
  return value && typeof value === "object" && !Array.isArray(value) ? value : {};
}

function arrayValue(value) {
  return Array.isArray(value) ? value : [];
}
