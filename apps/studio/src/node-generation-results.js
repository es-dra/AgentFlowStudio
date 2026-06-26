export function videoRevisionResultText(response) {
  const status = response?.job?.status || "blocked";
  const manifest = response?.safe_manifest || {};
  const block = manifest.blocks?.[0] || {};
  if (status === "succeeded") return "Experimental video revision completed through Runtime safe preview.";
  return [
    "Experimental video revision did not start.",
    `Status: ${status}`,
    `Reason: ${block.reason || "video revision provider path is not enabled"}`,
    "Goal: change requested effects while keeping unrelated aspects as stable as possible.",
  ].join("\n");
}

export function videoResultText(response) {
  const status = response?.job?.status || "blocked";
  const timing = videoTimingLine(response);
  if (status === "succeeded") return ["视频已完成，预览已通过安全预览地址加载。", timing].filter(Boolean).join("\n");
  if (status === "submitted") return `视频已提交，可继续刷新进度。\n任务编号：${response?.job?.job_id || "unknown"}${timing ? `\n${timing}` : ""}\n本地取消只会停止页面继续刷新，不代表生成平台侧任务已经取消，也不保证停止计费。`;
  if (status === "running") return `视频仍在生成中。\n任务编号：${response?.job?.job_id || "unknown"}${timing ? `\n${timing}` : ""}\n本地取消只会停止页面继续刷新，不代表生成平台侧任务已经取消，也不保证停止计费。`;
  if (status === "cancelled_local_only") {
    return `本地已停止继续刷新。\n任务编号：${response?.job?.job_id || "unknown"}\n这只更新页面状态，不代表生成平台侧任务已经取消，也不保证停止计费。`;
  }
  const reason = response?.safe_manifest?.blocks?.[0]?.reason || "视频生成服务未就绪";
  return `视频生成未开始或未完成。\n状态: ${status}\n原因: ${reason}`;
}

function videoTimingLine(response) {
  const progress = response?.job?.progress || {};
  const parts = [];
  if (progress.elapsed_sec != null) parts.push(`总耗时 ${formatSeconds(progress.elapsed_sec)}`);
  if (progress.queued_sec != null) parts.push(`排队 ${formatSeconds(progress.queued_sec)}`);
  if (progress.running_sec != null) parts.push(`生成 ${formatSeconds(progress.running_sec)}`);
  return parts.length ? `耗时：${parts.join(" / ")}` : "";
}

function formatSeconds(value) {
  const total = Math.max(0, Math.round(Number(value) || 0));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  if (minutes <= 0) return `${seconds}秒`;
  if (seconds === 0) return `${minutes}分`;
  return `${minutes}分${seconds}秒`;
}

export function keyframeResultText(response, request, succeeded, options = {}) {
  const kind = generationKind(request, options);
  const label = kind === "asset" ? "资产图" : "关键帧";
  const jobId = response?.job?.job_id || "not_available";
  const status = response?.job?.status || "blocked";
  const outputCount = response?.safe_manifest?.output_count ?? 0;
  if (isKeyframeInProgress(response)) {
    return [
      `${label}生成中，预览完成后会自动更新到节点。`,
      `任务编号：${jobId}`,
    ].join("\n");
  }
  if (!succeeded) {
    const reason = response?.safe_manifest?.blocks?.[0]?.reason || "image generation service is not ready";
    return [
      `${label}生成未完成，本次没有可用预览。`,
      `状态: ${status}`,
      `原因: ${reason}`,
    ].join("\n");
  }
  return [
    `${label}已生成`,
    `任务编号：${jobId}`,
    `请求比例: ${request.aspect_ratio}`,
    `候选数量: ${outputCount}`,
    response?.reusable_image_assets?.[0]?.asset_id ? `${kind === "asset" ? "资产素材" : "参考素材"}：${response.reusable_image_assets[0].asset_id}` : null,
    response?.candidate_previews?.[0]?.preview_url ? "预览已从安全预览地址加载。" : "未返回预览地址。",
  ].filter(Boolean).join("\n");
}

export function isKeyframeInProgress(response) {
  return ["submitted", "running", "pending"].includes(String(response?.job?.status || ""));
}

function generationKind(request, options) {
  if (options.kind) return options.kind;
  if (request?.node_parameters?.node_role === "asset_card_draft") return "asset";
  return "keyframe";
}

export function parseDuration(value) {
  const match = String(value || "5").match(/\d+/);
  return match ? Number(match[0]) : 5;
}
