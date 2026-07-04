import { redactUnsafeText } from "./safe-text-redaction.js";

export function formatRuntimeError(error, fallback = "请求失败") {
  const payload = structuredRuntimeErrorPayload(error);
  if (payload) {
    const code = safeErrorCode(payload.error || payload.detail_code || error?.errorCode);
    const details = payload.details && typeof payload.details === "object" && !Array.isArray(payload.details)
      ? payload.details
      : {};
    const detailText = [
      safeErrorText(payload.message, 240),
      safeErrorText(payload.detail, 240),
      safeErrorText(payload.raw_detail, 240),
      safeObjectSummary(details, 320),
      safeErrorText(error?.message, 240),
    ].filter(Boolean).join("\n");
    const message = promptOptimizerProviderMessage(detailText)
      || messageForCode(code)
      || safeErrorText(payload.message, 220)
      || safeErrorText(payload.detail, 220);
    const reason = firstSafeText(
      payload.reason,
      payload.raw_detail,
      details.reason,
      details.raw_detail,
      details.message,
    );
    const field = validationFieldMessage(details.fields || payload.fields || payload.detail);
    const userAction = safeErrorText(payload.user_action, 220);
    const requestId = safeErrorText(payload.request_id || error?.requestId, 120);
    const stage = safeErrorCode(payload.stage);
    return uniqueLines([
      message || code || fallback,
      reason && reason !== message ? `原因：${reason}` : "",
      field ? `字段：${field}` : "",
      code ? `代码：${code}` : "",
      userAction ? `建议：${userAction}` : "",
      requestId ? `请求编号：${requestId}` : "",
      stage ? `阶段：${stage}` : "",
    ]).join("\n").slice(0, 600);
  }
  const message = safeErrorText(error instanceof Error ? error.message : error, 240) || fallback;
  const promptOptimizerMessage = promptOptimizerProviderMessage(message);
  if (promptOptimizerMessage) return promptOptimizerMessage;
  return message.slice(0, 220);
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
  if (error?.payload && typeof error.payload === "object") {
    const payload = error.payload;
    if (Object.prototype.hasOwnProperty.call(payload, "detail")) {
      const detail = payload.detail;
      if (Array.isArray(detail)) {
        return {
          ...payload,
          error: payload.error || "request_validation_failed",
          message: validationErrorMessage(detail),
          details: {
            ...(payload.details && typeof payload.details === "object" ? payload.details : {}),
            fields: validationFields(detail),
            error_count: detail.length,
          },
        };
      }
      if (detail && typeof detail === "object") {
        return {
          ...payload,
          ...detail,
          details: detail.details && typeof detail.details === "object"
            ? detail.details
            : (payload.details && typeof payload.details === "object" ? payload.details : {}),
        };
      }
      return { ...payload, detail };
    }
    return payload;
  }
  return null;
}

function validationFields(items) {
  if (!Array.isArray(items)) return [];
  return items.slice(0, 8).map((item) => {
    const loc = Array.isArray(item?.loc) ? item.loc.join(".") : item?.field;
    return {
      field: String(loc || ""),
      message: safeErrorText(item?.msg || item?.message, 180),
      type: safeErrorText(item?.type, 120),
    };
  });
}

function validationErrorMessage(items) {
  const field = validationFieldMessage(items);
  return field ? "请求参数校验失败。" : "";
}

function validationFieldMessage(value) {
  const fields = Array.isArray(value) ? value : [];
  if (!fields.length) return "";
  const first = fields[0] || {};
  const field = safeFieldName(Array.isArray(first.loc) ? first.loc.join(".") : (first.field || first.loc));
  const message = safeErrorText(first.message || first.msg, 160);
  const type = safeErrorText(first.type, 120);
  const suffix = fields.length > 1 ? `；共 ${fields.length} 项` : "";
  if (field && message) return `${field}（${message}${type ? ` / ${type}` : ""}${suffix}）`;
  return [field, message || type].filter(Boolean).join("：") + suffix;
}

function firstSafeText(...items) {
  for (const item of items) {
    const text = safeErrorText(item, 220);
    if (text) return text;
  }
  return "";
}

function safeErrorText(value, limit = 220) {
  if (value == null) return "";
  if (Array.isArray(value)) return validationFieldMessage(value) || value.map((item) => safeErrorText(item, 80)).filter(Boolean).join(" ");
  if (typeof value === "object") return safeObjectSummary(value, limit);
  return redactUnsafeText(String(value).replace(/\[object Object\]/g, " "), limit);
}

function safeObjectSummary(value, limit = 220) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return "";
  const preferred = firstSafeText(
    value.reason,
    value.raw_detail,
    value.message,
    value.detail,
    value.error_description,
  );
  if (preferred) return preferred.slice(0, limit);
  const field = validationFieldMessage(value.fields);
  if (field) return field.slice(0, limit);
  const pairs = [];
  for (const [key, item] of Object.entries(value)) {
    if (pairs.length >= 3) break;
    if (/token|secret|authorization|cookie|base64|bytes|raw|provider/i.test(key)) continue;
    if (item && typeof item === "object") continue;
    const text = safeErrorText(item, 80);
    if (text) pairs.push(`${safeErrorCode(key)}=${text}`);
  }
  return pairs.join(" ").slice(0, limit);
}

function safeErrorCode(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_.-]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 80);
}

function safeFieldName(value) {
  const raw = String(value || "").trim();
  if (!raw) return "";
  const parts = raw.split(".").filter((part) => part && part !== "body");
  const labels = parts.map((part) => {
    const normalized = part.toLowerCase().replace(/[^a-z0-9_.-]+/g, "_");
    const known = {
      data_base64: "上传图片内容",
      mime_type: "图片类型",
      filename: "文件名",
      reference_target: "参考目标",
      role: "绑定角色",
      node_id: "节点",
    };
    return known[normalized] || safeErrorCode(normalized);
  }).filter(Boolean);
  return labels.join(".").slice(0, 120);
}

function uniqueLines(lines) {
  const seen = new Set();
  const result = [];
  for (const line of lines) {
    const text = safeErrorText(line, 600);
    if (!text || seen.has(text)) continue;
    seen.add(text);
    result.push(text);
  }
  return result;
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
