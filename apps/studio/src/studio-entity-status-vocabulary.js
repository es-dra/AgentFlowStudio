export const STUDIO_ENTITY_STATUS_VOCABULARY_VERSION = "p0-20260704";

export const STUDIO_STATUS_VOCABULARY = Object.freeze([
  status("queued", "排队中", ["job.progress.mode=queued", "job.status=pending"], "Request is waiting before active work."),
  status("submitted", "已提交", ["job.status=submitted"], "Runtime accepted a request and created a job identity."),
  status("running", "生成中", ["job.status=running", "node.status=generating"], "Work is active or being polled."),
  status("succeeded", "已完成", ["job.status=succeeded", "policyStatus=complete"], "Reviewable output exists; not yet accepted."),
  status("failed", "失败", ["job.status=failed", "node.status=error"], "Requested output did not complete."),
  status("retryable", "可重试", ["derived:shouldRetryFailedItemsOnly"], "A bounded retry is available."),
  status("cancelled", "已停止刷新", ["job.status=cancelled", "job.status=cancelled_local_only"], "Local continuation stopped; provider-side cancellation is not proven."),
  status("blocked", "已阻断", ["job.status=blocked", "safe_manifest.blocks[]"], "A known gate or reason blocks progress."),
  status("needs_attention", "需要检查", ["policyStatus=needs_attention"], "User must resolve or review a condition before the next step."),
  status("partial", "部分完成", ["runtime_recovery.status=partially_complete", "node.status=partial"], "Some output is preserved while some requested items failed or are missing."),
]);

export const STUDIO_ENTITY_VOCABULARY = Object.freeze([
  entity("project_asset", "Project Asset", "项目素材", "A safe project-scoped asset record that can be reviewed, referenced, or reused by Studio.", ["draft", "fixed", "rejected", "retired", "blocked", "needs_attention"], ["reference", "bind", "replace", "reject", "view_evidence", "view_lineage"]),
  entity("reference_input", "Reference Input", "参考输入", "A user-selected or node-derived visual/text reference candidate for a generation request.", ["draft", "bound", "unbound", "blocked", "needs_attention", "rejected"], ["reference", "bind", "unbind", "replace", "view_evidence"]),
  entity("generation_candidate", "Generation Candidate", "生成候选", "A single reviewable output candidate or missing/failed candidate slot.", ["queued", "submitted", "running", "succeeded", "partial", "failed", "retryable", "cancelled", "blocked", "needs_attention", "accepted", "rejected"], ["retry", "accept", "reject", "view_evidence", "view_lineage", "continue_to_video"]),
  entity("keyframe_version", "Keyframe Version", "关键帧版本", "A reviewable keyframe version tied to a node, prompt, references, and safe evidence.", ["draft", "succeeded", "partial", "failed", "retryable", "blocked", "needs_attention", "accepted", "rejected"], ["accept", "reject", "retry", "edit_keyframe", "continue_to_video", "view_evidence", "view_lineage"]),
  entity("video_revision", "Video Revision", "视频修订", "A video attempt or revision tied to a video node and safe evidence.", ["queued", "submitted", "running", "succeeded", "partial", "failed", "retryable", "cancelled", "blocked", "needs_attention", "accepted", "rejected"], ["retry", "accept", "reject", "replace", "view_evidence", "view_lineage"]),
  entity("binding", "Binding", "绑定", "A safe relationship between a node/request and an asset/reference/candidate.", ["bound", "unbound", "replaced", "blocked", "needs_attention"], ["bind", "unbind", "replace", "view_lineage", "view_evidence"]),
  entity("lineage", "Lineage", "来源链路", "A traceable chain of safe refs connecting inputs, assets, candidates, versions, revisions, jobs, and artifacts.", ["available", "partial", "blocked", "needs_attention"], ["view_lineage", "view_evidence", "reference", "replace"]),
]);

export const STUDIO_ACTION_VOCABULARY = Object.freeze([
  action("bind", "绑定", ["project_asset", "reference_input", "binding"]),
  action("unbind", "取消绑定", ["reference_input", "binding"]),
  action("replace", "替换", ["project_asset", "reference_input", "keyframe_version", "video_revision", "binding", "lineage"]),
  action("reference", "用作参考", ["project_asset", "reference_input", "lineage"]),
  action("retry", "重试", ["generation_candidate", "keyframe_version", "video_revision"]),
  action("accept", "采纳", ["generation_candidate", "keyframe_version", "video_revision"]),
  action("reject", "拒绝", ["project_asset", "generation_candidate", "keyframe_version", "video_revision", "reference_input"]),
  action("view_lineage", "查看来源链路", ["project_asset", "reference_input", "generation_candidate", "keyframe_version", "video_revision", "binding", "lineage"]),
  action("view_evidence", "查看证据", ["project_asset", "reference_input", "generation_candidate", "keyframe_version", "video_revision", "binding", "lineage"]),
  action("continue_to_video", "继续生成视频", ["generation_candidate", "keyframe_version"]),
  action("edit_keyframe", "编辑关键帧", ["keyframe_version"]),
]);

export function studioEntityVocabularyEntry(id) {
  return STUDIO_ENTITY_VOCABULARY.find((entry) => entry.id === id) || null;
}

export function studioStatusVocabularyEntry(id) {
  return STUDIO_STATUS_VOCABULARY.find((entry) => entry.id === id) || null;
}

export function studioActionVocabularyEntry(id) {
  return STUDIO_ACTION_VOCABULARY.find((entry) => entry.id === id) || null;
}

function entity(id, canonicalLabel, zhLabel, userMeaning, allowedStates, nextActions) {
  return Object.freeze({ id, canonicalLabel, zhLabel, userMeaning, allowedStates, nextActions });
}

function status(id, zhLabel, existingEquivalents, userMeaning) {
  return Object.freeze({ id, zhLabel, existingEquivalents, userMeaning });
}

function action(id, zhLabel, appliesTo) {
  return Object.freeze({ id, zhLabel, appliesTo });
}
