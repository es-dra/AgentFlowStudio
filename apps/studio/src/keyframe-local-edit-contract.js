import { keyframeFirstFrameAsset } from "./keyframe-video-continuation.js";

export const KEYFRAME_LOCAL_EDIT_REQUEST_SCHEMA = "afs_keyframe_local_edit_request.v0.1";
export const KEYFRAME_LOCAL_EDIT_PREFLIGHT_SCHEMA = "afs_keyframe_local_edit_preflight.v0.1";

const LOCAL_EDIT_EXECUTION_BLOCKED = {
  status: "contract_ready_execution_blocked",
  required_capability: "image_edit_or_masked_local_transform",
  reason: "first_slice_records_request_contract_only",
  user_message: "已记录局部编辑需求草稿；当前不会执行本地图像变换或调用 provider。",
};

const LOCAL_EDIT_NON_CLAIMS = [
  "no_provider_call",
  "no_generated_media",
  "no_pixel_transformation",
  "not_provider_or_human_acceptance",
  "not_full_frame_fallback",
];

const DEFAULT_PRESERVE_LOCKS = [
  "character_identity",
  "scene_layout",
  "camera_angle",
  "unmentioned_details",
];

const EDIT_SCOPE_KINDS = new Set(["mask_asset", "bbox", "polygon", "semantic_region"]);

export function createKeyframeLocalEditDraft(store, keyframeNode, options = {}) {
  const state = store.get();
  const source = state.nodes?.[keyframeNode?.id] || keyframeNode;
  if (!source) return null;
  const draft = buildKeyframeLocalEditDraft(state, source, options);
  store.set((s) => {
    const node = s.nodes?.[source.id];
    if (!node) return;
    node.params.keyframeLocalEditDraft = draft;
    node.params.local_edit_availability = draft.availability;
    node.result = keyframeLocalEditDraftResultText(draft);
  });
  return draft;
}

export function buildKeyframeLocalEditDraft(state, node, options = {}) {
  const generatedAt = String(options.generatedAt || new Date().toISOString());
  const parentLineage = keyframeLocalEditParentLineage(state, node);
  const request = {
    schema_version: KEYFRAME_LOCAL_EDIT_REQUEST_SCHEMA,
    request_id: String(options.requestId || localEditRequestId(node, parentLineage, generatedAt)),
    target_node_id: String(node?.id || ""),
    parent_lineage: parentLineage,
    edit_intent: cleanPublicText(options.editIntent || node?.params?.keyframeLocalEditDraft?.request?.edit_intent || node?.prompt || ""),
    edit_scope: normalizeEditScope(options.editScope || node?.params?.keyframeLocalEditDraft?.request?.edit_scope),
    preserve_locks: normalizeStringList(options.preserveLocks || node?.params?.keyframeLocalEditDraft?.request?.preserve_locks, DEFAULT_PRESERVE_LOCKS),
    negative_locks: normalizeStringList(options.negativeLocks || node?.params?.keyframeLocalEditDraft?.request?.negative_locks),
    fallback_policy: {
      allow_full_frame_fallback: false,
      fallback_truth_label: "not_allowed_in_first_slice",
      user_confirmation_required: true,
    },
    provider_capability_mode: "no_provider_execution",
    created_at: generatedAt,
    updated_at: generatedAt,
  };
  const preflight = keyframeLocalEditPreflight(request);
  return {
    schema_version: "afs_keyframe_local_edit_draft.v0.1",
    request,
    preflight,
    availability: availabilityFromPreflight(preflight),
  };
}

export function keyframeLocalEditPreflight(request) {
  const blockers = [];
  if (!request?.parent_lineage?.parent_keyframe_job_id) {
    blockers.push(blocker("missing_parent_keyframe_job", "缺少父关键帧任务，不能建立可追溯局部编辑草稿。"));
  }
  if (!request?.parent_lineage?.parent_image_asset_id) {
    blockers.push(blocker("missing_parent_image_asset", "缺少父关键帧图像资产，不能建立可执行局部编辑输入。"));
  }
  if (!request?.edit_intent) {
    blockers.push(blocker("missing_edit_intent", "缺少局部编辑意图。"));
  }
  if (!request?.edit_scope?.target_description) {
    blockers.push(blocker("missing_edit_scope", "缺少局部编辑区域描述。"));
  }
  const contractReady = blockers.length === 0;
  const tokenPayload = {
    schema_version: KEYFRAME_LOCAL_EDIT_PREFLIGHT_SCHEMA,
    target_node_id: request?.target_node_id || "",
    parent_lineage: request?.parent_lineage || {},
    edit_intent: request?.edit_intent || "",
    edit_scope: request?.edit_scope || {},
    preserve_locks: request?.preserve_locks || [],
    negative_locks: request?.negative_locks || [],
    fallback_policy: request?.fallback_policy || {},
  };
  return {
    schema_version: KEYFRAME_LOCAL_EDIT_PREFLIGHT_SCHEMA,
    request_id: request?.request_id || "",
    contract_status: contractReady ? "ready_no_provider_execution" : "draft_needs_input",
    execution_status: contractReady ? "blocked_no_local_transform" : "blocked_missing_required_input",
    provider_calls_started: false,
    local_transformation_started: false,
    generated_media_created: false,
    fallback_full_frame_edit: false,
    local_edit_truth_label: "request_contract_only",
    blocking_capability: "image_edit_or_masked_local_transform",
    blockers: contractReady
      ? [blocker("execution_not_implemented", "局部图像变换执行未实现；本切片只记录可审计请求合同。")]
      : blockers,
    allowed_next_actions: contractReady
      ? ["refine_edit_scope", "route_to_runtime_or_provider_implementation_lane"]
      : ["add_parent_image_asset", "add_edit_intent", "refine_edit_scope"],
    preflight_token: stableHash(tokenPayload),
    non_claims: [...LOCAL_EDIT_NON_CLAIMS],
  };
}

