export function formatRuntimeError(error, fallback = "请求失败") {
  const payload = structuredRuntimeErrorPayload(error);
  if (payload) {
    const code = String(payload.error || error?.errorCode || "").trim();
    const detailText = [
      payload.message,
      payload.detail,
      payload.raw_detail,
      payload.details,
      error?.message,
    ].map((item) => String(item || "")).join("\n");
    const message = promptOptimizerProviderMessage(detailText)
      || messageForCode(code)
      || String(payload.message || "").trim();
    const userAction = String(payload.user_action || "").trim();
    const requestId = String(payload.request_id || error?.requestId || "").trim();
    const stage = String(payload.stage || "").trim();
    return [
      message || code || fallback,
      userAction ? `建议：${userAction}` : "",
      requestId ? `请求编号：${requestId}` : "",
      stage ? `阶段：${stage}` : "",
    ].filter(Boolean).join("\n").slice(0, 600);
  }
  const message = error instanceof Error ? error.message : String(error || fallback);
  const promptOptimizerMessage = promptOptimizerProviderMessage(message);
  if (promptOptimizerMessage) return promptOptimizerMessage;
  return message.replace(/Bearer\s+\S+/gi, "Bearer <redacted>").slice(0, 220);
}

export function formatStructuredRuntimeError(error) {
  const payload = structuredRuntimeErrorPayload(error);
  if (!payload) return "";
  return formatRuntimeError(error, "");
}

export function messageForCode(code) {
  const messages = {
    request_validation_failed: "请求参数校验失败。",
    bad_request: "请求内容不正确。",
    invalid_request: "请求参数无效。",
    authentication_required: "需要登录后才能继续操作。",
    permission_denied: "当前账号没有权限执行该操作。",
    project_access_denied: "当前账号没有访问该项目的权限。",
    not_found: "请求的资源不存在。",
    conflict: "当前操作与最新状态冲突。",
    rate_limited: "请求过于频繁。",
    runtime_error: "运行服务内部错误。",
    auth_rate_limited: "登录或注册尝试过于频繁。",
    email_already_registered: "该邮箱已经注册。",
    invalid_email_or_password: "邮箱或密码不正确。",
    invalid_invite_code: "邀请码无效或已被使用。",
    studio_state_conflict: "画布状态版本冲突。",
    image_asset_not_found: "图片素材不存在或已失效。",
    visual_asset_not_found: "固定视觉资产不存在或已失效。",
    candidate_not_found: "生成候选结果不存在或已失效。",
    job_not_found: "生成任务不存在或已失效。",
    artifact_not_found: "产物记录不存在或已失效。",
    invalid_image_asset: "图片素材上传失败。",
    invalid_keyframe_generation: "关键帧生成请求参数无效。",
    invalid_asset_card_draft: "视觉素材卡草稿生成请求无效。",
    invalid_video_asset: "视频资产请求无效。",
    invalid_visual_asset: "固定视觉资产请求无效。",
    invalid_prompt_optimization: "提示词优化请求失败。",
    invalid_storyboard_breakdown: "分镜拆解请求失败。",
    invalid_shot_asset_plan: "单镜头资产规划请求失败。",
    invalid_sprite_chat: "Sprite 助手请求失败。",
    invalid_sprite_memory: "Sprite 记忆请求失败。",
    invalid_generation_comparison: "生成结果对比请求失败。",
    invalid_project_manifest: "项目清单无效。",
    invalid_artifact: "产物记录无效。",
    video_daily_quota_exceeded: "今日该项目视频生成次数已达到限制。",
    first_frame_asset_not_found: "首帧图片不存在或已失效。",
    last_frame_asset_not_found: "尾帧图片不存在或已失效。",
    invalid_candidate_count: "视频生成当前只支持 1 个候选。",
    unsupported_duration: "当前视频模型不支持该视频时长。",
    unsupported_resolution: "当前视频模型不支持该分辨率。",
    unsupported_aspect_ratio: "当前视频模型不支持该画幅比例。",
    provider_gate_closed: "生成服务未开启。",
    stale_preflight: "生成前检查结果已过期。",
    invalid_video_generation: "视频生成请求参数无效。",
  };
  return messages[String(code || "").trim()] || "";
}

function structuredRuntimeErrorPayload(error) {
  if (error?.payload?.detail && typeof error.payload.detail === "object") return error.payload.detail;
  if (error?.payload && typeof error.payload === "object") return error.payload;
  return null;
}

function promptOptimizerProviderMessage(value) {
  const text = String(value || "").toLowerCase();
  if (
    text.includes("provider returned infrastructure error")
    || text.includes("remote llm prompt optimization unavailable")
    || text.includes("unable to read `request.json`")
    || text.includes("unable to read request.json")
    || text.includes("unable to read `prompt.md`")
    || text.includes("unable to read prompt.md")
    || text.includes("bwrap:")
    || text.includes("failed rtm_newaddr")
    || text.includes("local command sandbox fails")
  ) {
    return "提示词优化失败，请检查 LLM provider 配置或稍后重试。";
  }
  return "";
}
