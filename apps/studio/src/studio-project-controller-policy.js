import { createRuntimeClient } from "./runtime-client.js";
import { formatRuntimeError } from "./runtime-error-utils.js";

const EMPTY_PROJECT_ID = "studio-empty";
const READ_ONLY_PROJECTION_PROJECT_TYPE = "m6_2_paid_image_video_asset_reuse";

export function emptyProjectRuntimeClient() {
  const runtime = createRuntimeClient(EMPTY_PROJECT_ID);
  return {
    ...runtime,
    loadStudioState: null,
    saveStudioState: null,
  };
}

export function isReadOnlyProjectionProject(projectId, projectSummaries = []) {
  const summary = projectSummaries.find((item) => item?.project_id === projectId) || {};
  const projectType = String(summary.project_type || "");
  return projectType === READ_ONLY_PROJECTION_PROJECT_TYPE;
}

export function safeProjectRuntimeError(error) {
  const formatted = formatRuntimeError(error, "未知错误");
  if (/network connection interrupted|Failed to fetch|Gateway timeout/i.test(formatted)) {
    return "Runtime 连接短暂中断，请刷新项目列表后再重试。";
  }
  return formatted;
}