export function keyframeLocalEditDraftResultText(draft) {
  const parent = draft?.request?.parent_lineage || {};
  const preflight = draft?.preflight || {};
  const firstBlocker = preflight.blockers?.[0]?.reason || LOCAL_EDIT_EXECUTION_BLOCKED.user_message;
  return [
    "局部编辑需求草稿已创建。",
    `父关键帧任务：${parent.parent_keyframe_job_id || "缺失"}`,
    `父图像资产：${parent.parent_image_asset_id || "缺失"}`,
    `合同状态：${preflight.contract_status || "unknown"}；执行状态：${preflight.execution_status || "unknown"}`,
    firstBlocker,
    "不会生成媒体、不会调用 provider、不会把整图重生成标记为局部编辑。",
  ].join("\n");
}

export function keyframeLocalEditParentLineage(state, node) {
  const imageAsset = keyframeFirstFrameAsset(state || {}, node);
  return {
    immutable_parent: true,
    parent_node_id: String(node?.id || ""),
    parent_keyframe_job_id: String(node?.params?.lastKeyframeCompletedJobId || node?.params?.lastKeyframeJobId || imageAsset?.source_job_id || ""),
    parent_image_asset_id: String(imageAsset?.asset_id || ""),
    parent_candidate_id: String(imageAsset?.source_candidate_id || imageAsset?.candidate_id || ""),
    parent_preview_url_present: Boolean(node?.previewUrl || imageAsset?.preview_url),
  };
}

function availabilityFromPreflight(preflight) {
  const blocked = preflight.blockers?.[0] || {};
  return {
    ...LOCAL_EDIT_EXECUTION_BLOCKED,
    status: preflight.contract_status === "ready_no_provider_execution"
      ? "contract_ready_execution_blocked"
      : "draft_needs_input",
    reason: blocked.code || LOCAL_EDIT_EXECUTION_BLOCKED.reason,
    user_message: blocked.reason || LOCAL_EDIT_EXECUTION_BLOCKED.user_message,
  };
}

function normalizeEditScope(scope) {
  const raw = scope && typeof scope === "object" ? scope : {};
  const kind = EDIT_SCOPE_KINDS.has(String(raw.kind || "")) ? String(raw.kind) : "semantic_region";
  return {
    kind,
    target_description: cleanPublicText(raw.target_description || raw.description || "请描述要修改的局部区域。", 240),
    mask_asset_id: cleanId(raw.mask_asset_id),
    bbox: normalizeBbox(raw.bbox),
    polygon: Array.isArray(raw.polygon) ? raw.polygon.slice(0, 16) : [],
  };
}

function normalizeBbox(value) {
  if (!value || typeof value !== "object") return null;
  const bbox = {};
  for (const key of ["x", "y", "width", "height"]) {
    const number = Number(value[key]);
    if (!Number.isFinite(number)) return null;
    bbox[key] = Math.max(0, Math.min(1, number));
  }
  return bbox;
}

function normalizeStringList(value, fallback = []) {
  const raw = Array.isArray(value) ? value : fallback;
  return raw.map((item) => cleanPublicText(item, 120)).filter(Boolean).slice(0, 12);
}

function blocker(code, reason) {
  return { code, reason, provider_calls_started: false, generated_media_created: false };
}

function localEditRequestId(node, parentLineage, generatedAt) {
  return `kle_${stableHash({
    node_id: node?.id || "",
    parent_keyframe_job_id: parentLineage.parent_keyframe_job_id || "",
    parent_image_asset_id: parentLineage.parent_image_asset_id || "",
    generated_at: generatedAt,
  }).slice(0, 12)}`;
}

function cleanId(value) {
  return String(value || "").replace(/[^a-zA-Z0-9_.:-]/g, "").slice(0, 120);
}

function cleanPublicText(value, limit = 500) {
  return String(value || "")
    .replace(/Bearer\s+\S+/gi, "Bearer <redacted>")
    .replace(/\b(?:token|secret|credential)\s*[:=]\s*\S+/gi, "<redacted>")
    .replace(/\bdata:[^\s"'<>]+/gi, "<media-bytes-redacted>")
    .replace(/[A-Za-z]:\\[^\s"'<>]+/g, "<local-path-redacted>")
    .replace(/\/(?:home|Users|mnt|var|tmp|opt)\/[^\s"'<>]+/g, "<local-path-redacted>")
    .replace(/https?:\/\/[^\s"'<>]+/g, "<url-redacted>")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, limit);
}

function stableHash(value) {
  const text = stableStringify(value);
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function stableStringify(value) {
  if (Array.isArray(value)) return `[${value.map((item) => stableStringify(item)).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${stableStringify(value[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}
