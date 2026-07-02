import { formatStructuredRuntimeError } from "./runtime-error-utils.js";
import { safePublicText } from "./generation-status-policy.js";

export function safeError(error) {
  const structured = formatStructuredRuntimeError(error);
  if (structured) return structured;
  const message = error instanceof Error ? error.message : String(error || "unknown error");
  const clean = message.replace(/Bearer\s+\S+/gi, "Bearer <redacted>");
  if (/Gateway timeout|504|network connection interrupted|Failed to fetch/i.test(clean)) {
    return "生成请求连接中断，正在尝试从已落盘素材找回结果。";
  }
  if (/AFS_ALLOW_REMOTE_|provider service not found|provider gate is closed|Remote .* calls are disabled/i.test(clean)) {
    return "生成服务未就绪，请检查本机配置与创作服务启动状态后重试。";
  }
  return clean.slice(0, 160);
}

export function setNodeError(store, nodeId, message) {
  store.set((s) => {
    const n = s.nodes[nodeId];
    if (!n) return;
    if (!n.params || typeof n.params !== "object") n.params = {};
    n.status = "error";
    n.result = message;
    n.params.generationPolicyStatus = "failed";
    n.params.generationBlockedReason = safePublicText(message);
    n.params.generationNextAction = "Resolve the blocked reason, then retry failed items only.";
  });
}
